#!/usr/bin/env python3
"""Comprehensive test of all MCP tools from end-user perspective."""

import asyncio
import json
import time
import logging
from datetime import datetime
from src.server import RSHealthMonitorServer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MCPToolsTester:
    """Test all MCP tools to validate end-user experience."""

    def __init__(self):
        self.server = RSHealthMonitorServer()
        self.test_results = {}
        self.performance_metrics = {}

    def log_test_result(self, tool_name: str, status: str, message: str, data=None, response_time=None):
        """Log test result for later analysis."""
        self.test_results[tool_name] = {
            "status": status,
            "message": message,
            "data": data,
            "response_time_ms": response_time,
            "timestamp": datetime.now().isoformat()
        }

    async def measure_performance(self, tool_name: str, coro):
        """Measure performance of a tool execution."""
        start_time = time.time()
        try:
            result = await coro
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            return result, response_time
        except Exception as e:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            raise e

    async def test_system_health_summary(self):
        """Test: Get comprehensive system health summary."""
        print("\n" + "="*60)
        print("🔍 Testing: system_health_summary")
        print("="*60)

        try:
            # Test basic health summary
            result, response_time = await self.measure_performance(
                "system_health_summary",
                self.server._system_health_summary({})
            )

            print(f"✅ Response Time: {response_time:.2f}ms")
            print(f"📊 Health Summary:")

            if hasattr(result, 'content') and result.content:
                for content in result.content:
                    if hasattr(content, 'text'):
                        health_data = json.loads(content.text)
                        print(f"   Overall Status: {health_data.get('overall_status', 'Unknown')}")
                        print(f"   Components Checked: {len(health_data.get('components', {}))}")
                        for component, status in health_data.get('components', {}).items():
                            print(f"   - {component}: {status.get('status', 'Unknown')}")

            self.log_test_result("system_health_summary", "PASS", "Successfully retrieved health summary",
                               response_time=response_time)

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            self.log_test_result("system_health_summary", "FAIL", str(e))

    async def test_database_performance(self):
        """Test: Check database performance monitoring."""
        print("\n" + "="*60)
        print("🗄️  Testing: check_database_performance")
        print("="*60)

        try:
            result, response_time = await self.measure_performance(
                "check_database_performance",
                self.server._check_database_performance({"include_slow_queries": True})
            )

            print(f"✅ Response Time: {response_time:.2f}ms")
            print(f"📈 Database Performance:")

            if hasattr(result, 'content') and result.content:
                for content in result.content:
                    if hasattr(content, 'text'):
                        db_data = json.loads(content.text)
                        print(f"   Database Type: {db_data.get('database_type', 'Unknown')}")
                        print(f"   Health Status: {db_data.get('health', {}).get('status', 'Unknown')}")
                        print(f"   Connection Stats Available: {'connection_stats' in db_data}")
                        print(f"   Table Stats Count: {len(db_data.get('table_stats', []))}")

            self.log_test_result("check_database_performance", "PASS", "Database performance check completed",
                               response_time=response_time)

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            self.log_test_result("check_database_performance", "FAIL", str(e))

    async def test_repair_queue(self):
        """Test: Monitor repair queue status."""
        print("\n" + "="*60)
        print("🔧 Testing: monitor_repair_queue")
        print("="*60)

        try:
            result, response_time = await self.measure_performance(
                "monitor_repair_queue",
                self.server._monitor_repair_queue({"include_stuck_repairs": True})
            )

            print(f"✅ Response Time: {response_time:.2f}ms")
            print(f"🔄 Queue Monitoring:")

            if hasattr(result, 'content') and result.content:
                for content in result.content:
                    if hasattr(content, 'text'):
                        queue_data = json.loads(content.text)
                        print(f"   Queue Health: {queue_data.get('health', {}).get('status', 'Unknown')}")
                        print(f"   Queue Status Available: {'queue_status' in queue_data}")
                        print(f"   Stuck Repairs Check: {'stuck_repairs' in queue_data}")

            self.log_test_result("monitor_repair_queue", "PASS", "Repair queue monitoring completed",
                               response_time=response_time)

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            self.log_test_result("monitor_repair_queue", "FAIL", str(e))

    async def test_api_performance(self):
        """Test: Check API performance."""
        print("\n" + "="*60)
        print("🌐 Testing: check_api_performance")
        print("="*60)

        try:
            result, response_time = await self.measure_performance(
                "check_api_performance",
                self.server._check_api_performance({})
            )

            print(f"✅ Response Time: {response_time:.2f}ms")
            print(f"🚀 API Performance:")

            if hasattr(result, 'content') and result.content:
                for content in result.content:
                    if hasattr(content, 'text'):
                        api_data = json.loads(content.text)
                        print(f"   API Health: {api_data.get('health', {}).get('status', 'Unknown')}")
                        print(f"   Metrics Available: {'metrics' in api_data}")

            self.log_test_result("check_api_performance", "PASS", "API performance check completed",
                               response_time=response_time)

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            self.log_test_result("check_api_performance", "FAIL", str(e))

    async def test_s3_usage(self):
        """Test: Analyze S3 storage usage."""
        print("\n" + "="*60)
        print("☁️  Testing: analyze_s3_usage")
        print("="*60)

        try:
            result, response_time = await self.measure_performance(
                "analyze_s3_usage",
                self.server._analyze_s3_usage({})
            )

            print(f"✅ Response Time: {response_time:.2f}ms")
            print(f"📦 S3 Storage Analysis:")

            if hasattr(result, 'content') and result.content:
                for content in result.content:
                    if hasattr(content, 'text'):
                        s3_data = json.loads(content.text)
                        if 'error' in s3_data:
                            print(f"   ⚠️  S3 Monitoring Disabled: {s3_data['error']}")
                        else:
                            print(f"   S3 Health: {s3_data.get('health', {}).get('status', 'Unknown')}")

            self.log_test_result("analyze_s3_usage", "PASS", "S3 usage analysis completed (disabled as expected)",
                               response_time=response_time)

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            self.log_test_result("analyze_s3_usage", "FAIL", str(e))

    async def test_user_activity(self):
        """Test: Track user and technician activity."""
        print("\n" + "="*60)
        print("👥 Testing: track_user_activity")
        print("="*60)

        try:
            result, response_time = await self.measure_performance(
                "track_user_activity",
                self.server._track_user_activity({"days": 30})
            )

            print(f"✅ Response Time: {response_time:.2f}ms")
            print(f"📊 User Activity Tracking:")

            if hasattr(result, 'content') and result.content:
                for content in result.content:
                    if hasattr(content, 'text'):
                        activity_data = json.loads(content.text)
                        print(f"   Activity Health: {activity_data.get('health', {}).get('status', 'Unknown')}")
                        print(f"   User Activity Available: {'user_activity' in activity_data}")
                        if 'user_activity' in activity_data:
                            user_stats = activity_data['user_activity']
                            print(f"   Total Users: {user_stats.get('total_users', 0)}")
                            print(f"   Total Technicians: {user_stats.get('total_technicians', 0)}")

            self.log_test_result("track_user_activity", "PASS", "User activity tracking completed",
                               response_time=response_time)

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            self.log_test_result("track_user_activity", "FAIL", str(e))

    async def test_alerts_management(self):
        """Test: Alert management system."""
        print("\n" + "="*60)
        print("🚨 Testing: Alert Management (get_active_alerts)")
        print("="*60)

        try:
            result, response_time = await self.measure_performance(
                "get_active_alerts",
                self.server._get_active_alerts({})
            )

            print(f"✅ Response Time: {response_time:.2f}ms")
            print(f"⚠️  Alert Management:")

            if hasattr(result, 'content') and result.content:
                for content in result.content:
                    if hasattr(content, 'text'):
                        alerts_data = json.loads(content.text)
                        alert_count = len(alerts_data.get('active_alerts', []))
                        print(f"   Active Alerts: {alert_count}")
                        if alert_count > 0:
                            for alert in alerts_data['active_alerts'][:3]:  # Show first 3
                                print(f"   - {alert.get('component', 'Unknown')}: {alert.get('severity', 'Unknown')}")

            self.log_test_result("get_active_alerts", "PASS", "Alert management system working",
                               response_time=response_time)

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            self.log_test_result("get_active_alerts", "FAIL", str(e))

    async def test_background_monitoring(self):
        """Test: Background monitoring start/stop."""
        print("\n" + "="*60)
        print("⏱️  Testing: Background Monitoring (start/stop)")
        print("="*60)

        try:
            # Test start monitoring
            start_result, start_time = await self.measure_performance(
                "start_monitoring",
                self.server._start_monitoring({"interval_seconds": 60})
            )

            print(f"✅ Start Monitoring Response Time: {start_time:.2f}ms")

            # Give it a moment
            await asyncio.sleep(0.1)

            # Test stop monitoring
            stop_result, stop_time = await self.measure_performance(
                "stop_monitoring",
                self.server._stop_monitoring({})
            )

            print(f"✅ Stop Monitoring Response Time: {stop_time:.2f}ms")
            print(f"🔄 Background monitoring start/stop cycle completed")

            self.log_test_result("background_monitoring", "PASS", "Background monitoring controls working",
                               response_time=(start_time + stop_time) / 2)

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            self.log_test_result("background_monitoring", "FAIL", str(e))

    async def run_comprehensive_test(self):
        """Run all MCP tools tests."""
        print("🚀 Starting Comprehensive MCP Tools Testing")
        print("=" * 80)
        print(f"⏰ Test Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🗄️  Database: {self.server.db_monitor.config.database_url if self.server.db_monitor else 'Not available'}")
        print("=" * 80)

        # Run all tests
        await self.test_system_health_summary()
        await self.test_database_performance()
        await self.test_repair_queue()
        await self.test_api_performance()
        await self.test_s3_usage()
        await self.test_user_activity()
        await self.test_alerts_management()
        await self.test_background_monitoring()

        # Print summary
        self.print_test_summary()

    def print_test_summary(self):
        """Print comprehensive test results summary."""
        print("\n" + "="*80)
        print("📋 COMPREHENSIVE TEST RESULTS SUMMARY")
        print("="*80)

        passed = sum(1 for result in self.test_results.values() if result['status'] == 'PASS')
        total = len(self.test_results)

        print(f"✅ Tests Passed: {passed}/{total}")
        print(f"📊 Success Rate: {(passed/total)*100:.1f}%")

        # Performance metrics
        response_times = [result['response_time_ms'] for result in self.test_results.values()
                         if result['response_time_ms'] is not None]
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            min_response_time = min(response_times)

            print(f"\n⚡ Performance Metrics:")
            print(f"   Average Response Time: {avg_response_time:.2f}ms")
            print(f"   Fastest Response: {min_response_time:.2f}ms")
            print(f"   Slowest Response: {max_response_time:.2f}ms")

        # Detailed results
        print(f"\n📝 Detailed Results:")
        for tool_name, result in self.test_results.items():
            status_icon = "✅" if result['status'] == 'PASS' else "❌"
            response_time = f"{result['response_time_ms']:.2f}ms" if result['response_time_ms'] else "N/A"
            print(f"   {status_icon} {tool_name}: {result['status']} ({response_time})")
            if result['status'] == 'FAIL':
                print(f"      Error: {result['message']}")

        print(f"\n🎯 End-User Experience Assessment:")
        if passed == total:
            print("   🌟 EXCELLENT: All MCP tools are working perfectly!")
            print("   🚀 Ready for production use with Claude Desktop")
        elif passed >= total * 0.8:
            print("   👍 GOOD: Most tools working, minor issues present")
            print("   ⚠️  Some features may have limitations")
        else:
            print("   ⚠️  NEEDS IMPROVEMENT: Several tools have issues")
            print("   🔧 Requires additional fixes before deployment")

        print("="*80)


async def main():
    """Run the comprehensive MCP tools test."""
    tester = MCPToolsTester()
    await tester.run_comprehensive_test()


if __name__ == "__main__":
    asyncio.run(main())