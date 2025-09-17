"""Simplified activity monitoring for RS Systems - SQLite compatible."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

from ..config import settings
from ..models.django_models import HealthCheckResult

logger = logging.getLogger(__name__)


class ActivityMonitor:
    """Monitor user and technician activity patterns (simplified for SQLite)."""

    def __init__(self, db_monitor):
        self.db_monitor = db_monitor
        self.thresholds = settings.thresholds

    async def get_active_users(self, days: int = 30) -> Dict[str, Any]:
        """Get simplified active user statistics."""
        # For SQLite, we'll use simpler queries
        query = """
        SELECT
            COUNT(DISTINCT u.id) as total_users,
            COUNT(DISTINCT t.id) as total_technicians
        FROM auth_user u
        LEFT JOIN technician_portal_technician t ON t.user_id = u.id
        """

        user_stats = {
            "total_users": 0,
            "total_technicians": 0,
            "active_users": 0,
            "active_today": 0,
            "active_week": 0,
            "active_technicians_today": 0
        }

        try:
            with self.db_monitor.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    row = cursor.fetchone()

                    if row:
                        user_stats["total_users"] = row[0] or 0
                        user_stats["total_technicians"] = row[1] or 0

                    # Get recent activity (simplified)
                    recent_query = """
                    SELECT COUNT(DISTINCT technician_id)
                    FROM technician_portal_repair
                    WHERE repair_date > date('now', '-1 day')
                    """
                    cursor.execute(recent_query)
                    recent = cursor.fetchone()
                    if recent:
                        user_stats["active_technicians_today"] = recent[0] or 0

        except Exception as e:
            logger.error(f"Failed to get active users: {e}")

        return user_stats

    async def get_customer_activity(self) -> Dict[str, Any]:
        """Get simplified customer activity metrics."""
        query = """
        SELECT
            COUNT(DISTINCT c.id) as total_customers,
            COUNT(DISTINCT r.customer_id) as customers_with_repairs
        FROM core_customer c
        LEFT JOIN technician_portal_repair r ON r.customer_id = c.id
        """

        customer_stats = {
            "total_customers": 0,
            "customers_with_repairs": 0,
            "active_customers_30d": 0,
            "new_customers_today": 0,
            "new_customers_week": 0
        }

        try:
            with self.db_monitor.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    row = cursor.fetchone()

                    if row:
                        customer_stats["total_customers"] = row[0] or 0
                        customer_stats["customers_with_repairs"] = row[1] or 0

        except Exception as e:
            logger.error(f"Failed to get customer activity: {e}")

        return customer_stats

    async def get_technician_performance(self) -> List[Dict[str, Any]]:
        """Get simplified technician performance metrics."""
        query = """
        SELECT
            t.id,
            u.username,
            COUNT(r.id) as total_repairs,
            COUNT(CASE WHEN r.queue_status = 'COMPLETED' THEN 1 END) as completed_repairs,
            MAX(r.repair_date) as last_repair_date
        FROM technician_portal_technician t
        JOIN auth_user u ON t.user_id = u.id
        LEFT JOIN technician_portal_repair r ON r.technician_id = t.id
        GROUP BY t.id, u.username
        ORDER BY total_repairs DESC
        LIMIT 20
        """

        technicians = []
        try:
            with self.db_monitor.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    rows = cursor.fetchall()

                    for row in rows:
                        technicians.append({
                            "technician_id": row[0],
                            "username": row[1],
                            "total_repairs": row[2] or 0,
                            "completed_repairs": row[3] or 0,
                            "last_repair_date": row[4],
                            "completion_rate": round((row[3] or 0) / max(row[2] or 1, 1) * 100, 2)
                        })

        except Exception as e:
            logger.error(f"Failed to get technician performance: {e}")

        return technicians

    async def check_health(self) -> HealthCheckResult:
        """Check activity monitoring health."""
        try:
            user_activity = await self.get_active_users()

            if user_activity.get("active_technicians_today", 0) == 0:
                return HealthCheckResult(
                    component="activity",
                    status="degraded",
                    message="No technician activity today",
                    response_time_ms=None,
                    details=user_activity
                )

            return HealthCheckResult(
                component="activity",
                status="healthy",
                message="Activity monitoring is functioning normally",
                response_time_ms=None,
                details=user_activity
            )
        except Exception as e:
            logger.error(f"Activity health check failed: {e}")
            return HealthCheckResult(
                component="activity",
                status="unhealthy",
                message=f"Activity monitoring failed: {str(e)}",
                response_time_ms=None
            )

    async def monitor(self) -> Dict[str, Any]:
        """Perform comprehensive activity monitoring."""
        results = {}

        # Run monitoring tasks
        tasks = [
            self.get_active_users(),
            self.get_customer_activity(),
            self.get_technician_performance(),
            self.check_health()
        ]

        try:
            user_activity, customer_activity, technician_performance, health = await asyncio.gather(*tasks)

            results = {
                "user_activity": user_activity,
                "customer_activity": customer_activity,
                "technician_performance": technician_performance,
                "health": health.dict() if health else None,
                "timestamp": datetime.now().isoformat()
            }

            # Check for issues
            issues = []
            if user_activity.get("active_technicians_today", 0) == 0:
                issues.append("No technician activity today")

            if customer_activity.get("customers_with_repairs", 0) == 0:
                issues.append("No customers have repairs")

            results["issues"] = issues
            results["has_issues"] = len(issues) > 0

        except Exception as e:
            logger.error(f"Activity monitoring failed: {e}")
            results = {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

        return results