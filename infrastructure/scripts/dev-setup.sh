#!/bin/bash

# Chorus Platform Development Setup Script
# This script sets up the development environment for the first time

set -e

echo "=========================================="
echo "🎵 Chorus Platform Development Setup"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if Docker is installed and running
check_docker() {
    log_info "Checking Docker installation..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    log_success "Docker is installed and running"
}

# Check if Docker Compose is available
check_docker_compose() {
    log_info "Checking Docker Compose installation..."
    
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    elif command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    else
        log_error "Docker Compose is not available. Please install Docker Compose."
        exit 1
    fi
    
    log_success "Docker Compose is available: $COMPOSE_CMD"
}

# Create necessary directories
create_directories() {
    log_info "Creating service directories..."
    
    mkdir -p ../services/{workflow-engine,process-monitor,system-agent,api-gateway,admin-ui,notification-service}
    
    log_success "Service directories created"
}

# Create .dockerignore files for each service
create_dockerignore_files() {
    log_info "Creating .dockerignore files..."
    
    # Common .dockerignore content
    cat > ../services/workflow-engine/.dockerignore << 'EOF'
# Build artifacts
target/
bin/
*.exe
*.dll
*.so
*.dylib

# Go specific
*.test
*.prof
vendor/

# IDE files
.vscode/
.idea/
*.swp
*.swo

# OS files
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Dependencies
node_modules/

# Test coverage
coverage.txt
coverage.out

# Docker
Dockerfile*
docker-compose*
.dockerignore

# Git
.git/
.gitignore

# Documentation
README.md
docs/
EOF

    # Python services .dockerignore
    for service in process-monitor system-agent notification-service; do
        cat > ../services/$service/.dockerignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Testing
.tox/
.nox/
.coverage
.pytest_cache/
cover/
htmlcov/

# Jupyter
.ipynb_checkpoints

# IDE files
.vscode/
.idea/
*.swp
*.swo

# OS files
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Docker
Dockerfile*
docker-compose*
.dockerignore

# Git
.git/
.gitignore

# Documentation
README.md
docs/
EOF
    done

    # Node.js services .dockerignore
    for service in api-gateway admin-ui; do
        cat > ../services/$service/.dockerignore << 'EOF'
# Dependencies
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
lerna-debug.log*
.pnpm-debug.log*

# Runtime data
pids
*.pid
*.seed
*.pid.lock

# Build outputs
build/
dist/
.next/
out/

# Testing
coverage/
.nyc_output

# Environment
.env
.env.local
.env.development.local
.env.test.local
.env.production.local

# IDE files
.vscode/
.idea/
*.swp
*.swo

# OS files
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Docker
Dockerfile*
docker-compose*
.dockerignore

# Git
.git/
.gitignore

# Documentation
README.md
docs/
EOF
    done
    
    log_success "Created .dockerignore files for all services"
}

# Create basic service structure
create_service_structure() {
    log_info "Creating basic service structure..."
    
    # Go service (workflow-engine)
    mkdir -p ../services/workflow-engine/{cmd,internal/{handlers,models,config},pkg}
    cat > ../services/workflow-engine/main.go << 'EOF'
package main

import (
    "fmt"
    "log"
    "net/http"
    "os"
)

func main() {
    port := os.Getenv("PORT")
    if port == "" {
        port = "8081"
    }

    http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
        w.WriteHeader(http.StatusOK)
        fmt.Fprint(w, "OK")
    })

    log.Printf("Workflow Engine starting on port %s", port)
    log.Fatal(http.ListenAndServe(":"+port, nil))
}
EOF

    cat > ../services/workflow-engine/go.mod << 'EOF'
module github.com/chorus/workflow-engine

go 1.21

require ()
EOF

    # Python services
    for service in process-monitor system-agent notification-service; do
        mkdir -p ../services/$service/{app,tests}
        cat > ../services/$service/app/main.py << 'EOF'
