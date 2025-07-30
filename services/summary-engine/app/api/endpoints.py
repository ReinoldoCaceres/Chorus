from fastapi import APIRouter, HTTPException, BackgroundTasks
from celery.result import AsyncResult
from typing import List
import structlog

from app.models.schemas import (
    SummaryRequest, SummaryResponse, SummaryResult,
    VectorStoreRequest, VectorSearchRequest, VectorSearchResult,
    HealthResponse
)
from app.workers.summary_worker import (
    generate_summary_task,
    store_conversation_vectors_task,
    search_similar_conversations_task
)
from app.celery_app import celery_app

logger = structlog.get_logger()
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Check Celery worker status
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        worker_count = len(active_workers) if active_workers else 0
        
        return HealthResponse(workers_active=worker_count)
    except Exception as e:
        logger.warning("Health check encountered issues", error=str(e))
        return HealthResponse(workers_active=0)


@router.post("/summary", response_model=SummaryResponse)
async def create_summary(request: SummaryRequest):
    """Create a new summary generation task"""
    try:
        # Start Celery task
        task = generate_summary_task.delay(
            conversation_id=str(request.conversation_id),
            messages=request.messages,
            summary_type=request.summary_type.value,
            max_length=request.max_length,
            context=request.context
        )
        
        logger.info("Summary task created",
                   task_id=task.id,
                   conversation_id=str(request.conversation_id))
        
        return SummaryResponse(
            task_id=task.id,
            conversation_id=request.conversation_id,
            summary_type=request.summary_type
        )
        
    except Exception as e:
        logger.error("Failed to create summary task", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create summary task")


@router.get("/summary/{task_id}", response_model=SummaryResult)
async def get_summary_result(task_id: str):
    """Get summary task result"""
    try:
        result = AsyncResult(task_id, app=celery_app)
        
        if result.state == "PENDING":
            raise HTTPException(status_code=202, detail="Task is still processing")
        elif result.state == "FAILURE":
            raise HTTPException(status_code=500, detail=f"Task failed: {result.info}")
        elif result.state == "SUCCESS":
            return SummaryResult(**result.result)
        else:
            raise HTTPException(status_code=202, detail=f"Task state: {result.state}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get summary result", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve summary result")


@router.post("/vector-store", response_model=dict)
async def store_conversation(request: VectorStoreRequest):
    """Store conversation in vector database"""
    try:
        # Start Celery task
        task = store_conversation_vectors_task.delay(
            conversation_id=str(request.conversation_id),
            messages=request.messages,
            metadata=request.metadata
        )
        
        logger.info("Vector storage task created",
                   task_id=task.id,
                   conversation_id=str(request.conversation_id))
        
        return {
            "task_id": task.id,
            "conversation_id": str(request.conversation_id),
            "status": "processing"
        }
        
    except Exception as e:
        logger.error("Failed to create vector storage task", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to store conversation")


@router.post("/vector-search", response_model=List[VectorSearchResult])
async def search_conversations(request: VectorSearchRequest):
    """Search for similar conversations"""
    try:
        # Start Celery task
        task = search_similar_conversations_task.delay(
            query=request.query,
            conversation_id=str(request.conversation_id) if request.conversation_id else None,
            limit=request.limit,
            similarity_threshold=request.similarity_threshold
        )
        
        # Wait for result (synchronous for search)
        result = task.get(timeout=30)
        
        # Convert to response format
        search_results = []
        for item in result.get("results", []):
            search_results.append(VectorSearchResult(**item))
        
        return search_results
        
    except Exception as e:
        logger.error("Failed to search conversations", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to search conversations")


@router.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    """Get the status of any task"""
    try:
        result = AsyncResult(task_id, app=celery_app)
        
        return {
            "task_id": task_id,
            "state": result.state,
            "info": result.info
        }
        
    except Exception as e:
        logger.error("Failed to get task status", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve task status")