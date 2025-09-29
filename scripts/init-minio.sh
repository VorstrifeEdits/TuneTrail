#!/bin/bash
set -e

# TuneTrail MinIO Initialization Script
# This script sets up MinIO buckets and policies for TuneTrail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration from environment variables
MINIO_ENDPOINT="${S3_ENDPOINT:-http://localhost:9000}"
MINIO_ACCESS_KEY="${S3_ACCESS_KEY:-minioadmin}"
MINIO_SECRET_KEY="${S3_SECRET_KEY:-minio_dev_password_2025}"
MINIO_REGION="${S3_REGION:-us-east-1}"

# Required buckets for TuneTrail
BUCKETS=(
    "audio-files"      # User uploaded audio files
    "user-uploads"     # Profile pictures, artwork, etc.
    "model-artifacts"  # ML model files and training data
    "cache"           # Temporary and cache files
)

echo -e "${BLUE}🪣 TuneTrail MinIO Setup${NC}"
echo -e "${BLUE}======================\n${NC}"

echo -e "${YELLOW}📊 Configuration:${NC}"
echo -e "  Endpoint: ${MINIO_ENDPOINT}"
echo -e "  Access Key: ${MINIO_ACCESS_KEY}"
echo -e "  Region: ${MINIO_REGION}"
echo ""

# Function to wait for MinIO to be ready
wait_for_minio() {
    echo -e "${YELLOW}🔄 Waiting for MinIO to be ready...${NC}"
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -s "${MINIO_ENDPOINT}/minio/health/ready" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ MinIO is ready${NC}"
            return 0
        fi

        echo -e "${YELLOW}   Attempt ${attempt}/${max_attempts} - MinIO not ready yet...${NC}"
        sleep 2
        ((attempt++))
    done

    echo -e "${RED}❌ MinIO failed to become ready after ${max_attempts} attempts${NC}"
    return 1
}

# Function to configure mc client
configure_mc() {
    echo -e "${YELLOW}🔧 Configuring MinIO client...${NC}"

    # Remove existing alias if it exists
    mc alias remove tunetrail-local 2>/dev/null || true

    # Add new alias
    mc alias set tunetrail-local "${MINIO_ENDPOINT}" "${MINIO_ACCESS_KEY}" "${MINIO_SECRET_KEY}"

    # Test connection
    mc admin info tunetrail-local > /dev/null
    echo -e "${GREEN}✅ MinIO client configured${NC}"
}

# Function to create bucket if it doesn't exist
create_bucket() {
    local bucket_name="$1"

    echo -e "${YELLOW}🔄 Creating bucket: ${bucket_name}...${NC}"

    if mc ls "tunetrail-local/${bucket_name}" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Bucket '${bucket_name}' already exists${NC}"
    else
        mc mb "tunetrail-local/${bucket_name}" --region="${MINIO_REGION}"
        echo -e "${GREEN}✅ Bucket '${bucket_name}' created${NC}"
    fi
}

# Function to set bucket policy
set_bucket_policy() {
    local bucket_name="$1"
    local policy_type="$2"

    echo -e "${YELLOW}🔄 Setting ${policy_type} policy for bucket: ${bucket_name}...${NC}"

    case $policy_type in
        "public-read")
            # Allow public read access for user uploads (profile pictures, etc.)
            mc anonymous set public "tunetrail-local/${bucket_name}"
            ;;
        "private")
            # Private access only for audio files and model artifacts
            mc anonymous set none "tunetrail-local/${bucket_name}"
            ;;
        *)
            echo -e "${RED}❌ Unknown policy type: ${policy_type}${NC}"
            return 1
            ;;
    esac

    echo -e "${GREEN}✅ Policy set for bucket '${bucket_name}'${NC}"
}

# Function to create lifecycle policy for cache bucket
set_lifecycle_policy() {
    local bucket_name="$1"
    local days="$2"

    echo -e "${YELLOW}🔄 Setting lifecycle policy for bucket: ${bucket_name} (${days} days)...${NC}"

    # Create temporary lifecycle policy file
    local policy_file="/tmp/lifecycle-${bucket_name}.json"
    cat > "$policy_file" <<EOF
{
    "Rules": [
        {
            "ID": "DeleteOldCacheFiles",
            "Status": "Enabled",
            "Expiration": {
                "Days": ${days}
            }
        }
    ]
}
EOF

    mc ilm set "tunetrail-local/${bucket_name}" --config "$policy_file"
    rm "$policy_file"

    echo -e "${GREEN}✅ Lifecycle policy set for bucket '${bucket_name}'${NC}"
}

# Main execution
main() {
    # Wait for MinIO to be ready
    if ! wait_for_minio; then
        echo -e "${RED}❌ MinIO setup failed - service not ready${NC}"
        exit 1
    fi

    # Configure mc client
    configure_mc

    echo ""
    echo -e "${BLUE}🪣 Creating buckets...${NC}"

    # Create buckets with appropriate policies
    create_bucket "audio-files"
    set_bucket_policy "audio-files" "private"

    create_bucket "user-uploads"
    set_bucket_policy "user-uploads" "public-read"

    create_bucket "model-artifacts"
    set_bucket_policy "model-artifacts" "private"

    create_bucket "cache"
    set_bucket_policy "cache" "private"
    set_lifecycle_policy "cache" 7  # Delete cache files after 7 days

    echo ""
    echo -e "${GREEN}✅ MinIO setup completed successfully!${NC}"
    echo ""
    echo -e "${BLUE}📊 Summary:${NC}"
    echo -e "  • audio-files: Private bucket for user audio files"
    echo -e "  • user-uploads: Public bucket for profile images, artwork"
    echo -e "  • model-artifacts: Private bucket for ML models and training data"
    echo -e "  • cache: Private bucket with 7-day lifecycle policy"
    echo ""
    echo -e "${BLUE}🌐 Access MinIO Console: ${MINIO_ENDPOINT%:9000}:9001${NC}"
    echo -e "${BLUE}======================\n${NC}"
}

# Run main function
main "$@"