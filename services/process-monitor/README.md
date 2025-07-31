# Process Monitor Service

The Process Monitor service is a comprehensive system monitoring solution for the Chorus platform. It provides real-time system metrics collection, process monitoring, service health checks, and intelligent alerting capabilities.

## Features

- **System Metrics Collection**: CPU, memory, disk, and network usage monitoring
- **Process Monitoring**: Individual process resource tracking and alerting
- **Service Health Checks**: Monitor health of all Chorus platform services
- **Alert Management**: Rule-based alerting with customizable thresholds
- **Real-time Dashboard**: Redis-cached metrics for instant dashboard updates
- **Background Tasks**: Automated metrics collection and alert checking
- **PostgreSQL Integration**: Persistent storage for metrics and alerts
- **RESTful API**: Comprehensive API for metrics querying and alert management

## Technology Stack

- **Framework**: FastAPI with Python 3.11+
- **Database**: PostgreSQL (monitoring schema)
- **Cache**: Redis for real-time metrics
- **System Monitoring**: psutil for system and process metrics
- **Background Tasks**: asyncio-based task management
- **Logging**: Structured logging with structlog

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL with monitoring schema
- Redis server
- pip or poetry for dependency management

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables:
```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/chorus_monitoring"
export REDIS_URL="redis://localhost:6379/0"
export DEBUG=true
```

3. Run the service:
```bash
python -m app.main
```

The service will start on port 8082 with automatic background tasks for metrics collection and alerting.

## Configuration

The service is configured via environment variables:

