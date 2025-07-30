# Chat Service API

A FastAPI-based microservice for managing live chat sessions and messages in the Chorus application.

## Features

- Real-time chat session management
- Message CRUD operations with soft deletion
- PostgreSQL database with SQLAlchemy ORM
- Redis integration for caching
- Structured logging with structlog
- Health check endpoints
- Docker support

## Project Structure

```
chat-service/
├── app/
│   ├── api/
│   │   └── endpoints.py          # API route definitions
│   ├── db/
│   │   ├── database.py           # Database connection
│   │   └── redis.py              # Redis connection
│   ├── models/
│   │   ├── database.py           # SQLAlchemy models
│   │   └── schemas.py            # Pydantic schemas
│   ├── services/
│   │   └── chat_service.py       # Business logic
│   ├── utils/
│   │   └── logging.py            # Logging configuration
│   ├── config.py                 # Settings and configuration
│   └── main.py                   # FastAPI application
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
- DATABASE_URL: PostgreSQL connection string
- REDIS_URL: Redis connection string
- SECRET_KEY: Application secret key

## Running the Service

### Local Development
```bash
python app/main.py
```

### With Docker
```bash
docker build -t chat-service .
docker run -p 8000:8000 chat-service
```

## API Endpoints

### Health Check
- `GET /api/v1/health` - Service health status

### Sessions
- `POST /api/v1/sessions` - Create new chat session
- `GET /api/v1/sessions/{session_id}` - Get session with messages
- `GET /api/v1/users/{user_id}/sessions` - Get user's sessions
- `PATCH /api/v1/sessions/{session_id}` - Update session
- `POST /api/v1/sessions/{session_id}/end` - End session

### Messages
- `POST /api/v1/sessions/{session_id}/messages` - Create message
- `GET /api/v1/sessions/{session_id}/messages` - Get session messages
- `DELETE /api/v1/messages/{message_id}` - Delete message

## Database Models

### LiveChatSession
- Session management with user/agent assignment
- Status tracking (active, ended, transferred)
- Metadata support for extensibility

### Message
- Message content with sender information
- Soft deletion support
- Extensible metadata

### MessageExtension
- Support for attachments, reactions, edit history
- Flexible JSON data storage

## Configuration

Environment variables are managed through Pydantic Settings:
- Database connection settings
- Redis configuration
- CORS origins
- Security settings

The service automatically creates database tables on startup.