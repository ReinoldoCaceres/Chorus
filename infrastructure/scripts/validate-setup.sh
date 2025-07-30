#!/bin/bash

# Chorus Platform Setup Validation Script
# This script validates that the Docker infrastructure is properly configured

set -e

echo "=========================================="
echo "🔍 Chorus Platform Setup Validation"
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

# Validation counters
CHECKS_PASSED=0
CHECKS_FAILED=0

# Helper function to run checks
run_check() {
    local check_name="$1"
    local check_command="$2"
    
    log_info "Checking $check_name..."
    
    if eval "$check_command" > /dev/null 2>&1; then
        log_success "$check_name is valid"
        ((CHECKS_PASSED++))
    else
        log_error "$check_name failed"
        ((CHECKS_FAILED++))
    fi
}

# Check Docker and Docker Compose
check_docker() {
    log_info "Validating Docker setup..."
    
    run_check "Docker installation" "docker --version"
    run_check "Docker daemon" "docker info"
    
    if docker compose version > /dev/null 2>&1; then
        COMPOSE_CMD="docker compose"
        log_success "Docker Compose v2 detected"
        ((CHECKS_PASSED++))
    elif command -v docker-compose > /dev/null 2>&1; then
        COMPOSE_CMD="docker-compose"
        log_success "Docker Compose v1 detected"
        ((CHECKS_PASSED++))
    else
        log_error "Docker Compose not found"
        ((CHECKS_FAILED++))
        return 1
    fi
}

# Validate Docker Compose files
validate_compose_files() {
    log_info "Validating Docker Compose configuration..."
    
    run_check "Main compose file syntax" "$COMPOSE_CMD -f docker-compose.yml config --quiet"
    run_check "Override compose file syntax" "$COMPOSE_CMD -f docker-compose.yml -f docker-compose.override.yml config --quiet"
}

# Check required directories and files
check_file_structure() {
    log_info "Validating file structure..."
    
    local required_files=(
        "docker-compose.yml"
        "docker-compose.override.yml"
        "postgres/init.sql"
        "nginx/nginx.conf"
        "nginx/nginx.dev.conf"
        "docker/base-python.dockerfile"
        "docker/base-node.dockerfile"
        "docker/base-go.dockerfile"
        "scripts/wait-for-it.sh"
        "scripts/dev-setup.sh"
    )
    
    for file in "${required_files[@]}"; do
        if [[ -f "$file" ]]; then
            log_success "Found $file"
            ((CHECKS_PASSED++))
        else
            log_error "Missing $file"
            ((CHECKS_FAILED++))
        fi
    done
    
    # Check service directories
    local service_dirs=(
        "../services/workflow-engine"
        "../services/process-monitor"
        "../services/system-agent"
        "../services/api-gateway"
        "../services/admin-ui"
        "../services/notification-service"
    )
    
    for dir in "${service_dirs[@]}"; do
        if [[ -d "$dir" ]]; then
            log_success "Found service directory $dir"
            ((CHECKS_PASSED++))
        else
            log_warning "Service directory $dir not found (will be created by dev-setup.sh)"
        fi
    done
}

# Check script permissions
check_script_permissions() {
    log_info "Validating script permissions..."
    
    local scripts=(
        "scripts/wait-for-it.sh"
        "scripts/dev-setup.sh"
        "scripts/validate-setup.sh"
    )
    
    for script in "${scripts[@]}"; do
        if [[ -x "$script" ]]; then
            log_success "$script is executable"
            ((CHECKS_PASSED++))
        else
            log_warning "$script is not executable, fixing..."
            chmod +x "$script"
            ((CHECKS_PASSED++))
        fi
    done
}

