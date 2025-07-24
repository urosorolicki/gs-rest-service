#!/bin/bash

# GS Rest Service Deployment Script
# Author: DevOps Team
# Description: Deploys the gs-rest-service Docker container to a remote server

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
DEFAULT_IMAGE="gs-rest-service:latest"
DEFAULT_PORT="777"
DEFAULT_CONTAINER_NAME="gs-rest-service"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Help function
show_help() {
    cat << EOF
GS Rest Service Deployment Script

Usage: $0 [OPTIONS]

Options:
    -h, --help              Show this help message
    -s, --server HOST       Deployment server hostname/IP
    -u, --user USER         SSH username (default: current user)
    -p, --port PORT         SSH port (default: 22)
    -i, --image IMAGE       Docker image to deploy (default: $DEFAULT_IMAGE)
    -c, --container NAME    Container name (default: $DEFAULT_CONTAINER_NAME)
    --app-port PORT         Application port (default: $DEFAULT_PORT)
    --local                 Deploy locally instead of remote server
    --build                 Build Docker image before deployment
    --no-health-check       Skip health check after deployment
    --dry-run              Show what would be done without executing

Examples:
    $0 --local --build
    $0 --server myserver.com --user deploy --build
    $0 --server 192.168.1.100 --image gs-rest-service:v1.0.0

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -s|--server)
                DEPLOY_SERVER="$2"
                shift 2
                ;;
            -u|--user)
                SSH_USER="$2"
                shift 2
                ;;
            -p|--port)
                SSH_PORT="$2"
                shift 2
                ;;
            -i|--image)
                DOCKER_IMAGE="$2"
                shift 2
                ;;
            -c|--container)
                CONTAINER_NAME="$2"
                shift 2
                ;;
            --app-port)
                APP_PORT="$2"
                shift 2
                ;;
            --local)
                LOCAL_DEPLOY=true
                shift
                ;;
            --build)
                BUILD_IMAGE=true
                shift
                ;;
            --no-health-check)
                SKIP_HEALTH_CHECK=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            *)
                error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Set defaults
set_defaults() {
    DOCKER_IMAGE="${DOCKER_IMAGE:-$DEFAULT_IMAGE}"
    CONTAINER_NAME="${CONTAINER_NAME:-$DEFAULT_CONTAINER_NAME}"
    APP_PORT="${APP_PORT:-$DEFAULT_PORT}"
    SSH_USER="${SSH_USER:-$(whoami)}"
    SSH_PORT="${SSH_PORT:-22}"
    LOCAL_DEPLOY="${LOCAL_DEPLOY:-false}"
    BUILD_IMAGE="${BUILD_IMAGE:-false}"
    SKIP_HEALTH_CHECK="${SKIP_HEALTH_CHECK:-false}"
    DRY_RUN="${DRY_RUN:-false}"
}

# Validate configuration
validate_config() {
    if [ "$LOCAL_DEPLOY" = false ] && [ -z "$DEPLOY_SERVER" ]; then
        error "Deployment server must be specified unless using --local"
        exit 1
    fi
    
    if [ "$BUILD_IMAGE" = true ]; then
        if [ ! -f "$SCRIPT_DIR/complete/Dockerfile" ]; then
            error "Dockerfile not found at $SCRIPT_DIR/complete/Dockerfile"
            exit 1
        fi
    fi
}

# Build Docker image
build_image() {
    log "Building Docker image: $DOCKER_IMAGE"
    
    if [ "$DRY_RUN" = true ]; then
        log "DRY RUN: Would build image with: docker build -t $DOCKER_IMAGE $SCRIPT_DIR/complete"
        return 0
    fi
    
    cd "$SCRIPT_DIR/complete"
    docker build -t "$DOCKER_IMAGE" .
    success "Docker image built successfully"
}

# Execute command locally or remotely
execute_command() {
    local cmd="$1"
    
    if [ "$DRY_RUN" = true ]; then
        if [ "$LOCAL_DEPLOY" = true ]; then
            log "DRY RUN: Would execute locally: $cmd"
        else
            log "DRY RUN: Would execute on $DEPLOY_SERVER: $cmd"
        fi
        return 0
    fi
    
    if [ "$LOCAL_DEPLOY" = true ]; then
        eval "$cmd"
    else
        ssh -p "$SSH_PORT" "${SSH_USER}@${DEPLOY_SERVER}" "$cmd"
    fi
}

