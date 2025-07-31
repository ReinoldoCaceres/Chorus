from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, Dict, Any, List
from uuid import UUID
import structlog

from app.models.database import NotificationSubscription
from app.models import schemas

logger = structlog.get_logger()


class SubscriptionService:
    """Service for managing notification subscriptions"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_subscription(
        self,
        subscription_data: schemas.NotificationSubscriptionCreate
    ) -> NotificationSubscription:
        """Create a new notification subscription"""
        try:
            # Check for existing subscription with same parameters
            existing = self.db.query(NotificationSubscription).filter(
                and_(
                    NotificationSubscription.tenant_id == subscription_data.tenant_id,
                    NotificationSubscription.user_id == subscription_data.user_id,
                    NotificationSubscription.event_type == subscription_data.event_type,
                    NotificationSubscription.channel == subscription_data.channel.value,
                    NotificationSubscription.endpoint == subscription_data.endpoint
                )
            ).first()
            
            if existing:
                # If subscription exists but is inactive, reactivate it
                if not existing.is_active:
                    existing.is_active = True
                    existing.preferences = subscription_data.preferences
                    self.db.commit()
                    self.db.refresh(existing)
                    
                    logger.info(
                        "Subscription reactivated",
                        subscription_id=str(existing.id),
                        tenant_id=str(subscription_data.tenant_id),
                        user_id=str(subscription_data.user_id)
                    )
                    
                    return existing
                else:
                    raise ValueError("Subscription already exists and is active")
            
            db_subscription = NotificationSubscription(
                tenant_id=subscription_data.tenant_id,
                user_id=subscription_data.user_id,
                event_type=subscription_data.event_type,
                channel=subscription_data.channel.value,
                endpoint=subscription_data.endpoint,
                is_active=subscription_data.is_active,
                preferences=subscription_data.preferences
            )
            
            self.db.add(db_subscription)
            self.db.commit()
            self.db.refresh(db_subscription)
            
            logger.info(
                "Subscription created",
                subscription_id=str(db_subscription.id),
                tenant_id=str(subscription_data.tenant_id),
                user_id=str(subscription_data.user_id),
                event_type=subscription_data.event_type,
                channel=subscription_data.channel.value
            )
            
            return db_subscription
            
        except Exception as e:
            logger.error("Failed to create subscription", error=str(e))
            self.db.rollback()
            raise
    
    async def get_subscription(self, subscription_id: UUID) -> Optional[NotificationSubscription]:
        """Get a subscription by ID"""
        return self.db.query(NotificationSubscription).filter(
            NotificationSubscription.id == subscription_id
        ).first()
    
    async def list_subscriptions(
        self,
        tenant_id: UUID,
        user_id: Optional[UUID] = None,
        page: int = 1,
        size: int = 50,
        event_type: Optional[str] = None,
        channel: Optional[schemas.NotificationChannel] = None,
        is_active: Optional[bool] = None
    ) -> schemas.SubscriptionListResponse:
        """List subscriptions with filtering and pagination"""
        query = self.db.query(NotificationSubscription).filter(
            NotificationSubscription.tenant_id == tenant_id
        )
        
        if user_id:
            query = query.filter(NotificationSubscription.user_id == user_id)
        
        if event_type:
            query = query.filter(NotificationSubscription.event_type == event_type)
        
        if channel:
            query = query.filter(NotificationSubscription.channel == channel.value)
        
        if is_active is not None:
            query = query.filter(NotificationSubscription.is_active == is_active)
        
        # Count total
        total = query.count()
        
        # Apply pagination and ordering
        offset = (page - 1) * size
        subscriptions = query.order_by(NotificationSubscription.created_at.desc()).offset(offset).limit(size).all()
        
        return schemas.SubscriptionListResponse(
            subscriptions=subscriptions,
            total=total,
            page=page,
            size=size
        )
    
    async def update_subscription(
        self,
        subscription_id: UUID,
        subscription_update: schemas.NotificationSubscriptionUpdate
    ) -> Optional[NotificationSubscription]:
        """Update a subscription"""
        try:
            db_subscription = await self.get_subscription(subscription_id)
            if not db_subscription:
                return None
            
            update_data = subscription_update.model_dump(exclude_unset=True)
            
            for field, value in update_data.items():
                if field == "channel" and value:
                    setattr(db_subscription, field, value.value)
                else:
                    setattr(db_subscription, field, value)
            
            self.db.commit()
            self.db.refresh(db_subscription)
            
            logger.info(
                "Subscription updated",
                subscription_id=str(subscription_id),
                updated_fields=list(update_data.keys())
            )
            
            return db_subscription
            
        except Exception as e:
            logger.error("Failed to update subscription", subscription_id=str(subscription_id), error=str(e))
            self.db.rollback()
            raise
    
    async def delete_subscription(self, subscription_id: UUID) -> bool:
        """Delete a subscription (soft delete by setting is_active=False)"""
        try:
            db_subscription = await self.get_subscription(subscription_id)
            if not db_subscription:
                return False
            
            db_subscription.is_active = False
            self.db.commit()
            
            logger.info("Subscription deleted", subscription_id=str(subscription_id))
            return True
            
        except Exception as e:
            logger.error("Failed to delete subscription", subscription_id=str(subscription_id), error=str(e))
            self.db.rollback()
            raise
    
    async def get_user_subscriptions(
        self,
        tenant_id: UUID,
        user_id: UUID,
        event_type: Optional[str] = None,
        channel: Optional[schemas.NotificationChannel] = None,
        active_only: bool = True
    ) -> List[NotificationSubscription]:
        """Get all subscriptions for a specific user"""
        query = self.db.query(NotificationSubscription).filter(
            and_(
                NotificationSubscription.tenant_id == tenant_id,
                NotificationSubscription.user_id == user_id
            )
        )
        
        if event_type:
            query = query.filter(NotificationSubscription.event_type == event_type)
        
        if channel:
            query = query.filter(NotificationSubscription.channel == channel.value)
        
        if active_only:
            query = query.filter(NotificationSubscription.is_active == True)
        
        return query.all()
    
    async def get_subscriptions_for_event(
        self,
        tenant_id: UUID,
        event_type: str,
        channel: Optional[schemas.NotificationChannel] = None
    ) -> List[NotificationSubscription]:
        """Get all active subscriptions for a specific event type"""
        query = self.db.query(NotificationSubscription).filter(
            and_(
                NotificationSubscription.tenant_id == tenant_id,
                NotificationSubscription.event_type == event_type,
                NotificationSubscription.is_active == True
            )
        )
        
        if channel:
            query = query.filter(NotificationSubscription.channel == channel.value)
        
        return query.all()
    
    async def bulk_subscribe(
        self,
        tenant_id: UUID,
        user_ids: List[UUID],
        event_type: str,
        channel: schemas.NotificationChannel,
        endpoint_mapping: Dict[UUID, str],
        preferences: Optional[Dict[str, Any]] = None
    ) -> List[NotificationSubscription]:
        """Create subscriptions for multiple users at once"""
        try:
            created_subscriptions = []
            
            for user_id in user_ids:
                if user_id not in endpoint_mapping:
                    logger.warning(
                        "Skipping user subscription - no endpoint provided",
                        user_id=str(user_id)
                    )
                    continue
                
                try:
                    subscription_data = schemas.NotificationSubscriptionCreate(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        event_type=event_type,
                        channel=channel,
                        endpoint=endpoint_mapping[user_id],
                        preferences=preferences or {}
                    )
                    
                    subscription = await self.create_subscription(subscription_data)
                    created_subscriptions.append(subscription)
                    
                except Exception as e:
                    logger.error(
                        "Failed to create bulk subscription",
                        user_id=str(user_id),
                        error=str(e)
                    )
                    continue
            
            logger.info(
                "Bulk subscription completed",
                tenant_id=str(tenant_id),
                event_type=event_type,
                channel=channel.value,
                total_requested=len(user_ids),
                successful=len(created_subscriptions)
            )
            
            return created_subscriptions
            
        except Exception as e:
            logger.error("Failed bulk subscription", error=str(e))
            raise
    
    async def bulk_unsubscribe(
        self,
        tenant_id: UUID,
        user_ids: List[UUID],
        event_type: Optional[str] = None,
        channel: Optional[schemas.NotificationChannel] = None
    ) -> int:
        """Unsubscribe multiple users from notifications"""
        try:
            query = self.db.query(NotificationSubscription).filter(
                and_(
                    NotificationSubscription.tenant_id == tenant_id,
                    NotificationSubscription.user_id.in_(user_ids),
                    NotificationSubscription.is_active == True
                )
            )
            
            if event_type:
                query = query.filter(NotificationSubscription.event_type == event_type)
            
            if channel:
                query = query.filter(NotificationSubscription.channel == channel.value)
            
            # Count affected subscriptions
            count = query.count()
            
            # Update subscriptions to inactive
            query.update({"is_active": False}, synchronize_session=False)
            self.db.commit()
            
            logger.info(
                "Bulk unsubscription completed",
                tenant_id=str(tenant_id),
                affected_count=count,
                user_count=len(user_ids)
            )
            
            return count
            
        except Exception as e:
            logger.error("Failed bulk unsubscription", error=str(e))
            self.db.rollback()
            raise
    
    async def validate_endpoint(
        self,
        channel: schemas.NotificationChannel,
        endpoint: str
    ) -> bool:
        """Validate an endpoint for a specific channel"""
        try:
            if channel == schemas.NotificationChannel.EMAIL:
                # Basic email validation
                import re
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                return bool(re.match(email_pattern, endpoint))
            
            elif channel == schemas.NotificationChannel.SMS:
                # Basic phone number validation (international format)
                import re
                phone_pattern = r'^\+[1-9]\d{1,14}$'
                return bool(re.match(phone_pattern, endpoint))
            
            elif channel in [
                schemas.NotificationChannel.WEBHOOK,
                schemas.NotificationChannel.SLACK,
                schemas.NotificationChannel.TEAMS
            ]:
                # Basic URL validation
                import re
                url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
                return bool(re.match(url_pattern, endpoint))
            
            return False
            
        except Exception as e:
            logger.error("Failed to validate endpoint", channel=channel.value, error=str(e))
            return False