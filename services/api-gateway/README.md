# API Gateway Service

The API Gateway serves as the single entry point for all client requests to the Chorus platform microservices. It provides authentication, authorization, rate limiting, request routing, and service health monitoring.

## Features

- **JWT Authentication & Authorization**: Validates JWT tokens and enforces role-based access control
- **Rate Limiting**: Redis-backed distributed rate limiting with different tiers for different endpoints
- **Request Routing**: Intelligent routing to backend microservices based on URL patterns
- **Health Monitoring**: Continuous health checks of downstream services with caching
- **Security Headers**: CORS, Helmet security headers, and input validation
- **Logging & Monitoring**: Structured logging with request/response tracking
- **Graceful Shutdown**: Proper cleanup of resources on application termination

## Architecture

The API Gateway follows a layered architecture:

```
Client Request
     ↓
Security Middleware (Helmet, CORS)
     ↓
Authentication Middleware (JWT)
     ↓
Rate Limiting Middleware (Redis)
     ↓
Route Handlers
     ↓
Proxy Service (Backend routing)
     ↓
Backend Microservices
```

## Configuration

The service is configured via environment variables:

### Server Configuration
- `PORT`: Server port (default: 8084)
- `HOST`: Server host (default: 0.0.0.0)
- `NODE_ENV`: Environment (development/production)

### Authentication
- `JWT_SECRET`: Secret key for JWT token validation
- `JWT_EXPIRES_IN`: Token expiration time (default: 6h)

### Redis Configuration
- `REDIS_HOST`: Redis host (default: localhost)
- `REDIS_PORT`: Redis port (default: 6379)
- `REDIS_PASSWORD`: Redis password (if required)

### Backend Services
- `CHAT_SERVICE_URL`: Chat service URL (default: http://localhost:8082)
- `PRESENCE_SERVICE_URL`: Presence service URL (default: http://localhost:8081)
- `SUMMARY_ENGINE_URL`: Summary engine URL (default: http://localhost:8083)
- `WEBSOCKET_GATEWAY_URL`: WebSocket gateway URL (default: http://localhost:8080)
- `*_TIMEOUT`: Service timeout in milliseconds (default: 30000)

### Rate Limiting
- `RATE_LIMIT_WINDOW_MS`: Rate limit window in milliseconds (default: 900000 - 15 minutes)
- `RATE_LIMIT_MAX_REQUESTS`: Max requests per window (default: 100)
- `RATE_LIMIT_SKIP_SUCCESSFUL`: Skip successful requests in rate limit (default: false)

### CORS
- `CORS_ORIGIN`: Allowed origins (comma-separated, default: http://localhost:3000)

### Logging
- `LOG_LEVEL`: Logging level (default: info)

## API Routes

### Public Endpoints
- `GET /health` - Service health check (includes downstream services)
- `GET /api/v1/info` - API version information

### Authenticated Endpoints (require JWT token)

#### Chat Service Routes
- `/api/v1/conversations/*` - Conversation management
- `/api/v1/messages/*` - Message handling
- `/api/v1/chat/*` - General chat operations

#### Presence Service Routes
- `/api/v1/presence/*` - Agent presence management
- `/api/v1/agents/*` - Agent information

#### Summary Engine Routes
- `/api/v1/summaries/*` - Conversation summaries
- `/api/v1/insights/*` - Analytics and insights (admin/supervisor only)

#### Admin Routes (admin role required)
- `/api/v1/admin/*` - Administrative operations

#### Service Health Routes
- `GET /api/v1/services/health` - All services health status
- `GET /api/v1/services/:serviceName/health` - Specific service health

## Rate Limiting

The gateway implements multiple rate limiting strategies:

1. **Default Rate Limiter**: 100 requests per 15 minutes for general API usage
2. **Authentication Rate Limiter**: 5 attempts per 15 minutes for auth endpoints
3. **Read-Only Rate Limiter**: 300 requests per 15 minutes for read operations
4. **Tenant Rate Limiter**: 1000 requests per tenant per 15 minutes

Rate limiting is backed by Redis for distributed scenarios.

## Authentication & Authorization

### JWT Token Structure
```json
{
  "id": "user-id",
  "tenantId": "tenant-id",
  "role": "agent|supervisor|admin",
  "permissions": ["permission1", "permission2"],
  "exp": 1234567890
}
```

### Role-Based Access Control
- **agent**: Basic chat operations
- **supervisor**: Agent management + chat operations
- **admin**: Full system access

### Request Headers
The gateway automatically adds these headers to downstream requests:
- `X-Tenant-ID`: Tenant identifier from JWT
- `X-User-ID`: User identifier from JWT
- `X-User-Role`: User role from JWT

## Health Monitoring

The gateway continuously monitors downstream services:
- Health checks every 30 seconds (configurable)
- Cached health status for fast responses
- Degraded routing when services are unhealthy
- Detailed health information in responses

## Development

### Prerequisites
- Node.js 18+
- Redis server
- Backend microservices running

### Installation
```bash
npm install
```

### Development Mode
```bash
npm run dev
```

### Production Build
```bash
npm run build
npm start
```

### Linting & Formatting
```bash
npm run lint
npm run format
```

## Docker

The service includes a Dockerfile for containerization:

```bash
docker build -t api-gateway .
docker run -p 8084:8084 api-gateway
```

## Environment Variables Example

```env
# Server
PORT=8084
HOST=0.0.0.0
NODE_ENV=production

# Authentication
JWT_SECRET=your-super-secret-jwt-key
JWT_EXPIRES_IN=6h

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password

# Services
CHAT_SERVICE_URL=http://chat-service:8082
PRESENCE_SERVICE_URL=http://presence-service:8081
SUMMARY_ENGINE_URL=http://summary-engine:8083
WEBSOCKET_GATEWAY_URL=http://websocket-gateway:8080

# Rate Limiting
RATE_LIMIT_WINDOW_MS=900000
RATE_LIMIT_MAX_REQUESTS=100

# CORS
CORS_ORIGIN=https://yourdomain.com,https://admin.yourdomain.com

# Logging
LOG_LEVEL=info
```

## Monitoring & Observability

The gateway provides extensive logging and monitoring capabilities:

- **Request/Response Logging**: All requests are logged with timing information
- **Error Tracking**: Comprehensive error logging with stack traces
- **Health Metrics**: Service health status and response times
- **Rate Limit Monitoring**: Rate limit violations and patterns
- **Security Events**: Authentication failures and suspicious activity

## Security Considerations

- JWT tokens are validated on every request
- Rate limiting prevents abuse and DDoS attacks
- Security headers protect against common vulnerabilities
- Tenant isolation ensures data separation
- Input validation and sanitization
- Graceful error handling without information leakage

## Troubleshooting

### Common Issues

1. **Service Unavailable (503)**: Backend service is down or unreachable
2. **Authentication Failed (401)**: Missing or invalid JWT token
3. **Rate Limited (429)**: Too many requests, implement backoff
4. **Bad Gateway (502)**: Communication error with backend service

### Logs
Check logs for detailed error information:
```bash
docker logs api-gateway
```

### Health Checks
Monitor service health:
```bash
curl http://localhost:8084/health
curl http://localhost:8084/api/v1/services/health
```