"""User and customer activity monitoring for RS Systems."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

from ..config import settings
from ..models.django_models import HealthCheckResult

logger = logging.getLogger(__name__)


class ActivityMonitor:
    """Monitor user and customer activity patterns."""

    def __init__(self, db_monitor):
        self.db_monitor = db_monitor
        self.thresholds = settings.thresholds

    async def get_active_users(self, days: int = 30) -> Dict[str, Any]:
        """Get active user statistics."""
        query = """
        SELECT
            COUNT(DISTINCT u.id) as total_users,
            COUNT(DISTINCT CASE 
                WHEN u.last_login > now() - interval '%s days' THEN u.id 
            END) as active_users,
            COUNT(DISTINCT CASE 
                WHEN u.last_login > now() - interval '1 day' THEN u.id 
            END) as active_today,
            COUNT(DISTINCT CASE 
                WHEN u.last_login > now() - interval '7 days' THEN u.id 
            END) as active_week,
            COUNT(DISTINCT t.id) as total_technicians,
            COUNT(DISTINCT CASE 
                WHEN t.id IS NOT NULL AND u.last_login > now() - interval '1 day' THEN t.id 
            END) as active_technicians_today
        FROM auth_user u
        LEFT JOIN technician_portal_technician t ON u.id = t.user_id
        WHERE u.is_active = true
        """

        try:
            with self.db_monitor.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (days,))
                    row = cursor.fetchone()

                    if row:
                        return {
                            "total_users": row[0],
                            "active_users_30d": row[1],
                            "active_today": row[2],
                            "active_week": row[3],
                            "total_technicians": row[4],
                            "active_technicians_today": row[5],
                            "activity_rate_pct": round((row[1] / row[0] * 100) if row[0] > 0 else 0, 2)
                        }
        except Exception as e:
            logger.error(f"Failed to get active users: {e}")

        return {}

    async def get_customer_activity(self) -> Dict[str, Any]:
        """Get customer activity metrics."""
        query = """
        SELECT
            COUNT(DISTINCT c.id) as total_customers,
            COUNT(DISTINCT CASE 
                WHEN r.created_at > now() - interval '30 days' THEN c.id 
            END) as active_customers_30d,
            COUNT(DISTINCT CASE 
                WHEN c.created_at > now() - interval '1 day' THEN c.id 
            END) as new_customers_today,
            COUNT(DISTINCT CASE 
                WHEN c.created_at > now() - interval '7 days' THEN c.id 
            END) as new_customers_week,
            AVG(CASE 
                WHEN r.customer_id IS NOT NULL THEN repair_count.count 
            END) as avg_repairs_per_customer
        FROM core_customer c
        LEFT JOIN technician_portal_repair r ON c.id = r.customer_id
        LEFT JOIN (
            SELECT customer_id, COUNT(*) as count
            FROM technician_portal_repair
            GROUP BY customer_id
        ) repair_count ON c.id = repair_count.customer_id
        """

        try:
            with self.db_monitor.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    row = cursor.fetchone()

                    if row:
                        return {
                            "total_customers": row[0],
                            "active_customers_30d": row[1],
                            "new_customers_today": row[2],
                            "new_customers_week": row[3],
                            "avg_repairs_per_customer": round(row[4] or 0, 2),
                            "engagement_rate_pct": round((row[1] / row[0] * 100) if row[0] > 0 else 0, 2)
                        }
        except Exception as e:
            logger.error(f"Failed to get customer activity: {e}")

        return {}

    async def get_technician_performance(self) -> List[Dict[str, Any]]:
        """Get technician performance metrics."""
        query = """
        SELECT
            t.id,
            u.username,
            u.last_login,
            COUNT(r.id) as total_repairs,
            COUNT(CASE WHEN r.queue_status = 'COMPLETED' THEN 1 END) as completed_repairs,
            COUNT(CASE WHEN r.created_at > now() - interval '7 days' THEN 1 END) as repairs_last_week,
            AVG(CASE 
                WHEN r.queue_status = 'COMPLETED' THEN 
                    EXTRACT(EPOCH FROM (r.updated_at - r.created_at)) / 3600 
            END) as avg_completion_hours,
            MAX(r.repair_date) as last_repair_date
        FROM technician_portal_technician t
        JOIN auth_user u ON t.user_id = u.id
        LEFT JOIN technician_portal_repair r ON t.id = r.technician_id
        GROUP BY t.id, u.username, u.last_login
        ORDER BY total_repairs DESC
        LIMIT 50
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
                            "last_login": row[2].isoformat() if row[2] else None,
                            "total_repairs": row[3],
                            "completed_repairs": row[4],
                            "repairs_last_week": row[5],
                            "avg_completion_hours": round(row[6] or 0, 2) if row[6] else None,
                            "last_repair_date": row[7].isoformat() if row[7] else None,
                            "completion_rate_pct": round((row[4] / row[3] * 100) if row[3] > 0 else 0, 2)
                        })
        except Exception as e:
            logger.error(f"Failed to get technician performance: {e}")

        return technicians

    async def get_login_patterns(self) -> Dict[str, Any]:
        """Analyze login patterns."""
        query = """
        WITH hourly_logins AS (
            SELECT
                EXTRACT(HOUR FROM last_login) as hour,
                EXTRACT(DOW FROM last_login) as day_of_week,
                COUNT(*) as login_count
            FROM auth_user
            WHERE last_login > now() - interval '30 days'
            GROUP BY EXTRACT(HOUR FROM last_login), EXTRACT(DOW FROM last_login)
        )
        SELECT
            hour,
            day_of_week,
            login_count
        FROM hourly_logins
        ORDER BY login_count DESC
        LIMIT 20
        """

        patterns = {
            "peak_hours": [],
            "peak_days": [],
            "by_hour": {},
            "by_day": {}
        }

        try:
            with self.db_monitor.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    rows = cursor.fetchall()

                    for row in rows:
                        hour = int(row[0])
                        day = int(row[1])
                        count = row[2]

                        if hour not in patterns["by_hour"]:
                            patterns["by_hour"][hour] = 0
                        patterns["by_hour"][hour] += count

                        if day not in patterns["by_day"]:
                            patterns["by_day"][day] = 0
                        patterns["by_day"][day] += count

                    # Identify peak hours
                    if patterns["by_hour"]:
                        sorted_hours = sorted(patterns["by_hour"].items(), key=lambda x: x[1], reverse=True)
                        patterns["peak_hours"] = [h[0] for h in sorted_hours[:3]]

                    # Identify peak days
                    day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
                    if patterns["by_day"]:
                        sorted_days = sorted(patterns["by_day"].items(), key=lambda x: x[1], reverse=True)
                        patterns["peak_days"] = [day_names[d[0]] for d in sorted_days[:3]]

        except Exception as e:
            logger.error(f"Failed to get login patterns: {e}")

        return patterns

    async def check_health(self) -> HealthCheckResult:
        """Check activity health."""
        try:
            user_activity = await self.get_active_users()
            
            inactive_hours = datetime.now() - timedelta(hours=self.thresholds.inactive_technicians_hours)
            
            if user_activity.get("active_technicians_today", 0) == 0:
                status = "degraded"
                message = "No technician activity today"
            elif user_activity.get("activity_rate_pct", 0) < 20:
                status = "degraded"
                message = "Low user activity rate"
            else:
                status = "healthy"
                message = "Normal user activity levels"

            return HealthCheckResult(
                component="activity",
                status=status,
                message=message,
                details=user_activity
            )
        except Exception as e:
            logger.error(f"Activity health check failed: {e}")
            return HealthCheckResult(
                component="activity",
                status="unhealthy",
                message=f"Activity health check failed: {str(e)}"
            )

    async def monitor(self) -> Dict[str, Any]:
        """Perform comprehensive activity monitoring."""
        try:
            tasks = [
                self.get_active_users(),
                self.get_customer_activity(),
                self.get_technician_performance(),
                self.get_login_patterns(),
                self.check_health()
            ]

            (
                user_activity,
                customer_activity,
                technician_performance,
                login_patterns,
                health
            ) = await asyncio.gather(*tasks)

            # Check for inactive technicians
            inactive_technicians = [
                t for t in technician_performance
                if not t["last_login"] or 
                datetime.fromisoformat(t["last_login"]) < datetime.now() - timedelta(hours=self.thresholds.inactive_technicians_hours)
            ]

            issues = []
            if inactive_technicians:
                issues.append({
                    "type": "inactive_technicians",
                    "severity": "warning",
                    "message": f"Found {len(inactive_technicians)} inactive technicians",
                    "technicians": [t["username"] for t in inactive_technicians[:5]]
                })

            return {
                "health": health.dict(),
                "user_activity": user_activity,
                "customer_activity": customer_activity,
                "technician_performance": technician_performance[:10],  # Top 10
                "login_patterns": login_patterns,
                "inactive_technicians": inactive_technicians,
                "issues": issues,
                "has_issues": len(issues) > 0,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Activity monitoring failed: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }