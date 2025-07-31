from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class NotificationChannel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    SLACK = "slack"
    TEAMS = "teams"


class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Template schemas
class NotificationTemplateBase(BaseModel):
    name: str = Field(..., max_length=255)
    channel: NotificationChannel
    subject: Optional[str] = Field(None, max_length=500)
    body_template: str
    variables: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class NotificationTemplateCreate(NotificationTemplateBase):
    tenant_id: UUID


class NotificationTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    channel: Optional[NotificationChannel] = None
    subject: Optional[str] = Field(None, max_length=500)
    body_template: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class NotificationTemplate(NotificationTemplateBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None


# Notification schemas
class NotificationBase(BaseModel):
    channel: NotificationChannel
    recipient: str = Field(..., max_length=255)
    subject: Optional[str] = Field(None, max_length=500)
    body: str
    data: Dict[str, Any] = Field(default_factory=dict)
    scheduled_at: Optional[datetime] = None


class NotificationCreate(NotificationBase):
    tenant_id: UUID
    template_id: Optional[UUID] = None


class NotificationCreateFromTemplate(BaseModel):
    tenant_id: UUID
    template_id: UUID
    recipient: str = Field(..., max_length=255)
    variables: Dict[str, Any] = Field(default_factory=dict)
    scheduled_at: Optional[datetime] = None


class NotificationUpdate(BaseModel):
    status: Optional[NotificationStatus] = None
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None


class Notification(NotificationBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    tenant_id: UUID
    template_id: Optional[UUID] = None
    status: NotificationStatus
    error_message: Optional[str] = None
    retry_count: int
    max_retries: int
    sent_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# Subscription schemas
class NotificationSubscriptionBase(BaseModel):
    event_type: str = Field(..., max_length=100)
    channel: NotificationChannel
    endpoint: str = Field(..., max_length=500)
    is_active: bool = True
    preferences: Dict[str, Any] = Field(default_factory=dict)


class NotificationSubscriptionCreate(NotificationSubscriptionBase):
    tenant_id: UUID
    user_id: UUID


class NotificationSubscriptionUpdate(BaseModel):
    event_type: Optional[str] = Field(None, max_length=100)
    channel: Optional[NotificationChannel] = None
    endpoint: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None
    preferences: Optional[Dict[str, Any]] = None


class NotificationSubscription(NotificationSubscriptionBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    tenant_id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime


# API response schemas
class NotificationListResponse(BaseModel):
    notifications: List[Notification]
    total: int
    page: int
    size: int


class TemplateListResponse(BaseModel):
    templates: List[NotificationTemplate]
    total: int
    page: int
    size: int


class SubscriptionListResponse(BaseModel):
    subscriptions: List[NotificationSubscription]
    total: int
    page: int
    size: int


# Delivery result schemas
class DeliveryResult(BaseModel):
    success: bool
    message: str
    external_id: Optional[str] = None
    error_code: Optional[str] = None


class BatchDeliveryResult(BaseModel):
    total: int
    successful: int
    failed: int
    results: List[DeliveryResult]


# Template rendering schemas
class TemplateRenderRequest(BaseModel):
    template_id: UUID
    variables: Dict[str, Any] = Field(default_factory=dict)


class TemplateRenderResponse(BaseModel):
    subject: Optional[str] = None
    body: str
    rendered_variables: Dict[str, Any]