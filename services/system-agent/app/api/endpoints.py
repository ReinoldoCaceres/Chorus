from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import structlog
import uuid
from datetime import datetime

from app.db.database import get_db
from app.services.task_service import TaskService
from app.services.chat_service import ChatService
from app.services.knowledge_service import KnowledgeService
from app.models.schemas import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskStatus,
    TaskType,
    ChatMessage,
    ChatResponse,
    ConversationResponse,
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    HealthResponse
)
from app.workers.task_worker import route_task

logger = structlog.get_logger()
router = APIRouter()

# Initialize services
task_service = TaskService()
chat_service = ChatService()
knowledge_service = KnowledgeService()


# Health check endpoint
@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow(),
        services={
            "database": "connected",
            "redis": "connected",
            "chromadb": "connected",
            "openai": "configured"
        }
    )


# Task Management Endpoints
@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Create a new task"""
    try:
        # Create task in database
        task = await task_service.create_task(db, task_data)
        
        # Route task to appropriate worker if it should be processed immediately
        if not task_data.scheduled_at or task_data.scheduled_at <= datetime.utcnow():
            background_tasks.add_task(
                route_task,
                task_data.task_type,
                str(task.id),
                task_data.payload
            )
        
        return task
    except Exception as e:
        logger.error("Failed to create task", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create task"
        )


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a task by ID"""
    task = await task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return task


@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: uuid.UUID,
    update_data: TaskUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a task"""
    task = await task_service.update_task(db, task_id, update_data)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return task


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a task"""
    success = await task_service.delete_task(db, task_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )


@router.get("/tasks", response_model=List[TaskResponse])
async def get_tasks(
    status: Optional[TaskStatus] = None,
    task_type: Optional[TaskType] = None,
    assigned_agent: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get tasks with optional filtering"""
    return await task_service.get_tasks(
        db, status, task_type, assigned_agent, limit, offset
    )


@router.get("/tasks/pending/queue", response_model=List[TaskResponse])
async def get_pending_tasks(
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """Get pending tasks in queue"""
    return await task_service.get_pending_tasks(db, limit)


@router.get("/tasks/statistics")
async def get_task_statistics(db: AsyncSession = Depends(get_db)):
    """Get task statistics"""
    return await task_service.get_task_statistics(db)


# Chat Endpoints
@router.post("/chat", response_model=ChatResponse)
async def chat(
    chat_message: ChatMessage,
    db: AsyncSession = Depends(get_db)
):
    """Process a chat message with AI response"""
    try:
        return await chat_service.process_chat_message(db, chat_message)
    except Exception as e:
        logger.error("Failed to process chat message", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process chat message"
        )


@router.get("/chat/{session_id}/history", response_model=List[ConversationResponse])
async def get_chat_history(
    session_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Get chat history for a session"""
    try:
        return await chat_service.get_conversation_history(db, session_id, limit)
    except Exception as e:
        logger.error("Failed to get chat history", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get chat history"
        )


@router.delete("/chat/{session_id}/memory", status_code=status.HTTP_204_NO_CONTENT)
async def clear_chat_memory(session_id: str):
    """Clear chat memory for a session"""
    success = await chat_service.clear_conversation_memory(session_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )


@router.get("/chat/sessions/active")
async def get_active_chat_sessions():
    """Get list of active chat sessions"""
    return {"sessions": await chat_service.get_active_sessions()}


# Knowledge Base Endpoints
@router.post("/knowledge", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_entry(
    knowledge_data: KnowledgeBaseCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new knowledge base entry"""
    try:
        return await knowledge_service.create_knowledge_entry(db, knowledge_data)
    except Exception as e:
        logger.error("Failed to create knowledge entry", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create knowledge entry"
        )


@router.get("/knowledge/{entry_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_entry(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a knowledge base entry by ID"""
    entry = await knowledge_service.get_knowledge_entry(db, entry_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge entry not found"
        )
    return entry


@router.put("/knowledge/{entry_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_entry(
    entry_id: uuid.UUID,
    update_data: KnowledgeBaseUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a knowledge base entry"""
    entry = await knowledge_service.update_knowledge_entry(db, entry_id, update_data)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge entry not found"
        )
    return entry


@router.delete("/knowledge/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_entry(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a knowledge base entry"""
    success = await knowledge_service.delete_knowledge_entry(db, entry_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge entry not found"
        )


@router.get("/knowledge", response_model=List[KnowledgeBaseResponse])
async def get_knowledge_entries(
    category: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get knowledge base entries with optional filtering"""
    return await knowledge_service.get_knowledge_entries(
        db, category, limit, offset
    )


@router.post("/knowledge/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    search_request: KnowledgeSearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """Search knowledge base using vector similarity"""
    try:
        return await knowledge_service.search_knowledge(db, search_request)
    except Exception as e:
        logger.error("Failed to search knowledge base", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search knowledge base"
        )


# Task Processing Endpoints (for manual task execution)
@router.post("/tasks/{task_id}/execute")
async def execute_task(
    task_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Manually execute a task"""
    task = await task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    if task.status != TaskStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task is not in pending status"
        )
    
    try:
        background_tasks.add_task(
            route_task,
            task.task_type,
            str(task.id),
            task.payload
        )
        return {"message": "Task execution started"}
    except Exception as e:
        logger.error("Failed to execute task", task_id=str(task_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute task"
        )


@router.post("/tasks/{task_id}/retry")
async def retry_task(
    task_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Retry a failed task"""
    task = await task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    if task.status != TaskStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task is not in failed status"
        )
    
    if task.retry_count >= task.max_retries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task has exceeded maximum retry attempts"
        )
    
    try:
        # Reset task to pending
        await task_service.update_task(
            db, task_id, TaskUpdate(status=TaskStatus.PENDING)
        )
        
        # Execute task
        background_tasks.add_task(
            route_task,
            task.task_type,
            str(task.id),
            task.payload
        )
        return {"message": "Task retry started"}
    except Exception as e:
        logger.error("Failed to retry task", task_id=str(task_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retry task"
        )