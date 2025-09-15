# Multi-stage build for RS Systems Health Monitor
FROM python:3.11-slim as builder

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# Production stage
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r rshealth && useradd -r -g rshealth rshealth

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Set working directory
WORKDIR /app

# Copy application code
COPY src/ ./src/
COPY .env ./.env
COPY mcp-catalog.json ./mcp-catalog.json
COPY mcp-registry.json ./mcp-registry.json

# Create logs directory
RUN mkdir -p /var/log/rs-health-monitor && \
    chown -R rshealth:rshealth /var/log/rs-health-monitor

# Create database directory for mounting
RUN mkdir -p /app/data && \
    chown -R rshealth:rshealth /app/data

# Set proper permissions
RUN chown -R rshealth:rshealth /app

# Switch to non-root user
USER rshealth

# Environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Expose MCP server port (if using TCP transport)
EXPOSE 8080

# Default command
CMD ["python", "-m", "src.server"]