"""AWS S3 storage monitoring for RS Systems."""

import asyncio
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

from ..config import settings
from ..models.django_models import HealthCheckResult

logger = logging.getLogger(__name__)


class StorageMonitor:
    """Monitor AWS S3 storage usage and performance."""

    def __init__(self):
        self.aws_config = settings.aws
        self.thresholds = settings.thresholds
        self.s3_client = None
        self._initialize_s3_client()

    def _initialize_s3_client(self):
        """Initialize S3 client with configured credentials."""
        try:
            if self.aws_config.access_key_id and self.aws_config.secret_access_key:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=self.aws_config.access_key_id,
                    aws_secret_access_key=self.aws_config.secret_access_key,
                    region_name=self.aws_config.region
                )
                logger.info("S3 client initialized successfully")
            else:
                logger.warning("AWS credentials not configured for S3 monitoring")
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")

    async def get_bucket_size(self) -> Dict[str, Any]:
        """Get total size and object count for the S3 bucket."""
        if not self.s3_client:
            return {"error": "S3 client not initialized"}

        bucket_stats = {
            "total_size_bytes": 0,
            "total_size_gb": 0,
            "object_count": 0,
            "by_prefix": {}
        }

        try:
            # Get bucket objects
            paginator = self.s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(Bucket=self.aws_config.s3_bucket_name)

            prefixes = {
                "damage-photos/before/": {"size": 0, "count": 0},
                "damage-photos/after/": {"size": 0, "count": 0},
                "other/": {"size": 0, "count": 0}
            }

            for page in page_iterator:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        bucket_stats["total_size_bytes"] += obj['Size']
                        bucket_stats["object_count"] += 1

                        # Categorize by prefix
                        key = obj['Key']
                        categorized = False
                        for prefix in prefixes:
                            if key.startswith(prefix):
                                prefixes[prefix]["size"] += obj['Size']
                                prefixes[prefix]["count"] += 1
                                categorized = True
                                break

                        if not categorized:
                            prefixes["other/"]["size"] += obj['Size']
                            prefixes["other/"]["count"] += 1

            bucket_stats["total_size_gb"] = round(bucket_stats["total_size_bytes"] / (1024**3), 2)

            # Convert prefix sizes to GB
            for prefix, data in prefixes.items():
                bucket_stats["by_prefix"][prefix] = {
                    "size_gb": round(data["size"] / (1024**3), 2),
                    "object_count": data["count"]
                }

        except ClientError as e:
            logger.error(f"Failed to get bucket size: {e}")
            bucket_stats["error"] = str(e)
        except Exception as e:
            logger.error(f"Unexpected error getting bucket size: {e}")
            bucket_stats["error"] = str(e)

        return bucket_stats

    async def get_large_files(self, size_threshold_mb: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get list of files exceeding size threshold."""
        if not self.s3_client:
            return []

        threshold = size_threshold_mb or self.thresholds.photo_size_mb
        threshold_bytes = threshold * 1024 * 1024
        large_files = []

        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(Bucket=self.aws_config.s3_bucket_name)

            for page in page_iterator:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        if obj['Size'] > threshold_bytes:
                            large_files.append({
                                "key": obj['Key'],
                                "size_mb": round(obj['Size'] / (1024 * 1024), 2),
                                "last_modified": obj['LastModified'].isoformat(),
                                "storage_class": obj.get('StorageClass', 'STANDARD')
                            })

            # Sort by size descending
            large_files.sort(key=lambda x: x['size_mb'], reverse=True)

            # Limit to top 50
            large_files = large_files[:50]

        except Exception as e:
            logger.error(f"Failed to get large files: {e}")

        return large_files

    async def estimate_costs(self, size_gb: float) -> Dict[str, float]:
        """Estimate monthly S3 storage costs."""
        # AWS S3 Standard pricing (approximate, varies by region)
        pricing = {
            "storage_per_gb": 0.023,  # First 50 TB / month
            "requests_per_1000": {
                "PUT": 0.005,
                "GET": 0.0004
            },
            "data_transfer_per_gb": 0.09  # Internet data transfer out
        }

        # Estimate based on typical usage patterns for RS Systems
        estimated_requests = {
            "PUT": 1000,  # New photos uploaded
            "GET": 5000   # Photos viewed
        }

        costs = {
            "storage": round(size_gb * pricing["storage_per_gb"], 2),
            "put_requests": round(
                (estimated_requests["PUT"] / 1000) * pricing["requests_per_1000"]["PUT"], 2
            ),
            "get_requests": round(
                (estimated_requests["GET"] / 1000) * pricing["requests_per_1000"]["GET"], 2
            ),
            "data_transfer": round(size_gb * 0.1 * pricing["data_transfer_per_gb"], 2)  # Assume 10% transfer
        }

        costs["total_estimated"] = round(sum(costs.values()), 2)

        return costs

    async def get_access_patterns(self) -> Dict[str, Any]:
        """Analyze S3 access patterns (requires CloudWatch integration)."""
        # This would typically integrate with CloudWatch for detailed metrics
        # For now, returning placeholder data structure
        return {
            "daily_uploads": 0,
            "daily_downloads": 0,
            "peak_hours": [],
            "most_accessed_prefixes": [],
            "note": "CloudWatch integration required for detailed metrics"
        }

    async def check_bucket_configuration(self) -> Dict[str, Any]:
        """Check S3 bucket configuration for best practices."""
        if not self.s3_client:
            return {"error": "S3 client not initialized"}

        config = {
            "versioning": False,
            "encryption": False,
            "lifecycle_rules": 0,
            "public_access_blocked": False,
            "logging_enabled": False
        }

        try:
            # Check versioning
            try:
                versioning = self.s3_client.get_bucket_versioning(Bucket=self.aws_config.s3_bucket_name)
                config["versioning"] = versioning.get('Status') == 'Enabled'
            except:
                pass

            # Check encryption
            try:
                encryption = self.s3_client.get_bucket_encryption(Bucket=self.aws_config.s3_bucket_name)
                config["encryption"] = bool(encryption.get('ServerSideEncryptionConfiguration'))
            except:
                pass

            # Check lifecycle rules
            try:
                lifecycle = self.s3_client.get_bucket_lifecycle_configuration(Bucket=self.aws_config.s3_bucket_name)
                config["lifecycle_rules"] = len(lifecycle.get('Rules', []))
            except:
                pass

            # Check public access block
            try:
                public_block = self.s3_client.get_public_access_block(Bucket=self.aws_config.s3_bucket_name)
                config["public_access_blocked"] = all([
                    public_block['PublicAccessBlockConfiguration'].get('BlockPublicAcls', False),
                    public_block['PublicAccessBlockConfiguration'].get('BlockPublicPolicy', False)
                ])
            except:
                pass

            # Check logging
            try:
                logging_config = self.s3_client.get_bucket_logging(Bucket=self.aws_config.s3_bucket_name)
                config["logging_enabled"] = 'LoggingEnabled' in logging_config
            except:
                pass

        except Exception as e:
            logger.error(f"Failed to check bucket configuration: {e}")
            config["error"] = str(e)

        return config

    async def check_health(self) -> HealthCheckResult:
        """Check S3 storage health."""
        if not self.s3_client:
            return HealthCheckResult(
                component="storage",
                status="unhealthy",
                message="S3 client not initialized - check AWS credentials"
            )

        try:
            # Try to head the bucket to check connectivity
            self.s3_client.head_bucket(Bucket=self.aws_config.s3_bucket_name)

            return HealthCheckResult(
                component="storage",
                status="healthy",
                message=f"S3 bucket {self.aws_config.s3_bucket_name} is accessible",
                details={
                    "bucket_name": self.aws_config.s3_bucket_name,
                    "region": self.aws_config.region
                }
            )
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                status = "unhealthy"
                message = f"S3 bucket {self.aws_config.s3_bucket_name} not found"
            elif error_code == '403':
                status = "unhealthy"
                message = f"Access denied to S3 bucket {self.aws_config.s3_bucket_name}"
            else:
                status = "unhealthy"
                message = f"S3 health check failed: {error_code}"

            return HealthCheckResult(
                component="storage",
                status=status,
                message=message
            )
        except Exception as e:
            return HealthCheckResult(
                component="storage",
                status="unhealthy",
                message=f"S3 health check failed: {str(e)}"
            )

    def check_thresholds(
        self,
        bucket_size: Dict[str, Any],
        large_files: List[Dict[str, Any]],
        costs: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Check if storage metrics exceed thresholds."""
        issues = []

        # Check total storage size
        if bucket_size.get("total_size_gb", 0) > self.thresholds.s3_storage_gb:
            issues.append({
                "type": "high_storage_usage",
                "severity": "warning",
                "message": f"S3 storage ({bucket_size['total_size_gb']}GB) exceeds threshold ({self.thresholds.s3_storage_gb}GB)",
                "value": bucket_size["total_size_gb"],
                "threshold": self.thresholds.s3_storage_gb
            })

        # Check for large files
        if large_files:
            issues.append({
                "type": "large_files_detected",
                "severity": "info",
                "message": f"Found {len(large_files)} files exceeding {self.thresholds.photo_size_mb}MB",
                "count": len(large_files),
                "largest_file": large_files[0] if large_files else None
            })

        # Check estimated costs
        if costs.get("total_estimated", 0) > self.thresholds.s3_cost_usd:
            issues.append({
                "type": "high_storage_cost",
                "severity": "warning",
                "message": f"Estimated S3 cost (${costs['total_estimated']}) exceeds threshold (${self.thresholds.s3_cost_usd})",
                "value": costs["total_estimated"],
                "threshold": self.thresholds.s3_cost_usd
            })

        return issues

    async def monitor(self) -> Dict[str, Any]:
        """Perform comprehensive S3 storage monitoring."""
        if not self.s3_client:
            return {
                "error": "S3 monitoring disabled - AWS credentials not configured",
                "timestamp": datetime.now().isoformat()
            }

        try:
            # Run all monitoring tasks
            tasks = [
                self.get_bucket_size(),
                self.get_large_files(),
                self.check_bucket_configuration(),
                self.check_health()
            ]

            bucket_size, large_files, bucket_config, health = await asyncio.gather(*tasks)

            # Estimate costs
            costs = await self.estimate_costs(bucket_size.get("total_size_gb", 0))

            # Get access patterns (if available)
            access_patterns = await self.get_access_patterns()

            # Check thresholds
            issues = self.check_thresholds(bucket_size, large_files, costs)

            return {
                "health": health.dict(),
                "bucket_size": bucket_size,
                "large_files": large_files[:10],  # Top 10 largest files
                "bucket_configuration": bucket_config,
                "estimated_costs": costs,
                "access_patterns": access_patterns,
                "issues": issues,
                "has_issues": len(issues) > 0,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"S3 monitoring failed: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }