# Chorus Platform Infrastructure

This directory contains the complete Docker infrastructure setup for the Chorus Platform, including all microservices, databases, and supporting tools.

## 🏗️ Architecture Overview

The Chorus Platform consists of the following components:

### Core Services
- **Workflow Engine** (Go) - Orchestrates and executes workflows
- **Process Monitor** (Python) - Monitors system processes and resources
- **System Agent** (Python) - AI-powered system agent with knowledge base
- **API Gateway** (Node.js) - Central API gateway and routing
- **Admin UI** (React) - Web interface for platform management
- **Notification Service** (Python) - Handles all platform notifications

### Infrastructure Services
- **PostgreSQL 15** - Primary database with schemas for all services
- **Redis 7** - Caching and session storage
- **ChromaDB** - Vector database for AI embeddings
- **Nginx** - Reverse proxy and load balancer
- **MailHog** - Email testing tool (development only)

### Development Tools
- **PgAdmin** - Database administration interface
- **Redis Commander** - Redis management interface

## 🚀 Quick Start

### Prerequisites
- Docker 20.x or later
- Docker Compose 2.x or later
- At least 4GB of available RAM
- Available ports: 80, 3000, 5432, 6379, 8000, 8081-8085

### First-Time Setup

1. **Run the development setup script:**
   ```bash
   cd infrastructure/scripts
   ./dev-setup.sh
   ```

2. **Start all services:**
   ```bash
   cd infrastructure
   docker compose up -d
   ```

3. **Verify services are running:**
   ```bash
   docker compose ps
   ```

### Access Points

- **Admin UI**: http://localhost:3000
- **API Gateway**: http://localhost:8084
- **Workflow Engine**: http://localhost:8081
- **Process Monitor**: http://localhost:8082
- **System Agent**: http://localhost:8083
- **Notification Service**: http://localhost:8085
- **MailHog UI**: http://localhost:8025
- **PgAdmin**: http://localhost:5050 (admin@chorus.local / admin)
- **Redis Commander**: http://localhost:8081

## 📁 Directory Structure

```
infrastructure/
├── docker/                    # Base Dockerfiles
│   ├── base-go.dockerfile
│   ├── base-node.dockerfile
│   └── base-python.dockerfile
├── nginx/                     # Nginx configurations
│   ├── nginx.conf            # Production configuration
│   └── nginx.dev.conf        # Development configuration
├── postgres/                  # Database setup
│   └── init.sql              # Database schema and initial data
├── scripts/                   # Utility scripts
│   ├── dev-setup.sh          # First-time development setup
│   └── wait-for-it.sh        # Service dependency waiter
├── docker-compose.yml         # Main compose file
├── docker-compose.override.yml # Development overrides
└── README.md                 # This file
```

## 🛠️ Development Workflow

### Starting Services

```bash
# Start all services
docker compose up -d

# Start specific services only
docker compose up -d postgres redis chromadb

# View logs
docker compose logs -f

# View logs for specific service
docker compose logs -f workflow-engine
```

### Stopping Services

```bash
# Stop all services
docker compose down

# Stop and remove volumes (⚠️ destroys data)
docker compose down -v

# Stop specific service
docker compose stop api-gateway
```

### Development Mode

The `docker-compose.override.yml` file automatically enables development features:

- **Hot reload** for all services
- **Source code mounting** for live editing
- **Extended timeouts** for debugging
- **Verbose logging** for troubleshooting
- **Additional development tools** (PgAdmin, Redis Commander)

### Building Services

```bash
# Rebuild all services
docker compose build

# Rebuild specific service
docker compose build workflow-engine

# Rebuild without cache
docker compose build --no-cache
```

### Database Management

```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U chorus -d chorus_db

# Run database migrations (if available)
docker compose exec workflow-engine ./migrate up

# Backup database
docker compose exec postgres pg_dump -U chorus chorus_db > backup.sql

# Restore database
docker compose exec -T postgres psql -U chorus -d chorus_db < backup.sql
```

### Logs and Debugging

