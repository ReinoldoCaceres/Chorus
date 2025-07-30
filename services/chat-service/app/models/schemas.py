from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID


# Base schemas
class MessageBase(BaseModel):
    content: str
    sender_type: str = Field(..., pattern="^(user|agent|system)$")
    sender_id: str
    metadata: Optional[Dict[str, Any]] = {}


class MessageCreate(MessageBase):
    pass


class MessageResponse(MessageBase):
    id: UUID
    session_id: UUID
    created_at: datetime
    is_deleted: bool = False
    
    class Config:
        from_attributes = True


class SessionBase(BaseModel):
    user_id: str
    agent_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}


class SessionCreate(SessionBase):
    pass


class SessionUpdate(BaseModel):
    agent_id: Optional[str] = None
    status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SessionResponse(SessionBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    ended_at: Optional[datetime] = None
    status: str
    
    class Config:
        from_attributes = True


class SessionWithMessages(SessionResponse):
    messages: List[MessageResponse] = []


# Health check response
class HealthResponse(BaseModel):
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    service: str = "chat-service"
    version: str = "1.0.0"