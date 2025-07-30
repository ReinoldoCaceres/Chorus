# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Chorus is an omnichannel live-chat platform designed as an extension for the Enkisys (Orchestra) agent platform. This is currently in the **architecture/planning phase** with no implementation code yet.

## Development Status

**IMPORTANT**: This codebase contains only technical documentation. No implementation has begun. When asked to implement features, you'll need to:
1. Create the appropriate directory structure
2. Initialize the relevant package managers (npm, pip, go mod)
3. Set up the microservices architecture as defined in the technical document

## Planned Architecture

The system will consist of 6 microservices:

1. **WebSocket Gateway (C1)** - Go with Gorilla WebSocket
2. **Chat-Service API (C2)** - Python with FastAPI
3. **Presence Service (C3)** - Go
4. **Summary Engine (C4)** - Python with LangChain
5. **Notification Worker (C5)** - Node.js with BullMQ
6. **Admin UI (C6)** - React with Vite

## Technology Stack

- **Languages**: Go, Python, Node.js, TypeScript/JavaScript
- **Databases**: PostgreSQL (primary), Redis (pub/sub & caching), ChromaDB (vectors)
- **Infrastructure**: AWS (us-east-2), Docker, ECS Fargate, ALB, CloudFront
- **Message Queue**: Redis with BullMQ
- **WebSocket**: Gorilla WebSocket (Go)
- **API Framework**: FastAPI (Python)
- **Frontend**: React + Vite

## Key Design Decisions

1. **Multi-tenant architecture** with tenant_id in all tables
2. **RBAC integration** with Enkisys existing system
3. **WebSocket-based** real-time messaging
4. **Microservices** deployed as Docker containers on ECS
5. **Event-driven** architecture using Redis pub/sub

## Database Schema

Key tables to implement:
- `live_chat_sessions` - Track active chat sessions
- `messages` - Extended with delivery/read receipts
- `agent_availability` - Track agent online status
- `chat_queue` - Manage waiting customers

## API Patterns

- REST APIs use `/api/v1/` prefix
- WebSocket endpoint: `/ws/v1/conversations/{conversationId}`
- All APIs require JWT authentication
- Tenant isolation via `X-Tenant-ID` header

## Security Considerations

- JWT tokens with 6-hour expiration
- AWS SSM Parameter Store for secrets
- TLS 1.3 minimum
- OWASP Top 10 compliance required
- No PII in logs

## Testing Requirements

- Unit test coverage ≥80%
- Contract testing with Pact
- Load testing with k6
- Integration tests for all API endpoints

## Performance Targets

- WebSocket latency: P99 < 100ms
- API response time: P95 < 200ms
- Support 10,000 concurrent WebSocket connections
- Message delivery: 99.9% reliability

## TODO Items from Architecture

Several numerical parameters are marked as TODO in the architecture document:
- Average Handle Time (AHT) target
- Message retention period
- Queue timeout values
- Rate limiting thresholds
- Autoscaling parameters

These should be confirmed with stakeholders before implementation.