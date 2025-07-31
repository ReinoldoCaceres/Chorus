from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, Dict, Any, List
from uuid import UUID
import jinja2
from jinja2 import Environment, DictLoader, TemplateError
import structlog

from app.models.database import NotificationTemplate
from app.models import schemas

logger = structlog.get_logger()


class TemplateService:
    """Service for managing notification templates"""
    
    def __init__(self, db: Session):
        self.db = db
        self.jinja_env = Environment(
            loader=DictLoader({}),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    async def create_template(self, template_data: schemas.NotificationTemplateCreate) -> NotificationTemplate:
        """Create a new notification template"""
        try:
            # Validate template syntax
            await self._validate_template_syntax(template_data.body_template, template_data.subject)
            
            db_template = NotificationTemplate(
                tenant_id=template_data.tenant_id,
                name=template_data.name,
                channel=template_data.channel.value,
                subject=template_data.subject,
                body_template=template_data.body_template,
                variables=template_data.variables,
                is_active=template_data.is_active
            )
            
            self.db.add(db_template)
            self.db.commit()
            self.db.refresh(db_template)
            
            logger.info(
                "Template created",
                template_id=str(db_template.id),
                tenant_id=str(template_data.tenant_id),
                name=template_data.name,
                channel=template_data.channel.value
            )
            
            return db_template
            
        except TemplateError as e:
            logger.error("Template syntax error", error=str(e))
            raise ValueError(f"Template syntax error: {str(e)}")
        except Exception as e:
            logger.error("Failed to create template", error=str(e))
            self.db.rollback()
            raise
    
    async def get_template(self, template_id: UUID) -> Optional[NotificationTemplate]:
        """Get a template by ID"""
        return self.db.query(NotificationTemplate).filter(
            NotificationTemplate.id == template_id
        ).first()
    
    async def list_templates(
        self,
        tenant_id: UUID,
        page: int = 1,
        size: int = 50,
        channel: Optional[schemas.NotificationChannel] = None,
        is_active: Optional[bool] = None
    ) -> schemas.TemplateListResponse:
        """List templates with filtering and pagination"""
        query = self.db.query(NotificationTemplate).filter(
            NotificationTemplate.tenant_id == tenant_id
        )
        
        if channel:
            query = query.filter(NotificationTemplate.channel == channel.value)
        
        if is_active is not None:
            query = query.filter(NotificationTemplate.is_active == is_active)
        
        # Count total
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * size
        templates = query.offset(offset).limit(size).all()
        
        return schemas.TemplateListResponse(
            templates=templates,
            total=total,
            page=page,
            size=size
        )
    
    async def update_template(
        self,
        template_id: UUID,
        template_update: schemas.NotificationTemplateUpdate
    ) -> Optional[NotificationTemplate]:
        """Update a template"""
        try:
            db_template = await self.get_template(template_id)
            if not db_template:
                return None
            
            update_data = template_update.model_dump(exclude_unset=True)
            
            # Validate template syntax if body_template or subject is being updated
            if "body_template" in update_data or "subject" in update_data:
                body_template = update_data.get("body_template", db_template.body_template)
                subject = update_data.get("subject", db_template.subject)
                await self._validate_template_syntax(body_template, subject)
            
            # Update fields
            for field, value in update_data.items():
                if field == "channel" and value:
                    setattr(db_template, field, value.value)
                else:
                    setattr(db_template, field, value)
            
            self.db.commit()
            self.db.refresh(db_template)
            
            logger.info(
                "Template updated",
                template_id=str(template_id),
                updated_fields=list(update_data.keys())
            )
            
            return db_template
            
        except TemplateError as e:
            logger.error("Template syntax error", error=str(e))
            raise ValueError(f"Template syntax error: {str(e)}")
        except Exception as e:
            logger.error("Failed to update template", template_id=str(template_id), error=str(e))
            self.db.rollback()
            raise
    
    async def delete_template(self, template_id: UUID) -> bool:
        """Delete a template (soft delete by setting is_active=False)"""
        try:
            db_template = await self.get_template(template_id)
            if not db_template:
                return False
            
            db_template.is_active = False
            self.db.commit()
            
            logger.info("Template deleted", template_id=str(template_id))
            return True
            
        except Exception as e:
            logger.error("Failed to delete template", template_id=str(template_id), error=str(e))
            self.db.rollback()
            raise
    
    async def render_template(
        self,
        template_id: UUID,
        variables: Dict[str, Any]
    ) -> Optional[schemas.TemplateRenderResponse]:
        """Render a template with provided variables"""
        try:
            db_template = await self.get_template(template_id)
            if not db_template or not db_template.is_active:
                return None
            
            # Merge template variables with provided variables
            all_variables = {**db_template.variables, **variables}
            
            # Render body
            body_template = self.jinja_env.from_string(db_template.body_template)
            rendered_body = body_template.render(**all_variables)
            
            # Render subject if exists
            rendered_subject = None
            if db_template.subject:
                subject_template = self.jinja_env.from_string(db_template.subject)
                rendered_subject = subject_template.render(**all_variables)
            
            return schemas.TemplateRenderResponse(
                subject=rendered_subject,
                body=rendered_body,
                rendered_variables=all_variables
            )
            
        except TemplateError as e:
            logger.error(
                "Template rendering error",
                template_id=str(template_id),
                error=str(e)
            )
            raise ValueError(f"Template rendering error: {str(e)}")
        except Exception as e:
            logger.error(
                "Failed to render template",
                template_id=str(template_id),
                error=str(e)
            )
            raise
    
    async def get_templates_by_channel(
        self,
        tenant_id: UUID,
        channel: schemas.NotificationChannel
    ) -> List[NotificationTemplate]:
        """Get all active templates for a specific channel"""
        return self.db.query(NotificationTemplate).filter(
            and_(
                NotificationTemplate.tenant_id == tenant_id,
                NotificationTemplate.channel == channel.value,
                NotificationTemplate.is_active == True
            )
        ).all()
    
    async def _validate_template_syntax(self, body_template: str, subject: Optional[str] = None):
        """Validate Jinja2 template syntax"""
        try:
            # Validate body template
            self.jinja_env.from_string(body_template)
            
            # Validate subject template if provided
            if subject:
                self.jinja_env.from_string(subject)
                
        except TemplateError as e:
            raise e