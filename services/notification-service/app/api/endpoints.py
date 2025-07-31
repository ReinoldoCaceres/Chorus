from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.db.database import get_db
from app.models import schemas
from app.models.database import Notification, NotificationTemplate, NotificationSubscription
from app.services.template_service import TemplateService
from app.services.delivery_service import DeliveryService
from app.services.subscription_service import SubscriptionService
from app.workers.notification_worker import send_notification_task

router = APIRouter()

# Template endpoints
@router.post("/templates", response_model=schemas.NotificationTemplate)
async def create_template(
    template: schemas.NotificationTemplateCreate,
    db: Session = Depends(get_db)
):
    """Create a new notification template"""
    template_service = TemplateService(db)
    return await template_service.create_template(template)


@router.get("/templates", response_model=schemas.TemplateListResponse)
async def list_templates(
    tenant_id: UUID = Query(...),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    channel: Optional[schemas.NotificationChannel] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    """List notification templates"""
    template_service = TemplateService(db)
    return await template_service.list_templates(
        tenant_id=tenant_id,
        page=page,
        size=size,
        channel=channel,
        is_active=is_active
    )


@router.get("/templates/{template_id}", response_model=schemas.NotificationTemplate)
async def get_template(
    template_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific notification template"""
    template_service = TemplateService(db)
    template = await template_service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.put("/templates/{template_id}", response_model=schemas.NotificationTemplate)
async def update_template(
    template_id: UUID,
    template_update: schemas.NotificationTemplateUpdate,
    db: Session = Depends(get_db)
):
    """Update a notification template"""
    template_service = TemplateService(db)
    template = await template_service.update_template(template_id, template_update)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete a notification template"""
    template_service = TemplateService(db)
    success = await template_service.delete_template(template_id)
    if not success:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"message": "Template deleted successfully"}


@router.post("/templates/{template_id}/render", response_model=schemas.TemplateRenderResponse)
async def render_template(
    template_id: UUID,
    render_request: schemas.TemplateRenderRequest,
    db: Session = Depends(get_db)
):
    """Render a template with variables"""
    template_service = TemplateService(db)
    result = await template_service.render_template(template_id, render_request.variables)
    if not result:
        raise HTTPException(status_code=404, detail="Template not found")
    return result


# Notification endpoints
@router.post("/notifications", response_model=schemas.Notification)
async def create_notification(
    notification: schemas.NotificationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Create and send a notification"""
    delivery_service = DeliveryService(db)
    notification_obj = await delivery_service.create_notification(notification)
    
    # Queue for async delivery
    background_tasks.add_task(
        send_notification_task.delay,
        str(notification_obj.id)
    )
    
    return notification_obj


@router.post("/notifications/from-template", response_model=schemas.Notification)
async def create_notification_from_template(
    notification: schemas.NotificationCreateFromTemplate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Create and send a notification from a template"""
    delivery_service = DeliveryService(db)
    notification_obj = await delivery_service.create_notification_from_template(notification)
    
    # Queue for async delivery
    background_tasks.add_task(
        send_notification_task.delay,
        str(notification_obj.id)
    )
    
    return notification_obj


@router.get("/notifications", response_model=schemas.NotificationListResponse)
async def list_notifications(
    tenant_id: UUID = Query(...),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    status: Optional[schemas.NotificationStatus] = Query(None),
    channel: Optional[schemas.NotificationChannel] = Query(None),
    recipient: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """List notifications"""
    delivery_service = DeliveryService(db)
    return await delivery_service.list_notifications(
        tenant_id=tenant_id,
        page=page,
        size=size,
        status=status,
        channel=channel,
        recipient=recipient
    )


@router.get("/notifications/{notification_id}", response_model=schemas.Notification)
async def get_notification(
    notification_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific notification"""
    delivery_service = DeliveryService(db)
    notification = await delivery_service.get_notification(notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification


@router.put("/notifications/{notification_id}", response_model=schemas.Notification)
async def update_notification(
    notification_id: UUID,
    notification_update: schemas.NotificationUpdate,
    db: Session = Depends(get_db)
):
    """Update a notification"""
    delivery_service = DeliveryService(db)
    notification = await delivery_service.update_notification(notification_id, notification_update)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification


@router.post("/notifications/{notification_id}/retry")
async def retry_notification(
    notification_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Retry a failed notification"""
    delivery_service = DeliveryService(db)
    notification = await delivery_service.get_notification(notification_id)
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    if notification.status not in ["failed", "cancelled"]:
        raise HTTPException(
            status_code=400, 
            detail="Only failed or cancelled notifications can be retried"
        )
    
    # Reset notification for retry
    await delivery_service.reset_notification_for_retry(notification_id)
    
    # Queue for async delivery
    background_tasks.add_task(
        send_notification_task.delay,
        str(notification_id)
    )
    
    return {"message": "Notification queued for retry"}


# Subscription endpoints
@router.post("/subscriptions", response_model=schemas.NotificationSubscription)
async def create_subscription(
    subscription: schemas.NotificationSubscriptionCreate,
    db: Session = Depends(get_db)
):
    """Create a new notification subscription"""
    subscription_service = SubscriptionService(db)
    return await subscription_service.create_subscription(subscription)


@router.get("/subscriptions", response_model=schemas.SubscriptionListResponse)
async def list_subscriptions(
    tenant_id: UUID = Query(...),
    user_id: Optional[UUID] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    event_type: Optional[str] = Query(None),
    channel: Optional[schemas.NotificationChannel] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    """List notification subscriptions"""
    subscription_service = SubscriptionService(db)
    return await subscription_service.list_subscriptions(
        tenant_id=tenant_id,
        user_id=user_id,
        page=page,
        size=size,
        event_type=event_type,
        channel=channel,
        is_active=is_active
    )


@router.get("/subscriptions/{subscription_id}", response_model=schemas.NotificationSubscription)
async def get_subscription(
    subscription_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific notification subscription"""
    subscription_service = SubscriptionService(db)
    subscription = await subscription_service.get_subscription(subscription_id)
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return subscription


@router.put("/subscriptions/{subscription_id}", response_model=schemas.NotificationSubscription)
async def update_subscription(
    subscription_id: UUID,
    subscription_update: schemas.NotificationSubscriptionUpdate,
    db: Session = Depends(get_db)
):
    """Update a notification subscription"""
    subscription_service = SubscriptionService(db)
    subscription = await subscription_service.update_subscription(subscription_id, subscription_update)
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return subscription


@router.delete("/subscriptions/{subscription_id}")
async def delete_subscription(
    subscription_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete a notification subscription"""
    subscription_service = SubscriptionService(db)
    success = await subscription_service.delete_subscription(subscription_id)
    if not success:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return {"message": "Subscription deleted successfully"}


# Batch operations
@router.post("/notifications/batch", response_model=schemas.BatchDeliveryResult)
async def send_batch_notifications(
    notifications: List[schemas.NotificationCreate],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Send multiple notifications in batch"""
    delivery_service = DeliveryService(db)
    results = []
    
    for notification in notifications:
        try:
            notification_obj = await delivery_service.create_notification(notification)
            # Queue for async delivery
            background_tasks.add_task(
                send_notification_task.delay,
                str(notification_obj.id)
            )
            results.append(schemas.DeliveryResult(
                success=True,
                message="Notification queued successfully",
                external_id=str(notification_obj.id)
            ))
        except Exception as e:
            results.append(schemas.DeliveryResult(
                success=False,
                message=str(e),
                error_code="CREATION_FAILED"
            ))
    
    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful
    
    return schemas.BatchDeliveryResult(
        total=len(results),
        successful=successful,
        failed=failed,
        results=results
    )


# Health and status endpoints
@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "notification-service"}


@router.get("/stats")
async def get_stats(
    tenant_id: UUID = Query(...),
    db: Session = Depends(get_db)
):
    """Get notification statistics"""
    delivery_service = DeliveryService(db)
    stats = await delivery_service.get_notification_stats(tenant_id)
    return stats