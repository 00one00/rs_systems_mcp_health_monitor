"""Configuration management for RS Systems Health Monitor."""

import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from dotenv import load_dotenv

load_dotenv()


class DatabaseConfig(BaseSettings):
    """Database configuration settings."""

    database_url: str = Field(
        default=os.getenv("DATABASE_URL", ""),
        description="PostgreSQL connection URL"
    )
    db_host: str = Field(default=os.getenv("DB_HOST", "localhost"))
    db_port: int = Field(default=int(os.getenv("DB_PORT", "5432")))
    db_name: str = Field(default=os.getenv("DB_NAME", "rs_systems"))
    db_user: str = Field(default=os.getenv("DB_USER", ""))
    db_password: str = Field(default=os.getenv("DB_PASSWORD", ""))
    connection_pool_size: int = Field(default=int(os.getenv("CONNECTION_POOL_SIZE", "20")))
    query_timeout_seconds: int = Field(default=int(os.getenv("QUERY_TIMEOUT_SECONDS", "30")))

    @validator("database_url", pre=True, always=True)
    def build_database_url(cls, v, values):
        """Build database URL from individual components if not provided."""
        if v:
            return v

        host = values.get("db_host", "localhost")
        port = values.get("db_port", 5432)
        name = values.get("db_name", "rs_systems")
        user = values.get("db_user", "")
        password = values.get("db_password", "")

        if user and password:
            return f"postgresql://{user}:{password}@{host}:{port}/{name}"
        return f"postgresql://{host}:{port}/{name}"

    class Config:
        env_prefix = "DB_"


class AWSConfig(BaseSettings):
    """AWS configuration settings."""

    access_key_id: str = Field(default=os.getenv("AWS_ACCESS_KEY_ID", ""))
    secret_access_key: str = Field(default=os.getenv("AWS_SECRET_ACCESS_KEY", ""))
    region: str = Field(default=os.getenv("AWS_REGION", "us-east-1"))
    s3_bucket_name: str = Field(default=os.getenv("S3_BUCKET_NAME", "rs-systems-media"))
    s3_damage_photos_prefix: str = Field(
        default=os.getenv("S3_DAMAGE_PHOTOS_PREFIX", "damage-photos/")
    )

    class Config:
        env_prefix = "AWS_"


class MonitoringThresholds(BaseSettings):
    """Monitoring threshold settings."""

    # Database thresholds
    db_query_ms: int = Field(
        default=int(os.getenv("ALERT_THRESHOLD_DB_QUERY_MS", "500"))
    )
    db_connections_pct: int = Field(
        default=int(os.getenv("ALERT_THRESHOLD_DB_CONNECTIONS_PCT", "80"))
    )
    db_lock_wait_ms: int = Field(
        default=int(os.getenv("ALERT_THRESHOLD_DB_LOCK_WAIT_MS", "1000"))
    )

    # Queue thresholds
    queue_stuck_hours: int = Field(
        default=int(os.getenv("ALERT_THRESHOLD_QUEUE_STUCK_HOURS", "24"))
    )
    queue_depth: int = Field(
        default=int(os.getenv("ALERT_THRESHOLD_QUEUE_DEPTH", "100"))
    )
    pending_repairs: int = Field(
        default=int(os.getenv("ALERT_THRESHOLD_PENDING_REPAIRS", "50"))
    )

    # API thresholds
    api_response_ms: int = Field(
        default=int(os.getenv("ALERT_THRESHOLD_API_RESPONSE_MS", "2000"))
    )
    api_error_rate_pct: int = Field(
        default=int(os.getenv("ALERT_THRESHOLD_API_ERROR_RATE_PCT", "5"))
    )
    api_requests_per_min: int = Field(
        default=int(os.getenv("ALERT_THRESHOLD_API_REQUESTS_PER_MIN", "1000"))
    )

    # Storage thresholds
    s3_storage_gb: int = Field(
        default=int(os.getenv("ALERT_THRESHOLD_S3_STORAGE_GB", "100"))
    )
    s3_cost_usd: int = Field(
        default=int(os.getenv("ALERT_THRESHOLD_S3_COST_USD", "500"))
    )
    photo_size_mb: int = Field(
        default=int(os.getenv("ALERT_THRESHOLD_PHOTO_SIZE_MB", "10"))
    )

    # Activity thresholds
    inactive_technicians_hours: int = Field(
        default=int(os.getenv("ALERT_THRESHOLD_INACTIVE_TECHNICIANS_HOURS", "2"))
    )
    low_activity_hours: int = Field(
        default=int(os.getenv("ALERT_THRESHOLD_LOW_ACTIVITY_HOURS", "4"))
    )

    class Config:
        env_prefix = "ALERT_THRESHOLD_"


