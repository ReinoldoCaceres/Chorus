from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from app.db.database import get_db
from app.models.schemas import (
    HealthResponse, SystemOverview, ServiceHealthCheck,
    SystemMetricResponse, ProcessMetricResponse, MetricsQuery,
    AlertResponse, AlertCreate, AlertUpdate, AlertStats,
    AlertRuleResponse, AlertRuleCreate, AlertRuleUpdate
)
from app.services.metrics_collector import MetricsCollector
from app.services.alert_manager import AlertManager
from app.db.redis import RedisCache
import structlog

logger = structlog.get_logger()

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse()


# System Monitoring Endpoints
@router.get("/system/overview", response_model=SystemOverview)
async def get_system_overview(db: Session = Depends(get_db)):
    """Get current system overview"""
    collector = MetricsCollector(db)
    return collector.get_system_overview()


@router.get("/system/health", response_model=List[ServiceHealthCheck])
async def get_service_health(db: Session = Depends(get_db)):
    """Get health status of all services"""
    alert_manager = AlertManager(db)
    return await alert_manager.check_service_health()


@router.post("/metrics/collect")
async def trigger_metrics_collection(
    background_tasks: BackgroundTasks,
    collect_processes: bool = Query(default=True, description="Also collect process metrics"),
    db: Session = Depends(get_db)
):
    """Manually trigger metrics collection"""
    def collect_metrics():
        collector = MetricsCollector(db)
        system_metrics = collector.collect_system_metrics()
        
        process_metrics = []
        if collect_processes:
            process_metrics = collector.collect_process_metrics()
        
        logger.info("Manual metrics collection completed",
                   system_metrics_count=len(system_metrics),
                   process_metrics_count=len(process_metrics))
    
    background_tasks.add_task(collect_metrics)
    return {"message": "Metrics collection started", "timestamp": datetime.utcnow()}


# Metrics Query Endpoints
@router.get("/metrics/system", response_model=List[SystemMetricResponse])
async def get_system_metrics(
    query: MetricsQuery = Depends(),
    db: Session = Depends(get_db)
):
    """Get system metrics with optional filtering"""
    from app.models.database import SystemMetric
    from sqlalchemy import desc, and_
    
    query_filters = []
    
    if query.metric_type:
        query_filters.append(SystemMetric.metric_type == query.metric_type)
    
    if query.hostname:
        query_filters.append(SystemMetric.hostname == query.hostname)
    
    if query.start_time:
        query_filters.append(SystemMetric.timestamp >= query.start_time)
    
    if query.end_time:
        query_filters.append(SystemMetric.timestamp <= query.end_time)
    
    db_query = db.query(SystemMetric)
    if query_filters:
        db_query = db_query.filter(and_(*query_filters))
    
    metrics = db_query.order_by(desc(SystemMetric.timestamp)).offset(query.offset).limit(query.limit).all()
    
    return metrics


@router.get("/metrics/processes", response_model=List[ProcessMetricResponse])
async def get_process_metrics(
    query: MetricsQuery = Depends(),
    process_name: Optional[str] = Query(None, description="Filter by process name"),
    db: Session = Depends(get_db)
):
    """Get process metrics with optional filtering"""
    from app.models.database import ProcessMetric
    from sqlalchemy import desc, and_
    
    query_filters = []
    
    if process_name:
        query_filters.append(ProcessMetric.process_name == process_name)
    
    if query.hostname:
        query_filters.append(ProcessMetric.hostname == query.hostname)
    
    if query.start_time:
        query_filters.append(ProcessMetric.timestamp >= query.start_time)
    
    if query.end_time:
        query_filters.append(ProcessMetric.timestamp <= query.end_time)
    
    db_query = db.query(ProcessMetric)
    if query_filters:
        db_query = db_query.filter(and_(*query_filters))
    
    metrics = db_query.order_by(desc(ProcessMetric.timestamp)).offset(query.offset).limit(query.limit).all()
    
    return metrics


@router.get("/metrics/latest/{hostname}")
async def get_latest_metrics(hostname: str):
    """Get latest cached metrics for a hostname from Redis"""
    redis = RedisCache()
    
    # Get all latest metrics for the hostname
    import redis as redis_lib  # Import redis library for pattern matching
    redis_client = redis_lib.from_url("redis://localhost:6379/0", decode_responses=True)
    
    pattern = f"latest:{hostname}:*"
    keys = redis_client.keys(pattern)
    
    latest_metrics = {}
    for key in keys:
        metric_type = key.replace(f"latest:{hostname}:", "")
        metric_data = redis.get_metric(key)
        if metric_data:
            latest_metrics[metric_type] = metric_data
    
    return {
        "hostname": hostname,
        "metrics": latest_metrics,
        "timestamp": datetime.utcnow()
    }


# Alert Endpoints
@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None, description="Filter by alert status"),
    severity: Optional[str] = Query(None, description="Filter by alert severity"),
    db: Session = Depends(get_db)
):
    """Get alerts with optional filtering"""
    alert_manager = AlertManager(db)
    alerts = alert_manager.get_alerts(skip=skip, limit=limit, status=status, severity=severity)
    return alerts


@router.post("/alerts", response_model=AlertResponse)
async def create_alert(
    alert_data: AlertCreate,
    db: Session = Depends(get_db)
):
    """Create a new alert"""
    alert_manager = AlertManager(db)
    alert = await alert_manager.create_alert(alert_data)
    return alert


