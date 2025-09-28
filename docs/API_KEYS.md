# API Keys Guide

## Overview

TuneTrail uses API keys for authentication and access control. Each API key can have specific scopes, rate limits, and expiration dates.

## Creating an API Key

### Via Dashboard

1. Log in to your TuneTrail account
2. Navigate to **Settings** → **API Keys**
3. Click **Create New API Key**
4. Configure:
   - **Name**: Descriptive name (e.g., "Production API", "Development")
   - **Environment**: development, staging, or production
   - **Scopes**: Select permissions needed
   - **Rate Limits**: Configure based on your plan
   - **Expiration**: Optional expiration date

### Via API

```bash
curl -X POST https://api.tunetrail.dev/api-keys \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production API",
    "environment": "production",
    "scopes": ["read:tracks", "read:recommendations"],
    "expires_in_days": 90
  }'
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "api_key": "tt_AbCdEfGhIjKlMnOpQrStUvWxYz123456",
  "name": "Production API",
  "key_prefix": "tt_AbCdEfGh",
  "scopes": ["read:tracks", "read:recommendations"],
  "environment": "production",
  "rate_limit_requests_per_minute": 60,
  "rate_limit_requests_per_hour": 1000,
  "rate_limit_requests_per_day": 10000,
  "created_at": "2025-09-27T10:00:00Z",
  "expires_at": "2025-12-26T10:00:00Z"
}
```

⚠️ **Important**: The full `api_key` is only shown once during creation. Store it securely!

## Using API Keys

### Authentication

Include your API key in the `Authorization` header:

```bash
curl https://api.tunetrail.dev/tracks \
  -H "Authorization: Bearer tt_your_api_key_here"
```

## Available Scopes

### Tracks
- `read:tracks` - Read track information
- `write:tracks` - Create and update tracks
- `delete:tracks` - Delete tracks

### Recommendations
- `read:recommendations` - Get music recommendations

### Playlists
- `read:playlists` - Read playlist information
- `write:playlists` - Create and update playlists
- `delete:playlists` - Delete playlists

### Audio Processing (Starter+)
- `read:audio_features` - Read audio feature analysis
- `write:audio_features` - Process audio and extract features

### ML Models (Pro+)
- `train:models` - Train custom ML models

### Analytics (Pro+)
- `read:analytics` - Access analytics and insights

### Admin (Pro+)
- `admin:webhooks` - Manage webhooks
- `admin:billing` - Access billing information

## Rate Limits

Rate limits vary by plan:

| Plan | Per Minute | Per Hour | Per Day |
|------|-----------|----------|---------|
| **Free** | 10 | 100 | 1,000 |
| **Starter** | 60 | 1,000 | 10,000 |
| **Pro** | 300 | 10,000 | 100,000 |
| **Enterprise** | Custom | Custom | Custom |

### Rate Limit Headers

Every response includes rate limit information:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 2025-09-27T10:05:00Z
```

### Rate Limit Exceeded

When you exceed your rate limit, you'll receive a `429 Too Many Requests` response:

```json
{
  "error": "Rate limit exceeded",
  "window": "minute",
  "reset_at": "2025-09-27T10:05:00Z",
  "rate_limit_info": {
    "minute": {
      "limit": 60,
      "remaining": 0,
      "reset_at": "2025-09-27T10:05:00Z"
    }
  }
}
```

## Managing API Keys

### List All Keys

```bash
curl https://api.tunetrail.dev/api-keys \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Get Key Details

```bash
curl https://api.tunetrail.dev/api-keys/{key_id} \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Update Key

```bash
curl -X PATCH https://api.tunetrail.dev/api-keys/{key_id} \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Name",
    "is_active": true
  }'
```

### Rotate Key

Creates a new key with the same settings and revokes the old one:

```bash
curl -X POST https://api.tunetrail.dev/api-keys/{key_id}/rotate \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Revoke Key

```bash
curl -X POST https://api.tunetrail.dev/api-keys/{key_id}/revoke \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Delete Key

```bash
curl -X DELETE https://api.tunetrail.dev/api-keys/{key_id} \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Usage Analytics

View usage statistics for your API key:

```bash
curl https://api.tunetrail.dev/api-keys/{key_id}/usage?days=7 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response:**
```json
{
  "api_key_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_requests": 5432,
  "successful_requests": 5320,
  "failed_requests": 112,
  "avg_response_time_ms": 145.3,
  "requests_by_endpoint": {
    "/tracks": 3200,
    "/recommendations": 2232
  },
  "requests_by_status_code": {
    "200": 5320,
    "404": 89,
    "500": 23
  },
  "period_start": "2025-09-20T10:00:00Z",
  "period_end": "2025-09-27T10:00:00Z"
}
```

## Security Best Practices

### ✅ Do

- **Store keys securely** - Use environment variables, never commit to git
- **Use separate keys** - Different keys for dev, staging, production
- **Rotate regularly** - Rotate keys every 90 days
- **Scope appropriately** - Only grant necessary permissions
- **Monitor usage** - Track for unexpected activity
- **Set expiration dates** - Use temporary keys when possible
- **Use IP whitelisting** - Restrict keys to known IPs

### ❌ Don't

- **Never commit keys** - Don't put keys in source control
- **Don't share keys** - Each team member should have their own
- **Don't use in client-side code** - Keys expose your account
- **Don't ignore rate limits** - Implement backoff strategies
- **Don't reuse revoked keys** - Create new keys after rotation

## Example: Environment Variables

### .env
```bash
TUNETRAIL_API_KEY=tt_your_production_key_here
TUNETRAIL_API_URL=https://api.tunetrail.dev
```

### Python
```python
import os
from tunetrail import TuneTrail

client = TuneTrail(api_key=os.environ.get("TUNETRAIL_API_KEY"))
tracks = client.tracks.list()
```

### Node.js
```javascript
const TuneTrail = require('tunetrail-sdk');

const client = new TuneTrail({
  apiKey: process.env.TUNETRAIL_API_KEY
});

const tracks = await client.tracks.list();
```

## Troubleshooting

### "Invalid API key"
- Check that your key is active and not expired
- Ensure you're using the correct key format: `tt_...`
- Verify the key hasn't been revoked

### "Insufficient permissions"
- Check that your key has the required scope
- Verify your plan supports the requested feature

### "Rate limit exceeded"
- Wait for the rate limit window to reset
- Implement exponential backoff
- Consider upgrading your plan

## Support

- **Documentation**: https://docs.tunetrail.dev
- **Community**: https://community.tunetrail.dev
- **Email**: support@tunetrail.dev