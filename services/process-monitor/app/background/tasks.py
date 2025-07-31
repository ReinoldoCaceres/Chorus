import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
import structlog
import signal
import sys

from app.db.database import SessionLocal
from app.services.metrics_collector import MetricsCollector
from app.services.alert_manager import AlertManager
from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class BackgroundTaskManager:
    """Manages background tasks for metrics collection and alert checking"""
    
    def __init__(self):
        self.running = False
        self.tasks: List[asyncio.Task] = []
        self.settings = settings
        
    async def start(self):
        """Start all background tasks"""
        if self.running:
            logger.warning("Background tasks already running")
            return
        
        self.running = True
        logger.info("Starting background tasks")
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Start tasks
        self.tasks = [
            asyncio.create_task(self._metrics_collection_loop()),
            asyncio.create_task(self._health_check_loop()),
            asyncio.create_task(self._alert_check_loop()),
            asyncio.create_task(self._cleanup_loop()),
        ]
        
        try:
            await asyncio.gather(*self.tasks)
        except asyncio.CancelledError:
            logger.info("Background tasks cancelled")
        except Exception as e:
            logger.error("Error in background tasks", error=str(e))
        finally:
            self.running = False
    
    async def stop(self):
        """Stop all background tasks"""
        if not self.running:
            return
        
        logger.info("Stopping background tasks")
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        logger.info("Background tasks stopped")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    async def _metrics_collection_loop(self):
        """Background task for collecting system and process metrics"""
        logger.info("Starting metrics collection loop", 
                   interval_seconds=self.settings.metrics_collection_interval)
        
        while self.running:
            try:
                start_time = datetime.utcnow()
                
                # Create new database session for this task
                db = SessionLocal()
                try:
                    collector = MetricsCollector(db)
                    
                    # Collect system metrics
                    system_metrics = collector.collect_system_metrics()
                    
                    # Collect process metrics (with targeted processes for better performance)
                    target_processes = [
                        "python", "node", "nginx", "postgres", "redis-server", 
                        "docker", "containerd", "uvicorn"
                    ]
                    process_metrics = collector.collect_process_metrics(target_processes)
                    
                    # Update system overview in Redis
                    overview = collector.get_system_overview()
                    
                    end_time = datetime.utcnow()
                    collection_duration = (end_time - start_time).total_seconds()
                    
                    logger.info("Metrics collection completed",
                               system_metrics=len(system_metrics),
                               process_metrics=len(process_metrics),
                               duration_seconds=collection_duration)
                
                finally:
                    db.close()
                
                # Wait for next collection interval
                await asyncio.sleep(self.settings.metrics_collection_interval)
                
            except asyncio.CancelledError:
                logger.info("Metrics collection loop cancelled")
                break
            except Exception as e:
                logger.error("Error in metrics collection loop", error=str(e))
                # Wait a bit before retrying to avoid tight error loops
                await asyncio.sleep(30)
    
    async def _health_check_loop(self):
        """Background task for checking service health"""
        logger.info("Starting health check loop", 
                   interval_seconds=self.settings.health_check_interval)
        
        while self.running:
            try:
                start_time = datetime.utcnow()
                
                # Create new database session for this task
                db = SessionLocal()
                try:
                    alert_manager = AlertManager(db)
                    
                    # Check health of all configured services
                    health_checks = await alert_manager.check_service_health()
                    
                    healthy_count = len([h for h in health_checks if h.status == "healthy"])
                    unhealthy_count = len(health_checks) - healthy_count
                    
                    end_time = datetime.utcnow()
                    check_duration = (end_time - start_time).total_seconds()
                    
                    logger.info("Service health check completed",
                               services_checked=len(health_checks),
                               healthy_services=healthy_count,
                               unhealthy_services=unhealthy_count,
                               duration_seconds=check_duration)
                
                finally:
                    db.close()
                
                # Wait for next health check interval
                await asyncio.sleep(self.settings.health_check_interval)
                
            except asyncio.CancelledError:
                logger.info("Health check loop cancelled")
                break
            except Exception as e:
                logger.error("Error in health check loop", error=str(e))
                # Wait a bit before retrying
                await asyncio.sleep(30)
    
    async def _alert_check_loop(self):
        """Background task for checking alert rules"""
        # Alert checking runs more frequently than metrics collection
        alert_check_interval = 60  # Check every minute
        
        logger.info("Starting alert check loop", 
                   interval_seconds=alert_check_interval)
        
        while self.running:
            try:
                start_time = datetime.utcnow()
                
                # Create new database session for this task
                db = SessionLocal()
                try:
                    alert_manager = AlertManager(db)
                    
                    # Check system alerts against all active rules
                    system_alerts = await alert_manager.check_system_alerts()
                    
                    end_time = datetime.utcnow()
                    check_duration = (end_time - start_time).total_seconds()
                    
                    if system_alerts:
                        logger.info("Alert check completed - alerts generated",
                                   alerts_created=len(system_alerts),
                                   duration_seconds=check_duration)
                    else:
                        logger.debug("Alert check completed - no alerts",
                                    duration_seconds=check_duration)
                
                finally:
                    db.close()
                
                # Wait for next alert check interval
                await asyncio.sleep(alert_check_interval)
                
            except asyncio.CancelledError:
                logger.info("Alert check loop cancelled")
                break
            except Exception as e:
                logger.error("Error in alert check loop", error=str(e))
                # Wait a bit before retrying
                await asyncio.sleep(30)
    
    async def _cleanup_loop(self):
        """Background task for cleaning up old data"""
        # Run cleanup once per hour
        cleanup_interval = 3600
        
        logger.info("Starting cleanup loop", 
                   interval_seconds=cleanup_interval)
        
        while self.running:
            try:
                start_time = datetime.utcnow()
                
                # Create new database session for this task
                db = SessionLocal()
                try:
                    await self._cleanup_old_metrics(db)
                    await self._cleanup_old_alerts(db)
                    
                    end_time = datetime.utcnow()
                    cleanup_duration = (end_time - start_time).total_seconds()
                    
                    logger.info("Cleanup completed",
                               duration_seconds=cleanup_duration)
                
                finally:
                    db.close()
                
                # Wait for next cleanup interval
                await asyncio.sleep(cleanup_interval)
                
            except asyncio.CancelledError:
                logger.info("Cleanup loop cancelled")
                break
            except Exception as e:
                logger.error("Error in cleanup loop", error=str(e))
                # Wait a bit before retrying
                await asyncio.sleep(300)  # 5 minutes
    
    async def _cleanup_old_metrics(self, db: Session):
        """Clean up old metric data"""
        from app.models.database import SystemMetric, ProcessMetric
        
        # Keep metrics for 30 days
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        # Delete old system metrics
        system_deleted = db.query(SystemMetric).filter(
            SystemMetric.created_at < cutoff_date
        ).delete()
        
        # Delete old process metrics (keep less time due to volume)
        process_cutoff = datetime.utcnow() - timedelta(days=7)
        process_deleted = db.query(ProcessMetric).filter(
            ProcessMetric.created_at < process_cutoff
        ).delete()
        
        db.commit()
        
        if system_deleted > 0 or process_deleted > 0:
            logger.info("Old metrics cleaned up",
                       system_metrics_deleted=system_deleted,
                       process_metrics_deleted=process_deleted)
    
    async def _cleanup_old_alerts(self, db: Session):
        """Clean up old resolved alerts"""
        from app.models.database import Alert
        
        # Keep resolved alerts for 90 days
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        
        alerts_deleted = db.query(Alert).filter(
            Alert.status == "resolved",
            Alert.updated_at < cutoff_date
        ).delete()
        
        db.commit()
        
        if alerts_deleted > 0:
            logger.info("Old alerts cleaned up",
                       alerts_deleted=alerts_deleted)