### Database & Cache
- `DATABASE_URL`: PostgreSQL connection string (default: postgresql://postgres:password@localhost:5432/chorus_monitoring)
- `REDIS_URL`: Redis connection string (default: redis://localhost:6379/0)

### Monitoring Settings
- `METRICS_COLLECTION_INTERVAL`: Seconds between metric collections (default: 30)
- `HEALTH_CHECK_INTERVAL`: Seconds between service health checks (default: 60)

### Alert Thresholds
- `CPU_ALERT_THRESHOLD`: CPU usage percentage threshold (default: 80.0)
- `MEMORY_ALERT_THRESHOLD`: Memory usage percentage threshold (default: 85.0)
- `DISK_ALERT_THRESHOLD`: Disk usage percentage threshold (default: 90.0)
- `RESPONSE_TIME_ALERT_THRESHOLD`: Service response time threshold in ms (default: 5000)

### Service Endpoints
Configure monitored services via `SERVICE_ENDPOINTS` environment variable or in config.py:

```python
service_endpoints = {
    "websocket-gateway": "http://localhost:8081/health",
    "chat-service": "http://localhost:8000/api/v1/health",
    "presence-service": "http://localhost:8083/health",
    "summary-engine": "http://localhost:8084/api/v1/health",
    "notification-worker": "http://localhost:8085/health",
    "admin-ui": "http://localhost:3000"
}
```

## API Endpoints

### System Monitoring

- `GET /api/v1/system/overview` - Current system overview
- `GET /api/v1/system/health` - Health status of all services
- `GET /api/v1/metrics/system` - Query system metrics
- `GET /api/v1/metrics/processes` - Query process metrics
- `GET /api/v1/metrics/latest/{hostname}` - Latest cached metrics
- `POST /api/v1/metrics/collect` - Trigger manual metrics collection

### Alert Management

- `GET /api/v1/alerts` - List alerts with filtering
- `POST /api/v1/alerts` - Create new alert
- `GET /api/v1/alerts/{alert_id}` - Get specific alert
- `PATCH /api/v1/alerts/{alert_id}` - Update alert (acknowledge/resolve)
- `GET /api/v1/alerts/stats` - Alert statistics
- `POST /api/v1/alerts/check` - Trigger manual alert check

### Alert Rules

- `GET /api/v1/alert-rules` - List alert rules
- `POST /api/v1/alert-rules` - Create new alert rule
- `GET /api/v1/alert-rules/{rule_id}` - Get specific rule
- `PATCH /api/v1/alert-rules/{rule_id}` - Update alert rule
- `DELETE /api/v1/alert-rules/{rule_id}` - Delete alert rule

### Dashboard

- `GET /api/v1/dashboard/overview` - Dashboard overview with key metrics
- `GET /api/v1/dashboard/metrics/summary` - Summarized metrics for charts

## Background Tasks

The service runs several background tasks:

1. **Metrics Collection** (every 30s): Collects system and process metrics
2. **Health Checks** (every 60s): Checks health of configured services
3. **Alert Checking** (every 60s): Evaluates alert rules against metrics
4. **Data Cleanup** (hourly): Removes old metrics and resolved alerts

### Running Background Tasks Standalone

For testing or development:

```bash
# Run single metrics collection
python -m app.background.tasks single

# Run single alert check
python -m app.background.tasks single alerts

# Run continuous background tasks
python -m app.background.tasks
```

## Database Schema

The service uses the `monitoring` schema in PostgreSQL:

### System Metrics (`monitoring.system_metrics`)
- Stores CPU, memory, disk, network metrics
- Indexed by hostname, metric_type, and timestamp
- Automatic cleanup after 30 days

### Process Metrics (`monitoring.process_metrics`)
- Stores per-process resource usage
- Includes CPU, memory, disk I/O metrics
- Automatic cleanup after 7 days

### Alerts (`monitoring.alerts`)
- Stores generated alerts with metadata
- Supports acknowledgment and resolution
- Status tracking and notification integration

### Alert Rules (`monitoring.alert_rules`)
- Configurable rules for automatic alert generation
- Support for system metrics, service health, and process monitoring
- Cooldown periods to prevent alert spam

## Alert Rule Examples

### System CPU Alert
```json
{
  "name": "High CPU Usage",
  "rule_type": "system_metric",
  "condition": {
    "metric_type": "cpu_usage_percent",
    "operator": ">",
    "threshold": 85.0,
    "time_window_minutes": 5
  },
  "severity": "high",
  "cooldown_minutes": 15
}
```

### Service Health Alert
```json
{
  "name": "Chat Service Down",
  "rule_type": "service_health",
  "condition": {
    "service_name": "chat-service",
    "max_response_time_ms": 5000
  },
  "severity": "critical",
  "cooldown_minutes": 5
}
```

### Process Memory Alert
```json
{
  "name": "High Python Memory Usage",
  "rule_type": "process_metric",
  "condition": {
    "process_name": "python",
    "metric_field": "memory_percent",
    "operator": ">",
    "threshold": 80.0
  },
  "severity": "medium",
  "cooldown_minutes": 10
}
```

## Redis Integration

The service uses Redis for:

- **Real-time Metrics Cache**: Latest metrics for dashboard
- **System Health Cache**: Service health status
- **Alert Broadcasting**: Publishes alerts to Redis channels

### Redis Key Patterns

- `latest:{hostname}:{metric_type}` - Latest metric values
- `health:{hostname}` - System health data
- `alerts` channel - Published alert notifications

## Monitoring & Observability

### Structured Logging

All logs are structured JSON with contextual information:

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "event": "Metrics collection completed",
  "hostname": "monitor-01",
  "system_metrics": 25,
  "process_metrics": 156,
  "duration_seconds": 2.34
}
```

### Health Endpoints

- `GET /health` - Basic health check
- `GET /status` - Extended status with system info
- `GET /` - Service information and features

### Performance Metrics

The service tracks its own performance:
- Metrics collection duration
- Alert checking duration  
- Database query performance
- Redis operation latency

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/ ./app/
EXPOSE 8082

CMD ["python", "-m", "app.main"]
```

### Environment Setup

Create a `.env` file:

```env
DEBUG=false
DATABASE_URL=postgresql://chorus:password@postgres:5432/chorus
REDIS_URL=redis://redis:6379/0
METRICS_COLLECTION_INTERVAL=30
HEALTH_CHECK_INTERVAL=60
CPU_ALERT_THRESHOLD=80.0
MEMORY_ALERT_THRESHOLD=85.0
DISK_ALERT_THRESHOLD=90.0
```

### Production Considerations

1. **Database Tuning**: Configure PostgreSQL for time-series workloads
2. **Redis Memory**: Monitor Redis memory usage for metric caching
3. **Log Rotation**: Set up log rotation for structured logs
4. **Monitoring**: Monitor the monitor - track its own resource usage
5. **Backup**: Regular backups of alert rules and historical data

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/
```

### Code Structure

```
app/
├── api/
│   └── endpoints.py          # FastAPI routes
├── background/
│   └── tasks.py             # Background task management
├── db/
│   ├── database.py          # SQLAlchemy setup
│   └── redis.py             # Redis utilities
├── models/
│   ├── database.py          # SQLAlchemy models
│   └── schemas.py           # Pydantic schemas
├── services/
│   ├── metrics_collector.py # System metrics collection
│   └── alert_manager.py     # Alert management
├── utils/
│   └── logging.py           # Structured logging setup
├── config.py                # Configuration settings
└── main.py                  # FastAPI application
```

## Troubleshooting

### Common Issues

1. **Database Connection**: Ensure PostgreSQL monitoring schema exists
2. **Redis Connection**: Verify Redis is accessible and configured
3. **Permission Errors**: Some system metrics require elevated permissions
4. **High Memory Usage**: Adjust metrics retention periods
5. **Alert Spam**: Configure appropriate cooldown periods

### Debug Mode

Enable debug logging:

```bash
export DEBUG=true
python -m app.main
```

### Manual Operations

```bash
# Test database connection
python -c "from app.db.database import engine; print(engine.execute('SELECT 1').scalar())"

# Test Redis connection
python -c "from app.db.redis import redis_client; print(redis_client.ping())"

# Collect metrics once
python -m app.background.tasks single

# Check alerts once
python -m app.background.tasks single alerts
```

## License

This service is part of the Chorus platform and follows the same licensing terms.