@router.get("/alerts/stats", response_model=AlertStats)
async def get_alert_stats(db: Session = Depends(get_db)):
    """Get alert statistics"""
    alert_manager = AlertManager(db)
    return alert_manager.get_alert_stats()


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: UUID, db: Session = Depends(get_db)):
    """Get a specific alert"""
    alert_manager = AlertManager(db)
    alert = alert_manager.get_alert(str(alert_id))
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.patch("/alerts/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: UUID,
    alert_update: AlertUpdate,
    db: Session = Depends(get_db)
):
    """Update an alert (acknowledge, resolve, etc.)"""
    alert_manager = AlertManager(db)
    alert = alert_manager.update_alert(str(alert_id), alert_update)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.post("/alerts/check")
async def trigger_alert_check(
    background_tasks: BackgroundTasks,
    hostname: Optional[str] = Query(None, description="Check alerts for specific hostname"),
    db: Session = Depends(get_db)
):
    """Manually trigger alert checking"""
    async def check_alerts():
        alert_manager = AlertManager(db)
        
        # Check system alerts
        system_alerts = await alert_manager.check_system_alerts(hostname)
        
        # Check service health
        health_checks = await alert_manager.check_service_health()
        
        logger.info("Manual alert check completed",
                   system_alerts_created=len(system_alerts),
                   services_checked=len(health_checks))
    
    background_tasks.add_task(check_alerts)
    return {"message": "Alert check started", "timestamp": datetime.utcnow()}


# Alert Rule Endpoints
@router.get("/alert-rules", response_model=List[AlertRuleResponse])
async def get_alert_rules(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(False, description="Only return active rules"),
    db: Session = Depends(get_db)
):
    """Get alert rules"""
    alert_manager = AlertManager(db)
    rules = alert_manager.get_alert_rules(skip=skip, limit=limit, active_only=active_only)
    return rules


@router.post("/alert-rules", response_model=AlertRuleResponse)
async def create_alert_rule(
    rule_data: AlertRuleCreate,
    db: Session = Depends(get_db)
):
    """Create a new alert rule"""
    alert_manager = AlertManager(db)
    rule = alert_manager.create_alert_rule(rule_data)
    return rule


@router.get("/alert-rules/{rule_id}", response_model=AlertRuleResponse)
async def get_alert_rule(rule_id: UUID, db: Session = Depends(get_db)):
    """Get a specific alert rule"""
    alert_manager = AlertManager(db)
    rule = alert_manager.get_alert_rule(str(rule_id))
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return rule


@router.patch("/alert-rules/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(
    rule_id: UUID,
    rule_update: AlertRuleUpdate,
    db: Session = Depends(get_db)
):
    """Update an alert rule"""
    alert_manager = AlertManager(db)
    rule = alert_manager.update_alert_rule(str(rule_id), rule_update)
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return rule


@router.delete("/alert-rules/{rule_id}")
async def delete_alert_rule(rule_id: UUID, db: Session = Depends(get_db)):
    """Delete an alert rule"""
    alert_manager = AlertManager(db)
    success = alert_manager.delete_alert_rule(str(rule_id))
    if not success:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return {"message": "Alert rule deleted successfully"}


# Dashboard/Aggregation Endpoints
@router.get("/dashboard/overview")
async def get_dashboard_overview(db: Session = Depends(get_db)):
    """Get dashboard overview with key metrics and alerts"""
    redis = RedisCache()
    alert_manager = AlertManager(db)
    
    # Get all system health data
    all_health = redis.get_all_system_health()
    
    # Get alert stats
    alert_stats = alert_manager.get_alert_stats()
    
    # Get recent service health checks
    recent_health_checks = await alert_manager.check_service_health()
    
    return {
        "timestamp": datetime.utcnow(),
        "system_health": all_health,
        "alert_stats": alert_stats,
        "service_health": recent_health_checks,
        "healthy_services": len([h for h in recent_health_checks if h.status == "healthy"]),
        "total_services": len(recent_health_checks)
    }


@router.get("/dashboard/metrics/summary")
async def get_metrics_summary(
    hostname: Optional[str] = Query(None, description="Filter by hostname"),
    hours: int = Query(24, ge=1, le=168, description="Hours of data to summarize"),
    db: Session = Depends(get_db)
):
    """Get summarized metrics for dashboard display"""
    from app.models.database import SystemMetric
    from sqlalchemy import func, desc
    
    since_time = datetime.utcnow() - timedelta(hours=hours)
    
    query = db.query(
        SystemMetric.hostname,
        SystemMetric.metric_type,
        func.avg(SystemMetric.metric_value).label('avg_value'),
        func.max(SystemMetric.metric_value).label('max_value'),
        func.min(SystemMetric.metric_value).label('min_value'),
        func.count(SystemMetric.id).label('sample_count')
    ).filter(SystemMetric.timestamp >= since_time)
    
    if hostname:
        query = query.filter(SystemMetric.hostname == hostname)
    
    metrics_summary = query.group_by(
        SystemMetric.hostname, 
        SystemMetric.metric_type
    ).all()
    
    # Organize by hostname
    summary_by_host = {}
    for metric in metrics_summary:
        hostname_key = metric.hostname
        if hostname_key not in summary_by_host:
            summary_by_host[hostname_key] = {}
        
        summary_by_host[hostname_key][metric.metric_type] = {
            "avg_value": float(metric.avg_value),
            "max_value": float(metric.max_value),
            "min_value": float(metric.min_value),
            "sample_count": metric.sample_count
        }
    
    return {
        "time_range_hours": hours,
        "summary": summary_by_host,
        "generated_at": datetime.utcnow()
    }