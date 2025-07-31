from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime, timedelta
import httpx
import structlog
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from twilio.rest import Client as TwilioClient

from app.models.database import Notification, NotificationTemplate
from app.models import schemas
from app.config import get_settings
from app.services.template_service import TemplateService

logger = structlog.get_logger()
settings = get_settings()


class DeliveryService:
    """Service for delivering notifications through various channels"""
    
    def __init__(self, db: Session):
        self.db = db
        self.template_service = TemplateService(db)
        
        # Initialize external clients
        self.sendgrid_client = None
        self.twilio_client = None
        
        if settings.sendgrid_api_key:
            self.sendgrid_client = SendGridAPIClient(api_key=settings.sendgrid_api_key)
        
        if settings.twilio_account_sid and settings.twilio_auth_token:
            self.twilio_client = TwilioClient(
                settings.twilio_account_sid,
                settings.twilio_auth_token
            )
    
    async def create_notification(self, notification_data: schemas.NotificationCreate) -> Notification:
        """Create a new notification"""
        try:
            db_notification = Notification(
                tenant_id=notification_data.tenant_id,
                template_id=notification_data.template_id,
                channel=notification_data.channel.value,
                recipient=notification_data.recipient,
                subject=notification_data.subject,
                body=notification_data.body,
                data=notification_data.data,
                scheduled_at=notification_data.scheduled_at or datetime.utcnow(),
                max_retries=settings.max_retry_attempts
            )
            
            self.db.add(db_notification)
            self.db.commit()
            self.db.refresh(db_notification)
            
            logger.info(
                "Notification created",
                notification_id=str(db_notification.id),
                tenant_id=str(notification_data.tenant_id),
                channel=notification_data.channel.value,
                recipient=notification_data.recipient
            )
            
            return db_notification
            
        except Exception as e:
            logger.error("Failed to create notification", error=str(e))
            self.db.rollback()
            raise
    
    async def create_notification_from_template(
        self,
        notification_data: schemas.NotificationCreateFromTemplate
    ) -> Notification:
        """Create a notification from a template"""
        try:
            # Render template
            rendered = await self.template_service.render_template(
                notification_data.template_id,
                notification_data.variables
            )
            
            if not rendered:
                raise ValueError("Template not found or inactive")
            
            # Get template to determine channel
            template = await self.template_service.get_template(notification_data.template_id)
            if not template:
                raise ValueError("Template not found")
            
            # Create notification with rendered content
            db_notification = Notification(
                tenant_id=notification_data.tenant_id,
                template_id=notification_data.template_id,
                channel=template.channel,
                recipient=notification_data.recipient,
                subject=rendered.subject,
                body=rendered.body,
                data=rendered.rendered_variables,
                scheduled_at=notification_data.scheduled_at or datetime.utcnow(),
                max_retries=settings.max_retry_attempts
            )
            
            self.db.add(db_notification)
            self.db.commit()
            self.db.refresh(db_notification)
            
            logger.info(
                "Notification created from template",
                notification_id=str(db_notification.id),
                template_id=str(notification_data.template_id),
                tenant_id=str(notification_data.tenant_id),
                channel=template.channel,
                recipient=notification_data.recipient
            )
            
            return db_notification
            
        except Exception as e:
            logger.error("Failed to create notification from template", error=str(e))
            self.db.rollback()
            raise
    
    async def get_notification(self, notification_id: UUID) -> Optional[Notification]:
        """Get a notification by ID"""
        return self.db.query(Notification).filter(
            Notification.id == notification_id
        ).first()
    
    async def list_notifications(
        self,
        tenant_id: UUID,
        page: int = 1,
        size: int = 50,
        status: Optional[schemas.NotificationStatus] = None,
        channel: Optional[schemas.NotificationChannel] = None,
        recipient: Optional[str] = None
    ) -> schemas.NotificationListResponse:
        """List notifications with filtering and pagination"""
        query = self.db.query(Notification).filter(
            Notification.tenant_id == tenant_id
        )
        
        if status:
            query = query.filter(Notification.status == status.value)
        
        if channel:
            query = query.filter(Notification.channel == channel.value)
        
        if recipient:
            query = query.filter(Notification.recipient.ilike(f"%{recipient}%"))
        
        # Count total
        total = query.count()
        
        # Apply pagination and ordering
        offset = (page - 1) * size
        notifications = query.order_by(Notification.created_at.desc()).offset(offset).limit(size).all()
        
        return schemas.NotificationListResponse(
            notifications=notifications,
            total=total,
            page=page,
            size=size
        )
    
    async def update_notification(
        self,
        notification_id: UUID,
        notification_update: schemas.NotificationUpdate
    ) -> Optional[Notification]:
        """Update a notification"""
        try:
            db_notification = await self.get_notification(notification_id)
            if not db_notification:
                return None
            
            update_data = notification_update.model_dump(exclude_unset=True)
            
            for field, value in update_data.items():
                if field == "status" and value:
                    setattr(db_notification, field, value.value)
                else:
                    setattr(db_notification, field, value)
            
            self.db.commit()
            self.db.refresh(db_notification)
            
            logger.info(
                "Notification updated",
                notification_id=str(notification_id),
                updated_fields=list(update_data.keys())
            )
            
            return db_notification
            
        except Exception as e:
            logger.error("Failed to update notification", notification_id=str(notification_id), error=str(e))
            self.db.rollback()
            raise
    
    async def reset_notification_for_retry(self, notification_id: UUID) -> bool:
        """Reset notification status for retry"""
        try:
            db_notification = await self.get_notification(notification_id)
            if not db_notification:
                return False
            
            db_notification.status = "pending"
            db_notification.error_message = None
            db_notification.scheduled_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info("Notification reset for retry", notification_id=str(notification_id))
            return True
            
        except Exception as e:
            logger.error("Failed to reset notification", notification_id=str(notification_id), error=str(e))
            self.db.rollback()
            raise
    
    async def deliver_notification(self, notification_id: UUID) -> schemas.DeliveryResult:
        """Deliver a notification through the appropriate channel"""
        db_notification = await self.get_notification(notification_id)
        if not db_notification:
            return schemas.DeliveryResult(
                success=False,
                message="Notification not found",
                error_code="NOT_FOUND"
            )
        
        try:
            # Update status to processing
            db_notification.status = "processing"
            self.db.commit()
            
            # Route to appropriate delivery method
            if db_notification.channel == "email":
                result = await self._deliver_email(db_notification)
            elif db_notification.channel == "sms":
                result = await self._deliver_sms(db_notification)
            elif db_notification.channel == "webhook":
                result = await self._deliver_webhook(db_notification)
            elif db_notification.channel == "slack":
                result = await self._deliver_slack(db_notification)
            elif db_notification.channel == "teams":
                result = await self._deliver_teams(db_notification)
            else:
                result = schemas.DeliveryResult(
                    success=False,
                    message=f"Unsupported channel: {db_notification.channel}",
                    error_code="UNSUPPORTED_CHANNEL"
                )
            
            # Update notification status based on result
            if result.success:
                db_notification.status = "sent"
                db_notification.sent_at = datetime.utcnow()
                db_notification.error_message = None
            else:
                db_notification.status = "failed"
                db_notification.error_message = result.message
                db_notification.retry_count += 1
            
            self.db.commit()
            
            logger.info(
                "Notification delivery completed",
                notification_id=str(notification_id),
                channel=db_notification.channel,
                success=result.success,
                retry_count=db_notification.retry_count
            )
            
            return result
            
        except Exception as e:
            logger.error("Failed to deliver notification", notification_id=str(notification_id), error=str(e))
            
            # Update notification with error
            db_notification.status = "failed"
            db_notification.error_message = str(e)
            db_notification.retry_count += 1
            self.db.commit()
            
            return schemas.DeliveryResult(
                success=False,
                message=str(e),
                error_code="DELIVERY_ERROR"
            )
    
    async def _deliver_email(self, notification: Notification) -> schemas.DeliveryResult:
        """Deliver email notification using SendGrid"""
        if not self.sendgrid_client:
            return schemas.DeliveryResult(
                success=False,
                message="SendGrid not configured",
                error_code="SERVICE_NOT_CONFIGURED"
            )
        
        try:
            message = Mail(
                from_email=settings.sendgrid_from_email,
                to_emails=notification.recipient,
                subject=notification.subject or "Notification",
                html_content=notification.body
            )
            
            response = self.sendgrid_client.send(message)
            
            if response.status_code in [200, 202]:
                return schemas.DeliveryResult(
                    success=True,
                    message="Email sent successfully",
                    external_id=response.headers.get("X-Message-Id")
                )
            else:
                return schemas.DeliveryResult(
                    success=False,
                    message=f"SendGrid API error: {response.status_code}",
                    error_code="SENDGRID_ERROR"
                )
                
        except Exception as e:
            return schemas.DeliveryResult(
                success=False,
                message=f"Email delivery failed: {str(e)}",
                error_code="EMAIL_ERROR"
            )
    
    async def _deliver_sms(self, notification: Notification) -> schemas.DeliveryResult:
        """Deliver SMS notification using Twilio"""
        if not self.twilio_client:
            return schemas.DeliveryResult(
                success=False,
                message="Twilio not configured",
                error_code="SERVICE_NOT_CONFIGURED"
            )
        
        try:
            message = self.twilio_client.messages.create(
                body=notification.body,
                from_=settings.twilio_from_number,
                to=notification.recipient
            )
            
            return schemas.DeliveryResult(
                success=True,
                message="SMS sent successfully",
                external_id=message.sid
            )
            
        except Exception as e:
            return schemas.DeliveryResult(
                success=False,
                message=f"SMS delivery failed: {str(e)}",
                error_code="SMS_ERROR"
            )
    
    async def _deliver_webhook(self, notification: Notification) -> schemas.DeliveryResult:
        """Deliver webhook notification"""
        try:
            payload = {
                "notification_id": str(notification.id),
                "tenant_id": str(notification.tenant_id),
                "subject": notification.subject,
                "body": notification.body,
                "data": notification.data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    notification.recipient,  # webhook URL
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code in [200, 201, 202, 204]:
                    return schemas.DeliveryResult(
                        success=True,
                        message="Webhook delivered successfully",
                        external_id=str(response.status_code)
                    )
                else:
                    return schemas.DeliveryResult(
                        success=False,
                        message=f"Webhook returned status {response.status_code}",
                        error_code="WEBHOOK_ERROR"
                    )
                    
        except Exception as e:
            return schemas.DeliveryResult(
                success=False,
                message=f"Webhook delivery failed: {str(e)}",
                error_code="WEBHOOK_ERROR"
            )
    
    async def _deliver_slack(self, notification: Notification) -> schemas.DeliveryResult:
        """Deliver Slack notification"""
        try:
            payload = {
                "text": notification.body,
                "username": "Chorus Notifications",
                "icon_emoji": ":bell:"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    notification.recipient,  # Slack webhook URL
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return schemas.DeliveryResult(
                        success=True,
                        message="Slack message sent successfully"
                    )
                else:
                    return schemas.DeliveryResult(
                        success=False,
                        message=f"Slack API returned status {response.status_code}",
                        error_code="SLACK_ERROR"
                    )
                    
        except Exception as e:
            return schemas.DeliveryResult(
                success=False,
                message=f"Slack delivery failed: {str(e)}",
                error_code="SLACK_ERROR"
            )
    
    async def _deliver_teams(self, notification: Notification) -> schemas.DeliveryResult:
        """Deliver Microsoft Teams notification"""
        try:
            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "summary": notification.subject or "Notification",
                "text": notification.body
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    notification.recipient,  # Teams webhook URL
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return schemas.DeliveryResult(
                        success=True,
                        message="Teams message sent successfully"
                    )
                else:
                    return schemas.DeliveryResult(
                        success=False,
                        message=f"Teams API returned status {response.status_code}",
                        error_code="TEAMS_ERROR"
                    )
                    
        except Exception as e:
            return schemas.DeliveryResult(
                success=False,
                message=f"Teams delivery failed: {str(e)}",
                error_code="TEAMS_ERROR"
            )
    
    async def get_notification_stats(self, tenant_id: UUID) -> Dict[str, Any]:
        """Get notification statistics for a tenant"""
        try:
            # Get counts by status
            status_counts = self.db.query(
                Notification.status,
                func.count(Notification.id).label("count")
            ).filter(
                Notification.tenant_id == tenant_id
            ).group_by(Notification.status).all()
            
            # Get counts by channel
            channel_counts = self.db.query(
                Notification.channel,
                func.count(Notification.id).label("count")
            ).filter(
                Notification.tenant_id == tenant_id
            ).group_by(Notification.channel).all()
            
            # Get recent activity (last 24 hours)
            recent_cutoff = datetime.utcnow() - timedelta(hours=24)
            recent_count = self.db.query(Notification).filter(
                and_(
                    Notification.tenant_id == tenant_id,
                    Notification.created_at >= recent_cutoff
                )
            ).count()
            
            return {
                "status_counts": {status: count for status, count in status_counts},
                "channel_counts": {channel: count for channel, count in channel_counts},
                "recent_24h": recent_count,
                "total": sum(count for _, count in status_counts)
            }
            
        except Exception as e:
            logger.error("Failed to get notification stats", tenant_id=str(tenant_id), error=str(e))
            raise