# Check available ports
check_ports() {
    log_info "Checking port availability..."
    
    local required_ports=(80 3000 5432 6379 8000 8081 8082 8083 8084 8085)
    local port_conflicts=()
    
    for port in "${required_ports[@]}"; do
        if lsof -i ":$port" > /dev/null 2>&1; then
            port_conflicts+=($port)
            log_warning "Port $port is in use"
        else
            log_success "Port $port is available"
            ((CHECKS_PASSED++))
        fi
    done
    
    if [[ ${#port_conflicts[@]} -gt 0 ]]; then
        log_warning "The following ports are in use: ${port_conflicts[*]}"
        log_warning "You may need to stop conflicting services or change port mappings"
    fi
}

# Check system resources
check_resources() {
    log_info "Checking system resources..."
    
    # Check available memory (Linux/macOS)
    if command -v free > /dev/null 2>&1; then
        local available_mem=$(free -m | awk 'NR==2{print $7}')
        if [[ $available_mem -gt 4000 ]]; then
            log_success "Sufficient memory available (${available_mem}MB)"
            ((CHECKS_PASSED++))
        else
            log_warning "Low memory available (${available_mem}MB). Recommended: 4GB+"
        fi
    elif command -v vm_stat > /dev/null 2>&1; then
        # macOS memory check
        local free_pages=$(vm_stat | grep "Pages free" | awk '{print $3}' | tr -d '.')
        local available_mem=$((free_pages * 4096 / 1024 / 1024))
        if [[ $available_mem -gt 4000 ]]; then
            log_success "Sufficient memory available (${available_mem}MB)"
            ((CHECKS_PASSED++))
        else
            log_warning "Low memory available (${available_mem}MB). Recommended: 4GB+"
        fi
    else
        log_warning "Cannot check memory availability on this system"
    fi
    
    # Check available disk space
    local available_space=$(df . | awk 'NR==2 {print $4}')
    local available_gb=$((available_space / 1024 / 1024))
    
    if [[ $available_gb -gt 10 ]]; then
        log_success "Sufficient disk space available (${available_gb}GB)"
        ((CHECKS_PASSED++))
    else
        log_warning "Low disk space available (${available_gb}GB). Recommended: 10GB+"
    fi
}

# Validate Dockerfiles
validate_dockerfiles() {
    log_info "Validating Dockerfiles..."
    
    local dockerfiles=(
        "docker/base-python.dockerfile"
        "docker/base-node.dockerfile"
        "docker/base-go.dockerfile"
    )
    
    for dockerfile in "${dockerfiles[@]}"; do
        if docker build -f "$dockerfile" -t "test-${dockerfile##*/}" . --dry-run > /dev/null 2>&1; then
            log_success "$dockerfile syntax is valid"
            ((CHECKS_PASSED++))
        else
            log_error "$dockerfile has syntax errors"
            ((CHECKS_FAILED++))
        fi
    done
}

# Test service connectivity requirements
test_service_dependencies() {
    log_info "Testing service dependency configuration..."
    
    # Check if compose file defines proper depends_on relationships
    local compose_content=$(docker compose -f docker-compose.yml config 2>/dev/null)
    
    if echo "$compose_content" | grep -q "depends_on"; then
        log_success "Service dependencies are defined"
        ((CHECKS_PASSED++))
    else
        log_warning "No service dependencies found in compose configuration"
    fi
    
    # Check if health checks are defined
    if echo "$compose_content" | grep -q "healthcheck"; then
        log_success "Health checks are configured"
        ((CHECKS_PASSED++))
    else
        log_warning "No health checks found in compose configuration"
    fi
}

# Main validation function
main() {
    echo "Starting validation..."
    echo ""
    
    check_docker
    validate_compose_files
    check_file_structure
    check_script_permissions
    check_ports
    check_resources
    validate_dockerfiles
    test_service_dependencies
    
    echo ""
    echo "=========================================="
    echo "📊 Validation Summary"
    echo "=========================================="
    echo -e "✅ Checks passed: ${GREEN}$CHECKS_PASSED${NC}"
    echo -e "❌ Checks failed: ${RED}$CHECKS_FAILED${NC}"
    echo ""
    
    if [[ $CHECKS_FAILED -eq 0 ]]; then
        log_success "🎉 All validations passed! Your setup is ready."
        echo ""
        echo "Next steps:"
        echo "1. Run './scripts/dev-setup.sh' to initialize the development environment"
        echo "2. Start services with 'docker compose up -d'"
        echo "3. Access the Admin UI at http://localhost:3000"
        return 0
    else
        log_error "⚠️  Some validations failed. Please fix the issues above before proceeding."
        echo ""
        echo "Common solutions:"
        echo "- Ensure Docker is running and you have sufficient privileges"
        echo "- Stop conflicting services using the reported ports"
        echo "- Check file permissions and ownership"
        echo "- Ensure sufficient system resources are available"
        return 1
    fi
}

# Change to infrastructure directory
cd "$(dirname "$0")/.."

# Run main validation
main "$@"