from celery import Celery
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from uuid import UUID
import structlog
import asyncio

from app.config import get_settings
from app.services.delivery_service import DeliveryService
from app.models.database import Notification

# Configure logging
logger = structlog.get_logger()

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "notification_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.notification_worker"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    task_routes={
        "app.workers.notification_worker.send_notification_task": {"queue": "notifications"},
        "app.workers.notification_worker.retry_failed_notifications": {"queue": "notifications"},
        "app.workers.notification_worker.cleanup_old_notifications": {"queue": "maintenance"}
    },
    beat_schedule={
        "retry-failed-notifications": {
            "task": "app.workers.notification_worker.retry_failed_notifications",
            "schedule": 300.0,  # Every 5 minutes
        },
        "cleanup-old-notifications": {
            "task": "app.workers.notification_worker.cleanup_old_notifications",
            "schedule": 3600.0,  # Every hour
        }
    }
)

# Database setup
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_session():
    """Get database session for worker tasks"""
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_notification_task(self, notification_id: str):
    """
    Celery task to send a notification
    
    Args:
        notification_id: UUID of the notification to send
    """
    db = get_db_session()
    
    try:
        notification_uuid = UUID(notification_id)
        delivery_service = DeliveryService(db)
        
        logger.info(
            "Processing notification",
            notification_id=notification_id,
            task_id=self.request.id
        )
        
        # Deliver the notification
        result = asyncio.run(delivery_service.deliver_notification(notification_uuid))
        
        if result.success:
            logger.info(
                "Notification sent successfully",
                notification_id=notification_id,
                task_id=self.request.id,
                external_id=result.external_id
            )
            return {
                "status": "success",
                "notification_id": notification_id,
                "message": result.message,
                "external_id": result.external_id
            }
        else:
            # Check if we should retry
            notification = asyncio.run(delivery_service.get_notification(notification_uuid))
            if notification and notification.retry_count < notification.max_retries:
                logger.warning(
                    "Notification delivery failed, retrying",
                    notification_id=notification_id,
                    retry_count=notification.retry_count,
                    max_retries=notification.max_retries,
                    error=result.message
                )
                
                # Retry with exponential backoff
                retry_delay = min(60 * (2 ** notification.retry_count), 3600)  # Max 1 hour
                raise self.retry(countdown=retry_delay, exc=Exception(result.message))
            else:
                logger.error(
                    "Notification delivery failed permanently",
                    notification_id=notification_id,
                    retry_count=notification.retry_count if notification else 0,
                    error=result.message
                )
                return {
                    "status": "failed",
                    "notification_id": notification_id,
                    "message": result.message,
                    "error_code": result.error_code
                }
    
    except Exception as e:
        logger.error(
            "Notification task failed with exception",
            notification_id=notification_id,
            task_id=self.request.id,
            error=str(e)
        )
        
        # Update notification status to failed
        try:
            notification_uuid = UUID(notification_id)
            delivery_service = DeliveryService(db)
            notification = asyncio.run(delivery_service.get_notification(notification_uuid))
            
            if notification:
                notification.status = "failed"
                notification.error_message = str(e)
                notification.retry_count += 1
                db.commit()
        except Exception as update_e:
            logger.error(
                "Failed to update notification status",
                notification_id=notification_id,
                error=str(update_e)
            )
        
        # Retry if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            retry_delay = min(60 * (2 ** self.request.retries), 3600)
            raise self.retry(countdown=retry_delay, exc=e)
        else:
            return {
                "status": "failed",
                "notification_id": notification_id,
                "message": str(e),
                "error_code": "TASK_FAILED"
            }
    
    finally:
        db.close()


@celery_app.task
def retry_failed_notifications():
    """
    Periodic task to retry failed notifications that haven't exceeded max retries
    """
    db = get_db_session()
    
    try:
        from datetime import datetime, timedelta
        
        # Find failed notifications that can be retried
        retry_cutoff = datetime.utcnow() - timedelta(minutes=settings.retry_delay_seconds / 60)
        
        failed_notifications = db.query(Notification).filter(
            Notification.status == "failed",
            Notification.retry_count < Notification.max_retries,
            Notification.updated_at <= retry_cutoff
        ).limit(settings.notification_batch_size).all()
        
        retried_count = 0
        
        for notification in failed_notifications:
            try:
                # Reset notification status
                notification.status = "pending"
                notification.error_message = None
                db.commit()
                
                # Queue for retry
                send_notification_task.delay(str(notification.id))
                retried_count += 1
                
                logger.info(
                    "Notification queued for retry",
                    notification_id=str(notification.id),
                    retry_count=notification.retry_count
                )
                
            except Exception as e:
                logger.error(
                    "Failed to queue notification for retry",
                    notification_id=str(notification.id),
                    error=str(e)
                )
                continue
        
        logger.info(
            "Retry task completed",
            total_found=len(failed_notifications),
            retried_count=retried_count
        )
        
        return {
            "status": "completed",
            "total_found": len(failed_notifications),
            "retried_count": retried_count
        }
    
    except Exception as e:
        logger.error("Retry task failed", error=str(e))
        return {
            "status": "failed",
            "message": str(e)
        }
    
    finally:
        db.close()


@celery_app.task
def cleanup_old_notifications():
    """
    Periodic task to clean up old notifications
    """
    db = get_db_session()
    
    try:
        from datetime import datetime, timedelta
        
        # Clean up notifications older than 30 days
        cleanup_cutoff = datetime.utcnow() - timedelta(days=30)
        
        # Count notifications to be cleaned up
        old_notifications = db.query(Notification).filter(
            Notification.created_at <= cleanup_cutoff,
            Notification.status.in_(["sent", "failed"])
        )
        
        count_to_cleanup = old_notifications.count()
        
        if count_to_cleanup > 0:
            # Delete in batches to avoid locking issues
            batch_size = 1000
            deleted_count = 0
            
            while True:
                batch = old_notifications.limit(batch_size).all()
                if not batch:
                    break
                
                for notification in batch:
                    db.delete(notification)
                
                db.commit()
                deleted_count += len(batch)
                
                logger.info(
                    "Deleted notification batch",
                    batch_size=len(batch),
                    total_deleted=deleted_count
                )
        
        logger.info(
            "Cleanup task completed",
            deleted_count=count_to_cleanup
        )
        
        return {
            "status": "completed",
            "deleted_count": count_to_cleanup
        }
    
    except Exception as e:
        logger.error("Cleanup task failed", error=str(e))
        return {
            "status": "failed",
            "message": str(e)
        }
    
    finally:
        db.close()


@celery_app.task
def send_batch_notifications(notification_ids: list):
    """
    Task to send multiple notifications in batch
    
    Args:
        notification_ids: List of notification UUIDs to send
    """
    results = []
    
    for notification_id in notification_ids:
        try:
            # Queue individual notification
            result = send_notification_task.delay(notification_id)
            results.append({
                "notification_id": notification_id,
                "task_id": result.id,
                "status": "queued"
            })
        except Exception as e:
            logger.error(
                "Failed to queue notification in batch",
                notification_id=notification_id,
                error=str(e)
            )
            results.append({
                "notification_id": notification_id,
                "status": "failed",
                "error": str(e)
            })
    
    logger.info(
        "Batch notifications queued",
        total_count=len(notification_ids),
        successful_count=sum(1 for r in results if r["status"] == "queued")
    )
    
    return {
        "status": "completed",
        "total_count": len(notification_ids),
        "results": results
    }


if __name__ == "__main__":
    # Start Celery worker
    celery_app.start()