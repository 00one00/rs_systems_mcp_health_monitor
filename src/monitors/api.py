"""API performance monitoring for RS Systems endpoints."""

import asyncio
import aiohttp
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
from collections import deque, defaultdict

from ..config import settings
from ..models.django_models import HealthCheckResult

logger = logging.getLogger(__name__)


class APIMonitor:
    """Monitor API endpoint performance and health."""

    def __init__(self):
        self.thresholds = settings.thresholds
        self.base_url = "http://localhost:8000"  # Default, can be overridden

        # Define RS Systems API endpoints to monitor
        self.endpoints = [
            {
                "path": "/api/repairs/",
                "method": "GET",
                "name": "Repairs List",
                "portal": "technician"
            },
            {
                "path": "/api/customers/",
                "method": "GET",
                "name": "Customers List",
                "portal": "customer"
            },
            {
                "path": "/referrals/api/rewards/",
                "method": "GET",
                "name": "Rewards API",
                "portal": "rewards"
            },
            {
                "path": "/api/technicians/",
                "method": "GET",
                "name": "Technicians List",
                "portal": "technician"
            },
            {
                "path": "/api/swagger/",
                "method": "GET",
                "name": "API Documentation",
                "portal": "all"
            }
        ]

        # Metrics storage (in-memory for now)
        self.response_times = defaultdict(lambda: deque(maxlen=1000))
        self.error_counts = defaultdict(int)
        self.request_counts = defaultdict(int)
        self.last_check = {}

    async def check_endpoint(self, endpoint: Dict[str, str]) -> Dict[str, Any]:
        """Check a single API endpoint."""
        url = f"{self.base_url}{endpoint['path']}"
        start_time = time.time()

        result = {
            "endpoint": endpoint["path"],
            "name": endpoint["name"],
            "portal": endpoint["portal"],
            "method": endpoint["method"],
            "timestamp": datetime.now().isoformat()
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=endpoint["method"],
                    url=url,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    response_time = (time.time() - start_time) * 1000

                    result.update({
                        "status_code": response.status,
                        "response_time_ms": round(response_time, 2),
                        "success": 200 <= response.status < 400,
                        "error": None
                    })

                    # Store metrics
                    self.response_times[endpoint["path"]].append(response_time)
                    self.request_counts[endpoint["path"]] += 1

                    if response.status >= 400:
                        self.error_counts[endpoint["path"]] += 1
                        result["error"] = f"HTTP {response.status}"

        except asyncio.TimeoutError:
            result.update({
                "status_code": None,
                "response_time_ms": None,
                "success": False,
                "error": "Timeout"
            })
            self.error_counts[endpoint["path"]] += 1

        except Exception as e:
            result.update({
                "status_code": None,
                "response_time_ms": None,
                "success": False,
                "error": str(e)
            })
            self.error_counts[endpoint["path"]] += 1

        self.last_check[endpoint["path"]] = datetime.now()
        return result

    async def check_all_endpoints(self) -> List[Dict[str, Any]]:
        """Check all configured endpoints concurrently."""
        tasks = [self.check_endpoint(endpoint) for endpoint in self.endpoints]
        results = await asyncio.gather(*tasks)
        return results

    def calculate_metrics(self) -> Dict[str, Any]:
        """Calculate aggregate API metrics."""
        metrics = {
            "endpoints": {},
            "summary": {
                "total_requests": 0,
                "total_errors": 0,
                "average_response_time_ms": 0,
                "error_rate_pct": 0
            }
        }

        total_response_times = []

        for path in self.response_times:
            times = list(self.response_times[path])
            if times:
                avg_time = sum(times) / len(times)
                total_response_times.extend(times)
            else:
                avg_time = 0

            requests = self.request_counts[path]
            errors = self.error_counts[path]
            error_rate = (errors / requests * 100) if requests > 0 else 0

            metrics["endpoints"][path] = {
                "request_count": requests,
                "error_count": errors,
                "error_rate_pct": round(error_rate, 2),
                "average_response_time_ms": round(avg_time, 2),
                "last_check": self.last_check.get(path, "").isoformat() if self.last_check.get(path) else None
            }

            metrics["summary"]["total_requests"] += requests
            metrics["summary"]["total_errors"] += errors

        # Calculate summary metrics
        if total_response_times:
            metrics["summary"]["average_response_time_ms"] = round(
                sum(total_response_times) / len(total_response_times), 2
            )

        if metrics["summary"]["total_requests"] > 0:
            metrics["summary"]["error_rate_pct"] = round(
                metrics["summary"]["total_errors"] / metrics["summary"]["total_requests"] * 100, 2
            )

        return metrics

    async def check_health(self) -> HealthCheckResult:
        """Perform API health check."""
        # Check a simple health endpoint
        health_endpoint = {"path": "/health/", "method": "GET", "name": "Health Check", "portal": "all"}
        result = await self.check_endpoint(health_endpoint)

        if result["success"]:
            status = "healthy"
            message = "API is responding normally"
        elif result["error"] == "Timeout":
            status = "degraded"
            message = "API is responding slowly"
        else:
            status = "unhealthy"
            message = f"API health check failed: {result.get('error', 'Unknown error')}"

        return HealthCheckResult(
            component="api",
            status=status,
            message=message,
            response_time_ms=result.get("response_time_ms"),
            details=result
        )

    def check_thresholds(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check if any metrics exceed configured thresholds."""
        issues = []

        # Check overall error rate
        if metrics["summary"]["error_rate_pct"] > self.thresholds.api_error_rate_pct:
            issues.append({
                "type": "high_error_rate",
                "severity": "critical",
                "message": f"API error rate ({metrics['summary']['error_rate_pct']}%) exceeds threshold ({self.thresholds.api_error_rate_pct}%)",
                "value": metrics["summary"]["error_rate_pct"],
                "threshold": self.thresholds.api_error_rate_pct
            })

        # Check average response time
        if metrics["summary"]["average_response_time_ms"] > self.thresholds.api_response_ms:
            issues.append({
                "type": "slow_response",
                "severity": "warning",
                "message": f"Average API response time ({metrics['summary']['average_response_time_ms']}ms) exceeds threshold ({self.thresholds.api_response_ms}ms)",
                "value": metrics["summary"]["average_response_time_ms"],
                "threshold": self.thresholds.api_response_ms
            })

        # Check individual endpoints
        for path, endpoint_metrics in metrics["endpoints"].items():
            if endpoint_metrics["average_response_time_ms"] > self.thresholds.api_response_ms:
                issues.append({
                    "type": "slow_endpoint",
                    "severity": "warning",
                    "endpoint": path,
                    "message": f"Endpoint {path} response time ({endpoint_metrics['average_response_time_ms']}ms) exceeds threshold",
                    "value": endpoint_metrics["average_response_time_ms"],
                    "threshold": self.thresholds.api_response_ms
                })

        return issues

    async def monitor(self) -> Dict[str, Any]:
        """Perform comprehensive API monitoring."""
        try:
            # Check all endpoints
            endpoint_results = await self.check_all_endpoints()

            # Calculate metrics
            metrics = self.calculate_metrics()

            # Check thresholds
            issues = self.check_thresholds(metrics)

            # Get health status
            health = await self.check_health()

            return {
                "health": health.dict(),
                "endpoint_results": endpoint_results,
                "metrics": metrics,
                "issues": issues,
                "has_issues": len(issues) > 0,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"API monitoring failed: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def reset_metrics(self):
        """Reset all collected metrics."""
        self.response_times.clear()
        self.error_counts.clear()
        self.request_counts.clear()
        self.last_check.clear()
        logger.info("API metrics reset")