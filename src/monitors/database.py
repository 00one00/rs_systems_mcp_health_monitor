"""Database monitoring adapter that auto-detects database type."""

import logging
from typing import Dict, List, Any, Optional

from ..config import settings
from ..models.django_models import HealthCheckResult, SystemMetrics

logger = logging.getLogger(__name__)


class DatabaseMonitor:
    """Unified database monitor that auto-detects database type."""

    def __init__(self):
        self.config = settings.database
        self.thresholds = settings.thresholds
        self.adapter = None
        self._initialize_adapter()

    def _initialize_adapter(self):
        """Initialize appropriate database adapter based on URL."""
        database_url = self.config.database_url.lower()

        try:
            if database_url.startswith('sqlite'):
                logger.info("Detected SQLite database, initializing SQLite monitor")
                from .database_sqlite import SQLiteMonitor
                self.adapter = SQLiteMonitor()
            elif database_url.startswith('postgresql') or database_url.startswith('postgres'):
                logger.info("Detected PostgreSQL database, initializing PostgreSQL monitor")
                from .database_postgresql import PostgreSQLMonitor
                self.adapter = PostgreSQLMonitor()
            else:
                logger.warning(f"Unknown database type in URL: {database_url}")
                logger.info("Defaulting to SQLite monitor")
                from .database_sqlite import SQLiteMonitor
                self.adapter = SQLiteMonitor()
        except Exception as e:
            logger.error(f"Failed to initialize database adapter: {e}")
            # Try SQLite as fallback
            try:
                from .database_sqlite import SQLiteMonitor
                self.adapter = SQLiteMonitor()
                logger.info("Initialized SQLite monitor as fallback")
            except Exception as fallback_error:
                logger.error(f"Failed to initialize fallback SQLite monitor: {fallback_error}")
                self.adapter = None

    async def check_health(self) -> Optional[HealthCheckResult]:
        """Perform database health check."""
        if not self.adapter:
            return HealthCheckResult(
                component="database",
                status="unhealthy",
                message="No database adapter available",
                response_time_ms=None
            )
        try:
            return await self.adapter.check_health()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return HealthCheckResult(
                component="database",
                status="unhealthy",
                message=f"Health check error: {str(e)}",
                response_time_ms=None
            )

    async def get_slow_queries(self, threshold_ms: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get slow queries from database."""
        if not self.adapter:
            return []
        try:
            return await self.adapter.get_slow_queries(threshold_ms)
        except Exception as e:
            logger.error(f"Failed to get slow queries: {e}")
            return []

    async def get_connection_stats(self) -> Dict[str, Any]:
        """Get database connection statistics."""
        if not self.adapter:
            return {"error": "No database adapter available"}
        try:
            return await self.adapter.get_connection_stats()
        except Exception as e:
            logger.error(f"Failed to get connection stats: {e}")
            return {"error": str(e)}

    async def get_table_stats(self) -> List[Dict[str, Any]]:
        """Get statistics for key tables."""
        if not self.adapter:
            return []
        try:
            # SQLite adapter has get_table_sizes, PostgreSQL has get_table_stats
            if hasattr(self.adapter, 'get_table_stats'):
                return await self.adapter.get_table_stats()
            elif hasattr(self.adapter, 'get_table_sizes'):
                return await self.adapter.get_table_sizes()
            else:
                return []
        except Exception as e:
            logger.error(f"Failed to get table stats: {e}")
            return []

    async def check_locks(self) -> List[Dict[str, Any]]:
        """Check for database locks."""
        if not self.adapter:
            return []
        try:
            return await self.adapter.check_locks()
        except Exception as e:
            logger.error(f"Failed to check locks: {e}")
            return []

    async def get_repair_status_distribution(self) -> Dict[str, int]:
        """Get distribution of repairs by status."""
        if not self.adapter:
            return {}

        try:
            # For SQLite, we need to query the Django database directly
            if hasattr(self.adapter, 'get_connection'):
                with self.adapter.get_connection() as conn:
                    cursor = conn.cursor()
                    # Try to query the repair table
                    try:
                        cursor.execute("""
                            SELECT queue_status, COUNT(*) as count
                            FROM technician_portal_repair
                            GROUP BY queue_status
                        """)
                        rows = cursor.fetchall()

                        distribution = {}
                        for row in rows:
                            distribution[row[0]] = row[1]
                        return distribution
                    except Exception as table_error:
                        logger.debug(f"Table technician_portal_repair might not exist: {table_error}")
                        return {}

            # Fallback for PostgreSQL adapter
            if hasattr(self.adapter, 'get_repair_status_distribution'):
                return await self.adapter.get_repair_status_distribution()

            return {}
        except Exception as e:
            logger.error(f"Failed to get repair status distribution: {e}")
            return {}

    async def get_performance_metrics(self) -> Optional[SystemMetrics]:
        """Get database performance metrics."""
        if not self.adapter:
            return None
        try:
            if hasattr(self.adapter, 'get_performance_metrics'):
                return await self.adapter.get_performance_metrics()
            else:
                # Basic metrics for adapters without this method
                health = await self.check_health()
                return SystemMetrics(
                    component="database",
                    metrics={
                        "status": health.status if health else "unknown",
                        "response_time_ms": health.response_time_ms if health else None
                    },
                    timestamp=health.timestamp if health else None
                )
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return None

    async def monitor(self) -> Dict[str, Any]:
        """Perform comprehensive database monitoring."""
        if not self.adapter:
            return {"error": "No database adapter available"}

        # If adapter has its own monitor method, use it
        if hasattr(self.adapter, 'monitor'):
            try:
                return await self.adapter.monitor()
            except Exception as e:
                logger.error(f"Adapter monitor failed: {e}")

        # Otherwise, build monitoring result from individual methods
        import asyncio
        from datetime import datetime

        results = {}

        # Run monitoring tasks
        tasks = {
            "health": self.check_health(),
            "slow_queries": self.get_slow_queries(),
            "connection_stats": self.get_connection_stats(),
            "table_stats": self.get_table_stats(),
            "locks": self.check_locks(),
            "repair_distribution": self.get_repair_status_distribution()
        }

        try:
            task_results = await asyncio.gather(*tasks.values(), return_exceptions=True)

            for key, result in zip(tasks.keys(), task_results):
                if isinstance(result, Exception):
                    logger.error(f"Task {key} failed: {result}")
                    results[key] = None
                else:
                    if key == "health" and result:
                        results[key] = result.dict()
                    else:
                        results[key] = result

            results["timestamp"] = datetime.now().isoformat()

            # Check for issues
            issues = []
            if results.get("slow_queries"):
                issues.append(f"Found {len(results['slow_queries'])} slow queries")

            if results.get("locks"):
                issues.append(f"Found {len(results['locks'])} database locks")

            results["issues"] = issues
            results["has_issues"] = len(issues) > 0

        except Exception as e:
            logger.error(f"Database monitoring failed: {e}")
            results["error"] = str(e)

        return results

    def get_connection(self):
        """Get a database connection (pass-through to adapter)."""
        if self.adapter and hasattr(self.adapter, 'get_connection'):
            return self.adapter.get_connection()
        else:
            raise Exception("No database adapter available or adapter doesn't support connections")

    def close(self):
        """Close database connections."""
        if self.adapter and hasattr(self.adapter, 'close'):
            self.adapter.close()