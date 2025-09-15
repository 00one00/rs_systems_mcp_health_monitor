"""Basic tests for RS Systems Health Monitor."""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.monitors.database import DatabaseMonitor
from src.monitors.api import APIMonitor
from src.monitors.queue import QueueMonitor
from src.monitors.storage import StorageMonitor
from src.monitors.activity import ActivityMonitor
from src.alerts import AlertManager
from src.config import settings


class TestDatabaseMonitor:
    """Test database monitoring functionality."""

    @pytest.fixture
    def mock_db_monitor(self):
        """Create a mock database monitor."""
        with patch('src.monitors.database.psycopg2.pool.ThreadedConnectionPool'):
            monitor = DatabaseMonitor()
            return monitor

    @pytest.mark.asyncio
    async def test_health_check(self, mock_db_monitor):
        """Test database health check."""
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        with patch.object(mock_db_monitor, 'get_connection') as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = mock_conn

            result = await mock_db_monitor.check_health()

            assert result.component == "database"
            assert result.status in ["healthy", "unhealthy"]
            assert result.message is not None

    @pytest.mark.asyncio
    async def test_slow_queries(self, mock_db_monitor):
        """Test slow query detection."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            ("SELECT * FROM test", "active", datetime.now(), 1500.0, "user", "db", "127.0.0.1")
        ]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        with patch.object(mock_db_monitor, 'get_connection') as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = mock_conn

            slow_queries = await mock_db_monitor.get_slow_queries()

            assert isinstance(slow_queries, list)


class TestAPIMonitor:
    """Test API monitoring functionality."""

    @pytest.fixture
    def api_monitor(self):
        """Create API monitor instance."""
        return APIMonitor()

    @pytest.mark.asyncio
    async def test_health_check(self, api_monitor):
        """Test API health check."""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = Mock()
            mock_response.status = 200
            mock_session.return_value.__aenter__.return_value.request.return_value.__aenter__.return_value = mock_response

            result = await api_monitor.check_health()

            assert result.component == "api"
            assert result.status in ["healthy", "degraded", "unhealthy"]

    def test_calculate_metrics(self, api_monitor):
        """Test metrics calculation."""
        # Add some test data
        api_monitor.response_times["/api/test/"].extend([100, 200, 300])
        api_monitor.request_counts["/api/test/"] = 3
        api_monitor.error_counts["/api/test/"] = 1

        metrics = api_monitor.calculate_metrics()

        assert "endpoints" in metrics
        assert "summary" in metrics
        assert metrics["summary"]["total_requests"] == 3
        assert metrics["summary"]["total_errors"] == 1


class TestQueueMonitor:
    """Test queue monitoring functionality."""

    @pytest.fixture
    def mock_queue_monitor(self):
        """Create a mock queue monitor."""
        mock_db_monitor = Mock()
        return QueueMonitor(mock_db_monitor)

    @pytest.mark.asyncio
    async def test_health_check(self, mock_queue_monitor):
        """Test queue health check."""
        # Mock the methods
        mock_queue_monitor.get_queue_status = Mock(return_value={"PENDING": {"count": 5}})
        mock_queue_monitor.get_stuck_repairs = Mock(return_value=[])

        result = await mock_queue_monitor.check_health()

        assert result.component == "queue"
        assert result.status in ["healthy", "degraded", "unhealthy"]


class TestStorageMonitor:
    """Test storage monitoring functionality."""

    @pytest.fixture
    def mock_storage_monitor(self):
        """Create a mock storage monitor."""
        with patch('boto3.client'):
            monitor = StorageMonitor()
            monitor.s3_client = Mock()
            return monitor

    @pytest.mark.asyncio
    async def test_health_check(self, mock_storage_monitor):
        """Test S3 health check."""
        # Mock successful head_bucket call
        mock_storage_monitor.s3_client.head_bucket.return_value = {}

        result = await mock_storage_monitor.check_health()

        assert result.component == "storage"
        assert result.status in ["healthy", "unhealthy"]

    @pytest.mark.asyncio
    async def test_get_bucket_size(self, mock_storage_monitor):
        """Test bucket size calculation."""
        # Mock paginator
        mock_paginator = Mock()
        mock_page = {
            'Contents': [
                {'Key': 'test1.jpg', 'Size': 1024},
                {'Key': 'test2.jpg', 'Size': 2048}
            ]
        }
        mock_paginator.paginate.return_value = [mock_page]
        mock_storage_monitor.s3_client.get_paginator.return_value = mock_paginator

        result = await mock_storage_monitor.get_bucket_size()

        assert "total_size_bytes" in result
        assert result["total_size_bytes"] == 3072
        assert result["object_count"] == 2


class TestActivityMonitor:
    """Test activity monitoring functionality."""

    @pytest.fixture
    def mock_activity_monitor(self):
        """Create a mock activity monitor."""
        mock_db_monitor = Mock()
        return ActivityMonitor(mock_db_monitor)

    @pytest.mark.asyncio
    async def test_health_check(self, mock_activity_monitor):
        """Test activity health check."""
        # Mock the get_active_users method
        mock_activity_monitor.get_active_users = Mock(return_value={
            "total_users": 100,
            "active_users_30d": 80,
            "active_technicians_today": 5
        })

        result = await mock_activity_monitor.check_health()

        assert result.component == "activity"
        assert result.status in ["healthy", "degraded", "unhealthy"]


class TestAlertManager:
    """Test alert management functionality."""

    @pytest.fixture
    def alert_manager(self):
        """Create alert manager instance."""
        return AlertManager()

    @pytest.mark.asyncio
    async def test_create_alert(self, alert_manager):
        """Test alert creation."""
        alert = await alert_manager.create_alert(
            severity="warning",
            component="test",
            title="Test Alert",
            message="This is a test alert"
        )

        assert alert.severity == "warning"
        assert alert.component == "test"
        assert alert.title == "Test Alert"
        assert alert.id in alert_manager.active_alerts

    @pytest.mark.asyncio
    async def test_resolve_alert(self, alert_manager):
        """Test alert resolution."""
        # Create an alert first
        alert = await alert_manager.create_alert(
            severity="info",
            component="test",
            title="Test Alert",
            message="Test message"
        )

        # Resolve it
        await alert_manager.resolve_alert(alert.id)

        assert alert.id not in alert_manager.active_alerts
        assert alert.is_resolved is True
        assert alert.resolved_at is not None

    def test_alert_summary(self, alert_manager):
        """Test alert summary generation."""
        summary = alert_manager.get_alert_summary()

        assert "active_alerts_count" in summary
        assert "severity_breakdown" in summary
        assert "component_breakdown" in summary


@pytest.mark.asyncio
async def test_configuration_validation():
    """Test configuration validation."""
    # This test would validate that the configuration system works correctly
    assert hasattr(settings, 'database')
    assert hasattr(settings, 'aws')
    assert hasattr(settings, 'thresholds')
    assert hasattr(settings, 'alerts')


if __name__ == "__main__":
    pytest.main([__file__])