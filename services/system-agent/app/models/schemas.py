from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from enum import Enum


# Enums
class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MessageType(str, Enum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


class TaskType(str, Enum):
    CHAT = "chat"
    KNOWLEDGE_SEARCH = "knowledge_search"
    KNOWLEDGE_UPDATE = "knowledge_update"
    ANALYSIS = "analysis"
    REPORT = "report"


# Task schemas
class TaskBase(BaseModel):
    task_type: TaskType
    priority: int = Field(default=5, ge=1, le=10)
    payload: Dict[str, Any]
    scheduled_at: Optional[datetime] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    status: Optional[TaskStatus] = None
    assigned_agent: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class TaskResponse(TaskBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    status: TaskStatus
    assigned_agent: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int
    max_retries: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# Knowledge Base schemas
class KnowledgeBaseBase(BaseModel):
    category: str
    title: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class KnowledgeBaseCreate(KnowledgeBaseBase):
    created_by: Optional[str] = None


class KnowledgeBaseUpdate(BaseModel):
    category: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


class KnowledgeBaseResponse(KnowledgeBaseBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    embedding_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None


# Conversation schemas
class ConversationBase(BaseModel):
    session_id: str
    message: str
    message_type: MessageType = MessageType.USER
    context: Dict[str, Any] = Field(default_factory=dict)
    user_id: Optional[str] = None


class ConversationCreate(ConversationBase):
    parent_message_id: Optional[UUID] = None


class ConversationResponse(ConversationBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    parent_message_id: Optional[UUID] = None
    created_at: datetime


# Chat schemas
class ChatMessage(BaseModel):
    message: str
    session_id: str
    user_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    message: str
    response: str
    session_id: str
    context: Dict[str, Any] = Field(default_factory=dict)
    sources: List[Dict[str, Any]] = Field(default_factory=list)


# Knowledge search schemas
class KnowledgeSearchRequest(BaseModel):
    query: str
    category: Optional[str] = None
    limit: int = Field(default=5, ge=1, le=20)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class KnowledgeSearchResult(BaseModel):
    id: UUID
    title: str
    content: str
    category: str
    similarity_score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class KnowledgeSearchResponse(BaseModel):
    query: str
    results: List[KnowledgeSearchResult]
    total_found: int


# Health check schema
class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
    services: Dict[str, str] = Field(default_factory=dict)