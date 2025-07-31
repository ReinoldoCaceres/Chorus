# Notification Service

A comprehensive notification service for the Chorus live-chat platform built with FastAPI and Celery. Supports multi-channel notifications including email, SMS, webhooks, Slack, and Microsoft Teams.

## Features

- **Multi-channel delivery**: Email (SendGrid), SMS (Twilio), webhooks, Slack, and Microsoft Teams
- **Template management**: Jinja2-based templates with variable substitution
- **Subscription management**: User-based notification preferences and subscriptions
- **Async processing**: Celery workers for reliable message delivery
- **Retry logic**: Configurable retry mechanisms with exponential backoff
- **Delivery tracking**: Complete audit trail of notification attempts
- **Batch operations**: Support for bulk notification sending
- **Template caching**: Optimized template rendering with TTL-based caching

## Technology Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Message Queue**: Redis with Celery
- **Template Engine**: Jinja2
- **Email Provider**: SendGrid
- **SMS Provider**: Twilio
- **Logging**: Structured logging with structlog

## Project Structure

```
notification-service/
├── app/
│   ├── api/
│   │   └── endpoints.py          # FastAPI route definitions
│   ├── db/
│   │   └── database.py           # Database connection and session management
│   ├── models/
│   │   ├── database.py           # SQLAlchemy database models
│   │   └── schemas.py            # Pydantic schemas for API validation
│   ├── services/
│   │   ├── template_service.py   # Template management and rendering
│   │   ├── delivery_service.py   # Multi-channel message delivery
│   │   └── subscription_service.py # Subscription management
│   ├── utils/
│   │   └── logging.py            # Structured logging configuration
│   ├── workers/
│   │   └── notification_worker.py # Celery tasks for async processing
│   ├── templates/                # Notification templates
│   │   ├── email_welcome.html
│   │   ├── email_chat_notification.html
│   │   ├── sms_chat_notification.txt
│   │   ├── slack_chat_notification.json
│   │   └── webhook_notification.json
│   ├── config.py                 # Application configuration
│   └── main.py                   # FastAPI application entry point
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Container configuration
├── worker.py                     # Celery worker entry point
├── celery_beat.py               # Celery scheduler entry point
└── README.md                    # This file
```

## Database Schema

The service uses the `notification` schema with the following tables:

- **templates**: Notification templates with Jinja2 content
- **notifications**: Individual notification records with delivery status
- **subscriptions**: User subscription preferences by channel and event type

## API Endpoints

### Templates
- `POST /api/v1/templates` - Create a new template
- `GET /api/v1/templates` - List templates with filtering
- `GET /api/v1/templates/{id}` - Get specific template
- `PUT /api/v1/templates/{id}` - Update template
- `DELETE /api/v1/templates/{id}` - Delete (deactivate) template
- `POST /api/v1/templates/{id}/render` - Render template with variables

### Notifications
- `POST /api/v1/notifications` - Send a notification
- `POST /api/v1/notifications/from-template` - Send from template
- `GET /api/v1/notifications` - List notifications with filtering
- `GET /api/v1/notifications/{id}` - Get specific notification
- `PUT /api/v1/notifications/{id}` - Update notification
- `POST /api/v1/notifications/{id}/retry` - Retry failed notification
- `POST /api/v1/notifications/batch` - Send multiple notifications

### Subscriptions
- `POST /api/v1/subscriptions` - Create subscription
- `GET /api/v1/subscriptions` - List subscriptions with filtering
- `GET /api/v1/subscriptions/{id}` - Get specific subscription
- `PUT /api/v1/subscriptions/{id}` - Update subscription
- `DELETE /api/v1/subscriptions/{id}` - Delete subscription

### System
- `GET /health` - Health check endpoint
- `GET /api/v1/stats` - Notification statistics

## Configuration

Environment variables:

```bash
# Application
DEBUG=false
API_V1_STR=/api/v1

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/chorus_notifications

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Security
SECRET_KEY=your-secret-key-here
CORS_ORIGINS=["http://localhost:3000"]

# SendGrid (Email)
SENDGRID_API_KEY=your-sendgrid-api-key
SENDGRID_FROM_EMAIL=noreply@chorus.example.com

# Twilio (SMS)
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_FROM_NUMBER=+1234567890

# Notification Settings
MAX_RETRY_ATTEMPTS=3
RETRY_DELAY_SECONDS=60
NOTIFICATION_BATCH_SIZE=100
TEMPLATE_CACHE_TTL=3600
```

## Quick Start

### Using Docker

1. **Build the image**:
   ```bash
   docker build -t chorus-notification-service .
   ```

2. **Run the service**:
   ```bash
   docker run -p 8085:8085 \
     -e DATABASE_URL=postgresql://user:pass@host:5432/db \
     -e REDIS_URL=redis://redis:6379/0 \
     -e SENDGRID_API_KEY=your-key \
     chorus-notification-service
   ```

3. **Run Celery worker**:
   ```bash
   docker run -d \
     -e DATABASE_URL=postgresql://user:pass@host:5432/db \
     -e REDIS_URL=redis://redis:6379/0 \
     chorus-notification-service \
     python worker.py
   ```

4. **Run Celery beat scheduler**:
   ```bash
   docker run -d \
     -e DATABASE_URL=postgresql://user:pass@host:5432/db \
     -e REDIS_URL=redis://redis:6379/0 \
     chorus-notification-service \
     python celery_beat.py
   ```

### Local Development

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables**:
   ```bash
   export DATABASE_URL=postgresql://user:pass@localhost:5432/chorus_notifications
   export REDIS_URL=redis://localhost:6379/0
   # ... other environment variables
   ```

3. **Run the API server**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8085 --reload
   ```

4. **Run Celery worker** (in another terminal):
   ```bash
   python worker.py
   ```

5. **Run Celery beat scheduler** (in another terminal):
   ```bash
   python celery_beat.py
   ```

## Usage Examples

### Create a Template

```python
import httpx

template_data = {
    "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "welcome_email",
    "channel": "email",
    "subject": "Welcome to {{ organization_name }}!",
    "body_template": "<h1>Welcome {{ user_name }}!</h1><p>Thanks for joining {{ organization_name }}.</p>",
    "variables": {
        "user_name": "string",
        "organization_name": "string"
    }
}

response = httpx.post("http://localhost:8085/api/v1/templates", json=template_data)
template = response.json()
```

### Send Notification from Template

```python
notification_data = {
    "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
    "template_id": template["id"],
    "recipient": "user@example.com",
    "variables": {
        "user_name": "John Doe",
        "organization_name": "Acme Corp"
    }
}

response = httpx.post("http://localhost:8085/api/v1/notifications/from-template", json=notification_data)
notification = response.json()
```

### Create Subscription

```python
subscription_data = {
    "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
    "user_id": "456e7890-e89b-12d3-a456-426614174000",
    "event_type": "chat_message",
    "channel": "email",
    "endpoint": "agent@example.com",
    "preferences": {
        "immediate": True,
        "digest": False
    }
}

response = httpx.post("http://localhost:8085/api/v1/subscriptions", json=subscription_data)
subscription = response.json()
```

## Monitoring and Operations

### Health Checks

```bash
curl http://localhost:8085/health
```

### Metrics and Statistics

```bash
curl "http://localhost:8085/api/v1/stats?tenant_id=123e4567-e89b-12d3-a456-426614174000"
```

### Celery Monitoring

Monitor Celery workers and tasks:

```bash
# Monitor workers
celery -A app.workers.notification_worker inspect active

# Monitor queues
celery -A app.workers.notification_worker inspect reserved

# Flower (web-based monitoring)
pip install flower
celery -A app.workers.notification_worker flower
```

## Channel-Specific Configuration

### Email (SendGrid)
- Requires `SENDGRID_API_KEY` and `SENDGRID_FROM_EMAIL`
- Supports HTML templates with full styling
- Automatic bounce and spam filtering

### SMS (Twilio)
- Requires `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_FROM_NUMBER`
- Message length automatically managed
- Delivery status tracking

### Webhooks
- POST requests to specified URLs
- JSON payload with notification data
- Configurable timeout and retry logic

### Slack
- Uses incoming webhooks or bot tokens
- Rich message formatting support
- Interactive buttons and attachments

### Microsoft Teams
- Webhook-based messaging
- Card-based message format
- Action buttons support

## Security Considerations

- All endpoints require proper authentication (JWT tokens recommended)
- Sensitive data (phone numbers, emails) is masked in logs
- Template variables are sandboxed to prevent code injection
- Rate limiting should be implemented at the API gateway level
- Database connections use connection pooling with SSL

## Performance

- Async processing via Celery prevents API blocking
- Template caching reduces rendering overhead
- Database queries are optimized with proper indexing
- Connection pooling for database and Redis
- Batch operations for high-volume scenarios

## Troubleshooting

### Common Issues

1. **Templates not rendering**: Check Jinja2 syntax and variable names
2. **Notifications stuck in pending**: Verify Celery workers are running
3. **Email delivery failures**: Validate SendGrid API key and from email
4. **SMS delivery failures**: Check Twilio credentials and phone number format
5. **Database connection errors**: Verify PostgreSQL connection string

### Log Analysis

The service uses structured logging. Key log events:
- `notification_events`: Notification lifecycle events
- `template_events`: Template operations
- `subscription_events`: Subscription changes
- `delivery_metrics`: Channel-specific delivery metrics
- `performance_metrics`: Operation timing and performance

### Debugging

Enable debug mode for detailed logging:

```bash
export DEBUG=true
```

Monitor Celery task execution:

```bash
celery -A app.workers.notification_worker events
```

## Contributing

1. Follow the existing code structure and patterns
2. Add tests for new features
3. Update documentation for API changes
4. Use structured logging for all operations
5. Ensure proper error handling and validation

## License

This service is part of the Chorus platform and follows the project's licensing terms.