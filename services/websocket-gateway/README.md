# WebSocket Gateway Service

A production-ready WebSocket gateway service for real-time communication in the Chorus application.

## Features

- WebSocket connection handling with Gorilla WebSocket
- JWT-based authentication
- Connection pooling and message broadcasting
- Health check endpoint
- Graceful shutdown
- Request logging middleware
- Dockerized deployment

## Environment Variables

- `PORT`: Server port (default: 8080)
- `JWT_SECRET`: Secret key for JWT validation (default: "your-secret-key")

## Endpoints

- `GET /health`: Health check endpoint
- `GET /ws?token=<jwt_token>`: WebSocket upgrade endpoint (requires JWT token)

## Usage

1. Build and run:
```bash
go mod tidy
go run main.go
```

2. Docker build:
```bash
docker build -t websocket-gateway .
docker run -p 8080:8080 -e JWT_SECRET=your-secret websocket-gateway
```

## WebSocket Connection

Connect to the WebSocket endpoint with a valid JWT token:
```javascript
const ws = new WebSocket('ws://localhost:8080/ws?token=your-jwt-token');
```

The JWT token should contain a `user_id` claim for user identification.