"""Django model definitions for RS Systems monitoring."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class RepairStatus(str, Enum):
    """Repair status choices matching Django model."""

    REQUESTED = "REQUESTED"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    DENIED = "DENIED"


class DamageType(str, Enum):
    """Damage type choices for repairs."""

    CHIP = "Chip"
    CRACK = "Crack"
    STAR_BREAK = "Star Break"
    BULLS_EYE = "Bull's Eye"
    COMBINATION = "Combination"
    OTHER = "Other"


class CustomerModel(BaseModel):
    """Customer model representation."""

    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_active: bool = True

    class Config:
        orm_mode = True


class TechnicianModel(BaseModel):
    """Technician model representation."""

    id: int
    user_id: int
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_repair_date: Optional[datetime] = None
    total_repairs: int = 0

    class Config:
        orm_mode = True


class RepairModel(BaseModel):
    """Repair model representation."""

    id: int
    technician_id: int
    customer_id: int
    unit_number: str
    repair_date: datetime
    queue_status: RepairStatus
    damage_type: DamageType
    damage_photo_before: Optional[str] = None
    damage_photo_after: Optional[str] = None
    customer_notes: Optional[str] = None
    technician_notes: Optional[str] = None
    drilled_before_repair: bool = False
    cost: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    completion_time: Optional[datetime] = None
    points_awarded: int = 0

    class Config:
        orm_mode = True


class UserModel(BaseModel):
    """Django User model representation."""

    id: int
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = True
    is_staff: bool = False
    is_superuser: bool = False
    last_login: Optional[datetime] = None
    date_joined: datetime

    class Config:
        orm_mode = True


class RewardModel(BaseModel):
    """Reward model representation."""

    id: int
    customer_id: int
    point_balance: int = 0
    total_points_earned: int = 0
    total_points_redeemed: int = 0
    last_earned_date: Optional[datetime] = None
    last_redeemed_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class SystemMetrics(BaseModel):
    """System-wide metrics for monitoring."""

    # Repair metrics
    total_repairs: int = 0
    pending_repairs: int = 0
    in_progress_repairs: int = 0
    completed_repairs_today: int = 0
    average_repair_time_hours: float = 0.0
    stuck_repairs: List[int] = Field(default_factory=list)

    # Customer metrics
    total_customers: int = 0
    active_customers_30d: int = 0
    new_customers_today: int = 0

    # Technician metrics
    total_technicians: int = 0
    active_technicians_today: int = 0
    inactive_technicians: List[int] = Field(default_factory=list)

    # Database metrics
    db_connection_count: int = 0
    db_connection_pool_usage_pct: float = 0.0
    slow_query_count: int = 0
    slow_queries: List[Dict[str, Any]] = Field(default_factory=list)

    # API metrics
    api_request_count: int = 0
    api_error_count: int = 0
    api_error_rate_pct: float = 0.0
    api_avg_response_time_ms: float = 0.0
    api_endpoints_health: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    # Storage metrics
    s3_total_size_gb: float = 0.0
    s3_object_count: int = 0
    s3_estimated_cost_usd: float = 0.0
    s3_large_files: List[Dict[str, Any]] = Field(default_factory=list)

    # System health
    overall_health_score: float = 100.0
    health_status: str = "HEALTHY"
    active_alerts: List[Dict[str, Any]] = Field(default_factory=list)
    last_check_timestamp: datetime = Field(default_factory=datetime.now)


class HealthCheckResult(BaseModel):
    """Health check result for a specific component."""

    component: str
    status: str  # "healthy", "degraded", "unhealthy"
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    response_time_ms: Optional[float] = None


class Alert(BaseModel):
    """Alert model for system notifications."""

    id: str
    severity: str  # "info", "warning", "critical"
    component: str
    title: str
    message: str
    threshold_value: Optional[float] = None
    actual_value: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    is_resolved: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MonitoringQuery(BaseModel):
    """Query parameters for monitoring requests."""

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    component: Optional[str] = None
    metric_type: Optional[str] = None
    limit: int = 100
    offset: int = 0
    include_details: bool = False