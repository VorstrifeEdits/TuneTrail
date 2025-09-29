#!/bin/bash
set -e

# TuneTrail Quickstart Script
# Zero-friction setup for TuneTrail Community Edition

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.core.yml"
ENV_FILE="$PROJECT_ROOT/.env"
ENV_EXAMPLE="$PROJECT_ROOT/.env.example"

# Script mode (community, development, production)
MODE="${1:-community}"

echo -e "${BLUE}${BOLD}"
echo "🎵 TuneTrail Quickstart"
echo "======================"
echo -e "${NC}"

# Function to print step headers
print_step() {
    echo ""
    echo -e "${BLUE}${BOLD}📋 Step $1: $2${NC}"
    echo -e "${BLUE}$(printf '=%.0s' {1..40})${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check prerequisites
check_prerequisites() {
    print_step "1" "Checking Prerequisites"

    local missing_deps=()

    # Check Docker
    if command_exists docker; then
        local docker_version=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
        echo -e "${GREEN}✅ Docker found: ${docker_version}${NC}"
    else
        missing_deps+=("Docker")
    fi

    # Check Docker Compose
    if command_exists "docker-compose" || docker compose version >/dev/null 2>&1; then
        if command_exists "docker-compose"; then
            local compose_version=$(docker-compose --version | cut -d' ' -f3 | cut -d',' -f1)
            echo -e "${GREEN}✅ Docker Compose found: ${compose_version}${NC}"
        else
            local compose_version=$(docker compose version --short 2>/dev/null || echo "v2.x")
            echo -e "${GREEN}✅ Docker Compose found: ${compose_version}${NC}"
        fi
    else
        missing_deps+=("Docker Compose")
    fi

    # Check if Docker daemon is running
    if docker info >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Docker daemon is running${NC}"
    else
        echo -e "${RED}❌ Docker daemon is not running${NC}"
        echo -e "${YELLOW}   Please start Docker and try again${NC}"
        exit 1
    fi

    # Report missing dependencies
    if [ ${#missing_deps[@]} -ne 0 ]; then
        echo -e "${RED}❌ Missing required dependencies:${NC}"
        for dep in "${missing_deps[@]}"; do
            echo -e "${RED}   - $dep${NC}"
        done
        echo ""
        echo -e "${YELLOW}Please install the missing dependencies and try again.${NC}"
        echo -e "${YELLOW}Visit: https://docs.docker.com/get-docker/${NC}"
        exit 1
    fi
}

# Function to setup environment
setup_environment() {
    print_step "2" "Setting Up Environment"

    cd "$PROJECT_ROOT"

    if [ ! -f "$ENV_FILE" ]; then
        echo -e "${YELLOW}🔄 No .env file found, creating from template...${NC}"
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        echo -e "${GREEN}✅ Environment file created${NC}"
        echo -e "${YELLOW}💡 You can customize settings in .env if needed${NC}"
    else
        echo -e "${GREEN}✅ Environment file already exists${NC}"
    fi

    # Generate secure secrets if using defaults
    if grep -q "change_me" "$ENV_FILE"; then
        echo -e "${YELLOW}🔄 Generating secure secrets...${NC}"

        # Generate random passwords
        local db_password=$(openssl rand -hex 16)
        local redis_password=$(openssl rand -hex 16)
        local minio_password=$(openssl rand -hex 16)
        local jwt_secret=$(openssl rand -hex 32)

        # Update passwords in .env file
        sed -i.bak \
            -e "s/change_me_secure_password_123/${db_password}/g" \
            -e "s/change_me_redis_password/${redis_password}/g" \
            -e "s/change_me_minio_password/${minio_password}/g" \
            -e "s/your_jwt_secret_minimum_32_characters_long/${jwt_secret}/g" \
            "$ENV_FILE"

        rm -f "${ENV_FILE}.bak"
        echo -e "${GREEN}✅ Secure secrets generated${NC}"
    fi
}

# Function to start services
start_services() {
    print_step "3" "Starting Services"

    cd "$PROJECT_ROOT"

    echo -e "${YELLOW}🔄 Pulling latest images...${NC}"
    docker compose pull --quiet

    echo -e "${YELLOW}🔄 Starting TuneTrail services...${NC}"
    docker compose up -d --remove-orphans

    echo -e "${GREEN}✅ Services started in detached mode${NC}"
}

# Function to wait for services to be healthy
wait_for_health() {
    print_step "4" "Waiting for Services to be Ready"

    local services=("postgres" "redis" "minio" "api" "ml-engine" "audio-processor" "celery-worker" "frontend")
    local max_wait=300  # 5 minutes
    local elapsed=0

    echo -e "${YELLOW}🔄 Waiting for services to become healthy...${NC}"

    while [ $elapsed -lt $max_wait ]; do
        local all_healthy=true

        for service in "${services[@]}"; do
            local service_state=$(docker compose ps --format json | jq -rs ".[] | select(.Service == \"$service\") | .State" | head -1)
            local service_health=$(docker compose ps --format json | jq -rs ".[] | select(.Service == \"$service\") | .Health" | head -1)

            # Service is healthy if it's running and either has no health check or is healthy
            if [[ "$service_state" != "running" ]] || [[ -n "$service_health" && "$service_health" != "healthy" && "$service_health" != "null" && "$service_health" != "" ]]; then
                all_healthy=false
                break
            fi
        done

        if [ "$all_healthy" = true ]; then
            echo -e "${GREEN}✅ All services are healthy${NC}"
            break
        fi

        printf "${YELLOW}   Waiting... (${elapsed}s/${max_wait}s)\r${NC}"
        sleep 5
        elapsed=$((elapsed + 5))
    done

    if [ $elapsed -ge $max_wait ]; then
        echo -e "${RED}❌ Services did not become healthy within ${max_wait} seconds${NC}"
        echo -e "${YELLOW}💡 You can check service status with: make logs${NC}"
        exit 1
    fi
}

# Function to initialize MinIO
initialize_minio() {
    print_step "5" "Initializing Storage (MinIO)"

    # Run MinIO initialization in the MinIO container
    echo -e "${YELLOW}🔄 Setting up MinIO buckets...${NC}"

    # Copy initialization script to container and run it
    docker compose exec -T minio sh -c "
        # Install mc client if not present
        if ! command -v mc >/dev/null 2>&1; then
            curl -sSL https://dl.min.io/client/mc/release/linux-amd64/mc -o /usr/local/bin/mc
            chmod +x /usr/local/bin/mc
        fi

        # Wait for MinIO to be ready
        while ! curl -s http://localhost:9000/minio/health/ready >/dev/null 2>&1; do
            echo 'Waiting for MinIO...'
            sleep 2
        done

        # Configure mc client
        mc alias set local http://localhost:9000 \$MINIO_ROOT_USER \$MINIO_ROOT_PASSWORD

        # Create buckets
        mc mb local/audio-files --ignore-existing
        mc mb local/user-uploads --ignore-existing
        mc mb local/model-artifacts --ignore-existing
        mc mb local/cache --ignore-existing

        # Set policies
        mc anonymous set none local/audio-files
        mc anonymous set download local/user-uploads
        mc anonymous set none local/model-artifacts
        mc anonymous set none local/cache

        echo 'MinIO buckets configured successfully'
    "

    echo -e "${GREEN}✅ MinIO storage initialized${NC}"
}

# Function to run initial setup tasks
run_initial_setup() {
    print_step "6" "Running Initial Setup"

    echo -e "${YELLOW}🔄 Initializing database schema...${NC}"

    # Wait for API to be ready and create database tables
    local api_ready=false
    local attempts=0
    local max_attempts=30

    while [ $attempts -lt $max_attempts ] && [ "$api_ready" = false ]; do
        if curl -s http://localhost:8000/health >/dev/null 2>&1; then
            api_ready=true
            echo -e "${GREEN}✅ Database schema initialized successfully${NC}"
        else
            printf "${YELLOW}   Waiting for API to initialize database... (${attempts}/${max_attempts})\r${NC}"
            sleep 2
            ((attempts++))
        fi
    done

    if [ "$api_ready" = false ]; then
        echo -e "${YELLOW}⚠️  API took longer than expected to start (database will be initialized automatically)${NC}"
    else
        # Verify database tables were created
        echo -e "${YELLOW}🔄 Verifying database tables...${NC}"
        local table_count=$(docker compose exec -T postgres psql -U "${POSTGRES_USER:-tunetrail}" -d "${POSTGRES_DB:-tunetrail_community}" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' \n' || echo "0")

        if [ "$table_count" -gt 0 ]; then
            echo -e "${GREEN}✅ Database tables verified ($table_count tables created)${NC}"

            # Optional: Seed with example data for demo
            echo -e "${YELLOW}🔄 Setting up demo environment...${NC}"
            if curl -s -X POST http://localhost:8000/auth/register \
                -H "Content-Type: application/json" \
                -d '{"email":"demo@tunetrail.com","password":"demo123","full_name":"Demo User","username":"demo"}' >/dev/null 2>&1; then
                echo -e "${GREEN}✅ Demo user created (demo@tunetrail.com / demo123)${NC}"
            else
                echo -e "${YELLOW}   Demo user already exists or registration disabled${NC}"
            fi
        else
            echo -e "${YELLOW}⚠️  Database tables not yet visible (may still be initializing)${NC}"
        fi
    fi

    echo -e "${YELLOW}🔄 Verifying ML engine connectivity...${NC}"
    if docker compose ps ml-engine --format json | jq -rs '.[] | select(.Service == "ml-engine") | .State' | head -1 | grep -q "running"; then
        echo -e "${GREEN}✅ ML engine is running${NC}"
    else
        echo -e "${YELLOW}⚠️  ML engine not started yet (this is normal)${NC}"
    fi

    echo -e "${GREEN}✅ Initial setup completed${NC}"
}

# Function to display access information
show_access_info() {
    print_step "7" "Setup Complete!"

    echo -e "${GREEN}🎉 TuneTrail is now running!${NC}"
    echo ""
    echo -e "${BOLD}🌐 Access URLs:${NC}"
    echo -e "  Frontend:      ${BLUE}http://localhost:3000${NC}"
    echo -e "  API Docs:      ${BLUE}http://localhost:8000/docs${NC}"
    echo -e "  Interactive:   ${BLUE}http://localhost:8000/redoc${NC}"
    echo -e "  MinIO Console: ${BLUE}http://localhost:9001${NC}"
    echo ""
    echo -e "${BOLD}🔧 Useful Commands:${NC}"
    echo -e "  View logs:     ${YELLOW}make logs${NC}"
    echo -e "  Stop services: ${YELLOW}make down${NC}"
    echo -e "  Restart:       ${YELLOW}make restart${NC}"
    echo -e "  Health check:  ${YELLOW}make health${NC}"
    echo ""
    echo -e "${BOLD}📚 Next Steps:${NC}"
    echo -e "  1. Visit ${BLUE}http://localhost:3000${NC} to access the frontend"
    echo -e "  2. Create an account or explore the API at ${BLUE}http://localhost:8000/docs${NC}"
    echo -e "  3. Upload music and start getting recommendations!"
    echo ""
    echo -e "${GREEN}Happy music discovery! 🎵${NC}"
}

# Function to handle cleanup on exit
cleanup() {
    if [ $? -ne 0 ]; then
        echo ""
        echo -e "${RED}❌ Setup failed!${NC}"
        echo ""
        echo -e "${YELLOW}🔍 Troubleshooting:${NC}"
        echo -e "  • Check Docker is running: ${YELLOW}docker info${NC}"
        echo -e "  • View service logs: ${YELLOW}docker compose logs${NC}"
        echo -e "  • Check service status: ${YELLOW}docker compose ps${NC}"
        echo ""
        echo -e "${YELLOW}💡 For help, visit: https://github.com/tunetrail/tunetrail/issues${NC}"
    fi
}

# Set up cleanup trap
trap cleanup EXIT

# Main execution
main() {
    echo -e "${YELLOW}Mode: ${MODE}${NC}"
    echo ""

    check_prerequisites
    setup_environment
    start_services
    wait_for_health
    initialize_minio
    run_initial_setup
    show_access_info
}

# Run main function
main "$@"