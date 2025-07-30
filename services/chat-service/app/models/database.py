from sqlalchemy import Column, String, DateTime, Text, Boolean, ForeignKey, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


class LiveChatSession(Base):
    __tablename__ = "live_chat_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    agent_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    status = Column(String, default="active", nullable=False)  # active, ended, transferred
    metadata = Column(JSON, default={})
    
    # Relationships
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("live_chat_sessions.id"), nullable=False)
    content = Column(Text, nullable=False)
    sender_type = Column(String, nullable=False)  # user, agent, system
    sender_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_deleted = Column(Boolean, default=False)
    metadata = Column(JSON, default={})
    
    # Relationships
    session = relationship("LiveChatSession", back_populates="messages")
    extensions = relationship("MessageExtension", back_populates="message", cascade="all, delete-orphan")


class MessageExtension(Base):
    __tablename__ = "message_extensions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False)
    extension_type = Column(String, nullable=False)  # attachment, reaction, edit_history, etc.
    data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    message = relationship("Message", back_populates="extensions")