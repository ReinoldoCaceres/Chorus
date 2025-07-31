import structlog
import logging
import sys
from typing import Any, Dict


def configure_logging():
    """Configure structured logging for the notification service"""
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = None) -> structlog.BoundLogger:
    """Get a structured logger instance"""
    return structlog.get_logger(name)


class LoggerMixin:
    """Mixin class to add logging capabilities to other classes"""
    
    @property
    def logger(self) -> structlog.BoundLogger:
        """Get logger for this class"""
        return get_logger(self.__class__.__name__)


def log_notification_event(
    event_type: str,
    notification_id: str = None,
    tenant_id: str = None,
    channel: str = None,
    recipient: str = None,
    **kwargs: Any
):
    """Log notification-specific events with consistent structure"""
    logger = get_logger("notification_events")
    
    log_data: Dict[str, Any] = {
        "event_type": event_type,
        **kwargs
    }
    
    if notification_id:
        log_data["notification_id"] = notification_id
    if tenant_id:
        log_data["tenant_id"] = tenant_id
    if channel:
        log_data["channel"] = channel
    if recipient:
        # Mask sensitive recipient data for privacy
        if channel == "email":
            # Mask email: example@domain.com -> e****e@domain.com
            if "@" in recipient:
                local, domain = recipient.split("@", 1)
                if len(local) > 2:
                    masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
                else:
                    masked_local = "*" * len(local)
                log_data["recipient"] = f"{masked_local}@{domain}"
            else:
                log_data["recipient"] = "*" * len(recipient)
        elif channel == "sms":
            # Mask phone: +1234567890 -> +****567890
            if len(recipient) > 6:
                log_data["recipient"] = recipient[:2] + "*" * (len(recipient) - 6) + recipient[-4:]
            else:
                log_data["recipient"] = "*" * len(recipient)
        else:
            # For webhooks, slack, teams - just indicate presence
            log_data["recipient"] = f"<{channel}_endpoint>"
    
    logger.info("Notification event", **log_data)


def log_template_event(
    event_type: str,
    template_id: str = None,
    tenant_id: str = None,
    template_name: str = None,
    channel: str = None,
    **kwargs: Any
):
    """Log template-specific events with consistent structure"""
    logger = get_logger("template_events")
    
    log_data: Dict[str, Any] = {
        "event_type": event_type,
        **kwargs
    }
    
    if template_id:
        log_data["template_id"] = template_id
    if tenant_id:
        log_data["tenant_id"] = tenant_id
    if template_name:
        log_data["template_name"] = template_name
    if channel:
        log_data["channel"] = channel
    
    logger.info("Template event", **log_data)


def log_subscription_event(
    event_type: str,
    subscription_id: str = None,
    tenant_id: str = None,
    user_id: str = None,
    channel: str = None,
    **kwargs: Any
):
    """Log subscription-specific events with consistent structure"""
    logger = get_logger("subscription_events")
    
    log_data: Dict[str, Any] = {
        "event_type": event_type,
        **kwargs
    }
    
    if subscription_id:
        log_data["subscription_id"] = subscription_id
    if tenant_id:
        log_data["tenant_id"] = tenant_id
    if user_id:
        log_data["user_id"] = user_id
    if channel:
        log_data["channel"] = channel
    
    logger.info("Subscription event", **log_data)


def log_delivery_metrics(
    channel: str,
    status: str,
    duration_ms: int = None,
    error_code: str = None,
    tenant_id: str = None,
    **kwargs: Any
):
    """Log delivery metrics for monitoring and alerting"""
    logger = get_logger("delivery_metrics")
    
    log_data: Dict[str, Any] = {
        "metric_type": "delivery",
        "channel": channel,
        "status": status,
        **kwargs
    }
    
    if duration_ms is not None:
        log_data["duration_ms"] = duration_ms
    if error_code:
        log_data["error_code"] = error_code
    if tenant_id:
        log_data["tenant_id"] = tenant_id
    
    logger.info("Delivery metrics", **log_data)


def log_performance_metrics(
    operation: str,
    duration_ms: int,
    status: str = "success",
    **kwargs: Any
):
    """Log performance metrics for operations"""
    logger = get_logger("performance_metrics")
    
    log_data: Dict[str, Any] = {
        "metric_type": "performance",
        "operation": operation,
        "duration_ms": duration_ms,
        "status": status,
        **kwargs
    }
    
    logger.info("Performance metrics", **log_data)