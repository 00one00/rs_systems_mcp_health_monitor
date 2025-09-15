"""Database monitoring for RS Systems PostgreSQL database."""

import asyncio
import psycopg2
import psycopg2.pool
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
from contextlib import contextmanager

from ..config import settings
from ..models.django_models import HealthCheckResult, SystemMetrics

logger = logging.getLogger(__name__)


class DatabaseMonitor:
    """Monitor PostgreSQL database performance and health."""

    def __init__(self):
        self.config = settings.database
        self.thresholds = settings.thresholds
        self.connection_pool = None
        self._initialize_pool()

    def _initialize_pool(self):
        """Initialize PostgreSQL connection pool."""
        try:
            self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=2,
                maxconn=self.config.connection_pool_size,
                dsn=self.config.database_url
            )
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """Get a database connection from the pool."""
        conn = None
        try:
            conn = self.connection_pool.getconn()
            yield conn
        finally:
            if conn:
                self.connection_pool.putconn(conn)

    async def check_health(self) -> HealthCheckResult:
        """Perform comprehensive database health check."""
        start_time = datetime.now()
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Simple health check query
                    cursor.execute("SELECT 1")
                    cursor.fetchone()

            response_time = (datetime.now() - start_time).total_seconds() * 1000

            return HealthCheckResult(
                component="database",
                status="healthy",
                message="Database is responding normally",
                response_time_ms=response_time,
                details={
                    "connection_pool_size": self.config.connection_pool_size,
                    "response_time_ms": response_time
                }
            )
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return HealthCheckResult(
                component="database",
                status="unhealthy",
                message=f"Database health check failed: {str(e)}",
                response_time_ms=None
            )

    async def get_slow_queries(self, threshold_ms: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get slow queries from PostgreSQL."""
        threshold = threshold_ms or self.thresholds.db_query_ms

        query = """
        SELECT
            query,
            state,
            query_start,
            EXTRACT(EPOCH FROM (now() - query_start)) * 1000 as duration_ms,
            usename,
            datname,
            client_addr
        FROM pg_stat_activity
        WHERE state != 'idle'
            AND query NOT LIKE 'SELECT query%'
            AND EXTRACT(EPOCH FROM (now() - query_start)) * 1000 > %s
        ORDER BY duration_ms DESC
        LIMIT 20
        """

        slow_queries = []
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (threshold,))
                    rows = cursor.fetchall()

                    for row in rows:
                        slow_queries.append({
                            "query": row[0][:500],  # Truncate long queries
                            "state": row[1],
                            "start_time": row[2].isoformat() if row[2] else None,
                            "duration_ms": round(row[3], 2),
                            "user": row[4],
                            "database": row[5],
                            "client_address": row[6]
                        })
        except Exception as e:
            logger.error(f"Failed to get slow queries: {e}")

        return slow_queries

    async def get_connection_stats(self) -> Dict[str, Any]:
        """Get database connection statistics."""
        query = """
        SELECT
            count(*) as total_connections,
            count(*) FILTER (WHERE state = 'active') as active_connections,
            count(*) FILTER (WHERE state = 'idle') as idle_connections,
            count(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction,
            max(EXTRACT(EPOCH FROM (now() - query_start)) * 1000) as longest_query_ms
        FROM pg_stat_activity
        WHERE datname = %s
        """

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (self.config.db_name,))
                    row = cursor.fetchone()

                    total = row[0] or 0
                    pool_usage_pct = (total / self.config.connection_pool_size * 100) if self.config.connection_pool_size > 0 else 0

                    return {
                        "total_connections": total,
                        "active_connections": row[1] or 0,
                        "idle_connections": row[2] or 0,
                        "idle_in_transaction": row[3] or 0,
                        "longest_query_ms": round(row[4] or 0, 2),
                        "pool_size": self.config.connection_pool_size,
                        "pool_usage_pct": round(pool_usage_pct, 2)
                    }
        except Exception as e:
            logger.error(f"Failed to get connection stats: {e}")
            return {}

    async def get_table_stats(self) -> List[Dict[str, Any]]:
        """Get statistics for key RS Systems tables."""
        tables = [
            'technician_portal_repair',
            'core_customer',
            'auth_user',
            'rewards_referrals_reward',
            'technician_portal_technician'
        ]

        stats = []
        query = """
        SELECT
            schemaname,
            tablename,
            n_tup_ins as inserts,
            n_tup_upd as updates,
            n_tup_del as deletes,
            n_live_tup as live_tuples,
            n_dead_tup as dead_tuples,
            last_vacuum,
            last_autovacuum
        FROM pg_stat_user_tables
        WHERE tablename = %s
        """

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    for table in tables:
                        cursor.execute(query, (table,))
                        row = cursor.fetchone()

                        if row:
                            stats.append({
                                "schema": row[0],
                                "table": row[1],
                                "inserts": row[2],
                                "updates": row[3],
                                "deletes": row[4],
                                "live_tuples": row[5],
                                "dead_tuples": row[6],
                                "last_vacuum": row[7].isoformat() if row[7] else None,
                                "last_autovacuum": row[8].isoformat() if row[8] else None,
                                "bloat_ratio": round(row[6] / max(row[5], 1) * 100, 2)
                            })
        except Exception as e:
            logger.error(f"Failed to get table stats: {e}")

        return stats

    async def check_locks(self) -> List[Dict[str, Any]]:
        """Check for database locks."""
        query = """
        SELECT
            blocked_locks.pid AS blocked_pid,
            blocked_activity.usename AS blocked_user,
            blocking_locks.pid AS blocking_pid,
            blocking_activity.usename AS blocking_user,
            blocked_activity.query AS blocked_query,
            blocking_activity.query AS blocking_query,
            EXTRACT(EPOCH FROM (now() - blocked_activity.query_start)) * 1000 as blocked_duration_ms
        FROM pg_catalog.pg_locks blocked_locks
        JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
        JOIN pg_catalog.pg_locks blocking_locks
            ON blocking_locks.locktype = blocked_locks.locktype
            AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
            AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
            AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
            AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
            AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
            AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
            AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
            AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
            AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
            AND blocking_locks.pid != blocked_locks.pid
        JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
        WHERE NOT blocked_locks.granted
        """

        locks = []
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    rows = cursor.fetchall()

                    for row in rows:
                        locks.append({
                            "blocked_pid": row[0],
                            "blocked_user": row[1],
                            "blocking_pid": row[2],
                            "blocking_user": row[3],
                            "blocked_query": row[4][:200] if row[4] else None,
                            "blocking_query": row[5][:200] if row[5] else None,
                            "blocked_duration_ms": round(row[6] or 0, 2)
                        })
        except Exception as e:
            logger.error(f"Failed to check locks: {e}")

        return locks

    async def get_repair_status_distribution(self) -> Dict[str, int]:
        """Get distribution of repairs by status."""
        query = """
        SELECT queue_status, COUNT(*) as count
        FROM technician_portal_repair
        GROUP BY queue_status
        """

        distribution = {}
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    rows = cursor.fetchall()

                    for row in rows:
                        distribution[row[0]] = row[1]
        except Exception as e:
            logger.error(f"Failed to get repair status distribution: {e}")

        return distribution

    async def monitor(self) -> Dict[str, Any]:
        """Perform comprehensive database monitoring."""
        results = {}

        # Run all monitoring tasks concurrently
        tasks = [
            self.check_health(),
            self.get_slow_queries(),
            self.get_connection_stats(),
            self.get_table_stats(),
            self.check_locks(),
            self.get_repair_status_distribution()
        ]

        try:
            health, slow_queries, conn_stats, table_stats, locks, repair_dist = await asyncio.gather(*tasks)

            results = {
                "health": health.dict() if health else None,
                "slow_queries": slow_queries,
                "connection_stats": conn_stats,
                "table_stats": table_stats,
                "locks": locks,
                "repair_distribution": repair_dist,
                "timestamp": datetime.now().isoformat()
            }

            # Check for issues
            issues = []
            if slow_queries:
                issues.append(f"Found {len(slow_queries)} slow queries")

            if conn_stats.get("pool_usage_pct", 0) > self.thresholds.db_connections_pct:
                issues.append(f"High connection pool usage: {conn_stats.get('pool_usage_pct')}%")

            if locks:
                issues.append(f"Found {len(locks)} database locks")

            results["issues"] = issues
            results["has_issues"] = len(issues) > 0

        except Exception as e:
            logger.error(f"Database monitoring failed: {e}")
            results["error"] = str(e)

        return results

    def close(self):
        """Close the connection pool."""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("Database connection pool closed")