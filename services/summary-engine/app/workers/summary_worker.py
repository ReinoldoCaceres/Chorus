from celery import current_task
from celery.exceptions import Retry
from typing import List, Dict, Any
from uuid import UUID
import structlog
from datetime import datetime

from app.celery_app import celery_app
from app.services.summary_service import SummaryService
from app.services.vector_store import VectorStoreService
from app.models.schemas import SummaryType
from app.utils.logging import configure_logging

# Configure logging
configure_logging()
logger = structlog.get_logger()


@celery_app.task(bind=True, name="generate_summary")
def generate_summary_task(
    self,
    conversation_id: str,
    messages: List[str],
    summary_type: str = "conversation",
    max_length: int = 500,
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Celery task to generate conversation summary"""
    task_id = self.request.id
    logger.info("Starting summary generation task",
                task_id=task_id,
                conversation_id=conversation_id,
                summary_type=summary_type)
    
    try:
        # Update task state
        current_task.update_state(
            state="PROCESSING",
            meta={"status": "Generating summary..."}
        )
        
        # Initialize summary service
        summary_service = SummaryService()
        
        # Generate summary
        result = summary_service.generate_summary(
            messages=messages,
            summary_type=SummaryType(summary_type),
            max_length=max_length,
            context=context or {}
        )
        
        # Add task metadata
        result.update({
            "task_id": task_id,
            "conversation_id": conversation_id,
            "summary_type": summary_type,
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat()
        })
        
        logger.info("Summary generation completed",
                   task_id=task_id,
                   conversation_id=conversation_id)
        
        return result
        
    except Exception as e:
        logger.error("Summary generation failed",
                    task_id=task_id,
                    conversation_id=conversation_id,
                    error=str(e))
        
        current_task.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise


@celery_app.task(bind=True, name="store_conversation_vectors")
def store_conversation_vectors_task(
    self,
    conversation_id: str,
    messages: List[Dict[str, Any]],
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Celery task to store conversation in vector database"""
    task_id = self.request.id
    logger.info("Starting vector storage task",
                task_id=task_id,
                conversation_id=conversation_id)
    
    try:
        # Update task state
        current_task.update_state(
            state="PROCESSING",
            meta={"status": "Storing conversation vectors..."}
        )
        
        # Initialize vector store service
        vector_service = VectorStoreService()
        
        # Store conversation
        success = vector_service.store_conversation(
            conversation_id=UUID(conversation_id),
            messages=messages,
            metadata=metadata
        )
        
        result = {
            "task_id": task_id,
            "conversation_id": conversation_id,
            "success": success,
            "completed_at": datetime.utcnow().isoformat()
        }
        
        logger.info("Vector storage completed",
                   task_id=task_id,
                   conversation_id=conversation_id,
                   success=success)
        
        return result
        
    except Exception as e:
        logger.error("Vector storage failed",
                    task_id=task_id,
                    conversation_id=conversation_id,
                    error=str(e))
        
        current_task.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise


@celery_app.task(bind=True, name="search_similar_conversations")
def search_similar_conversations_task(
    self,
    query: str,
    conversation_id: str = None,
    limit: int = 10,
    similarity_threshold: float = 0.7
) -> Dict[str, Any]:
    """Celery task to search for similar conversations"""
    task_id = self.request.id
    logger.info("Starting similarity search task",
                task_id=task_id,
                query_length=len(query))
    
    try:
        # Update task state
        current_task.update_state(
            state="PROCESSING",
            meta={"status": "Searching similar conversations..."}
        )
        
        # Initialize vector store service
        vector_service = VectorStoreService()
        
        # Perform search
        results = vector_service.search_similar(
            query=query,
            conversation_id=UUID(conversation_id) if conversation_id else None,
            limit=limit,
            similarity_threshold=similarity_threshold
        )
        
        result = {
            "task_id": task_id,
            "query": query,
            "results": results,
            "results_count": len(results),
            "completed_at": datetime.utcnow().isoformat()
        }
        
        logger.info("Similarity search completed",
                   task_id=task_id,
                   results_count=len(results))
        
        return result
        
    except Exception as e:
        logger.error("Similarity search failed",
                    task_id=task_id,
                    error=str(e))
        
        current_task.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise