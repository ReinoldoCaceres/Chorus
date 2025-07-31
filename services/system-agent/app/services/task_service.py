from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from datetime import datetime, timedelta
import structlog
import uuid

from app.config import get_settings
from app.models.database import Task
from app.models.schemas import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskStatus,
    TaskType
)

logger = structlog.get_logger()
settings = get_settings()


class TaskService:
    """Service for managing agent tasks"""
    
    def __init__(self):
        self.settings = settings
    
    async def create_task(
        self, 
        db: AsyncSession, 
        task_data: TaskCreate
    ) -> TaskResponse:
        """Create a new task"""
        try:
            db_task = Task(
                **task_data.model_dump(),
                max_retries=self.settings.max_retries
            )
            db.add(db_task)
            await db.commit()
            await db.refresh(db_task)
            
            logger.info("Created new task", 
                       task_id=str(db_task.id), 
                       task_type=task_data.task_type,
                       priority=task_data.priority)
            
            return TaskResponse.model_validate(db_task)
            
        except Exception as e:
            await db.rollback()
            logger.error("Failed to create task", error=str(e))
            raise
    
    async def get_task(
        self, 
        db: AsyncSession, 
        task_id: uuid.UUID
    ) -> Optional[TaskResponse]:
        """Get a task by ID"""
        try:
            result = await db.execute(
                select(Task).where(Task.id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if task:
                return TaskResponse.model_validate(task)
            return None
            
        except Exception as e:
            logger.error("Failed to get task", 
                        task_id=str(task_id), error=str(e))
            raise
    
    async def update_task(
        self, 
        db: AsyncSession, 
        task_id: uuid.UUID, 
        update_data: TaskUpdate
    ) -> Optional[TaskResponse]:
        """Update a task"""
        try:
            result = await db.execute(
                select(Task).where(Task.id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if not task:
                return None
            
            # Update fields
            update_dict = update_data.model_dump(exclude_unset=True)
            for field, value in update_dict.items():
                setattr(task, field, value)
            
            # Set timestamps based on status changes
            if "status" in update_dict:
                if update_dict["status"] == TaskStatus.RUNNING and not task.started_at:
                    task.started_at = datetime.utcnow()
                elif update_dict["status"] in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    if not task.completed_at:
                        task.completed_at = datetime.utcnow()
            
            await db.commit()
            await db.refresh(task)
            
            logger.info("Updated task", 
                       task_id=str(task_id), 
                       updated_fields=list(update_dict.keys()))
            
            return TaskResponse.model_validate(task)
            
        except Exception as e:
            await db.rollback()
            logger.error("Failed to update task", 
                        task_id=str(task_id), error=str(e))
            raise
    
    async def delete_task(
        self, 
        db: AsyncSession, 
        task_id: uuid.UUID
    ) -> bool:
        """Delete a task"""
        try:
            result = await db.execute(
                select(Task).where(Task.id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if not task:
                return False
            
            await db.delete(task)
            await db.commit()
            
            logger.info("Deleted task", task_id=str(task_id))
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error("Failed to delete task", 
                        task_id=str(task_id), error=str(e))
            raise
    
    async def get_tasks(
        self, 
        db: AsyncSession,
        status: Optional[TaskStatus] = None,
        task_type: Optional[TaskType] = None,
        assigned_agent: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[TaskResponse]:
        """Get tasks with optional filtering"""
        try:
            query = select(Task)
            
            # Apply filters
            conditions = []
            if status:
                conditions.append(Task.status == status)
            if task_type:
                conditions.append(Task.task_type == task_type)
            if assigned_agent:
                conditions.append(Task.assigned_agent == assigned_agent)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            query = query.offset(offset).limit(limit).order_by(Task.created_at.desc())
            
            result = await db.execute(query)
            tasks = result.scalars().all()
            
            return [TaskResponse.model_validate(task) for task in tasks]
            
        except Exception as e:
            logger.error("Failed to get tasks", error=str(e))
            raise
    
    async def get_pending_tasks(
        self, 
        db: AsyncSession, 
        limit: int = 10
    ) -> List[TaskResponse]:
        """Get pending tasks ordered by priority and scheduled time"""
        try:
            current_time = datetime.utcnow()
            
            query = select(Task).where(
                and_(
                    Task.status == TaskStatus.PENDING,
                    or_(
                        Task.scheduled_at.is_(None),
                        Task.scheduled_at <= current_time
                    )
                )
            ).order_by(
                Task.priority.desc(),  # Higher priority first
                Task.created_at.asc()   # Older tasks first for same priority
            ).limit(limit)
            
            result = await db.execute(query)
            tasks = result.scalars().all()
            
            return [TaskResponse.model_validate(task) for task in tasks]
            
        except Exception as e:
            logger.error("Failed to get pending tasks", error=str(e))
            raise
    
    async def get_failed_tasks_for_retry(
        self, 
        db: AsyncSession, 
        limit: int = 10
    ) -> List[TaskResponse]:
        """Get failed tasks that can be retried"""
        try:
            query = select(Task).where(
                and_(
                    Task.status == TaskStatus.FAILED,
                    Task.retry_count < Task.max_retries
                )
            ).order_by(
                Task.priority.desc(),
                Task.updated_at.asc()
            ).limit(limit)
            
            result = await db.execute(query)
            tasks = result.scalars().all()
            
            return [TaskResponse.model_validate(task) for task in tasks]
            
        except Exception as e:
            logger.error("Failed to get failed tasks for retry", error=str(e))
            raise
    
    async def mark_task_as_running(
        self, 
        db: AsyncSession, 
        task_id: uuid.UUID, 
        agent_id: str = "system-agent"
    ) -> Optional[TaskResponse]:
        """Mark a task as running and assign to agent"""
        update_data = TaskUpdate(
            status=TaskStatus.RUNNING,
            assigned_agent=agent_id
        )
        return await self.update_task(db, task_id, update_data)
    
    async def mark_task_as_completed(
        self, 
        db: AsyncSession, 
        task_id: uuid.UUID, 
        result: Dict[str, Any]
    ) -> Optional[TaskResponse]:
        """Mark a task as completed with result"""
        update_data = TaskUpdate(
            status=TaskStatus.COMPLETED,
            result=result
        )
        return await self.update_task(db, task_id, update_data)
    
    async def mark_task_as_failed(
        self, 
        db: AsyncSession, 
        task_id: uuid.UUID, 
        error_message: str,
        increment_retry: bool = True
    ) -> Optional[TaskResponse]:
        """Mark a task as failed with error message"""
        try:
            result = await db.execute(
                select(Task).where(Task.id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if not task:
                return None
            
            # Increment retry count if requested
            if increment_retry:
                task.retry_count += 1
            
            # Determine final status
            if task.retry_count >= task.max_retries:
                final_status = TaskStatus.FAILED
            else:
                final_status = TaskStatus.PENDING  # Will be retried
            
            update_data = TaskUpdate(
                status=final_status,
                error_message=error_message
            )
            
            return await self.update_task(db, task_id, update_data)
            
        except Exception as e:
            logger.error("Failed to mark task as failed", 
                        task_id=str(task_id), error=str(e))
            raise
    
    async def get_task_statistics(self, db: AsyncSession) -> Dict[str, Any]:
        """Get task statistics"""
        try:
            # Count tasks by status
            status_counts = {}
            for status in TaskStatus:
                result = await db.execute(
                    select(Task).where(Task.status == status)
                )
                count = len(result.scalars().all())
                status_counts[status.value] = count
            
            # Count tasks by type
            type_counts = {}
            for task_type in TaskType:
                result = await db.execute(
                    select(Task).where(Task.task_type == task_type)
                )
                count = len(result.scalars().all())
                type_counts[task_type.value] = count
            
            # Get recent activity (last 24 hours)
            yesterday = datetime.utcnow() - timedelta(days=1)
            result = await db.execute(
                select(Task).where(Task.created_at >= yesterday)
            )
            recent_tasks = len(result.scalars().all())
            
            return {
                "status_counts": status_counts,
                "type_counts": type_counts,
                "recent_tasks_24h": recent_tasks,
                "total_tasks": sum(status_counts.values())
            }
            
        except Exception as e:
            logger.error("Failed to get task statistics", error=str(e))
            raise