class AlertConfig(BaseSettings):
    """Alert configuration settings."""

    enabled: bool = Field(default=os.getenv("ALERT_ENABLED", "true").lower() == "true")
    cooldown_minutes: int = Field(default=int(os.getenv("ALERT_COOLDOWN_MINUTES", "15")))

    # Slack configuration
    slack_webhook_url: Optional[str] = Field(default=os.getenv("SLACK_WEBHOOK_URL"))
    slack_channel: str = Field(default=os.getenv("SLACK_CHANNEL", "#rs-systems-alerts"))
    slack_username: str = Field(default=os.getenv("SLACK_USERNAME", "RS Health Monitor"))

    # Email configuration
    email_enabled: bool = Field(
        default=os.getenv("EMAIL_ALERT_ENABLED", "false").lower() == "true"
    )
    email_from: str = Field(default=os.getenv("EMAIL_ALERT_FROM", "monitoring@rssystems.com"))
    email_to: List[str] = Field(default_factory=lambda: [
        email.strip()
        for email in os.getenv("EMAIL_ALERT_TO", "admin@rssystems.com").split(",")
    ])
    email_smtp_host: str = Field(default=os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com"))
    email_smtp_port: int = Field(default=int(os.getenv("EMAIL_SMTP_PORT", "587")))
    email_smtp_user: Optional[str] = Field(default=os.getenv("EMAIL_SMTP_USER"))
    email_smtp_password: Optional[str] = Field(default=os.getenv("EMAIL_SMTP_PASSWORD"))

    class Config:
        env_prefix = "ALERT_"


class MCPConfig(BaseSettings):
    """MCP server configuration settings."""

    server_name: str = Field(default=os.getenv("MCP_SERVER_NAME", "rs-health-monitor"))
    server_version: str = Field(default=os.getenv("MCP_SERVER_VERSION", "1.0.0"))
    server_port: int = Field(default=int(os.getenv("MCP_SERVER_PORT", "8080")))
    websocket_enabled: bool = Field(
        default=os.getenv("MCP_WEBSOCKET_ENABLED", "true").lower() == "true"
    )
    websocket_port: int = Field(default=int(os.getenv("MCP_WEBSOCKET_PORT", "8081")))

    class Config:
        env_prefix = "MCP_"


class MonitoringConfig(BaseSettings):
    """General monitoring configuration."""

    interval_seconds: int = Field(
        default=int(os.getenv("MONITORING_INTERVAL_SECONDS", "30"))
    )
    health_check_interval_seconds: int = Field(
        default=int(os.getenv("HEALTH_CHECK_INTERVAL_SECONDS", "60"))
    )
    metrics_retention_days: int = Field(
        default=int(os.getenv("METRICS_RETENTION_DAYS", "30"))
    )
    max_concurrent_monitors: int = Field(
        default=int(os.getenv("MAX_CONCURRENT_MONITORS", "5"))
    )

    class Config:
        env_prefix = "MONITORING_"


class FeatureFlags(BaseSettings):
    """Feature flag settings."""

    enable_database_monitoring: bool = Field(
        default=os.getenv("ENABLE_DATABASE_MONITORING", "true").lower() == "true"
    )
    enable_api_monitoring: bool = Field(
        default=os.getenv("ENABLE_API_MONITORING", "true").lower() == "true"
    )
    enable_queue_monitoring: bool = Field(
        default=os.getenv("ENABLE_QUEUE_MONITORING", "true").lower() == "true"
    )
    enable_s3_monitoring: bool = Field(
        default=os.getenv("ENABLE_S3_MONITORING", "true").lower() == "true"
    )
    enable_activity_monitoring: bool = Field(
        default=os.getenv("ENABLE_ACTIVITY_MONITORING", "true").lower() == "true"
    )
    enable_predictive_alerts: bool = Field(
        default=os.getenv("ENABLE_PREDICTIVE_ALERTS", "false").lower() == "true"
    )

    class Config:
        env_prefix = "ENABLE_"


class LoggingConfig(BaseSettings):
    """Logging configuration settings."""

    level: str = Field(default=os.getenv("LOG_LEVEL", "INFO"))
    file_path: str = Field(
        default=os.getenv("LOG_FILE_PATH", "/var/log/rs-health-monitor/health.log")
    )
    max_size_mb: int = Field(default=int(os.getenv("LOG_MAX_SIZE_MB", "100")))
    backup_count: int = Field(default=int(os.getenv("LOG_BACKUP_COUNT", "5")))

    class Config:
        env_prefix = "LOG_"


class Settings:
    """Main settings class combining all configurations."""

    def __init__(self):
        self.database = DatabaseConfig()
        self.aws = AWSConfig()
        self.thresholds = MonitoringThresholds()
        self.alerts = AlertConfig()
        self.mcp = MCPConfig()
        self.monitoring = MonitoringConfig()
        self.features = FeatureFlags()
        self.logging = LoggingConfig()

        # Environment
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.is_production = self.environment == "production"
        self.is_development = self.environment == "development"

        # Django settings
        self.django_settings_module = os.getenv("DJANGO_SETTINGS_MODULE", "rs_systems.settings")
        self.django_secret_key = os.getenv("DJANGO_SECRET_KEY", "")

        # Redis (optional)
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_enabled = os.getenv("REDIS_ENABLED", "false").lower() == "true"

        # Security
        self.api_key = os.getenv("API_KEY", "")
        self.enable_ssl_verification = os.getenv("ENABLE_SSL_VERIFICATION", "true").lower() == "true"

    def validate(self) -> bool:
        """Validate required settings."""
        errors = []

        # Check database configuration
        if not self.database.database_url and not (self.database.db_user and self.database.db_password):
            errors.append("Database configuration is incomplete")

        # Check AWS configuration if S3 monitoring is enabled
        if self.features.enable_s3_monitoring:
            if not self.aws.access_key_id or not self.aws.secret_access_key:
                errors.append("AWS credentials are required for S3 monitoring")

        # Check alert configuration
        if self.alerts.enabled:
            if not self.alerts.slack_webhook_url and not self.alerts.email_enabled:
                errors.append("At least one alert channel must be configured")

        if errors:
            print("Configuration errors:")
            for error in errors:
                print(f"  - {error}")
            return False

        return True


# Global settings instance
settings = Settings()