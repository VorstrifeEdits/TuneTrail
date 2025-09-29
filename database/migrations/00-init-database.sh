#!/bin/bash
set -e

# TuneTrail Database Initialization Script
# This script ensures the database and extensions are properly set up
# Runs before SQL migrations in /docker-entrypoint-initdb.d

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 TuneTrail Database Initialization${NC}"
echo -e "${BLUE}=====================================\n${NC}"

# Database configuration from environment
DB_NAME="${POSTGRES_DB:-tunetrail_community}"
DB_USER="${POSTGRES_USER:-tunetrail}"

echo -e "${YELLOW}📊 Configuration:${NC}"
echo -e "  Database: ${DB_NAME}"
echo -e "  User: ${DB_USER}"
echo ""

# Function to run SQL commands
run_sql() {
    local sql="$1"
    local description="$2"
    echo -e "${YELLOW}🔄 ${description}...${NC}"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
        $sql
EOSQL
    echo -e "${GREEN}✅ ${description} completed${NC}"
}

# Verify database exists (created automatically by postgres image from POSTGRES_DB env var)
echo -e "${YELLOW}🔄 Verifying database connection...${NC}"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -c "SELECT current_database(), current_user;" > /dev/null
echo -e "${GREEN}✅ Database connection verified${NC}"

# Enable required extensions
run_sql "
    -- Enable required extensions for TuneTrail
    CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";
    CREATE EXTENSION IF NOT EXISTS \"pgcrypto\";
    CREATE EXTENSION IF NOT EXISTS \"vector\";
" "Installing PostgreSQL extensions (uuid-ossp, pgcrypto, vector)"

# Set up connection permissions
run_sql "
    -- Grant connection permissions
    GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
" "Setting up database permissions"

# Note: Database tables will be created automatically by the API using SQLAlchemy
echo -e "${YELLOW}ℹ️  Database tables will be created by the TuneTrail API on startup${NC}"
echo -e "${YELLOW}   This ensures schema consistency with the application models${NC}"

echo ""
echo -e "${GREEN}✅ TuneTrail database initialization completed successfully!${NC}"
echo -e "${BLUE}=====================================\n${NC}"