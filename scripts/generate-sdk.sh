#!/bin/bash
# Generate client SDKs from OpenAPI specification

set -e

echo "🔧 Generating TuneTrail SDKs..."

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create output directories
mkdir -p sdks/python
mkdir -p sdks/typescript
mkdir -p sdks/go

# Start the API server to generate OpenAPI spec
echo "${BLUE}Starting API server to generate OpenAPI spec...${NC}"
cd services/api
uvicorn main:app --host 0.0.0.0 --port 8000 &
API_PID=$!
sleep 5

# Download OpenAPI specification
echo "${BLUE}Downloading OpenAPI specification...${NC}"
curl -s http://localhost:8000/openapi.json > ../../openapi.json

# Kill the API server
kill $API_PID

cd ../..

# Generate Python SDK using openapi-generator
echo "${BLUE}Generating Python SDK...${NC}"
docker run --rm \
  -v ${PWD}:/local \
  openapitools/openapi-generator-cli generate \
  -i /local/openapi.json \
  -g python \
  -o /local/sdks/python \
  --additional-properties=packageName=tunetrail,projectName=tunetrail-sdk,packageVersion=1.0.0

# Generate TypeScript SDK
echo "${BLUE}Generating TypeScript SDK...${NC}"
docker run --rm \
  -v ${PWD}:/local \
  openapitools/openapi-generator-cli generate \
  -i /local/openapi.json \
  -g typescript-axios \
  -o /local/sdks/typescript \
  --additional-properties=npmName=tunetrail-sdk,npmVersion=1.0.0,supportsES6=true

# Generate Go SDK
echo "${BLUE}Generating Go SDK...${NC}"
docker run --rm \
  -v ${PWD}:/local \
  openapitools/openapi-generator-cli generate \
  -i /local/openapi.json \
  -g go \
  -o /local/sdks/go \
  --additional-properties=packageName=tunetrail

echo "${GREEN}✅ SDK generation complete!${NC}"
echo ""
echo "Generated SDKs:"
echo "  - Python:     sdks/python/"
echo "  - TypeScript: sdks/typescript/"
echo "  - Go:         sdks/go/"
echo ""
echo "To publish:"
echo "  Python:     cd sdks/python && python setup.py sdist && twine upload dist/*"
echo "  TypeScript: cd sdks/typescript && npm publish"
echo "  Go:         git tag and push to repository"