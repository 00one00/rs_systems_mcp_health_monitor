#!/bin/bash
# Startup script for RS Health Monitor MCP Server (Docker version)

# Set the working directory to the script location
cd "$(dirname "$0")"

# Ensure logs directory exists
mkdir -p logs

# Stop any existing container
docker stop rs-health-monitor-mcp 2>/dev/null || true
docker rm rs-health-monitor-mcp 2>/dev/null || true

# Run the MCP server container
docker run --rm --name rs-health-monitor-mcp \
  -v "$(pwd)/logs:/var/log/rs-health-monitor" \
  -v "$(pwd)/.env:/app/.env:ro" \
  -v "/Users/drakeduncan/projects/rs_systems_branch2/db.sqlite3:/app/data/db.sqlite3:ro" \
  -v "$(pwd)/mcp-catalog.json:/app/mcp-catalog.json:ro" \
  -v "$(pwd)/mcp-registry.json:/app/mcp-registry.json:ro" \
  -e MCP_CATALOG_PATH="/app/mcp-catalog.json" \
  -e MCP_REGISTRY_PATH="/app/mcp-registry.json" \
  rs-health-monitor