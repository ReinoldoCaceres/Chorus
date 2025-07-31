from sqlalchemy import Column, String, DateTime, Text, JSON, Boolean, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


class NotificationTemplate(Base):
    """Notification template model"""
    __tablename__ = "templates"
    __table_args__ = {"schema": "notification"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String(255), nullable=False)
    channel = Column(String(50), nullable=False)  # email, sms, webhook, slack, teams
    subject = Column(String(500))
    body_template = Column(Text, nullable=False)
    variables = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True))


class Notification(Base):
    """Notification model"""
    __tablename__ = "notifications"
    __table_args__ = {"schema": "notification"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    template_id = Column(UUID(as_uuid=True), ForeignKey("notification.templates.id"))
    channel = Column(String(50), nullable=False)  # email, sms, webhook, slack, teams
    recipient = Column(String(255), nullable=False)
    subject = Column(String(500))
    body = Column(Text, nullable=False)
    data = Column(JSON, default=dict)
    status = Column(String(50), default="pending")  # pending, sent, failed, cancelled
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    scheduled_at = Column(DateTime(timezone=True))
    sent_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class NotificationSubscription(Base):
    """Notification subscription model"""
    __tablename__ = "subscriptions"
    __table_args__ = {"schema": "notification"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    event_type = Column(String(100), nullable=False)
    channel = Column(String(50), nullable=False)  # email, sms, webhook, slack, teams
    endpoint = Column(String(500), nullable=False)  # email address, phone number, webhook URL
    is_active = Column(Boolean, default=True)
    preferences = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())