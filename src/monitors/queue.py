"""Repair queue monitoring for RS Systems."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
import psycopg2

from ..config import settings
from ..models.django_models import RepairStatus, HealthCheckResult

logger = logging.getLogger(__name__)


class QueueMonitor:
    """Monitor repair queue health and performance."""

    def __init__(self, db_monitor):
        self.db_monitor = db_monitor  # Reuse database connection from DatabaseMonitor
        self.thresholds = settings.thresholds

    async def get_queue_status(self) -> Dict[str, Any]:
        """Get current repair queue status."""
        query = """
        SELECT
            queue_status,
            COUNT(*) as count,
            AVG(EXTRACT(EPOCH FROM (now() - created_at)) / 3600) as avg_age_hours,
            MAX(EXTRACT(EPOCH FROM (now() - created_at)) / 3600) as max_age_hours,
            MIN(EXTRACT(EPOCH FROM (now() - created_at)) / 3600) as min_age_hours
        FROM technician_portal_repair
        WHERE queue_status != 'COMPLETED'
        GROUP BY queue_status
        """

        queue_status = {}
        try:
            with self.db_monitor.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    rows = cursor.fetchall()

                    for row in rows:
                        status = row[0]
                        queue_status[status] = {
                            "count": row[1],
                            "average_age_hours": round(row[2] or 0, 2),
                            "max_age_hours": round(row[3] or 0, 2),
                            "min_age_hours": round(row[4] or 0, 2)
                        }
        except Exception as e:
            logger.error(f"Failed to get queue status: {e}")

        return queue_status

    async def get_stuck_repairs(self) -> List[Dict[str, Any]]:
        """Identify repairs that have been stuck in the same status for too long."""
        threshold_hours = self.thresholds.queue_stuck_hours

        query = """
        SELECT
            r.id,
            r.unit_number,
            r.queue_status,
            r.created_at,
            r.updated_at,
            c.name as customer_name,
            t.id as technician_id,
            u.username as technician_name,
            EXTRACT(EPOCH FROM (now() - r.updated_at)) / 3600 as stuck_hours
        FROM technician_portal_repair r
        LEFT JOIN core_customer c ON r.customer_id = c.id
        LEFT JOIN technician_portal_technician t ON r.technician_id = t.id
        LEFT JOIN auth_user u ON t.user_id = u.id
        WHERE r.queue_status NOT IN ('COMPLETED', 'DENIED')
            AND r.updated_at < now() - interval '%s hours'
        ORDER BY r.updated_at ASC
        LIMIT 50
        """

        stuck_repairs = []
        try:
            with self.db_monitor.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (threshold_hours,))
                    rows = cursor.fetchall()

                    for row in rows:
                        stuck_repairs.append({
                            "repair_id": row[0],
                            "unit_number": row[1],
                            "status": row[2],
                            "created_at": row[3].isoformat() if row[3] else None,
                            "updated_at": row[4].isoformat() if row[4] else None,
                            "customer_name": row[5],
                            "technician_id": row[6],
                            "technician_name": row[7],
                            "stuck_hours": round(row[8] or 0, 2)
                        })
        except Exception as e:
            logger.error(f"Failed to get stuck repairs: {e}")

        return stuck_repairs

    async def get_processing_times(self) -> Dict[str, Any]:
        """Calculate average processing times between status transitions."""
        query = """
        WITH status_transitions AS (
            SELECT
                queue_status,
                created_at,
                updated_at,
                CASE
                    WHEN queue_status = 'COMPLETED' THEN
                        EXTRACT(EPOCH FROM (updated_at - created_at)) / 3600
                    ELSE NULL
                END as completion_time_hours
            FROM technician_portal_repair
            WHERE created_at > now() - interval '30 days'
        )
        SELECT
            AVG(completion_time_hours) as avg_completion_hours,
            MIN(completion_time_hours) as min_completion_hours,
            MAX(completion_time_hours) as max_completion_hours,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY completion_time_hours) as median_completion_hours,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY completion_time_hours) as p95_completion_hours
        FROM status_transitions
        WHERE completion_time_hours IS NOT NULL
        """

        processing_times = {}
        try:
            with self.db_monitor.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    row = cursor.fetchone()

                    if row:
                        processing_times = {
                            "average_completion_hours": round(row[0] or 0, 2),
                            "min_completion_hours": round(row[1] or 0, 2),
                            "max_completion_hours": round(row[2] or 0, 2),
                            "median_completion_hours": round(row[3] or 0, 2),
                            "p95_completion_hours": round(row[4] or 0, 2)
                        }
        except Exception as e:
            logger.error(f"Failed to get processing times: {e}")

        return processing_times

    async def get_technician_queue_load(self) -> List[Dict[str, Any]]:
        """Get queue load per technician."""
        query = """
        SELECT
            t.id as technician_id,
            u.username as technician_name,
            COUNT(r.id) as total_repairs,
            SUM(CASE WHEN r.queue_status = 'IN_PROGRESS' THEN 1 ELSE 0 END) as in_progress,
            SUM(CASE WHEN r.queue_status = 'PENDING' THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN r.queue_status = 'APPROVED' THEN 1 ELSE 0 END) as approved,
            AVG(CASE
                WHEN r.queue_status = 'IN_PROGRESS' THEN
                    EXTRACT(EPOCH FROM (now() - r.updated_at)) / 3600
                ELSE NULL
            END) as avg_in_progress_hours
        FROM technician_portal_technician t
        JOIN auth_user u ON t.user_id = u.id
        LEFT JOIN technician_portal_repair r ON t.id = r.technician_id
            AND r.queue_status NOT IN ('COMPLETED', 'DENIED')
        GROUP BY t.id, u.username
        HAVING COUNT(r.id) > 0
        ORDER BY total_repairs DESC
        """

        technician_load = []
        try:
            with self.db_monitor.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    rows = cursor.fetchall()

                    for row in rows:
                        technician_load.append({
                            "technician_id": row[0],
                            "technician_name": row[1],
                            "total_active_repairs": row[2],
                            "in_progress": row[3],
                            "pending": row[4],
                            "approved": row[5],
                            "avg_in_progress_hours": round(row[6] or 0, 2) if row[6] else None
                        })
        except Exception as e:
            logger.error(f"Failed to get technician queue load: {e}")

        return technician_load

    async def get_queue_throughput(self) -> Dict[str, Any]:
        """Calculate queue throughput metrics."""
        query = """
        WITH daily_stats AS (
            SELECT
                DATE(created_at) as date,
                COUNT(*) FILTER (WHERE queue_status = 'REQUESTED') as new_requests,
                COUNT(*) FILTER (WHERE queue_status = 'COMPLETED') as completed_repairs
            FROM technician_portal_repair
            WHERE created_at > now() - interval '7 days'
            GROUP BY DATE(created_at)
        )
        SELECT
            AVG(new_requests) as avg_daily_requests,
            AVG(completed_repairs) as avg_daily_completions,
            SUM(new_requests) as total_requests_7d,
            SUM(completed_repairs) as total_completions_7d
        FROM daily_stats
        """

        throughput = {}
        try:
            with self.db_monitor.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    row = cursor.fetchone()

                    if row:
                        throughput = {
                            "avg_daily_requests": round(row[0] or 0, 2),
                            "avg_daily_completions": round(row[1] or 0, 2),
                            "total_requests_7d": row[2] or 0,
                            "total_completions_7d": row[3] or 0,
                            "completion_rate_pct": round(
                                (row[3] / row[2] * 100) if row[2] and row[2] > 0 else 0, 2
                            )
                        }
        except Exception as e:
            logger.error(f"Failed to get queue throughput: {e}")

        return throughput

    async def check_health(self) -> HealthCheckResult:
        """Check overall queue health."""
        try:
            queue_status = await self.get_queue_status()
            stuck_repairs = await self.get_stuck_repairs()

            total_pending = sum(
                status_data["count"]
                for status, status_data in queue_status.items()
                if status in ["PENDING", "REQUESTED", "APPROVED"]
            )

            if stuck_repairs:
                status = "degraded"
                message = f"Found {len(stuck_repairs)} stuck repairs"
            elif total_pending > self.thresholds.pending_repairs:
                status = "degraded"
                message = f"High pending repair count: {total_pending}"
            else:
                status = "healthy"
                message = "Queue is processing normally"

            return HealthCheckResult(
                component="queue",
                status=status,
                message=message,
                details={
                    "total_pending": total_pending,
                    "stuck_repairs_count": len(stuck_repairs)
                }
            )
        except Exception as e:
            logger.error(f"Queue health check failed: {e}")
            return HealthCheckResult(
                component="queue",
                status="unhealthy",
                message=f"Queue health check failed: {str(e)}"
            )

    def check_thresholds(
        self,
        queue_status: Dict[str, Any],
        stuck_repairs: List[Dict[str, Any]],
        throughput: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Check if queue metrics exceed thresholds."""
        issues = []

        # Check for stuck repairs
        if stuck_repairs:
            issues.append({
                "type": "stuck_repairs",
                "severity": "warning",
                "message": f"Found {len(stuck_repairs)} repairs stuck for over {self.thresholds.queue_stuck_hours} hours",
                "count": len(stuck_repairs),
                "repairs": [r["repair_id"] for r in stuck_repairs[:5]]  # First 5 IDs
            })

        # Check queue depth
        total_queue = sum(status_data["count"] for status_data in queue_status.values())
        if total_queue > self.thresholds.queue_depth:
            issues.append({
                "type": "high_queue_depth",
                "severity": "warning",
                "message": f"Queue depth ({total_queue}) exceeds threshold ({self.thresholds.queue_depth})",
                "value": total_queue,
                "threshold": self.thresholds.queue_depth
            })

        # Check pending repairs
        pending_count = queue_status.get("PENDING", {}).get("count", 0)
        if pending_count > self.thresholds.pending_repairs:
            issues.append({
                "type": "high_pending_count",
                "severity": "warning",
                "message": f"Pending repairs ({pending_count}) exceeds threshold ({self.thresholds.pending_repairs})",
                "value": pending_count,
                "threshold": self.thresholds.pending_repairs
            })

        # Check completion rate
        if throughput.get("completion_rate_pct", 100) < 50:
            issues.append({
                "type": "low_completion_rate",
                "severity": "critical",
                "message": f"Low completion rate: {throughput.get('completion_rate_pct', 0)}%",
                "value": throughput.get("completion_rate_pct", 0)
            })

        return issues

    async def monitor(self) -> Dict[str, Any]:
        """Perform comprehensive queue monitoring."""
        try:
            # Run all monitoring tasks concurrently
            tasks = [
                self.get_queue_status(),
                self.get_stuck_repairs(),
                self.get_processing_times(),
                self.get_technician_queue_load(),
                self.get_queue_throughput(),
                self.check_health()
            ]

            (
                queue_status,
                stuck_repairs,
                processing_times,
                technician_load,
                throughput,
                health
            ) = await asyncio.gather(*tasks)

            # Check thresholds
            issues = self.check_thresholds(queue_status, stuck_repairs, throughput)

            return {
                "health": health.dict(),
                "queue_status": queue_status,
                "stuck_repairs": stuck_repairs,
                "processing_times": processing_times,
                "technician_load": technician_load,
                "throughput": throughput,
                "issues": issues,
                "has_issues": len(issues) > 0,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Queue monitoring failed: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }