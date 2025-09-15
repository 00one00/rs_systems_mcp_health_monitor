# RS Systems Health Monitor - MCP Server

A Model Context Protocol (MCP) server that provides comprehensive health monitoring for RS Systems windshield repair application. This tool integrates with Claude Desktop to provide real-time monitoring, alerting, and diagnostics through natural language interactions.

## Features

### Core Monitoring Capabilities
- **Database Performance**: PostgreSQL/SQLite monitoring with slow query detection
- **API Health**: Endpoint response times and error rate tracking
- **Repair Queue**: Monitor repair workflow status and stuck repairs
- **AWS S3 Storage**: Track usage, costs, and large file detection
- **User Activity**: Monitor technician and customer activity patterns

### Alert System
- Real-time threshold-based alerts
- Multiple severity levels (Critical, Warning, Info)
- Slack and email notifications
- Alert history and resolution tracking
- Configurable cooldown periods

### MCP Integration
- Full MCP SDK compatibility for Claude Desktop
- Rich tool interface for monitoring commands
- Background monitoring with configurable intervals
- Natural language interaction through Claude

## Prerequisites

- Python 3.11 or higher
- Claude Desktop application
- Access to RS Systems database (PostgreSQL or SQLite)
- AWS credentials for S3 monitoring (optional)
- Slack webhook URL for notifications (optional)

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/00one00/rs_systems_mcp_health_monitor.git
cd rs_systems_mcp_health_monitor
```

### Step 2: Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your configuration
# IMPORTANT: Update database credentials and AWS keys
nano .env  # or use your preferred editor
```

Key configuration settings in `.env`:

```env
# Database Configuration (Required)
DATABASE_URL=sqlite:///path/to/your/db.sqlite3
# Or for PostgreSQL:
# DATABASE_URL=postgresql://username:password@localhost:5432/rs_systems

# AWS Configuration (Optional, for S3 monitoring)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name

# Slack Notifications (Optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Feature Flags - Enable/disable specific monitors
ENABLE_DATABASE_MONITORING=true
ENABLE_API_MONITORING=true
ENABLE_QUEUE_MONITORING=true
ENABLE_S3_MONITORING=true
ENABLE_ACTIVITY_MONITORING=true
```

### Step 4: Configure Claude Desktop

Add the MCP server to your Claude Desktop configuration:

1. Open Claude Desktop settings
2. Navigate to the MCP Servers section
3. Add a new server configuration:

**For macOS/Linux:**
Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "rs-health-monitor": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/rs_systems_mcp_health_monitor",
      "env": {
        "PYTHONPATH": "/path/to/rs_systems_mcp_health_monitor"
      }
    }
  }
}
```

**For Windows:**
Edit `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "rs-health-monitor": {
      "command": "C:\\path\\to\\venv\\Scripts\\python.exe",
      "args": ["-m", "src.server"],
      "cwd": "C:\\path\\to\\rs_systems_mcp_health_monitor",
      "env": {
        "PYTHONPATH": "C:\\path\\to\\rs_systems_mcp_health_monitor"
      }
    }
  }
}
```

### Step 5: Restart Claude Desktop

After configuring, restart Claude Desktop to load the MCP server.

## Usage with Claude

Once configured, you can interact with the health monitor through natural language in Claude Desktop:

### Basic Commands

```
"Check the overall system health"
"Show me database performance metrics"
"Are there any stuck repairs in the queue?"
"Analyze S3 storage usage and costs"
"Track user activity for the last 30 days"
"Show me all critical alerts"
"Start continuous monitoring every 60 seconds"
```

### Example Interactions

**Getting a System Health Summary:**
```
You: "Give me a comprehensive health check of the RS Systems"
Claude: [Uses system_health_summary tool to provide detailed status]
```

**Checking for Issues:**
```
You: "Are there any performance issues with the database?"
Claude: [Uses check_database_performance to analyze and report slow queries]
```

**Managing Alerts:**
```
You: "Show me all active alerts and resolve the one about high API response time"
Claude: [Lists alerts and resolves specified alert]
```

## MCP Tools Reference

The following tools are available through the MCP interface:

### `system_health_summary`
Get a comprehensive overview of system health across all components.

### `check_database_performance`
Monitor database performance, connection pool usage, and slow queries.

### `monitor_repair_queue`
Check repair queue status, stuck repairs, and technician workload.

### `check_api_performance`
Monitor API endpoint response times and error rates.

### `analyze_s3_usage`
Analyze S3 storage usage, costs, and large files.

### `track_user_activity`
Monitor user and technician activity patterns over time.

### `get_active_alerts`
Retrieve current active system alerts with filtering options.

### `start_monitoring`
Begin continuous background monitoring at specified intervals.

### `stop_monitoring`
Stop continuous background monitoring.

### `resolve_alert`
Mark a specific alert as resolved.

## Docker Deployment (Optional)

For production deployments, you can use Docker:

```bash
# Build and run with Docker Compose
docker-compose up -d rs-health-monitor

# Or build manually
docker build -t rs-health-monitor .
docker run -d --name rs-health-monitor \
  --env-file .env \
  -p 8080:8080 \
  rs-health-monitor
```

## Monitoring Thresholds

Default alert thresholds (configurable in `.env`):

- **Database**: Queries >500ms trigger warnings
- **API**: Error rate >5% triggers alerts
- **Queue**: Repairs stuck >24 hours trigger alerts
- **Storage**: S3 usage >100GB triggers notifications
- **Activity**: No technician activity for 2 hours during business hours

## Troubleshooting

### MCP Server Not Connecting

1. Verify Python path in Claude Desktop config
2. Check that virtual environment is properly activated
3. Ensure all dependencies are installed: `pip install -r requirements.txt`
4. Check logs: `tail -f logs/*.log`

### Database Connection Issues

1. Verify database credentials in `.env`
2. Test connection:
   ```bash
   python -c "from src.monitors.database import DatabaseMonitor; import asyncio; asyncio.run(DatabaseMonitor().check_health())"
   ```
3. Ensure database is accessible from your network

### AWS S3 Access Issues

1. Verify AWS credentials in `.env`
2. Test AWS access:
   ```bash
   aws s3 ls s3://your-bucket-name --region us-east-1
   ```
3. Check IAM permissions for the AWS user

### No Data Appearing

1. Check feature flags in `.env` - ensure monitors are enabled
2. Verify data exists in the database
3. Check monitor-specific configurations

## Security Best Practices

1. **Never commit `.env` file** - It contains sensitive credentials
2. **Use environment-specific credentials** - Don't use production credentials in development
3. **Rotate credentials regularly** - Update AWS keys and database passwords periodically
4. **Limit database permissions** - Use read-only access where possible
5. **Secure Slack webhooks** - Keep webhook URLs private
6. **Use HTTPS for APIs** - Ensure all external connections use SSL

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-mock

# Run tests
pytest tests/

# Run with coverage
pytest --cov=src tests/
```

### Code Style

```bash
# Format code
black src/

# Lint code
pylint src/

# Type checking
mypy src/
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and test thoroughly
4. Commit with clear messages: `git commit -m "Add feature: description"`
5. Push to your fork: `git push origin feature-name`
6. Create a Pull Request

## License

MIT License - See LICENSE file for details

## Support

- **Issues**: Report bugs and request features via [GitHub Issues](https://github.com/00one00/rs_systems_mcp_health_monitor/issues)
- **Documentation**: Check the [Wiki](https://github.com/00one00/rs_systems_mcp_health_monitor/wiki) for additional guides
- **MCP Documentation**: Learn more about MCP at [Anthropic's MCP Docs](https://modelcontextprotocol.io)

## Acknowledgments

Built with the [Model Context Protocol SDK](https://github.com/anthropics/mcp) by Anthropic.

---

**RS Systems Health Monitor** - Keeping your windshield repair application running smoothly!