# Standalone task runner for development/testing
async def run_single_metrics_collection():
    """Run a single metrics collection cycle"""
    logger.info("Running single metrics collection")
    
    db = SessionLocal()
    try:
        collector = MetricsCollector(db)
        
        # Collect all metrics
        system_metrics = collector.collect_system_metrics()
        process_metrics = collector.collect_process_metrics()
        overview = collector.get_system_overview()
        
        logger.info("Single metrics collection completed",
                   system_metrics=len(system_metrics),
                   process_metrics=len(process_metrics))
        
        return {
            "system_metrics": len(system_metrics),
            "process_metrics": len(process_metrics),
            "overview": overview
        }
    
    finally:
        db.close()


async def run_single_alert_check():
    """Run a single alert check cycle"""
    logger.info("Running single alert check")
    
    db = SessionLocal()
    try:
        alert_manager = AlertManager(db)
        
        # Check all alerts
        system_alerts = await alert_manager.check_system_alerts()
        health_checks = await alert_manager.check_service_health()
        
        logger.info("Single alert check completed",
                   system_alerts=len(system_alerts),
                   health_checks=len(health_checks))
        
        return {
            "system_alerts": len(system_alerts),
            "health_checks": len(health_checks),
            "alerts": system_alerts
        }
    
    finally:
        db.close()


# Main entry point for background task manager
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "single":
        # Run single collection for testing
        if len(sys.argv) > 2 and sys.argv[2] == "alerts":
            result = asyncio.run(run_single_alert_check())
        else:
            result = asyncio.run(run_single_metrics_collection())
        print(f"Result: {result}")
    else:
        # Run continuous background tasks
        task_manager = BackgroundTaskManager()
        try:
            asyncio.run(task_manager.start())
        except KeyboardInterrupt:
            logger.info("Received interrupt, shutting down...")
        except Exception as e:
            logger.error("Fatal error in background tasks", error=str(e))
            sys.exit(1)