import os
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": os.getenv("SERVICE_NAME", "unknown")})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8082))
    app.run(host='0.0.0.0', port=port, debug=True)
EOF

        cat > ../services/$service/requirements.txt << 'EOF'
Flask==2.3.3
psycopg2-binary==2.9.7
redis==4.6.0
requests==2.31.0
python-dotenv==1.0.0
pydantic==2.3.0
sqlalchemy==2.0.21
alembic==1.12.0
EOF
    done

    # Node.js services
    for service in api-gateway admin-ui; do
        mkdir -p ../services/$service/{src,public,tests}
        cat > ../services/$service/package.json << EOF
{
  "name": "chorus-$service",
  "version": "1.0.0",
  "description": "Chorus Platform $service",
  "main": "src/index.js",
  "scripts": {
    "start": "node src/index.js",
    "dev": "nodemon src/index.js",
    "test": "jest"
  },
  "dependencies": {
    "express": "^4.18.2",
    "cors": "^2.8.5",
    "helmet": "^7.0.0",
    "dotenv": "^16.3.1"
  },
  "devDependencies": {
    "nodemon": "^3.0.1",
    "jest": "^29.7.0"
  }
}
EOF

        cat > ../services/$service/src/index.js << 'EOF'
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
require('dotenv').config();

const app = express();
const port = process.env.PORT || 3000;

// Middleware
app.use(helmet());
app.use(cors());
app.use(express.json());

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({ 
        status: 'healthy', 
        service: process.env.SERVICE_NAME || 'unknown',
        timestamp: new Date().toISOString()
    });
});

app.listen(port, '0.0.0.0', () => {
    console.log(`${process.env.SERVICE_NAME || 'Service'} running on port ${port}`);
});
EOF
    done
    
    log_success "Created basic service structure"
}

# Pull required Docker images
pull_images() {
    log_info "Pulling required Docker images..."
    
    docker pull postgres:15-alpine
    docker pull redis:7-alpine
    docker pull chromadb/chroma:latest
    docker pull nginx:alpine
    docker pull mailhog/mailhog:latest
    
    log_success "Docker images pulled"
}

# Start the development environment
start_environment() {
    log_info "Starting the development environment..."
    
    cd ../
    $COMPOSE_CMD -f infrastructure/docker-compose.yml up -d postgres redis chromadb
    
    log_info "Waiting for database to be ready..."
    sleep 10
    
    log_success "Core services started"
    log_info "You can now start all services with: $COMPOSE_CMD -f infrastructure/docker-compose.yml up -d"
}

# Main execution
main() {
    log_info "Starting Chorus Platform development setup..."
    
    check_docker
    check_docker_compose
    create_directories
    create_dockerignore_files
    create_service_structure
    pull_images
    start_environment
    
    echo ""
    log_success "🎉 Development environment setup complete!"
    echo ""
    echo "📋 Next steps:"
    echo "   1. Start all services: $COMPOSE_CMD -f infrastructure/docker-compose.yml up -d"
    echo "   2. View logs: $COMPOSE_CMD -f infrastructure/docker-compose.yml logs -f"
    echo "   3. Access services:"
    echo "      - Admin UI: http://localhost:3000"
    echo "      - API Gateway: http://localhost:8084"
    echo "      - Workflow Engine: http://localhost:8081"
    echo "      - Process Monitor: http://localhost:8082"
    echo "      - System Agent: http://localhost:8083"
    echo "      - Notification Service: http://localhost:8085"
    echo "      - MailHog (email testing): http://localhost:8025"
    echo "   4. Stop services: $COMPOSE_CMD -f infrastructure/docker-compose.yml down"
    echo ""
    echo "🔧 Development tips:"
    echo "   - Use docker-compose.override.yml for local customizations"
    echo "   - Check service health: curl http://localhost:8081/health"
    echo "   - View database: Connect to postgres://chorus:chorus_password@localhost:5432/chorus_db"
    echo ""
}

# Execute main function
main "$@"