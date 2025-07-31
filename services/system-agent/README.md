# System Agent Service

The System Agent is an AI-powered service that provides intelligent task processing, knowledge management, and chat functionality for the Chorus platform. Built with Python, FastAPI, LangChain, and ChromaDB.

## Features

- **AI-Powered Chat**: Conversational AI with RAG (Retrieval Augmented Generation)
- **Knowledge Management**: Vector-based knowledge base with semantic search
- **Task Processing**: Asynchronous task queue management with Celery
- **Multi-Modal Analysis**: Support for various analysis and reporting tasks
- **RESTful API**: Comprehensive REST API for all functionality

## Technology Stack

- **Framework**: FastAPI
- **AI/ML**: LangChain, OpenAI GPT models
- **Vector Database**: ChromaDB
- **Database**: PostgreSQL (async)
- **Message Queue**: Redis + Celery
- **Logging**: Structlog

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL
- Redis
- OpenAI API key

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables:
```bash
export DATABASE_URL="postgresql+asyncpg://chorus:chorus_password@localhost:5432/chorus"
export REDIS_URL="redis://localhost:6379/0"
export OPENAI_API_KEY="your-openai-api-key"
```

3. Start the service:
```bash
python -m app.main
```

4. Start Celery worker (in separate terminal):
```bash
celery -A app.workers.task_worker:celery_app worker --loglevel=info
```

The service will be available at `http://localhost:8083`

## API Endpoints

### Health Check
- `GET /api/v1/health` - Service health status

### Task Management
- `POST /api/v1/tasks` - Create a new task
- `GET /api/v1/tasks` - List tasks with optional filtering
- `GET /api/v1/tasks/{task_id}` - Get specific task
- `PUT /api/v1/tasks/{task_id}` - Update task
- `DELETE /api/v1/tasks/{task_id}` - Delete task
- `POST /api/v1/tasks/{task_id}/execute` - Execute task manually
- `POST /api/v1/tasks/{task_id}/retry` - Retry failed task

### Chat Interface
- `POST /api/v1/chat` - Send chat message and get AI response
- `GET /api/v1/chat/{session_id}/history` - Get conversation history
- `DELETE /api/v1/chat/{session_id}/memory` - Clear conversation memory
- `GET /api/v1/chat/sessions/active` - List active chat sessions

### Knowledge Base
- `POST /api/v1/knowledge` - Create knowledge entry
- `GET /api/v1/knowledge` - List knowledge entries
- `GET /api/v1/knowledge/{entry_id}` - Get specific entry
- `PUT /api/v1/knowledge/{entry_id}` - Update entry
- `DELETE /api/v1/knowledge/{entry_id}` - Delete entry
- `POST /api/v1/knowledge/search` - Search knowledge base

## Task Types

The system supports several task types:

### Chat Tasks
Process conversational AI requests with RAG capabilities.

```json
{
  "task_type": "chat",
  "priority": 5,
  "payload": {
    "message": "What is the status of our system?",
    "session_id": "user123",
    "user_id": "user123",
    "context": {}
  }
}
```

### Knowledge Search Tasks
Perform semantic search across the knowledge base.

```json
{
  "task_type": "knowledge_search",
  "payload": {
    "query": "How to configure Redis?",
    "category": "infrastructure",
    "limit": 5,
    "similarity_threshold": 0.7
  }
}
```

### Analysis Tasks
Perform AI-powered analysis on provided data.

```json
{
  "task_type": "analysis",
  "payload": {
    "analysis_type": "performance",
    "data": "System metrics data...",
    "context": {"timeframe": "24h"}
  }
}
```

### Report Tasks
Generate comprehensive reports using AI.

```json
{
  "task_type": "report",
  "payload": {
    "report_type": "summary",
    "data_sources": ["metrics", "logs"],
    "parameters": {"period": "weekly"}
  }
}
```

## Configuration

The service can be configured using environment variables:

### Application Settings
- `DEBUG`: Enable debug mode (default: false)
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string

### AI Settings
- `OPENAI_API_KEY`: OpenAI API key
- `OPENAI_MODEL`: OpenAI model to use (default: gpt-3.5-turbo)
- `MAX_TOKENS`: Maximum tokens per response (default: 2000)
- `AGENT_TEMPERATURE`: AI temperature setting (default: 0.7)

### ChromaDB Settings
- `CHROMADB_HOST`: ChromaDB host (default: localhost)
- `CHROMADB_PORT`: ChromaDB port (default: 8000)
- `CHROMADB_PERSIST_DIRECTORY`: Local persistence directory

### Task Settings
- `MAX_RETRIES`: Maximum task retry attempts (default: 3)
- `TASK_TIMEOUT`: Task timeout in seconds (default: 300)

## Database Schema

The service uses the following database tables in the `agent` schema:

- `agent.tasks`: Task queue and execution tracking
- `agent.knowledge_base`: Knowledge entries with metadata
- `agent.conversations`: Chat conversation history

## Knowledge Management

The knowledge base supports:

- **Categories**: Organize knowledge by category
- **Tags**: Flexible tagging system
- **Metadata**: Additional structured data
- **Vector Search**: Semantic similarity search
- **Full-text Content**: Rich text content storage

### Adding Knowledge

```bash
curl -X POST "http://localhost:8083/api/v1/knowledge" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "troubleshooting",
    "title": "Redis Connection Issues",
    "content": "When Redis connection fails, check: 1) Redis is running, 2) Connection string is correct, 3) Network connectivity",
    "tags": ["redis", "connection", "troubleshooting"],
    "metadata": {"severity": "high"}
  }'
```

## Chat Interface

The chat interface provides:

- **Context Awareness**: Maintains conversation context
- **RAG Integration**: Uses knowledge base for informed responses
- **Session Management**: Separate conversations per session
- **Memory Management**: Configurable conversation memory

### Chat Example

```bash
curl -X POST "http://localhost:8083/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How do I troubleshoot Redis connection issues?",
    "session_id": "user123",
    "user_id": "user123"
  }'
```

## Monitoring

The service provides several monitoring endpoints:

- Health check endpoint for service status
- Task statistics for queue monitoring
- Active session tracking for chat usage

## Development

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Linting
flake8 app/

# Type checking
mypy app/

# Formatting
black app/
```

### Docker Development

```bash
# Build image
docker build -t system-agent .

# Run with Docker Compose
docker-compose up system-agent
```

## Architecture

The System Agent follows a microservices architecture with:

- **API Layer**: FastAPI REST endpoints
- **Service Layer**: Business logic and AI integration
- **Data Layer**: PostgreSQL and ChromaDB
- **Worker Layer**: Celery task processing
- **Cache Layer**: Redis for session and job data

## Contributing

1. Follow the existing code patterns
2. Add tests for new functionality
3. Update documentation
4. Use structured logging
5. Handle errors gracefully

## Troubleshooting

### Common Issues

1. **ChromaDB Connection**: Ensure ChromaDB is running and accessible
2. **OpenAI API**: Verify API key is valid and has sufficient credits
3. **Database Connection**: Check PostgreSQL connection and schema
4. **Redis Connection**: Ensure Redis is running for Celery tasks

### Logs

The service uses structured logging. Check logs for detailed error information:

```bash
# View application logs
tail -f logs/system-agent.log

# View Celery worker logs
celery -A app.workers.task_worker:celery_app worker --loglevel=debug
```

## License

This service is part of the Chorus platform.