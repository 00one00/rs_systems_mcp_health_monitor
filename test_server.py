#!/usr/bin/env python3
"""Test script for RS Health Monitor MCP Server."""

import asyncio
import json
import logging
from src.server import RSHealthMonitorServer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_server():
    """Test the MCP server functionality."""
    logger.info("Initializing RS Health Monitor Server...")
    server = RSHealthMonitorServer()

    # Test health check
    logger.info("\n=== Testing System Health Summary ===")
    try:
        if server.db_monitor:
            health = await server.db_monitor.check_health()
            logger.info(f"Database Health: {health.status}")
            logger.info(f"Message: {health.message}")
            if health.details:
                logger.info(f"Details: {json.dumps(health.details, indent=2)}")
        else:
            logger.warning("Database monitor not available")
    except Exception as e:
        logger.error(f"Health check failed: {e}")

    # Test connection stats
    logger.info("\n=== Testing Database Connection Stats ===")
    try:
        if server.db_monitor:
            stats = await server.db_monitor.get_connection_stats()
            logger.info(f"Connection Stats: {json.dumps(stats, indent=2)}")
        else:
            logger.warning("Database monitor not available")
    except Exception as e:
        logger.error(f"Connection stats failed: {e}")

    # Test table stats
    logger.info("\n=== Testing Table Statistics ===")
    try:
        if server.db_monitor:
            table_stats = await server.db_monitor.get_table_stats()
            logger.info(f"Found {len(table_stats)} tables")
            for table in table_stats[:5]:  # Show first 5 tables
                logger.info(f"  Table: {table.get('table_name', 'unknown')}, Rows: {table.get('row_count', 0)}")
        else:
            logger.warning("Database monitor not available")
    except Exception as e:
        logger.error(f"Table stats failed: {e}")

    # Test repair status distribution
    logger.info("\n=== Testing Repair Status Distribution ===")
    try:
        if server.db_monitor:
            distribution = await server.db_monitor.get_repair_status_distribution()
            if distribution:
                logger.info(f"Repair Status Distribution: {json.dumps(distribution, indent=2)}")
            else:
                logger.info("No repair data found (table might not exist)")
        else:
            logger.warning("Database monitor not available")
    except Exception as e:
        logger.error(f"Repair distribution failed: {e}")

    # Test API monitor
    logger.info("\n=== Testing API Monitor ===")
    try:
        if server.api_monitor:
            health = await server.api_monitor.check_health()
            logger.info(f"API Health: {health.status}")
            logger.info(f"Message: {health.message}")
        else:
            logger.warning("API monitor not available")
    except Exception as e:
        logger.error(f"API monitor failed: {e}")

    # Test queue monitor
    logger.info("\n=== Testing Queue Monitor ===")
    try:
        if server.queue_monitor:
            queue_health = await server.queue_monitor.check_health()
            logger.info(f"Queue Health: {queue_health.status}")
            logger.info(f"Message: {queue_health.message}")
        else:
            logger.warning("Queue monitor not available")
    except Exception as e:
        logger.error(f"Queue monitor failed: {e}")

    # Test activity monitor
    logger.info("\n=== Testing Activity Monitor ===")
    try:
        if server.activity_monitor:
            activity = await server.activity_monitor.check_health()
            logger.info(f"Activity Monitor Health: {activity.status}")
            logger.info(f"Message: {activity.message}")
        else:
            logger.warning("Activity monitor not available")
    except Exception as e:
        logger.error(f"Activity monitor failed: {e}")

    # Test alert manager
    logger.info("\n=== Testing Alert Manager ===")
    try:
        if server.alert_manager:
            alerts = server.alert_manager.get_active_alerts()
            logger.info(f"Active alerts: {len(alerts)}")
            for alert in alerts[:3]:  # Show first 3 alerts
                logger.info(f"  Alert: {alert.get('component', 'unknown')} - {alert.get('severity', 'unknown')}")
        else:
            logger.warning("Alert manager not available")
    except Exception as e:
        logger.error(f"Alert manager failed: {e}")

    logger.info("\n=== Server Test Complete ===")


if __name__ == "__main__":
    asyncio.run(test_server())