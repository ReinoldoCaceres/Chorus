# Presence Service

A production-ready presence tracking service for the Chorus application using Redis for state management.

## Features

- Real-time presence tracking with Redis TTL
- Heartbeat mechanism for active user detection
- Online users listing
- User status management (online, away, busy, offline)
- Health check endpoint
- Graceful shutdown
- Request logging middleware
- Dockerized deployment

## Environment Variables

- `PORT`: Server port (default: 8081)
- `REDIS_URL`: Redis connection URL (default: "redis://localhost:6379")
- `REDIS_DB`: Redis database number (default: 0)
- `PRESENCE_TTL_SECONDS`: Presence TTL in seconds (default: 120)

## Endpoints

- `GET /health`: Health check endpoint
- `POST /presence/heartbeat`: Update user presence (heartbeat)
- `GET /presence/status?user_id=<id>`: Get user presence status
- `GET /presence/online`: Get list of online users

## Usage

1. Build and run:
```bash
go mod tidy
go run main.go
```

2. Docker build:
```bash
docker build -t presence-service .
docker run -p 8081:8081 -e REDIS_URL=redis://redis:6379 presence-service
```

## API Examples

### Send Heartbeat
```bash
curl -X POST http://localhost:8081/presence/heartbeat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123", "status": "online", "device": "web"}'
```

### Get User Status
```bash
curl http://localhost:8081/presence/status?user_id=user123
```

### Get Online Users
```bash
curl http://localhost:8081/presence/online
```