import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
import structlog

from app.models.database import Alert, AlertRule, SystemMetric, ProcessMetric
from app.models.schemas import (
    AlertCreate, AlertUpdate, AlertResponse, 
    AlertRuleCreate, AlertRuleUpdate, AlertRuleResponse,
    ServiceHealthCheck, AlertStats
)
from app.db.redis import RedisCache
from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class AlertManager:
    """Alert management and generation service"""
    
    def __init__(self, db: Session):
        self.db = db
        self.redis = RedisCache()
        self.settings = settings
        
    async def check_service_health(self) -> List[ServiceHealthCheck]:
        """Check health of all configured services"""
        health_checks = []
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for service_name, endpoint in self.settings.service_endpoints.items():
                start_time = datetime.utcnow()
                
                try:
                    response = await client.get(endpoint)
                    end_time = datetime.utcnow()
                    response_time_ms = int((end_time - start_time).total_seconds() * 1000)
                    
                    status = "healthy" if response.status_code == 200 else "unhealthy"
                    error_message = None if status == "healthy" else f"HTTP {response.status_code}"
                    
                except httpx.TimeoutException:
                    response_time_ms = None
                    status = "timeout"
                    error_message = "Request timeout"
                    
                except Exception as e:
                    response_time_ms = None
                    status = "unhealthy"
                    error_message = str(e)
                
                health_check = ServiceHealthCheck(
                    service_name=service_name,
                    endpoint=endpoint,
                    status=status,
                    response_time_ms=response_time_ms,
                    last_checked=datetime.utcnow(),
                    error_message=error_message
                )
                
                health_checks.append(health_check)
                
                # Generate alerts for unhealthy services
                if status != "healthy":
                    await self._create_service_alert(service_name, status, error_message, response_time_ms)
        
        logger.info("Completed service health checks", 
                   service_count=len(health_checks),
                   healthy_count=len([h for h in health_checks if h.status == "healthy"]))
        
        return health_checks
    
    async def check_system_alerts(self, hostname: Optional[str] = None) -> List[Alert]:
        """Check system metrics against alert rules and generate alerts"""
        alerts_created = []
        
        try:
            # Get active alert rules
            active_rules = self.db.query(AlertRule).filter(AlertRule.is_active == True).all()
            
            for rule in active_rules:
                try:
                    alert = await self._evaluate_alert_rule(rule, hostname)
                    if alert:
                        alerts_created.append(alert)
                except Exception as e:
                    logger.error("Failed to evaluate alert rule", 
                               rule_name=rule.name, 
                               error=str(e))
            
            logger.info("Completed system alert checks", 
                       rules_evaluated=len(active_rules),
                       alerts_created=len(alerts_created))
            
            return alerts_created
            
        except Exception as e:
            logger.error("Failed to check system alerts", error=str(e))
            return []
    
    async def _evaluate_alert_rule(self, rule: AlertRule, hostname: Optional[str] = None) -> Optional[Alert]:
        """Evaluate a single alert rule against current metrics"""
        try:
            condition = rule.condition
            rule_type = rule.rule_type
            
            if rule_type == "system_metric":
                return await self._evaluate_system_metric_rule(rule, condition, hostname)
            elif rule_type == "service_health":
                return await self._evaluate_service_health_rule(rule, condition)
            elif rule_type == "process_metric":
                return await self._evaluate_process_metric_rule(rule, condition, hostname)
            else:
                logger.warning("Unknown rule type", rule_name=rule.name, rule_type=rule_type)
                return None
                
        except Exception as e:
            logger.error("Failed to evaluate alert rule", 
                        rule_name=rule.name, 
                        error=str(e))
            return None
    
    async def _evaluate_system_metric_rule(self, rule: AlertRule, condition: Dict[str, Any], 
                                         hostname: Optional[str] = None) -> Optional[Alert]:
        """Evaluate system metric alert rule"""
        metric_type = condition.get("metric_type")
        operator = condition.get("operator", ">")
        threshold = Decimal(str(condition.get("threshold", 0)))
        time_window_minutes = condition.get("time_window_minutes", 5)
        
        if not metric_type:
            return None
        
        # Check if we're in cooldown period
        if await self._is_in_cooldown(rule):
            return None
        
        # Get recent metrics
        since_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        query = self.db.query(SystemMetric).filter(
            SystemMetric.metric_type == metric_type,
            SystemMetric.timestamp >= since_time
        )
        
        if hostname:
            query = query.filter(SystemMetric.hostname == hostname)
        
        recent_metrics = query.order_by(desc(SystemMetric.timestamp)).limit(10).all()
        
        if not recent_metrics:
            return None
        
        # Evaluate condition
        latest_metric = recent_metrics[0]
        current_value = latest_metric.metric_value
        
        alert_triggered = False
        if operator == ">":
            alert_triggered = current_value > threshold
        elif operator == "<":
            alert_triggered = current_value < threshold
        elif operator == ">=":
            alert_triggered = current_value >= threshold
        elif operator == "<=":
            alert_triggered = current_value <= threshold
        elif operator == "==":
            alert_triggered = current_value == threshold
        
        if alert_triggered:
            alert_data = AlertCreate(
                alert_type="system_metric",
                severity=rule.severity,
                source=f"system:{latest_metric.hostname}",
                title=f"{rule.name} - {metric_type} Alert",
                description=f"{metric_type} value {current_value} {operator} {threshold} on {latest_metric.hostname}",
                alert_metadata={
                    "rule_id": str(rule.id),
                    "metric_type": metric_type,
                    "current_value": float(current_value),
                    "threshold": float(threshold),
                    "operator": operator,
                    "hostname": latest_metric.hostname,
                    "metric_unit": latest_metric.metric_unit
                }
            )
            
            alert = await self.create_alert(alert_data)
            await self._update_rule_last_triggered(rule)
            
            return alert
        
        return None
    
    async def _evaluate_service_health_rule(self, rule: AlertRule, condition: Dict[str, Any]) -> Optional[Alert]:
        """Evaluate service health alert rule"""
        service_name = condition.get("service_name")
        max_response_time = condition.get("max_response_time_ms", self.settings.response_time_alert_threshold)
        
        if not service_name:
            return None
        
        # Check if we're in cooldown period
        if await self._is_in_cooldown(rule):
            return None
        
        # Get cached health data from Redis
        health_data = self.redis.get_system_health(service_name)
        if not health_data:
            return None
        
        # Check for service down or slow response
        if (health_data.get("status") != "healthy" or 
            (health_data.get("response_time_ms", 0) > max_response_time)):
            
            alert_data = AlertCreate(
                alert_type="service_health",
                severity=rule.severity,
                source=f"service:{service_name}",
                title=f"{rule.name} - Service Health Alert",
                description=f"Service {service_name} is {health_data.get('status', 'unknown')}",
                alert_metadata={
                    "rule_id": str(rule.id),
                    "service_name": service_name,
                    "status": health_data.get("status"),
                    "response_time_ms": health_data.get("response_time_ms"),
                    "error_message": health_data.get("error_message")
                }
            )
            
            alert = await self.create_alert(alert_data)
            await self._update_rule_last_triggered(rule)
            
            return alert
        
        return None
    
    async def _evaluate_process_metric_rule(self, rule: AlertRule, condition: Dict[str, Any], 
                                          hostname: Optional[str] = None) -> Optional[Alert]:
        """Evaluate process metric alert rule"""
        process_name = condition.get("process_name")
        metric_field = condition.get("metric_field", "cpu_percent")
        operator = condition.get("operator", ">")
        threshold = Decimal(str(condition.get("threshold", 0)))
        time_window_minutes = condition.get("time_window_minutes", 5)
        
        if not process_name:
            return None
        
        # Check if we're in cooldown period
        if await self._is_in_cooldown(rule):
            return None
        
        # Get recent process metrics
        since_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        query = self.db.query(ProcessMetric).filter(
            ProcessMetric.process_name == process_name,
            ProcessMetric.timestamp >= since_time
        )
        
        if hostname:
            query = query.filter(ProcessMetric.hostname == hostname)
        
        recent_metrics = query.order_by(desc(ProcessMetric.timestamp)).limit(10).all()
        
        if not recent_metrics:
            return None
        
        # Evaluate condition
        latest_metric = recent_metrics[0]
        current_value = getattr(latest_metric, metric_field)
        
        if current_value is None:
            return None
        
        alert_triggered = False
        if operator == ">":
            alert_triggered = current_value > threshold
        elif operator == "<":
            alert_triggered = current_value < threshold
        elif operator == ">=":
            alert_triggered = current_value >= threshold
        elif operator == "<=":
            alert_triggered = current_value <= threshold
        elif operator == "==":
            alert_triggered = current_value == threshold
        
        if alert_triggered:
            alert_data = AlertCreate(
                alert_type="process_metric",
                severity=rule.severity,
                source=f"process:{latest_metric.hostname}:{process_name}",
                title=f"{rule.name} - Process Alert",
                description=f"Process {process_name} {metric_field} {current_value} {operator} {threshold} on {latest_metric.hostname}",
                alert_metadata={
                    "rule_id": str(rule.id),
                    "process_name": process_name,
                    "metric_field": metric_field,
                    "current_value": float(current_value),
                    "threshold": float(threshold),
                    "operator": operator,
                    "hostname": latest_metric.hostname,
                    "process_id": latest_metric.process_id
                }
            )
            
            alert = await self.create_alert(alert_data)
            await self._update_rule_last_triggered(rule)
            
            return alert
        
        return None
    
    async def _create_service_alert(self, service_name: str, status: str, 
                                  error_message: Optional[str], response_time_ms: Optional[int]) -> Alert:
        """Create alert for service health issues"""
        severity = "critical" if status == "unhealthy" else "high" if status == "timeout" else "medium"
        
        alert_data = AlertCreate(
            alert_type="service_health",
            severity=severity,
            source=f"service:{service_name}",
            title=f"Service {service_name} Health Alert",
            description=f"Service {service_name} is {status}: {error_message or 'No additional details'}",
            metadata={
                "service_name": service_name,
                "status": status,
                "response_time_ms": response_time_ms,
                "error_message": error_message,
                "auto_generated": True
            }
        )
        
        return await self.create_alert(alert_data)
    
    async def _is_in_cooldown(self, rule: AlertRule) -> bool:
        """Check if alert rule is in cooldown period"""
        if not rule.cooldown_minutes or rule.cooldown_minutes <= 0:
            return False
        
        # Check for recent alerts from this rule
        since_time = datetime.utcnow() - timedelta(minutes=rule.cooldown_minutes)
        recent_alert = self.db.query(Alert).filter(
            Alert.alert_metadata.contains({"rule_id": str(rule.id)}),
            Alert.created_at >= since_time
        ).first()
        
        return recent_alert is not None
    
    async def _update_rule_last_triggered(self, rule: AlertRule) -> None:
        """Update the last triggered timestamp for a rule"""
        # Note: This would require adding a last_triggered_at field to the AlertRule model
        # For now, we'll just log it
        logger.info("Alert rule triggered", rule_name=rule.name, rule_id=str(rule.id))
    
    # CRUD operations for alerts
    async def create_alert(self, alert_data: AlertCreate) -> Alert:
        """Create a new alert"""
        alert = Alert(**alert_data.model_dump())
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        
        # Publish alert to Redis
        alert_dict = AlertResponse.model_validate(alert).model_dump()
        self.redis.publish_alert("alerts", alert_dict)
        
        logger.info("Alert created", 
                   alert_id=str(alert.id), 
                   alert_type=alert.alert_type,
                   severity=alert.severity)
        
        return alert
    
    def get_alerts(self, skip: int = 0, limit: int = 100, 
                   status: Optional[str] = None, severity: Optional[str] = None) -> List[Alert]:
        """Get alerts with optional filtering"""
        query = self.db.query(Alert)
        
        if status:
            query = query.filter(Alert.status == status)
        if severity:
            query = query.filter(Alert.severity == severity)
        
        return query.order_by(desc(Alert.created_at)).offset(skip).limit(limit).all()
    
    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get a specific alert by ID"""
        return self.db.query(Alert).filter(Alert.id == alert_id).first()
    
    def update_alert(self, alert_id: str, alert_update: AlertUpdate) -> Optional[Alert]:
        """Update an alert"""
        alert = self.get_alert(alert_id)
        if not alert:
            return None
        
        update_data = alert_update.model_dump(exclude_unset=True)
        
        # Handle special fields
        if alert_update.status == "acknowledged" and not alert.acknowledged_at:
            update_data["acknowledged_at"] = datetime.utcnow()
        elif alert_update.status == "resolved" and not alert.resolved_at:
            update_data["resolved_at"] = datetime.utcnow()
        
        for field, value in update_data.items():
            setattr(alert, field, value)
        
        self.db.commit()
        self.db.refresh(alert)
        
        logger.info("Alert updated", 
                   alert_id=str(alert.id), 
                   status=alert.status)
        
        return alert
    
    def get_alert_stats(self) -> AlertStats:
        """Get alert statistics"""
        total_alerts = self.db.query(Alert).count()
        active_alerts = self.db.query(Alert).filter(Alert.status == "active").count()
        acknowledged_alerts = self.db.query(Alert).filter(Alert.status == "acknowledged").count()
        resolved_alerts = self.db.query(Alert).filter(Alert.status == "resolved").count()
        
        critical_alerts = self.db.query(Alert).filter(Alert.severity == "critical").count()
        high_alerts = self.db.query(Alert).filter(Alert.severity == "high").count()
        medium_alerts = self.db.query(Alert).filter(Alert.severity == "medium").count()
        low_alerts = self.db.query(Alert).filter(Alert.severity == "low").count()
        info_alerts = self.db.query(Alert).filter(Alert.severity == "info").count()
        
        return AlertStats(
            total_alerts=total_alerts,
            active_alerts=active_alerts,
            acknowledged_alerts=acknowledged_alerts,
            resolved_alerts=resolved_alerts,
            critical_alerts=critical_alerts,
            high_alerts=high_alerts,
            medium_alerts=medium_alerts,
            low_alerts=low_alerts,
            info_alerts=info_alerts
        )
    
    # CRUD operations for alert rules
    def create_alert_rule(self, rule_data: AlertRuleCreate) -> AlertRule:
        """Create a new alert rule"""
        rule = AlertRule(**rule_data.model_dump())
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        
        logger.info("Alert rule created", 
                   rule_id=str(rule.id), 
                   rule_name=rule.name)
        
        return rule
    
    def get_alert_rules(self, skip: int = 0, limit: int = 100, 
                       active_only: bool = False) -> List[AlertRule]:
        """Get alert rules"""
        query = self.db.query(AlertRule)
        
        if active_only:
            query = query.filter(AlertRule.is_active == True)
        
        return query.order_by(AlertRule.name).offset(skip).limit(limit).all()
    
    def get_alert_rule(self, rule_id: str) -> Optional[AlertRule]:
        """Get a specific alert rule by ID"""
        return self.db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    
    def update_alert_rule(self, rule_id: str, rule_update: AlertRuleUpdate) -> Optional[AlertRule]:
        """Update an alert rule"""
        rule = self.get_alert_rule(rule_id)
        if not rule:
            return None
        
        update_data = rule_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(rule, field, value)
        
        self.db.commit()
        self.db.refresh(rule)
        
        logger.info("Alert rule updated", 
                   rule_id=str(rule.id), 
                   rule_name=rule.name)
        
        return rule
    
    def delete_alert_rule(self, rule_id: str) -> bool:
        """Delete an alert rule"""
        rule = self.get_alert_rule(rule_id)
        if not rule:
            return False
        
        self.db.delete(rule)
        self.db.commit()
        
        logger.info("Alert rule deleted", 
                   rule_id=str(rule.id), 
                   rule_name=rule.name)
        
        return True