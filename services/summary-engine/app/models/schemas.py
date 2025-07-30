from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID
from enum import Enum


class SummaryType(str, Enum):
    CONVERSATION = "conversation"
    TOPIC = "topic"
    SENTIMENT = "sentiment"
    KEY_POINTS = "key_points"


class SummaryRequest(BaseModel):
    conversation_id: UUID
    messages: List[str]
    summary_type: SummaryType = SummaryType.CONVERSATION
    max_length: Optional[int] = Field(default=500, ge=50, le=2000)
    context: Optional[Dict[str, Any]] = {}


class SummaryResponse(BaseModel):
    task_id: str
    conversation_id: UUID
    summary_type: SummaryType
    status: str = "pending"  # pending, processing, completed, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SummaryResult(BaseModel):
    task_id: str
    conversation_id: UUID
    summary_type: SummaryType
    summary: str
    confidence_score: Optional[float] = None
    key_topics: List[str] = []
    sentiment: Optional[str] = None
    metadata: Dict[str, Any] = {}
    created_at: datetime
    completed_at: datetime


class VectorStoreRequest(BaseModel):
    conversation_id: UUID
    messages: List[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]] = {}


class VectorSearchRequest(BaseModel):
    query: str
    conversation_id: Optional[UUID] = None
    limit: int = Field(default=10, ge=1, le=100)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class VectorSearchResult(BaseModel):
    content: str
    metadata: Dict[str, Any]
    similarity_score: float


class HealthResponse(BaseModel):
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    service: str = "summary-engine"
    version: str = "1.0.0"
    workers_active: int = 0