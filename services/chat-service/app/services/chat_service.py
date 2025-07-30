from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.database import LiveChatSession, Message, MessageExtension
from app.models.schemas import SessionCreate, SessionUpdate, MessageCreate
from typing import Optional, List
from uuid import UUID
from datetime import datetime
import structlog

logger = structlog.get_logger()


class ChatService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_session(self, session_data: SessionCreate) -> LiveChatSession:
        """Create a new chat session"""
        try:
            session = LiveChatSession(**session_data.model_dump())
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)
            
            logger.info("Chat session created", session_id=str(session.id), user_id=session.user_id)
            return session
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to create session", error=str(e))
            raise
    
    def get_session(self, session_id: UUID) -> Optional[LiveChatSession]:
        """Get a chat session by ID"""
        return self.db.query(LiveChatSession).filter(LiveChatSession.id == session_id).first()
    
    def get_user_sessions(self, user_id: str, active_only: bool = False) -> List[LiveChatSession]:
        """Get all sessions for a user"""
        query = self.db.query(LiveChatSession).filter(LiveChatSession.user_id == user_id)
        if active_only:
            query = query.filter(LiveChatSession.status == "active")
        return query.order_by(LiveChatSession.created_at.desc()).all()
    
    def update_session(self, session_id: UUID, session_update: SessionUpdate) -> Optional[LiveChatSession]:
        """Update a chat session"""
        session = self.get_session(session_id)
        if not session:
            return None
        
        try:
            update_data = session_update.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(session, field, value)
            
            session.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(session)
            
            logger.info("Session updated", session_id=str(session_id))
            return session
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to update session", session_id=str(session_id), error=str(e))
            raise
    
    def end_session(self, session_id: UUID) -> Optional[LiveChatSession]:
        """End a chat session"""
        session = self.get_session(session_id)
        if not session:
            return None
        
        try:
            session.status = "ended"
            session.ended_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(session)
            
            logger.info("Session ended", session_id=str(session_id))
            return session
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to end session", session_id=str(session_id), error=str(e))
            raise
    
    def create_message(self, session_id: UUID, message_data: MessageCreate) -> Optional[Message]:
        """Create a new message in a session"""
        session = self.get_session(session_id)
        if not session:
            return None
        
        try:
            message = Message(
                session_id=session_id,
                **message_data.model_dump()
            )
            self.db.add(message)
            
            # Update session updated_at
            session.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(message)
            
            logger.info("Message created", 
                       message_id=str(message.id), 
                       session_id=str(session_id),
                       sender_type=message.sender_type)
            return message
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to create message", session_id=str(session_id), error=str(e))
            raise
    
    def get_session_messages(self, session_id: UUID, limit: int = 100, offset: int = 0) -> List[Message]:
        """Get messages for a session"""
        return (self.db.query(Message)
                .filter(and_(Message.session_id == session_id, Message.is_deleted == False))
                .order_by(Message.created_at.asc())
                .limit(limit)
                .offset(offset)
                .all())
    
    def delete_message(self, message_id: UUID) -> Optional[Message]:
        """Soft delete a message"""
        message = self.db.query(Message).filter(Message.id == message_id).first()
        if not message:
            return None
        
        try:
            message.is_deleted = True
            self.db.commit()
            self.db.refresh(message)
            
            logger.info("Message deleted", message_id=str(message_id))
            return message
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to delete message", message_id=str(message_id), error=str(e))
            raise