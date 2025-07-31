from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, Numeric, JSON, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


class SystemMetric(Base):
    __tablename__ = "system_metrics"
    __table_args__ = {"schema": "monitoring"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hostname = Column(String(255), nullable=False)
    metric_type = Column(String(100), nullable=False)
    metric_value = Column(Numeric, nullable=False)
    metric_unit = Column(String(50), nullable=True)
    tags = Column(JSON, default={})
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ProcessMetric(Base):
    __tablename__ = "process_metrics" 
    __table_args__ = {"schema": "monitoring"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    process_id = Column(Integer, nullable=False)
    process_name = Column(String(255), nullable=False)
    hostname = Column(String(255), nullable=False)
    cpu_percent = Column(Numeric(5, 2), nullable=True)
    memory_mb = Column(Numeric, nullable=True)
    memory_percent = Column(Numeric(5, 2), nullable=True)
    disk_read_bytes = Column(BigInteger, nullable=True)
    disk_write_bytes = Column(BigInteger, nullable=True)
    network_sent_bytes = Column(BigInteger, nullable=True)
    network_recv_bytes = Column(BigInteger, nullable=True)
    status = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = {"schema": "monitoring"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_type = Column(String(100), nullable=False)
    severity = Column(String(50), nullable=False)
    source = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    alert_metadata = Column(JSON, default={})
    status = Column(String(50), default="active", nullable=False)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(255), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class AlertRule(Base):
    __tablename__ = "alert_rules"
    __table_args__ = {"schema": "monitoring"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    rule_type = Column(String(100), nullable=False)
    condition = Column(JSON, nullable=False)
    severity = Column(String(50), nullable=False)
    notification_channels = Column(JSON, default=[])
    cooldown_minutes = Column(Integer, default=5)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)