# Chorus - AI-Powered Collaborative Chat Platform

Chorus is a microservices-based platform that provides real-time chat functionality with AI-powered features including conversation summarization, smart notifications, and presence tracking.

## Architecture Overview

The platform consists of six microservices:

- **Websocket Gateway (C1)** - Go service handling WebSocket connections and real-time message routing
- **Chat Service (C2)** - Python FastAPI service managing chat operations and message persistence
- **Presence Service (C3)** - Go service tracking user online/offline status and activity
- **Summary Engine (C4)** - Python LangChain service providing AI-powered conversation summaries
- **Notification Worker (C5)** - Node.js service handling async notifications (email, push, in-app)
- **Admin UI (C6)** - React Vite application for system administration

## Technology Stack

- **Languages**: Go, Python, Node.js, TypeScript
- **Frameworks**: FastAPI, LangChain, Express.js, React, Vite
- **Databases**: PostgreSQL, MongoDB, Redis
- **Message Queue**: RabbitMQ
- **Container**: Docker, Docker Compose
- **API Gateway**: Kong

## Prerequisites

- Docker and Docker Compose
- Make
- Git
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)
- Go 1.21+ (for local development)

## Quick Start

1. Clone the repository:
```bash
git clone <repository-url>
cd Chorus
```

2. Copy environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Start all services:
```bash
make up
```

4. Access the services:
- Admin UI: http://localhost:3000
- API Gateway: http://localhost:8000
- WebSocket Gateway: ws://localhost:8080

## Development

### Running Services Individually

```bash
# Start infrastructure only
make infra-up

# Run specific service
make run-chat-service
make run-websocket-gateway
# ... etc
```

### Running Tests

```bash
# Run all tests
make test

# Run tests for specific service
make test-chat-service
make test-websocket-gateway
# ... etc
```

### Building Services

```bash
# Build all services
make build

# Build specific service
make build-chat-service
make build-websocket-gateway
# ... etc
```

## Project Structure

```
chorus/
├── services/
│   ├── websocket-gateway/    # Go WebSocket service
│   ├── chat-service/         # Python FastAPI service
│   ├── presence-service/     # Go presence tracking
│   ├── summary-engine/       # Python LangChain AI service
│   ├── notification-worker/  # Node.js notification service
│   └── admin-ui/            # React admin interface
├── infrastructure/          # Docker compose and shared configs
├── shared/                 # Common utilities and protocols
├── docs/                   # Additional documentation
├── .env.example           # Environment variables template
├── .gitignore            # Git ignore rules
├── Makefile              # Development commands
└── README.md             # This file
```

## Configuration

All services are configured through environment variables. See `.env.example` for a complete list of required variables.

Key configuration areas:
- Database connections (PostgreSQL, MongoDB, Redis)
- RabbitMQ connection
- API keys (OpenAI for Summary Engine)
- Service ports and endpoints
- JWT secrets and security settings

## API Documentation

- Chat Service API: http://localhost:8001/docs
- Presence Service API: http://localhost:8002/docs
- Summary Engine API: http://localhost:8003/docs
- Notification Service API: http://localhost:8004/docs

## Monitoring

- Health checks available at `/health` for each service
- Metrics endpoint at `/metrics` (Prometheus format)
- Distributed tracing with OpenTelemetry

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests: `make test`
4. Submit a pull request

## License

[Your License Here]

## Support

For issues and questions:
- Create an issue in the repository
- Contact the team at support@chorus.example.com