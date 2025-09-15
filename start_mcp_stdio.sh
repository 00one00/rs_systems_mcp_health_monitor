#!/bin/bash
# Startup script for RS Health Monitor MCP Server (stdio mode for Claude Desktop)

# Set the working directory to the script location
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Set environment variables
export PYTHONPATH="$(pwd)"
export PYTHONUNBUFFERED=1

# Run the MCP server in stdio mode (not Docker)
python3 -m src.server