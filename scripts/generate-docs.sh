#!/bin/bash
# Generate static documentation from OpenAPI spec

set -e

echo "📚 Generating TuneTrail Documentation..."

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Create output directory
mkdir -p docs/api-reference

# Start API server
echo "${BLUE}Starting API server...${NC}"
cd services/api
uvicorn main:app --host 0.0.0.0 --port 8000 &
API_PID=$!
sleep 5

cd ../..

# Download OpenAPI spec
echo "${BLUE}Downloading OpenAPI specification...${NC}"
curl -s http://localhost:8000/openapi.json > openapi.json

# Generate ReDoc static HTML
echo "${BLUE}Generating ReDoc HTML documentation...${NC}"
npx @redocly/cli build-docs openapi.json \
  --output docs/api-reference/index.html \
  --title "TuneTrail API Documentation" \
  --theme.colors.primary.main="#6366f1"

# Generate Swagger UI static HTML
echo "${BLUE}Generating Swagger UI documentation...${NC}"
cat > docs/api-reference/swagger.html <<EOF
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>TuneTrail API - Swagger UI</title>
  <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
  <link rel="icon" type="image/png" href="https://tunetrail.dev/favicon.png" />
  <style>
    html { box-sizing: border-box; overflow: -moz-scrollbars-vertical; overflow-y: scroll; }
    *, *:before, *:after { box-sizing: inherit; }
    body { margin:0; padding:0; }
  </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
  <script>
    window.onload = function() {
      const ui = SwaggerUIBundle({
        url: "/openapi.json",
        dom_id: '#swagger-ui',
        deepLinking: true,
        presets: [
          SwaggerUIBundle.presets.apis,
          SwaggerUIStandalonePreset
        ],
        plugins: [
          SwaggerUIBundle.plugins.DownloadUrl
        ],
        layout: "StandaloneLayout"
      });
      window.ui = ui;
    };
  </script>
</body>
</html>
EOF

# Generate Markdown documentation using widdershins
echo "${BLUE}Generating Markdown documentation...${NC}"
npx widdershins openapi.json \
  --language_tabs 'python:Python' 'javascript:JavaScript' 'shell:cURL' \
  --summary \
  --omitHeader \
  -o docs/api-reference/API.md

# Kill API server
kill $API_PID

echo "${GREEN}✅ Documentation generation complete!${NC}"
echo ""
echo "Generated documentation:"
echo "  - ReDoc HTML:  docs/api-reference/index.html"
echo "  - Swagger UI:  docs/api-reference/swagger.html"
echo "  - Markdown:    docs/api-reference/API.md"
echo "  - OpenAPI:     openapi.json"
echo ""
echo "To view locally:"
echo "  python -m http.server 8080 --directory docs/api-reference"