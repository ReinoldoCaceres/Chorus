from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from decimal import Decimal


# Health Check Schemas
class HealthResponse(BaseModel):
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    service: str = "Process Monitor API"
    version: str = "1.0.0"


class ServiceHealthCheck(BaseModel):
    service_name: str
    endpoint: str
    status: str  # healthy, unhealthy, timeout
    response_time_ms: Optional[int] = None
    last_checked: datetime
    error_message: Optional[str] = None


# System Metrics Schemas
class SystemMetricBase(BaseModel):
    hostname: str
    metric_type: str
    metric_value: Decimal
    metric_unit: Optional[str] = None
    tags: Dict[str, Any] = Field(default_factory=dict)


class SystemMetricCreate(SystemMetricBase):
    pass


class SystemMetricResponse(SystemMetricBase):
    id: UUID
    timestamp: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


# Process Metrics Schemas
class ProcessMetricBase(BaseModel):
    process_id: int
    process_name: str
    hostname: str
    cpu_percent: Optional[Decimal] = None
    memory_mb: Optional[Decimal] = None
    memory_percent: Optional[Decimal] = None
    disk_read_bytes: Optional[int] = None
    disk_write_bytes: Optional[int] = None
    network_sent_bytes: Optional[int] = None
    network_recv_bytes: Optional[int] = None
    status: Optional[str] = None


class ProcessMetricCreate(ProcessMetricBase):
    pass


class ProcessMetricResponse(ProcessMetricBase):
    id: UUID
    timestamp: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


# Alert Schemas
class AlertBase(BaseModel):
    alert_type: str
    severity: str = Field(..., pattern="^(critical|high|medium|low|info)$")
    source: str
    title: str
    description: Optional[str] = None
    alert_metadata: Dict[str, Any] = Field(default_factory=dict)


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(active|acknowledged|resolved|suppressed)$")
    acknowledged_by: Optional[str] = None
    resolved_by: Optional[str] = None


class AlertResponse(AlertBase):
    id: UUID
    status: str
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Alert Rule Schemas
class AlertRuleBase(BaseModel):
    name: str
    description: Optional[str] = None
    rule_type: str
    condition: Dict[str, Any]
    severity: str = Field(..., pattern="^(critical|high|medium|low|info)$")
    notification_channels: List[str] = Field(default_factory=list)
    cooldown_minutes: int = Field(default=5, ge=0)
    is_active: bool = True


class AlertRuleCreate(AlertRuleBase):
    pass


class AlertRuleUpdate(BaseModel):
    description: Optional[str] = None
    condition: Optional[Dict[str, Any]] = None
    severity: Optional[str] = Field(None, pattern="^(critical|high|medium|low|info)$")
    notification_channels: Optional[List[str]] = None
    cooldown_minutes: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class AlertRuleResponse(AlertRuleBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Metrics Dashboard Schemas
class SystemOverview(BaseModel):
    hostname: str
    cpu_usage: Optional[Decimal] = None
    memory_usage: Optional[Decimal] = None
    disk_usage: Optional[Decimal] = None
    network_io: Optional[Dict[str, int]] = None
    process_count: int
    uptime_seconds: Optional[int] = None
    last_updated: datetime


class MetricsQuery(BaseModel):
    metric_type: Optional[str] = None
    hostname: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


# Alert Statistics
class AlertStats(BaseModel):
    total_alerts: int
    active_alerts: int
    acknowledged_alerts: int
    resolved_alerts: int
    critical_alerts: int
    high_alerts: int
    medium_alerts: int
    low_alerts: int
    info_alerts: int