```bash
# Follow all logs
docker compose logs -f

# Show last 100 lines for specific service
docker compose logs --tail=100 system-agent

# Show logs since specific time
docker compose logs --since="2h" api-gateway

# Get shell access to container
docker compose exec workflow-engine sh
```

## 🔧 Configuration

### Environment Variables

Each service can be configured through environment variables defined in the compose files:

- **Database**: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
- **Redis**: `REDIS_HOST`, `REDIS_PORT`
- **ChromaDB**: `CHROMADB_HOST`, `CHROMADB_PORT`, `CHROMADB_AUTH_TOKEN`
- **Service-specific**: Check individual service documentation

### Service Discovery

Services communicate using Docker's internal DNS:
- `postgres:5432` - PostgreSQL database
- `redis:6379` - Redis cache
- `chromadb:8000` - ChromaDB vector database
- `workflow-engine:8081` - Workflow Engine API
- `process-monitor:8082` - Process Monitor API
- `system-agent:8083` - System Agent API
- `api-gateway:8084` - API Gateway
- `notification-service:8085` - Notification Service API

### Volumes

Persistent data is stored in Docker volumes:
- `postgres_data` - Database data
- `redis_data` - Redis persistence
- `chromadb_data` - Vector database data
- `go_mod_cache` - Go module cache
- `python_cache` - Python package cache
- `node_modules_*` - Node.js dependencies

## 🏥 Health Checks

All services include health checks that monitor:
- **HTTP endpoints** - Service responsiveness
- **Database connections** - Connection pool status
- **External dependencies** - Required service availability

Check service health:
```bash
docker compose ps
```

## 🔒 Security Considerations

### Development Security
- Default passwords are used (change for production)
- CORS is permissive for development
- Debug endpoints are exposed
- No TLS/SSL encryption

### Production Recommendations
- Use secrets management for credentials
- Enable TLS/SSL certificates
- Restrict CORS origins
- Remove debug tools and endpoints
- Use network policies for service isolation
- Enable audit logging

## 🚨 Troubleshooting

### Common Issues

1. **Port conflicts**:
   ```bash
   # Check what's using a port
   lsof -i :8081
   
   # Kill process using port
   kill -9 $(lsof -t -i :8081)
   ```

2. **Service startup failures**:
   ```bash
   # Check service logs
   docker compose logs service-name
   
   # Check service dependencies
   docker compose config
   ```

3. **Database connection issues**:
   ```bash
   # Test database connectivity
   docker compose exec postgres pg_isready -U chorus
   
   # Check database logs
   docker compose logs postgres
   ```

4. **Out of disk space**:
   ```bash
   # Clean unused Docker resources
   docker system prune -a
   
   # Remove unused volumes
   docker volume prune
   ```

5. **Memory issues**:
   ```bash
   # Check container memory usage
   docker stats
   
   # Increase Docker memory limit in Docker Desktop
   ```

### Performance Tuning

1. **Increase memory limits** in Docker Desktop
2. **Use SSD storage** for better I/O performance
3. **Disable unused services** to save resources
4. **Enable BuildKit** for faster builds:
   ```bash
   export DOCKER_BUILDKIT=1
   ```

### Reset Everything

```bash
# Stop all services and remove everything
docker compose down -v --remove-orphans

# Remove all Chorus-related images
docker images | grep chorus | awk '{print $3}' | xargs docker rmi -f

# Remove all unused resources
docker system prune -a --volumes

# Start fresh
./scripts/dev-setup.sh
```

## 🤝 Contributing

When adding new services:

1. Create service directory in `../services/`
2. Add service definition to `docker-compose.yml`
3. Create appropriate base Dockerfile in `infrastructure/docker/`
4. Add development overrides to `docker-compose.override.yml`
5. Update this README with new service information
6. Add health checks and proper dependency management

## 📚 Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Docker Image](https://hub.docker.com/_/postgres)
- [Redis Docker Image](https://hub.docker.com/_/redis)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Nginx Docker Image](https://hub.docker.com/_/nginx)