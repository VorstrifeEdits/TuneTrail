#!/bin/bash

# TuneTrail Commercial Edition Database Management
# This script helps set up Alembic migrations for commercial deployments

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
API_DIR="$PROJECT_ROOT/services/api"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

print_section() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

print_step() {
    echo -e "${YELLOW}🔄 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if we're in commercial mode
check_commercial_mode() {
    if [[ "${EDITION:-}" != "commercial" && "${EDITION:-}" != "saas" && "${EDITION:-}" != "enterprise" ]]; then
        print_error "This script is for commercial edition only"
        echo "Set EDITION=commercial (or saas/enterprise) in your environment"
        exit 1
    fi
}

# Install Alembic if not present
install_alembic() {
    print_step "Checking Alembic installation..."

    cd "$API_DIR"
    if ! pip show alembic >/dev/null 2>&1; then
        print_step "Installing Alembic..."
        pip install alembic
        print_success "Alembic installed"
    else
        print_success "Alembic already installed"
    fi
}

# Generate initial migration from current models
generate_initial_migration() {
    print_step "Generating initial migration from current models..."

    cd "$API_DIR/migrations"

    # Check if there are already migrations
    if ls versions/*.py >/dev/null 2>&1; then
        echo "Migrations already exist:"
        ls -la versions/
        echo ""
        read -p "Generate new migration anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_success "Skipping migration generation"
            return
        fi
    fi

    # Generate the migration
    alembic revision --autogenerate -m "Initial TuneTrail schema"
    print_success "Initial migration generated"
}

# Apply migrations
apply_migrations() {
    print_step "Applying migrations to database..."

    cd "$API_DIR/migrations"
    alembic upgrade head
    print_success "Migrations applied successfully"
}

# Show migration status
show_status() {
    print_step "Current migration status:"

    cd "$API_DIR/migrations"
    alembic current
    echo ""
    alembic history --verbose
}

# Main execution
main() {
    print_section "TuneTrail Commercial Edition Database Setup"

    check_commercial_mode
    install_alembic

    case "${1:-setup}" in
        "setup")
            generate_initial_migration
            apply_migrations
            show_status
            ;;
        "migrate")
            apply_migrations
            show_status
            ;;
        "status")
            show_status
            ;;
        "generate")
            shift
            message="${1:-Auto-generated migration}"
            cd "$API_DIR/migrations"
            alembic revision --autogenerate -m "$message"
            ;;
        *)
            echo "Usage: $0 [setup|migrate|status|generate]"
            echo ""
            echo "Commands:"
            echo "  setup     - Initial setup (generate + apply migrations)"
            echo "  migrate   - Apply pending migrations"
            echo "  status    - Show current migration status"
            echo "  generate  - Generate new migration from model changes"
            exit 1
            ;;
    esac

    print_success "Commercial edition database management completed"
}

main "$@"