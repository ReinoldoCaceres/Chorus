from typing import Dict, Any
import structlog
import asyncio
from contextlib import asynccontextmanager

from app.celery_app import celery_app
from app.config import get_settings
from app.db.database import AsyncSessionLocal
from app.services.task_service import TaskService
from app.services.chat_service import ChatService
from app.services.knowledge_service import KnowledgeService
from app.models.schemas import (
    TaskType, 
    ChatMessage, 
    KnowledgeSearchRequest,
    KnowledgeBaseCreate
)

logger = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def get_db_session():
    """Get database session for async operations"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error("Database session error in worker", error=str(e))
            raise
        finally:
            await session.close()


def run_async_task(coro):
    """Helper to run async functions in Celery tasks"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, name="process_chat_task")
def process_chat_task(self, task_id: str, payload: Dict[str, Any]):
    """Process a chat task"""
    logger.info("Processing chat task", task_id=task_id)
    
    async def _process_chat():
        try:
            async with get_db_session() as db:
                task_service = TaskService()
                chat_service = ChatService()
                
                # Mark task as running
                await task_service.mark_task_as_running(db, task_id, "celery-worker")
                
                # Create chat message from payload
                chat_message = ChatMessage(**payload)
                
                # Process the chat message
                chat_response = await chat_service.process_chat_message(db, chat_message)
                
                # Mark task as completed
                result = {
                    "response": chat_response.response,
                    "session_id": chat_response.session_id,
                    "sources_used": len(chat_response.sources),
                    "context": chat_response.context
                }
                
                await task_service.mark_task_as_completed(db, task_id, result)
                
                logger.info("Chat task completed", task_id=task_id)
                return result
                
        except Exception as e:
            async with get_db_session() as db:
                task_service = TaskService()
                await task_service.mark_task_as_failed(
                    db, task_id, f"Chat processing failed: {str(e)}"
                )
            logger.error("Chat task failed", task_id=task_id, error=str(e))
            raise
    
    return run_async_task(_process_chat())


@celery_app.task(bind=True, name="process_knowledge_search_task")
def process_knowledge_search_task(self, task_id: str, payload: Dict[str, Any]):
    """Process a knowledge search task"""
    logger.info("Processing knowledge search task", task_id=task_id)
    
    async def _process_knowledge_search():
        try:
            async with get_db_session() as db:
                task_service = TaskService()
                knowledge_service = KnowledgeService()
                
                # Mark task as running
                await task_service.mark_task_as_running(db, task_id, "celery-worker")
                
                # Create search request from payload
                search_request = KnowledgeSearchRequest(**payload)
                
                # Perform knowledge search
                search_response = await knowledge_service.search_knowledge(
                    db, search_request
                )
                
                # Mark task as completed
                result = {
                    "query": search_response.query,
                    "results": [
                        {
                            "id": str(r.id),
                            "title": r.title,
                            "content": r.content[:500] + "..." if len(r.content) > 500 else r.content,
                            "category": r.category,
                            "similarity_score": r.similarity_score,
                            "tags": r.tags
                        }
                        for r in search_response.results
                    ],
                    "total_found": search_response.total_found
                }
                
                await task_service.mark_task_as_completed(db, task_id, result)
                
                logger.info("Knowledge search task completed", 
                           task_id=task_id, 
                           results_found=search_response.total_found)
                return result
                
        except Exception as e:
            async with get_db_session() as db:
                task_service = TaskService()
                await task_service.mark_task_as_failed(
                    db, task_id, f"Knowledge search failed: {str(e)}"
                )
            logger.error("Knowledge search task failed", task_id=task_id, error=str(e))
            raise
    
    return run_async_task(_process_knowledge_search())


@celery_app.task(bind=True, name="process_knowledge_update_task")
def process_knowledge_update_task(self, task_id: str, payload: Dict[str, Any]):
    """Process a knowledge update task"""
    logger.info("Processing knowledge update task", task_id=task_id)
    
    async def _process_knowledge_update():
        try:
            async with get_db_session() as db:
                task_service = TaskService()
                knowledge_service = KnowledgeService()
                
                # Mark task as running
                await task_service.mark_task_as_running(db, task_id, "celery-worker")
                
                operation = payload.get("operation", "create")
                
                if operation == "create":
                    # Create new knowledge entry
                    knowledge_data = KnowledgeBaseCreate(**payload["data"])
                    entry = await knowledge_service.create_knowledge_entry(
                        db, knowledge_data
                    )
                    result = {
                        "operation": "create",
                        "entry_id": str(entry.id),
                        "title": entry.title,
                        "category": entry.category
                    }
                    
                elif operation == "update":
                    # Update existing knowledge entry
                    entry_id = payload["entry_id"]
                    update_data = payload["data"]
                    entry = await knowledge_service.update_knowledge_entry(
                        db, entry_id, update_data
                    )
                    result = {
                        "operation": "update",
                        "entry_id": str(entry.id) if entry else None,
                        "success": entry is not None
                    }
                    
                elif operation == "delete":
                    # Delete knowledge entry
                    entry_id = payload["entry_id"]
                    success = await knowledge_service.delete_knowledge_entry(
                        db, entry_id
                    )
                    result = {
                        "operation": "delete",
                        "entry_id": entry_id,
                        "success": success
                    }
                    
                else:
                    raise ValueError(f"Unknown operation: {operation}")
                
                await task_service.mark_task_as_completed(db, task_id, result)
                
                logger.info("Knowledge update task completed", 
                           task_id=task_id, 
                           operation=operation)
                return result
                
        except Exception as e:
            async with get_db_session() as db:
                task_service = TaskService()
                await task_service.mark_task_as_failed(
                    db, task_id, f"Knowledge update failed: {str(e)}"
                )
            logger.error("Knowledge update task failed", task_id=task_id, error=str(e))
            raise
    
    return run_async_task(_process_knowledge_update())


