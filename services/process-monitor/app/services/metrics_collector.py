import psutil
import socket
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
import structlog

from app.models.database import SystemMetric, ProcessMetric
from app.models.schemas import SystemMetricCreate, ProcessMetricCreate, SystemOverview
from app.db.redis import RedisCache
from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class MetricsCollector:
    """System metrics collection service using psutil"""
    
    def __init__(self, db: Session):
        self.db = db
        self.hostname = socket.gethostname()
        self.redis = RedisCache()
        
    def collect_system_metrics(self) -> List[SystemMetric]:
        """Collect comprehensive system metrics"""
        metrics = []
        timestamp = datetime.utcnow()
        
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            metrics.extend([
                self._create_system_metric("cpu_usage_percent", cpu_percent, "percent", timestamp),
                self._create_system_metric("cpu_count", cpu_count, "count", timestamp),
            ])
            
            if cpu_freq:
                metrics.append(
                    self._create_system_metric("cpu_frequency_mhz", cpu_freq.current, "mhz", timestamp)
                )
            
            # Memory metrics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            metrics.extend([
                self._create_system_metric("memory_total_mb", memory.total / (1024**2), "mb", timestamp),
                self._create_system_metric("memory_available_mb", memory.available / (1024**2), "mb", timestamp),
                self._create_system_metric("memory_used_mb", memory.used / (1024**2), "mb", timestamp),
                self._create_system_metric("memory_usage_percent", memory.percent, "percent", timestamp),
                self._create_system_metric("swap_total_mb", swap.total / (1024**2), "mb", timestamp),
                self._create_system_metric("swap_used_mb", swap.used / (1024**2), "mb", timestamp),
                self._create_system_metric("swap_usage_percent", swap.percent, "percent", timestamp),
            ])
            
            # Disk metrics
            disk_usage = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            
            metrics.extend([
                self._create_system_metric("disk_total_gb", disk_usage.total / (1024**3), "gb", timestamp),
                self._create_system_metric("disk_used_gb", disk_usage.used / (1024**3), "gb", timestamp),
                self._create_system_metric("disk_free_gb", disk_usage.free / (1024**3), "gb", timestamp),
                self._create_system_metric("disk_usage_percent", 
                    (disk_usage.used / disk_usage.total) * 100, "percent", timestamp),
            ])
            
            if disk_io:
                metrics.extend([
                    self._create_system_metric("disk_read_bytes", disk_io.read_bytes, "bytes", timestamp),
                    self._create_system_metric("disk_write_bytes", disk_io.write_bytes, "bytes", timestamp),
                    self._create_system_metric("disk_read_count", disk_io.read_count, "count", timestamp),
                    self._create_system_metric("disk_write_count", disk_io.write_count, "count", timestamp),
                ])
            
            # Network metrics
            network_io = psutil.net_io_counters()
            if network_io:
                metrics.extend([
                    self._create_system_metric("network_bytes_sent", network_io.bytes_sent, "bytes", timestamp),
                    self._create_system_metric("network_bytes_recv", network_io.bytes_recv, "bytes", timestamp),
                    self._create_system_metric("network_packets_sent", network_io.packets_sent, "count", timestamp),
                    self._create_system_metric("network_packets_recv", network_io.packets_recv, "count", timestamp),
                ])
            
            # System uptime
            boot_time = psutil.boot_time()
            uptime_seconds = time.time() - boot_time
            metrics.append(
                self._create_system_metric("uptime_seconds", uptime_seconds, "seconds", timestamp)
            )
            
            # Load average (Unix systems only)
            try:
                load_avg = psutil.getloadavg()
                metrics.extend([
                    self._create_system_metric("load_avg_1min", load_avg[0], "avg", timestamp),
                    self._create_system_metric("load_avg_5min", load_avg[1], "avg", timestamp),
                    self._create_system_metric("load_avg_15min", load_avg[2], "avg", timestamp),
                ])
            except AttributeError:
                # getloadavg not available on Windows
                pass
            
            # Store metrics in database
            for metric in metrics:
                self.db.add(metric)
            self.db.commit()
            
            # Cache latest metrics in Redis
            self._cache_latest_metrics(metrics)
            
            logger.info("Collected system metrics", 
                       hostname=self.hostname, 
                       metric_count=len(metrics))
            
            return metrics
            
        except Exception as e:
            logger.error("Failed to collect system metrics", 
                        hostname=self.hostname, 
                        error=str(e))
            self.db.rollback()
            return []
    
    def collect_process_metrics(self, target_processes: Optional[List[str]] = None) -> List[ProcessMetric]:
        """Collect metrics for specific processes or all processes"""
        metrics = []
        timestamp = datetime.utcnow()
        
        try:
            # Get all running processes
            for proc in psutil.process_iter(['pid', 'name', 'status']):
                try:
                    proc_info = proc.info
                    process_name = proc_info['name']
                    
                    # Filter by target processes if specified
                    if target_processes and process_name not in target_processes:
                        continue
                    
                    # Get detailed process metrics
                    with proc.oneshot():
                        cpu_percent = proc.cpu_percent()
                        memory_info = proc.memory_info()
                        memory_percent = proc.memory_percent()
                        
                        # IO counters (may not be available on all systems)
                        try:
                            io_counters = proc.io_counters()
                            disk_read_bytes = io_counters.read_bytes
                            disk_write_bytes = io_counters.write_bytes
                        except (psutil.AccessDenied, AttributeError):
                            disk_read_bytes = None
                            disk_write_bytes = None
                        
                        # Network IO (not directly available per process)
                        network_sent_bytes = None
                        network_recv_bytes = None
                        
                        metric = ProcessMetric(
                            process_id=proc_info['pid'],
                            process_name=process_name,
                            hostname=self.hostname,
                            cpu_percent=Decimal(str(cpu_percent)),
                            memory_mb=Decimal(str(memory_info.rss / (1024**2))),
                            memory_percent=Decimal(str(memory_percent)),
                            disk_read_bytes=disk_read_bytes,
                            disk_write_bytes=disk_write_bytes,
                            network_sent_bytes=network_sent_bytes,
                            network_recv_bytes=network_recv_bytes,
                            status=proc_info['status'],
                            timestamp=timestamp
                        )
                        
                        metrics.append(metric)
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    # Process disappeared or access denied
                    continue
            
            # Store metrics in database
            for metric in metrics:
                self.db.add(metric)
            self.db.commit()
            
            logger.info("Collected process metrics", 
                       hostname=self.hostname, 
                       process_count=len(metrics))
            
            return metrics
            
        except Exception as e:
            logger.error("Failed to collect process metrics", 
                        hostname=self.hostname, 
                        error=str(e))
            self.db.rollback()
            return []
    
    def get_system_overview(self) -> SystemOverview:
        """Get current system overview"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network_io = psutil.net_io_counters()
            boot_time = psutil.boot_time()
            uptime_seconds = int(time.time() - boot_time)
            
            # Count processes
            process_count = len(psutil.pids())
            
            network_data = None
            if network_io:
                network_data = {
                    "bytes_sent": network_io.bytes_sent,
                    "bytes_recv": network_io.bytes_recv
                }
            
            overview = SystemOverview(
                hostname=self.hostname,
                cpu_usage=Decimal(str(cpu_percent)),
                memory_usage=Decimal(str(memory.percent)),
                disk_usage=Decimal(str((disk.used / disk.total) * 100)),
                network_io=network_data,
                process_count=process_count,
                uptime_seconds=uptime_seconds,
                last_updated=datetime.utcnow()
            )
            
            # Cache overview in Redis
            self.redis.set_system_health(self.hostname, overview.model_dump_json())
            
            return overview
            
        except Exception as e:
            logger.error("Failed to get system overview", 
                        hostname=self.hostname, 
                        error=str(e))
            # Return empty overview
            return SystemOverview(
                hostname=self.hostname,
                process_count=0,
                last_updated=datetime.utcnow()
            )
    
    def _create_system_metric(self, metric_type: str, value: float, unit: str, 
                            timestamp: datetime, tags: Dict[str, Any] = None) -> SystemMetric:
        """Create a SystemMetric instance"""
        return SystemMetric(
            hostname=self.hostname,
            metric_type=metric_type,
            metric_value=Decimal(str(value)),
            metric_unit=unit,
            tags=tags or {},
            timestamp=timestamp
        )
    
    def _cache_latest_metrics(self, metrics: List[SystemMetric]) -> None:
        """Cache latest metrics in Redis for quick access"""
        try:
            latest_metrics = {}
            for metric in metrics:
                key = f"{metric.hostname}:{metric.metric_type}"
                latest_metrics[key] = {
                    "value": float(metric.metric_value),
                    "unit": metric.metric_unit,
                    "timestamp": metric.timestamp.isoformat(),
                    "tags": metric.tags
                }
            
            # Store in Redis with 10 minute expiration
            for key, data in latest_metrics.items():
                self.redis.set_metric(f"latest:{key}", data, expire=600)
                
        except Exception as e:
            logger.warning("Failed to cache metrics in Redis", error=str(e))