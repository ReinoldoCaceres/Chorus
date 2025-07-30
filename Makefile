.PHONY: help up down restart build test clean logs ps infra-up infra-down

# Default target
help:
	@echo "Chorus Platform Development Commands"
	@echo ""
	@echo "Basic Commands:"
	@echo "  make up              - Start all services"
	@echo "  make down            - Stop all services"
	@echo "  make restart         - Restart all services"
	@echo "  make build           - Build all service images"
	@echo "  make logs            - Show logs from all services"
	@echo "  make ps              - List running services"
	@echo "  make clean           - Clean up volumes and images"
	@echo ""
	@echo "Infrastructure:"
	@echo "  make infra-up        - Start infrastructure services only"
	@echo "  make infra-down      - Stop infrastructure services"
	@echo ""
	@echo "Service-specific commands:"
	@echo "  make run-websocket   - Run websocket gateway"
	@echo "  make run-chat        - Run chat service"
	@echo "  make run-presence    - Run presence service"
	@echo "  make run-summary     - Run summary engine"
	@echo "  make run-notification - Run notification worker"
	@echo "  make run-admin       - Run admin UI"
	@echo ""
	@echo "Testing:"
	@echo "  make test            - Run all tests"
	@echo "  make test-websocket  - Test websocket gateway"
	@echo "  make test-chat       - Test chat service"
	@echo "  make test-presence   - Test presence service"
	@echo "  make test-summary    - Test summary engine"
	@echo "  make test-notification - Test notification worker"
	@echo "  make test-admin      - Test admin UI"
	@echo ""
	@echo "Development:"
	@echo "  make dev             - Start services in development mode"
	@echo "  make lint            - Run linters for all services"
	@echo "  make fmt             - Format code for all services"

# Docker Compose commands
up:
	docker-compose -f infrastructure/docker-compose.yml up -d

down:
	docker-compose -f infrastructure/docker-compose.yml down

restart:
	docker-compose -f infrastructure/docker-compose.yml restart

build:
	docker-compose -f infrastructure/docker-compose.yml build

logs:
	docker-compose -f infrastructure/docker-compose.yml logs -f

ps:
	docker-compose -f infrastructure/docker-compose.yml ps

clean:
	docker-compose -f infrastructure/docker-compose.yml down -v
	docker system prune -f

# Infrastructure only
infra-up:
	docker-compose -f infrastructure/docker-compose.infra.yml up -d

infra-down:
	docker-compose -f infrastructure/docker-compose.infra.yml down

# Individual service runners (for development)
run-websocket:
	cd services/websocket-gateway && go run cmd/main.go

run-chat:
	cd services/chat-service && python -m uvicorn main:app --reload --port 8001

run-presence:
	cd services/presence-service && go run cmd/main.go

run-summary:
	cd services/summary-engine && python -m uvicorn main:app --reload --port 8003

run-notification:
	cd services/notification-worker && npm run dev

run-admin:
	cd services/admin-ui && npm run dev

# Testing commands
test:
	@echo "Running all tests..."
	@make test-websocket
	@make test-chat
	@make test-presence
	@make test-summary
	@make test-notification
	@make test-admin

test-websocket:
	cd services/websocket-gateway && go test ./...

test-chat:
	cd services/chat-service && pytest

test-presence:
	cd services/presence-service && go test ./...

test-summary:
	cd services/summary-engine && pytest

test-notification:
	cd services/notification-worker && npm test

test-admin:
	cd services/admin-ui && npm test

# Development mode
dev:
	@echo "Starting services in development mode..."
	docker-compose -f infrastructure/docker-compose.yml -f infrastructure/docker-compose.dev.yml up

# Code quality
lint:
	@echo "Running linters..."
	cd services/websocket-gateway && golangci-lint run
	cd services/chat-service && flake8 . && mypy .
	cd services/presence-service && golangci-lint run
	cd services/summary-engine && flake8 . && mypy .
	cd services/notification-worker && npm run lint
	cd services/admin-ui && npm run lint

fmt:
	@echo "Formatting code..."
	cd services/websocket-gateway && go fmt ./...
	cd services/chat-service && black . && isort .
	cd services/presence-service && go fmt ./...
	cd services/summary-engine && black . && isort .
	cd services/notification-worker && npm run format
	cd services/admin-ui && npm run format

# Database migrations
migrate-up:
	@echo "Running database migrations..."
	cd services/chat-service && alembic upgrade head

migrate-down:
	@echo "Rolling back database migrations..."
	cd services/chat-service && alembic downgrade -1

migrate-create:
	@echo "Creating new migration..."
	cd services/chat-service && alembic revision --autogenerate -m "$(name)"

# Utility commands
setup-dev:
	@echo "Setting up development environment..."
	cp .env.example .env
	@echo "Please edit .env with your configuration"
	@echo "Installing dependencies..."
	cd services/notification-worker && npm install
	cd services/admin-ui && npm install
	cd services/chat-service && pip install -r requirements.txt
	cd services/summary-engine && pip install -r requirements.txt
	@echo "Development environment ready!"

# Service logs
logs-websocket:
	docker-compose -f infrastructure/docker-compose.yml logs -f websocket-gateway

logs-chat:
	docker-compose -f infrastructure/docker-compose.yml logs -f chat-service

logs-presence:
	docker-compose -f infrastructure/docker-compose.yml logs -f presence-service

logs-summary:
	docker-compose -f infrastructure/docker-compose.yml logs -f summary-engine

logs-notification:
	docker-compose -f infrastructure/docker-compose.yml logs -f notification-worker

logs-admin:
	docker-compose -f infrastructure/docker-compose.yml logs -f admin-ui

# Health checks
health:
	@echo "Checking service health..."
	@curl -f http://localhost:8000/health || echo "API Gateway: DOWN"
	@curl -f http://localhost:8001/health || echo "Chat Service: DOWN"
	@curl -f http://localhost:8002/health || echo "Presence Service: DOWN"
	@curl -f http://localhost:8003/health || echo "Summary Engine: DOWN"
	@curl -f http://localhost:8004/health || echo "Notification Worker: DOWN"
	@curl -f http://localhost:3000 || echo "Admin UI: DOWN"