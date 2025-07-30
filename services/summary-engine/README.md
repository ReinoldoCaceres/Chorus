# Summary Engine

A LangChain-powered microservice for generating conversation summaries and managing vector-based conversation search using ChromaDB.

## Features

- Conversation summarization using LangChain and OpenAI
- Multiple summary types (conversation, topic, sentiment, key points)
- Vector storage and similarity search with ChromaDB
- Asynchronous task processing with Celery
- Redis-backed task queue and result storage
- Structured logging with structlog
- Health check endpoints
- Docker support

## Project Structure

```
summary-engine/
├── app/
│   ├── api/
│   │   └── endpoints.py          # API route definitions
│   ├── models/
│   │   └── schemas.py            # Pydantic schemas
│   ├── services/
│   │   ├── summary_service.py    # LangChain summary generation
│   │   └── vector_store.py       # ChromaDB vector operations
│   ├── workers/
│   │   └── summary_worker.py     # Celery task definitions
│   ├── utils/
│   │   └── logging.py            # Logging configuration
│   ├── celery_app.py             # Celery configuration
│   ├── config.py                 # Settings and configuration
│   └── main.py                   # FastAPI application
├── worker.py                     # Celery worker startup script
├── Dockerfile
├── requirements.txt
└── README.md
```

## Installation

1. Copy environment variables:
```bash
cp .env.example .env
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your environment variables in `.env`:
- OPENAI_API_KEY: Your OpenAI API key
- REDIS_URL: Redis connection string
- CHROMADB_PERSIST_DIRECTORY: Directory for ChromaDB storage

## Running the Service

### Local Development

1. Start the API server:
```bash
python app/main.py
```

2. Start Celery worker (in separate terminal):
```bash
celery -A app.celery_app worker --loglevel=info
```

### With Docker
```bash
# Build image
docker build -t summary-engine .

# Run API server
docker run -p 8001:8001 summary-engine

# Run worker (separate container)
docker run summary-engine celery -A app.celery_app worker --loglevel=info
```

## API Endpoints

### Health Check
- `GET /api/v1/health` - Service health status with worker count

### Summary Generation
- `POST /api/v1/summary` - Create summary generation task
- `GET /api/v1/summary/{task_id}` - Get summary result

### Vector Storage
- `POST /api/v1/vector-store` - Store conversation in vector database
- `POST /api/v1/vector-search` - Search for similar conversations

### Task Management
- `GET /api/v1/tasks/{task_id}/status` - Get task status

## Summary Types

### Conversation Summary
General overview of the conversation covering main topics and key points.

### Topic Summary
Structured summary organized by the main topics discussed.

### Sentiment Analysis
Analysis of emotional tone and participant attitudes throughout the conversation.

### Key Points
Extraction of action items, decisions, and important takeaways.

## Vector Search

The service uses ChromaDB to store conversation embeddings for similarity search:
- Automatic text chunking for large conversations
- OpenAI embeddings for semantic search
- Configurable similarity thresholds
- Metadata filtering by conversation ID

## Celery Tasks

### generate_summary_task
Asynchronous summary generation with configurable parameters.

### store_conversation_vectors_task
Store conversation messages in vector database for future search.

### search_similar_conversations_task
Search for conversations similar to a given query.

## Configuration

Environment variables managed through Pydantic Settings:
- OpenAI API configuration
- Redis/Celery settings
- ChromaDB configuration
- Summary generation parameters

## Error Handling

- Comprehensive error logging with structured logs
- Task failure handling with retry mechanisms
- Graceful degradation for external service failures
- Health checks for service monitoring