@celery_app.task(bind=True, name="process_analysis_task")
def process_analysis_task(self, task_id: str, payload: Dict[str, Any]):
    """Process a general analysis task"""
    logger.info("Processing analysis task", task_id=task_id)
    
    async def _process_analysis():
        try:
            async with get_db_session() as db:
                task_service = TaskService()
                chat_service = ChatService()
                
                # Mark task as running
                await task_service.mark_task_as_running(db, task_id, "celery-worker")
                
                analysis_type = payload.get("analysis_type", "general")
                data = payload.get("data", "")
                context = payload.get("context", {})
                
                # Create a system message for analysis
                system_prompt = f"""
                Perform a {analysis_type} analysis on the provided data.
                
                Data to analyze:
                {data}
                
                Context: {context}
                
                Please provide a structured analysis with key insights, findings, and recommendations.
                """
                
                # Use chat service to generate analysis
                chat_message = ChatMessage(
                    message=system_prompt,
                    session_id=f"analysis_{task_id}",
                    context={"task_type": "analysis", "analysis_type": analysis_type}
                )
                
                chat_response = await chat_service.process_chat_message(db, chat_message)
                
                # Mark task as completed
                result = {
                    "analysis_type": analysis_type,
                    "analysis": chat_response.response,
                    "sources_consulted": len(chat_response.sources),
                    "context": context
                }
                
                await task_service.mark_task_as_completed(db, task_id, result)
                
                logger.info("Analysis task completed", task_id=task_id, type=analysis_type)
                return result
                
        except Exception as e:
            async with get_db_session() as db:
                task_service = TaskService()
                await task_service.mark_task_as_failed(
                    db, task_id, f"Analysis failed: {str(e)}"
                )
            logger.error("Analysis task failed", task_id=task_id, error=str(e))
            raise
    
    return run_async_task(_process_analysis())


@celery_app.task(bind=True, name="process_report_task")
def process_report_task(self, task_id: str, payload: Dict[str, Any]):
    """Process a report generation task"""
    logger.info("Processing report task", task_id=task_id)
    
    async def _process_report():
        try:
            async with get_db_session() as db:
                task_service = TaskService()
                chat_service = ChatService()
                
                # Mark task as running
                await task_service.mark_task_as_running(db, task_id, "celery-worker")
                
                report_type = payload.get("report_type", "summary")
                data_sources = payload.get("data_sources", [])
                parameters = payload.get("parameters", {})
                
                # Create a system message for report generation
                system_prompt = f"""
                Generate a {report_type} report based on the provided data sources and parameters.
                
                Data Sources: {data_sources}
                Parameters: {parameters}
                
                Please create a comprehensive report with:
                1. Executive Summary
                2. Key Findings
                3. Detailed Analysis
                4. Recommendations
                5. Appendices (if needed)
                
                Format the report in a professional manner with clear sections and bullet points where appropriate.
                """
                
                # Use chat service to generate report
                chat_message = ChatMessage(
                    message=system_prompt,
                    session_id=f"report_{task_id}",
                    context={"task_type": "report", "report_type": report_type}
                )
                
                chat_response = await chat_service.process_chat_message(db, chat_message)
                
                # Mark task as completed
                result = {
                    "report_type": report_type,
                    "report": chat_response.response,
                    "data_sources": data_sources,
                    "parameters": parameters,
                    "knowledge_sources_used": len(chat_response.sources),
                    "generated_at": str(asyncio.get_event_loop().time())
                }
                
                await task_service.mark_task_as_completed(db, task_id, result)
                
                logger.info("Report task completed", task_id=task_id, type=report_type)
                return result
                
        except Exception as e:
            async with get_db_session() as db:
                task_service = TaskService()
                await task_service.mark_task_as_failed(
                    db, task_id, f"Report generation failed: {str(e)}"
                )
            logger.error("Report task failed", task_id=task_id, error=str(e))
            raise
    
    return run_async_task(_process_report())


# Task routing based on task type
def route_task(task_type: str, task_id: str, payload: Dict[str, Any]):
    """Route task to appropriate worker function"""
    task_map = {
        TaskType.CHAT: process_chat_task,
        TaskType.KNOWLEDGE_SEARCH: process_knowledge_search_task,
        TaskType.KNOWLEDGE_UPDATE: process_knowledge_update_task,
        TaskType.ANALYSIS: process_analysis_task,
        TaskType.REPORT: process_report_task,
    }
    
    worker_func = task_map.get(task_type)
    if not worker_func:
        raise ValueError(f"Unknown task type: {task_type}")
    
    return worker_func.delay(task_id, payload)