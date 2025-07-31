# Workflow Engine Service

The Workflow Engine service is responsible for managing and executing workflows within the Chorus platform. It provides a flexible, scalable engine for automating business processes and complex multi-step operations.

## Features

- **Workflow Template Management**: Create, update, and manage reusable workflow templates
- **Workflow Instance Execution**: Execute workflow instances with state management
- **Multiple Step Types**: Support for action, condition, parallel, wait, and subflow steps
- **Real-time Monitoring**: Track workflow execution in real-time
- **Event-driven Architecture**: Redis pub/sub for real-time events
- **Retry Mechanisms**: Automatic retry on step failures with configurable policies
- **Webhook Triggers**: Support for webhook-triggered workflows
- **REST API**: Comprehensive API for workflow management

## Architecture

The service consists of several key components:

- **Engine**: Core workflow execution engine with concurrent processing
- **Executor**: Step execution logic for different step types
- **Handlers**: HTTP API handlers for REST endpoints
- **Models**: Database models and DTOs
- **Middleware**: Authentication and logging middleware

## Configuration

The service is configured via environment variables:

```bash
# Server Configuration
PORT=8081
ENVIRONMENT=development

# Database Configuration
DATABASE_URL=postgres://chorus:password@localhost:5432/chorus?sslmode=disable

# Redis Configuration  
REDIS_URL=redis://localhost:6379

# JWT Configuration
JWT_SECRET=your-secret-key

# Workflow Engine Configuration
MAX_CONCURRENT_WORKFLOWS=100
WORKFLOW_CHECK_INTERVAL=10
STEP_RETRY_LIMIT=3
STEP_TIMEOUT=300
```

## API Endpoints

### Workflow Templates

- `GET /api/v1/templates` - List workflow templates
- `POST /api/v1/templates` - Create workflow template
- `GET /api/v1/templates/:id` - Get workflow template
- `PUT /api/v1/templates/:id` - Update workflow template
- `DELETE /api/v1/templates/:id` - Delete workflow template

### Workflow Instances

- `GET /api/v1/instances` - List workflow instances
- `POST /api/v1/instances` - Create workflow instance
- `GET /api/v1/instances/:id` - Get workflow instance
- `PUT /api/v1/instances/:id/start` - Start workflow instance
- `PUT /api/v1/instances/:id/pause` - Pause workflow instance
- `PUT /api/v1/instances/:id/resume` - Resume workflow instance
- `PUT /api/v1/instances/:id/cancel` - Cancel workflow instance
- `GET /api/v1/instances/:id/steps` - Get workflow instance steps

### Triggers

- `POST /api/v1/triggers/webhook/:template_id` - Trigger workflow via webhook

### Health Check

- `GET /health` - Service health check

## Step Types

### Action Steps

Execute specific actions like HTTP requests, sending emails, or updating variables.

```json
{
  "id": "send_email",
  "name": "Send Welcome Email",
  "type": "action",
  "config": {
    "action": "send_email",
    "to": "user@example.com",
    "subject": "Welcome!",
    "body": "Welcome to our platform!"
  }
}
```

### Condition Steps

Evaluate conditions to control workflow flow.

```json
{
  "id": "check_status",
  "name": "Check User Status",
  "type": "condition",
  "config": {
    "field": "user_status",
    "operator": "equals",
    "value": "active"
  },
  "next_steps": ["active_user_flow", "inactive_user_flow"]
}
```

### Parallel Steps

Execute multiple steps in parallel.

```json
{
  "id": "parallel_processing",
  "name": "Process Multiple Tasks",
  "type": "parallel",
  "config": {
    "parallel_steps": [
      {"action": "process_data_1"},
      {"action": "process_data_2"},
      {"action": "process_data_3"}
    ]
  }
}
```

### Wait Steps

Wait for a specific duration or event.

```json
{
  "id": "wait_for_approval",
  "name": "Wait for Approval",
  "type": "wait",
  "config": {
    "wait_type": "event",
    "event": "approval_received"
  }
}
```

### Subflow Steps

Execute another workflow as a subprocess.

```json
{
  "id": "execute_subflow",
  "name": "Execute Data Processing Workflow",
  "type": "subflow",
  "config": {
    "subflow_id": "data_processing_template_id"
  }
}
```

## Workflow Schema Example

```json
{
  "steps": [
    {
      "id": "validate_input",
      "name": "Validate Input Data",
      "type": "condition",
      "conditions": [
        {
          "field": "email",
          "operator": "contains",
          "value": "@"
        }
      ],
      "next_steps": ["send_welcome", "send_error"]
    },
    {
      "id": "send_welcome",
      "name": "Send Welcome Email",
      "type": "action",
      "config": {
        "action": "send_email",
        "to": "{{variables.email}}",
        "subject": "Welcome!",
        "body": "Welcome to our platform!"
      },
      "next_steps": ["log_success"]
    },
    {
      "id": "send_error",
      "name": "Log Invalid Email",
      "type": "action",
      "config": {
        "action": "log_message",
        "message": "Invalid email provided: {{variables.email}}",
        "level": "error"
      }
    },
    {
      "id": "log_success",
      "name": "Log Success",
      "type": "action",
      "config": {
        "action": "log_message",
        "message": "Welcome email sent successfully",
        "level": "info"
      }
    }
  ]
}
```

## Database Schema

The service uses the following database tables in the `workflow` schema:

- `workflow.templates` - Workflow template definitions
- `workflow.instances` - Workflow instance executions
- `workflow.steps` - Individual step executions
- `workflow.triggers` - Workflow trigger configurations

## Development

### Prerequisites

- Go 1.21+
- PostgreSQL 14+
- Redis 6+

### Running the Service

1. Install dependencies:
```bash
go mod download
```

2. Set up environment variables (see Configuration section)

3. Run the service:
```bash
go run main.go
```

The service will start on port 8081 (or the port specified in the PORT environment variable).

### Testing

Run the tests:
```bash
go test ./...
```

### Building

Build the service:
```bash
go build -o workflow-engine main.go
```

## Deployment

The service is designed to run as a Docker container in AWS ECS Fargate. See the Dockerfile for container configuration.

## Monitoring

The service provides:
- Structured JSON logging
- Health check endpoint
- Redis pub/sub events for real-time monitoring
- Step execution metrics

## Security

- JWT authentication for all API endpoints
- Database connection pooling with secure credentials
- Input validation and sanitization
- SQL injection protection via GORM

## Error Handling

The service implements comprehensive error handling:
- Graceful degradation on external service failures
- Automatic retry mechanisms for transient errors
- Detailed error logging and reporting
- Circuit breaker patterns for external dependencies

## Performance

- Concurrent workflow processing with configurable limits
- Connection pooling for database and Redis
- Efficient step execution with proper resource management
- Horizontal scaling support