# Deploy application
deploy_app() {
    log "Starting deployment of $DOCKER_IMAGE"
    
    # Stop existing container
    log "Stopping existing container (if running)..."
    execute_command "docker stop $CONTAINER_NAME || true"
    execute_command "docker rm $CONTAINER_NAME || true"
    
    # Pull/load image if not building locally
    if [ "$BUILD_IMAGE" = false ] && [ "$LOCAL_DEPLOY" = false ]; then
        log "Pulling Docker image on remote server..."
        execute_command "docker pull $DOCKER_IMAGE"
    elif [ "$BUILD_IMAGE" = false ] && [ "$LOCAL_DEPLOY" = true ]; then
        log "Using local Docker image: $DOCKER_IMAGE"
    fi
    
    # Run new container
    log "Starting new container..."
    local run_cmd="docker run -d \
        --name $CONTAINER_NAME \
        --restart unless-stopped \
        -p $APP_PORT:777 \
        -e SPRING_PROFILES_ACTIVE=production \
        $DOCKER_IMAGE"
    
    execute_command "$run_cmd"
    
    if [ "$DRY_RUN" = false ]; then
        success "Container started successfully"
        
        # Wait for service to start
        log "Waiting for service to start..."
        sleep 30
    fi
}

# Health check
health_check() {
    if [ "$SKIP_HEALTH_CHECK" = true ]; then
        warning "Skipping health check"
        return 0
    fi
    
    log "Performing health check..."
    
    local health_cmd="curl -f http://localhost:$APP_PORT/greeting"
    
    if [ "$DRY_RUN" = true ]; then
        log "DRY RUN: Would perform health check with: $health_cmd"
        return 0
    fi
    
    local max_attempts=5
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        log "Health check attempt $attempt/$max_attempts"
        
        if execute_command "$health_cmd" > /dev/null 2>&1; then
            success "Health check passed - service is running!"
            return 0
        fi
        
        if [ $attempt -lt $max_attempts ]; then
            warning "Health check failed, retrying in 10 seconds..."
            sleep 10
        fi
        
        ((attempt++))
    done
    
    error "Health check failed after $max_attempts attempts"
    return 1
}

# Get service status
get_status() {
    log "Getting service status..."
    
    if [ "$DRY_RUN" = true ]; then
        log "DRY RUN: Would check service status"
        return 0
    fi
    
    execute_command "docker ps | grep $CONTAINER_NAME || echo 'Container not running'"
    execute_command "curl -s http://localhost:$APP_PORT/greeting || echo 'Service not responding'"
}

# Main deployment function
main() {
    log "GS Rest Service Deployment Script Starting..."
    
    parse_args "$@"
    set_defaults
    validate_config
    
    # Print configuration
    log "Deployment Configuration:"
    log "  Docker Image: $DOCKER_IMAGE"
    log "  Container Name: $CONTAINER_NAME"
    log "  Application Port: $APP_PORT"
    log "  Local Deploy: $LOCAL_DEPLOY"
    log "  Build Image: $BUILD_IMAGE"
    log "  Dry Run: $DRY_RUN"
    
    if [ "$LOCAL_DEPLOY" = false ]; then
        log "  Deploy Server: $DEPLOY_SERVER"
        log "  SSH User: $SSH_USER"
        log "  SSH Port: $SSH_PORT"
    fi
    
    # Build image if requested
    if [ "$BUILD_IMAGE" = true ]; then
        build_image
    fi
    
    # Deploy application
    deploy_app
    
    # Health check
    health_check
    
    # Show final status
    get_status
    
    success "Deployment completed successfully!"
    log "Service should be available at:"
    if [ "$LOCAL_DEPLOY" = true ]; then
        log "  http://localhost:$APP_PORT/greeting"
    else
        log "  http://$DEPLOY_SERVER:$APP_PORT/greeting"
    fi
}

# Run main function with all arguments
main "$@"
