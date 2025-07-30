from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.db.database import get_db
from app.models.schemas import (
    SessionCreate, SessionUpdate, SessionResponse, SessionWithMessages,
    MessageCreate, MessageResponse,
    HealthResponse
)
from app.services.chat_service import ChatService
import structlog

logger = structlog.get_logger()

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse()


# Session endpoints
@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    session_data: SessionCreate,
    db: Session = Depends(get_db)
):
    """Create a new chat session"""
    service = ChatService(db)
    session = service.create_session(session_data)
    return session


@router.get("/sessions/{session_id}", response_model=SessionWithMessages)
async def get_session(
    session_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a session with its messages"""
    service = ChatService(db)
    session = service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = service.get_session_messages(session_id)
    return SessionWithMessages(
        **SessionResponse.model_validate(session).model_dump(),
        messages=messages
    )


@router.get("/users/{user_id}/sessions", response_model=List[SessionResponse])
async def get_user_sessions(
    user_id: str,
    active_only: bool = Query(False, description="Only return active sessions"),
    db: Session = Depends(get_db)
):
    """Get all sessions for a user"""
    service = ChatService(db)
    sessions = service.get_user_sessions(user_id, active_only)
    return sessions


@router.patch("/sessions/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: UUID,
    session_update: SessionUpdate,
    db: Session = Depends(get_db)
):
    """Update a session"""
    service = ChatService(db)
    session = service.update_session(session_id, session_update)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/sessions/{session_id}/end", response_model=SessionResponse)
async def end_session(
    session_id: UUID,
    db: Session = Depends(get_db)
):
    """End a chat session"""
    service = ChatService(db)
    session = service.end_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


# Message endpoints
@router.post("/sessions/{session_id}/messages", response_model=MessageResponse)
async def create_message(
    session_id: UUID,
    message_data: MessageCreate,
    db: Session = Depends(get_db)
):
    """Create a new message in a session"""
    service = ChatService(db)
    message = service.create_message(session_id, message_data)
    if not message:
        raise HTTPException(status_code=404, detail="Session not found")
    return message


@router.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
async def get_session_messages(
    session_id: UUID,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get messages for a session"""
    service = ChatService(db)
    
    # Check if session exists
    session = service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = service.get_session_messages(session_id, limit, offset)
    return messages


@router.delete("/messages/{message_id}", response_model=MessageResponse)
async def delete_message(
    message_id: UUID,
    db: Session = Depends(get_db)
):
    """Soft delete a message"""
    service = ChatService(db)
    message = service.delete_message(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    return message