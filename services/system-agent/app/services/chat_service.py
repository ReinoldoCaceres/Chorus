from typing import List, Dict, Any, Optional
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferWindowMemory
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import structlog
import uuid

from app.config import get_settings
from app.models.database import Conversation
from app.models.schemas import (
    ChatMessage,
    ChatResponse,
    ConversationCreate,
    ConversationResponse,
    MessageType,
    KnowledgeSearchRequest
)
from app.services.knowledge_service import KnowledgeService

logger = structlog.get_logger()
settings = get_settings()


class ChatService:
    """Service for AI-powered chat functionality with RAG"""
    
    def __init__(self):
        self.settings = settings
        self.knowledge_service = KnowledgeService()
        self._chat_model = None
        self._conversation_memories = {}  # Session-based memory storage
        
    @property
    def chat_model(self):
        """Lazy initialization of ChatOpenAI model"""
        if self._chat_model is None:
            try:
                self._chat_model = ChatOpenAI(
                    model=self.settings.openai_model,
                    temperature=self.settings.agent_temperature,
                    max_tokens=self.settings.max_tokens,
                    openai_api_key=self.settings.openai_api_key
                )
                logger.info("ChatOpenAI model initialized", 
                           model=self.settings.openai_model)
            except Exception as e:
                logger.error("Failed to initialize ChatOpenAI model", error=str(e))
                raise
        return self._chat_model
    
    def get_conversation_memory(self, session_id: str) -> ConversationBufferWindowMemory:
        """Get or create conversation memory for a session"""
        if session_id not in self._conversation_memories:
            self._conversation_memories[session_id] = ConversationBufferWindowMemory(
                k=10,  # Keep last 10 exchanges
                return_messages=True
            )
            logger.info("Created new conversation memory", session_id=session_id)
        return self._conversation_memories[session_id]
    
    async def save_conversation_message(
        self, 
        db: AsyncSession, 
        session_id: str,
        message: str,
        message_type: MessageType,
        user_id: Optional[str] = None,
        context: Dict[str, Any] = None,
        parent_message_id: Optional[uuid.UUID] = None
    ) -> ConversationResponse:
        """Save a conversation message to database"""
        try:
            conversation_data = ConversationCreate(
                session_id=session_id,
                message=message,
                message_type=message_type,
                user_id=user_id,
                context=context or {},
                parent_message_id=parent_message_id
            )
            
            db_conversation = Conversation(**conversation_data.model_dump())
            db.add(db_conversation)
            await db.commit()
            await db.refresh(db_conversation)
            
            return ConversationResponse.model_validate(db_conversation)
            
        except Exception as e:
            await db.rollback()
            logger.error("Failed to save conversation message", 
                        session_id=session_id, error=str(e))
            raise
    
    async def get_conversation_history(
        self, 
        db: AsyncSession, 
        session_id: str,
        limit: int = 50
    ) -> List[ConversationResponse]:
        """Get conversation history for a session"""
        try:
            result = await db.execute(
                select(Conversation)
                .where(Conversation.session_id == session_id)
                .order_by(Conversation.created_at.desc())
                .limit(limit)
            )
            conversations = result.scalars().all()
            conversations.reverse()  # Return in chronological order
            
            return [ConversationResponse.model_validate(conv) for conv in conversations]
            
        except Exception as e:
            logger.error("Failed to get conversation history", 
                        session_id=session_id, error=str(e))
            raise
    
    async def retrieve_relevant_knowledge(
        self, 
        db: AsyncSession, 
        query: str,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant knowledge for RAG"""
        try:
            search_request = KnowledgeSearchRequest(
                query=query,
                limit=limit,
                similarity_threshold=0.6
            )
            
            search_results = await self.knowledge_service.search_knowledge(
                db, search_request
            )
            
            # Format results for context
            knowledge_sources = []
            for result in search_results.results:
                knowledge_sources.append({
                    "title": result.title,
                    "content": result.content,
                    "category": result.category,
                    "similarity_score": result.similarity_score,
                    "id": str(result.id)
                })
            
            logger.info("Retrieved knowledge for RAG", 
                       query=query, sources_count=len(knowledge_sources))
            
            return knowledge_sources
            
        except Exception as e:
            logger.error("Failed to retrieve relevant knowledge", 
                        query=query, error=str(e))
            return []  # Return empty list on error, don't fail the chat
    
    def build_system_prompt(self, knowledge_sources: List[Dict[str, Any]]) -> str:
        """Build system prompt with relevant knowledge"""
        base_prompt = """You are a helpful AI assistant for the Chorus platform. You have access to relevant knowledge from the system's knowledge base to help answer questions accurately.

Instructions:
1. Use the provided knowledge sources to inform your responses
2. Be helpful, accurate, and concise
3. If you're not sure about something, say so
4. Cite relevant sources when appropriate
5. Maintain a professional and friendly tone

"""
        
        if knowledge_sources:
            base_prompt += "\nRelevant Knowledge Sources:\n"
            for i, source in enumerate(knowledge_sources, 1):
                base_prompt += f"\n{i}. {source['title']} (Category: {source['category']})\n"
                base_prompt += f"   {source['content']}\n"
        
        return base_prompt
    
    async def process_chat_message(
        self, 
        db: AsyncSession, 
        chat_message: ChatMessage
    ) -> ChatResponse:
        """Process a chat message with RAG-enhanced response"""
        try:
            session_id = chat_message.session_id
            user_message = chat_message.message
            
            # Save user message
            user_conv = await self.save_conversation_message(
                db, session_id, user_message, MessageType.USER, 
                chat_message.user_id, chat_message.context
            )
            
            # Retrieve relevant knowledge
            knowledge_sources = await self.retrieve_relevant_knowledge(
                db, user_message
            )
            
            # Build system prompt with knowledge
            system_prompt = self.build_system_prompt(knowledge_sources)
            
            # Get conversation memory
            memory = self.get_conversation_memory(session_id)
            
            # Create messages for the model
            messages = [SystemMessage(content=system_prompt)]
            
            # Add conversation history from memory
            for message in memory.chat_memory.messages:
                messages.append(message)
            
            # Add current user message
            messages.append(HumanMessage(content=user_message))
            
            # Generate response
            response = await self.chat_model.agenerate([messages])
            ai_response = response.generations[0][0].text
            
            # Update memory
            memory.chat_memory.add_user_message(user_message)
            memory.chat_memory.add_ai_message(ai_response)
            
            # Save AI response
            ai_conv = await self.save_conversation_message(
                db, session_id, ai_response, MessageType.AGENT,
                context={
                    "knowledge_sources_used": len(knowledge_sources),
                    "model": self.settings.openai_model,
                    "parent_message_id": str(user_conv.id)
                },
                parent_message_id=user_conv.id
            )
            
            # Format knowledge sources for response
            formatted_sources = []
            for source in knowledge_sources:
                formatted_sources.append({
                    "id": source["id"],
                    "title": source["title"],
                    "category": source["category"],
                    "similarity_score": source["similarity_score"]
                })
            
            logger.info("Chat message processed", 
                       session_id=session_id, 
                       message_length=len(user_message),
                       response_length=len(ai_response),
                       sources_used=len(knowledge_sources))
            
            return ChatResponse(
                message=user_message,
                response=ai_response,
                session_id=session_id,
                context={
                    "conversation_id": str(ai_conv.id),
                    "model_used": self.settings.openai_model,
                    **chat_message.context
                },
                sources=formatted_sources
            )
            
        except Exception as e:
            logger.error("Failed to process chat message", 
                        session_id=chat_message.session_id, error=str(e))
            raise
    
    async def clear_conversation_memory(self, session_id: str) -> bool:
        """Clear conversation memory for a session"""
        try:
            if session_id in self._conversation_memories:
                del self._conversation_memories[session_id]
                logger.info("Cleared conversation memory", session_id=session_id)
                return True
            return False
            
        except Exception as e:
            logger.error("Failed to clear conversation memory", 
                        session_id=session_id, error=str(e))
            return False
    
    async def get_active_sessions(self) -> List[str]:
        """Get list of active chat sessions"""
        return list(self._conversation_memories.keys())