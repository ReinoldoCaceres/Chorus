from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.db.database import Base


class Task(Base):
    """Agent Tasks table model"""
    __tablename__ = "tasks"
    __table_args__ = {"schema": "agent"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_type = Column(String(100), nullable=False)
    priority = Column(Integer, default=5)
    payload = Column(JSON, nullable=False)
    status = Column(String(50), default="pending")
    assigned_agent = Column(String(255))
    result = Column(JSON)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    scheduled_at = Column(DateTime(timezone=True))
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class KnowledgeBase(Base):
    """Agent Knowledge Base table model"""
    __tablename__ = "knowledge_base"
    __table_args__ = {"schema": "agent"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    embedding_id = Column(String(255))
    metadata = Column(JSON, default={})
    tags = Column(JSON, default=[])
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(255))


class Conversation(Base):
    """Agent Conversations table model"""
    __tablename__ = "conversations"
    __table_args__ = {"schema": "agent"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(255), nullable=False)
    user_id = Column(String(255))
    message_type = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    context = Column(JSON, default={})
    parent_message_id = Column(UUID(as_uuid=True), ForeignKey("agent.conversations.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Self-referential relationship for message threading
    parent_message = relationship("Conversation", remote_side=[id], backref="replies")