#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${PURPLE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    Django Master Template                    ║"
echo "║                   Development Setup Script                  ║"
echo "║                     (Docker Compose Mode)                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')] ✅ $1${NC}"
}

log_error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ❌ $1${NC}" >&2
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] ⚠️  $1${NC}"
}

log_step() {
    echo -e "${PURPLE}[$(date +'%H:%M:%S')] 🚀 $1${NC}"
}

log_info() {
    echo -e "${CYAN}[$(date +'%H:%M:%S')] 📍 $1${NC}"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    log_error "Docker is not running. Please start Docker Desktop and try again."
    exit 1
fi

log_success "Docker is running"

# Check if docker-compose is available
if ! command -v docker-compose > /dev/null 2>&1; then
    log_error "docker-compose is not installed. Please install Docker Compose and try again."
    exit 1
fi

log_success "Docker Compose is available"

# Parse command line arguments
FULL_RESET=false
QUIET=false
SKIP_BUILD=false
SETUP_VSCODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --reset)
            FULL_RESET=true
            shift
            ;;
        --quiet)
            QUIET=true
            shift
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --vscode)
            SETUP_VSCODE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --reset       Full reset: remove all containers, volumes, and images"
            echo "  --quiet       Quiet mode: minimal output"
            echo "  --skip-build  Skip Docker build step (use existing images)"
            echo "  --vscode      Show VS Code setup instructions"
            echo "  --help, -h    Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Full reset if requested
if [ "$FULL_RESET" = true ]; then
    log_step "Performing full reset..."

    log "Stopping all containers..."
    docker-compose down -v --remove-orphans

    log "Removing project volumes..."
    docker volume rm master-tamplate_postgres_data master-tamplate_static_volume master-tamplate_media_volume 2>/dev/null || true

    log "Removing project images..."
    docker images | grep master-tamplate | awk '{print $3}' | xargs docker rmi -f 2>/dev/null || true

    log "Pruning Docker system..."
    docker system prune -f

    log_success "Full reset completed"
else
    log_step "Stopping existing containers..."
    docker-compose down
fi

# Build images
if [ "$SKIP_BUILD" != true ]; then
    log_step "Building Docker images (this may take a few minutes)..."
    docker-compose build --no-cache
    log_success "Docker images built successfully"
else
    log_warning "Skipping build step as requested"
fi

# Start services
log_step "Starting services..."
docker-compose up -d

# Wait for services to be healthy
log_step "Waiting for services to be ready..."

max_attempts=90
attempt=0

while [ $attempt -lt $max_attempts ]; do
    # Check if web service is responding
    if curl -f http://localhost:8000/admin/login/ > /dev/null 2>&1; then
        break
    fi

    # Check for common error patterns
    if docker-compose logs web 2>/dev/null | grep -q "Syntax error"; then
        log_error "Shell syntax error detected in web container"
        docker-compose logs --tail=10 web
        exit 1
    fi

    if docker-compose logs web 2>/dev/null | grep -q "Permission denied"; then
        log_error "Permission error detected in web container"
        docker-compose logs --tail=10 web
        exit 1
    fi

    attempt=$((attempt + 1))
    if [ $((attempt % 15)) -eq 0 ]; then
        log "Still waiting for services... (attempt $attempt/$max_attempts)"
        log "Checking container status:"
        docker-compose ps
    fi
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    log_error "Services failed to start within expected time. Checking logs..."
    echo ""
    log "=== Container Status ==="
    docker-compose ps
    echo ""
    log "=== Web Container Logs ==="
    docker-compose logs --tail=20 web
    echo ""
    log "=== Database Container Logs ==="
    docker-compose logs --tail=10 db
    exit 1
fi

log_success "All services are ready!"

# Show service status
log_step "Service Status:"
docker-compose ps

echo -e "\n${GREEN}🎉 Development environment is ready!${NC}\n"

echo -e "${YELLOW}📍 Access Points:${NC}"
echo -e "   🌐 Django App:      http://localhost:8000"
echo -e "   🔐 Admin Panel:     http://localhost:8000/admin/"
echo -e "   📚 API Docs:        http://localhost:8000/api/docs/"
echo -e "   🗄️  PostgreSQL:      localhost:5432"
echo -e "   🔴 Redis:           localhost:6379"

echo -e "\n${YELLOW}🔑 Default Credentials:${NC}"
echo -e "   Username: admin"
echo -e "   Password: admin123"

echo -e "\n${YELLOW}📋 Useful Commands:${NC}"
echo -e "   📊 View logs:         docker-compose logs -f"
echo -e "   🔧 Django shell:      docker-compose exec web python manage.py shell"
echo -e "   🧪 Run tests:         docker-compose exec web pytest"
echo -e "   🔄 Restart web:       docker-compose restart web"
echo -e "   ⏹️  Stop services:     docker-compose stop"
echo -e "   🗑️  Full cleanup:      $0 --reset"

# VS Code setup information
if [ "$SETUP_VSCODE" = true ] || [ -d ".vscode" ]; then
    echo -e "\n${CYAN}💻 VS Code Setup:${NC}"
    echo -e "   1. Install recommended extensions (VS Code will prompt)"
    echo -e "   2. Configure Python interpreter: Ctrl+Shift+P > Python: Select Interpreter"
    echo -e "   3. Use path: /usr/local/bin/python"
    echo -e "   4. See docs/VSCODE_SETUP.md for detailed instructions"

    if command -v code > /dev/null 2>&1; then
        echo -e "   🚀 Quick setup: code . (opens project in VS Code)"
    fi
fi

if [ "$QUIET" != true ]; then
    echo -e "\n${BLUE}💡 Pro Tips:${NC}"
    echo -e "   - Run 'docker-compose logs -f web' to see Django logs in real-time"
    echo -e "   - Use 'docker-compose exec web bash' to enter the container"
    echo -e "   - Check docs/DOCKER.md for troubleshooting tips"
    echo -e "   - Check docs/VSCODE_SETUP.md for VS Code configuration\n"
fi
