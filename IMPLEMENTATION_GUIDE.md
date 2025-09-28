# TuneTrail - Complete Implementation Guide

## 🎵 TuneTrail: Dual-Model Music Recommendation Platform

**Version:** 1.0.0
**Date:** September 2025
**Domains:**
- API/Backend: `api.tunetrail.dev` (SaaS) / `localhost:8000` (Community)
- Frontend: `tunetrail.app` (SaaS) / `localhost:3000` (Community)
- Community Hub: `community.tunetrail.dev`
- Documentation: `docs.tunetrail.dev`

---

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Edition Comparison](#edition-comparison)
3. [Prerequisites](#prerequisites)
4. [Project Structure](#project-structure)
5. [Phase 1: Foundation Setup](#phase-1-foundation-setup)
6. [Phase 2: Database & Core Services](#phase-2-database--core-services)
7. [Phase 3: API Service (FastAPI)](#phase-3-api-service-fastapi)
8. [Phase 4: ML Engine](#phase-4-ml-engine)
9. [Phase 5: Audio Processing Pipeline](#phase-5-audio-processing-pipeline)
10. [Phase 6: Frontend Application](#phase-6-frontend-application)
11. [Phase 7: Authentication & Billing (SaaS)](#phase-7-authentication--billing-saas)
12. [Phase 8: Deployment](#phase-8-deployment)
13. [Phase 9: Monitoring & Maintenance](#phase-9-monitoring--maintenance)
14. [Troubleshooting](#troubleshooting)
15. [Contributing](#contributing)

---

## Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        TuneTrail Platform                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────┐      ┌──────────────────────┐       │
│  │  Community Edition   │      │    SaaS Edition      │       │
│  │  (Self-Hosted)       │      │  (Cloud-Hosted)      │       │
│  └──────────────────────┘      └──────────────────────┘       │
│           │                              │                      │
│           └──────────┬───────────────────┘                     │
│                      │                                          │
│              ┌───────▼────────┐                                │
│              │  Shared Core   │                                │
│              │   Codebase     │                                │
│              └────────────────┘                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Service Architecture

```
Frontend (Next.js)
    ↓
API Gateway (FastAPI)
    ↓
├─→ ML Engine (PyTorch)
│   ├─ Content-Based Filtering
│   ├─ LightGCN (Collaborative)
│   └─ Neural CF (Premium)
│
├─→ Audio Processor (Librosa/Essentia)
│   ├─ Feature Extraction
│   ├─ Embedding Generation
│   └─ Batch Processing
│
├─→ Auth Service (SaaS Only)
│   ├─ User Management
│   ├─ OAuth Integration
│   └─ Stripe Billing
│
└─→ Data Layer
    ├─ PostgreSQL + pgvector
    ├─ Redis Cache
    └─ S3/MinIO Storage
```

---

## Edition Comparison

| Feature | Community (Free) | Starter ($9/mo) | Pro ($29/mo) | Enterprise ($99/mo) |
|---------|-----------------|-----------------|--------------|-------------------|
| **Deployment** | Self-hosted | Cloud (our infra) | Cloud | Cloud or On-premise |
| **Users** | Unlimited | 5 | 25 | Unlimited |
| **Tracks** | Unlimited (local) | 10,000 | 100,000 | Unlimited |
| **ML Models** | Basic Content | + Collaborative | + Neural CF | + Custom Models |
| **API Access** | Local only | 1,000 calls/day | 10,000 calls/day | Unlimited |
| **Audio Analysis** | Unlimited (local) | 100/day | 1,000/day | Unlimited |
| **Batch Processing** | ✅ | ✅ | ✅ | ✅ |
| **Webhooks** | ❌ | ❌ | ✅ | ✅ |
| **Custom Domain** | ✅ | ❌ | ✅ | ✅ |
| **White Label** | ✅ (AGPL) | ❌ | ❌ | ✅ (Commercial) |
| **Support** | Community | Email | Priority | Dedicated |
| **Updates** | Manual | Automatic | Automatic | Automatic |
| **SLA** | None | 99% | 99.5% | 99.9% |

---

## Prerequisites

### System Requirements

**Minimum (Community Edition):**
- RAM: 8GB
- Storage: 50GB free
- CPU: 4 cores
- OS: Ubuntu 22.04 LTS / macOS 14+ / Windows 11 WSL2

**Recommended:**
- RAM: 16GB
- Storage: 100GB SSD
- CPU: 8 cores
- GPU: Optional (for faster ML training)

### Software Requirements

```bash
# Required
Docker 24.0+
Docker Compose v2.20+
Git 2.40+

# Optional but recommended
Node.js 20.x LTS (for frontend development)
Python 3.12+ (for ML development)
PostgreSQL 16 (for local dev without Docker)
```

### Installation Verification

```bash
# Verify Docker
docker --version
docker-compose --version

# Verify system resources
free -h  # Check RAM
df -h    # Check disk space
lscpu    # Check CPU cores
```

---

## Project Structure

```
tunetrail/
├── README.md
├── IMPLEMENTATION_GUIDE.md (this file)
├── LICENSE (Dual: AGPL + Commercial)
├── .gitignore
├── .env.example
├── .env.saas.example
│
├── docker-compose.yml              # Community edition
├── docker-compose.saas.yml         # SaaS edition
├── docker-compose.dev.yml          # Development overrides
│
├── core/                           # Shared core functionality
│   ├── __init__.py
│   ├── models/
│   │   ├── base/                   # Community models
│   │   │   ├── content_based.py
│   │   │   └── collaborative.py
│   │   ├── premium/                # SaaS models
│   │   │   ├── lightgcn.py
│   │   │   └── neural_cf.py
│   │   └── enterprise/             # Enterprise only
│   │       └── custom_trainer.py
│   ├── features/
│   │   ├── audio_features.py
│   │   └── musical_features.py
│   └── utils/
│       ├── config.py
│       └── helpers.py
│
├── services/
│   ├── api/                        # FastAPI Backend
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── routers/
│   │   │   ├── public/            # Community endpoints
│   │   │   │   ├── auth.py
│   │   │   │   ├── tracks.py
│   │   │   │   ├── recommendations.py
│   │   │   │   └── playlists.py
│   │   │   ├── premium/           # SaaS endpoints
│   │   │   │   ├── advanced_ml.py
│   │   │   │   ├── batch_processing.py
│   │   │   │   └── webhooks.py
│   │   │   └── admin/             # Admin panel
│   │   │       ├── dashboard.py
│   │   │       ├── billing.py
│   │   │       └── users.py
│   │   ├── middleware/
│   │   │   ├── auth.py
│   │   │   ├── tenant.py
│   │   │   └── usage.py
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── track.py
│   │   │   └── organization.py
│   │   └── utils/
│   │       ├── features.py
│   │       └── cache.py
│   │
│   ├── ml-engine/                  # ML Processing
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── engine.py
│   │   ├── models/
│   │   │   ├── base/
│   │   │   ├── premium/
│   │   │   └── enterprise/
│   │   └── utils/
│   │       ├── feature_extractor.py
│   │       └── model_selector.py
│   │
│   ├── audio-processor/            # Audio Analysis
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── processor.py
│   │   ├── extractors/
│   │   │   ├── librosa_features.py
│   │   │   ├── essentia_features.py
│   │   │   └── audio_embeddings.py
│   │   └── utils/
│   │       └── batch_processor.py
│   │
│   ├── frontend/                   # Next.js Frontend
│   │   ├── Dockerfile
│   │   ├── package.json
│   │   ├── next.config.js
│   │   ├── tsconfig.json
│   │   ├── tailwind.config.js
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── layout.tsx
│   │   │   │   ├── page.tsx
│   │   │   │   └── (auth)/
│   │   │   ├── components/
│   │   │   │   ├── shared/        # Both editions
│   │   │   │   ├── premium/       # SaaS only
│   │   │   │   └── admin/         # Admin UI
│   │   │   ├── hooks/
│   │   │   │   ├── useAuth.ts
│   │   │   │   ├── useFeatures.ts
│   │   │   │   └── useRecommendations.ts
│   │   │   ├── lib/
│   │   │   │   ├── api.ts
│   │   │   │   └── utils.ts
│   │   │   └── config/
│   │   │       └── features.ts
│   │   └── public/
│   │
│   ├── auth-service/               # SaaS Only
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── main.py
│   │   ├── stripe_handler.py
│   │   └── oauth_providers.py
│   │
│   └── usage-tracker/              # SaaS Only
│       ├── Dockerfile
│       ├── requirements.txt
│       ├── tracker.py
│       ├── limits.py
│       └── billing.py
│
├── database/
│   ├── migrations/
│   │   ├── 001_init.sql
│   │   ├── 002_multi_tenant.sql
│   │   └── 003_usage_tracking.sql
│   └── seeds/
│       └── sample_data.sql
│
├── deployment/
│   ├── community/
│   │   ├── docker/
│   │   │   └── docker-compose.community.yml
│   │   ├── kubernetes/
│   │   │   └── k8s-manifests/
│   │   └── raspberry-pi/
│   │       └── README.md
│   └── saas/
│       ├── terraform/
│       │   ├── main.tf
│       │   └── variables.tf
│       ├── kubernetes/
│       │   └── k8s-production/
│       └── monitoring/
│           ├── prometheus.yml
│           └── grafana-dashboards/
│
├── scripts/
│   ├── setup-community.sh
│   ├── setup-dev.sh
│   ├── deploy-saas.sh
│   ├── migrate-db.sh
│   ├── test-all.sh
│   └── backup.sh
│
├── docs/
│   ├── API.md
│   ├── ML_MODELS.md
│   ├── DEPLOYMENT.md
│   ├── CONTRIBUTING.md
│   └── ARCHITECTURE.md
│
└── volumes/                        # Docker volumes (gitignored)
    ├── postgres_data/
    ├── redis_data/
    ├── minio_data/
    ├── model_cache/
    └── audio_features/
```

---

## Phase 1: Foundation Setup

### Step 1.1: Environment Configuration

**Community Edition** (`.env.example`):

```env
# TuneTrail Community Edition Configuration
# Copy this file to .env and update values

#============================================
# EDITION SETTINGS
#============================================
EDITION=community
ENVIRONMENT=development
DEBUG=true

#============================================
# DATABASE (PostgreSQL + pgvector)
#============================================
POSTGRES_USER=tunetrail
POSTGRES_PASSWORD=change_me_secure_password_123
POSTGRES_DB=tunetrail_community
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}

#============================================
# REDIS CACHE
#============================================
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=change_me_redis_password
REDIS_URL=redis://:${REDIS_PASSWORD}@${REDIS_HOST}:${REDIS_PORT}/0

#============================================
# SECURITY
#============================================
# Generate with: openssl rand -hex 32
JWT_SECRET=your_jwt_secret_minimum_32_characters_long
API_KEY=your_api_key_for_internal_services

#============================================
# ML CONFIGURATION
#============================================
MODEL_TIER=basic              # basic, premium, enterprise
MAX_WORKERS=4
ENABLE_GPU=false
TORCH_HOME=/models
MODEL_CACHE_DIR=/models

#============================================
# AUDIO PROCESSING
#============================================
FEATURE_EXTRACTION_BATCH_SIZE=100
AUDIO_SAMPLE_RATE=22050
MAX_AUDIO_LENGTH_SECONDS=600

#============================================
# STORAGE (Local/MinIO)
#============================================
STORAGE_TYPE=minio
S3_ENDPOINT=http://minio:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=change_me_minio_password
S3_BUCKET=tunetrail-audio
S3_REGION=us-east-1

#============================================
# CELERY TASK QUEUE
#============================================
CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@redis:6379/1
CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD}@redis:6379/2
CELERY_TASK_SERIALIZER=json
CELERY_RESULT_SERIALIZER=json

#============================================
# FRONTEND
#============================================
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
NEXT_PUBLIC_EDITION=community

#============================================
# MONITORING (Optional)
#============================================
ENABLE_TELEMETRY=false
SENTRY_DSN=
PROMETHEUS_PORT=9090

#============================================
# COMMUNITY FEATURES
#============================================
ENABLE_USER_REGISTRATION=true
ENABLE_MODEL_SHARING=true
ENABLE_FEDERATION=false
MAX_TRACK_UPLOAD_SIZE_MB=100
```

**SaaS Edition** (`.env.saas.example`):

```env
# TuneTrail SaaS Edition Configuration
# This is for production deployment only

#============================================
# EDITION SETTINGS
#============================================
EDITION=saas
ENVIRONMENT=production
DEBUG=false

#============================================
# DATABASE (Managed PostgreSQL)
#============================================
DATABASE_URL=postgresql://user:pass@db.tunetrail.dev:5432/tunetrail_saas?sslmode=require
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

#============================================
# REDIS (Managed Redis Cluster)
#============================================
REDIS_URL=rediss://redis.tunetrail.dev:6380/0?ssl_cert_reqs=required
REDIS_CLUSTER_MODE=true

#============================================
# SECURITY
#============================================
JWT_SECRET=production_secret_minimum_64_characters_long_and_very_secure
API_KEY=production_api_key_for_internal_services
ENCRYPTION_KEY=production_encryption_key_for_sensitive_data

#============================================
# AUTHENTICATION (Auth0/OAuth)
#============================================
AUTH0_DOMAIN=tunetrail.auth0.com
AUTH0_CLIENT_ID=your_auth0_client_id
AUTH0_CLIENT_SECRET=your_auth0_client_secret
AUTH0_AUDIENCE=https://api.tunetrail.dev

# Social OAuth
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret

#============================================
# STRIPE BILLING
#============================================
STRIPE_PUBLIC_KEY=pk_live_xxxxx
STRIPE_SECRET_KEY=sk_live_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx
STRIPE_PRICE_ID_STARTER=price_xxxxx
STRIPE_PRICE_ID_PRO=price_xxxxx
STRIPE_PRICE_ID_ENTERPRISE=price_xxxxx

#============================================
# ML CONFIGURATION
#============================================
MODEL_TIER=premium
MAX_WORKERS=8
ENABLE_GPU=true
GPU_INSTANCES=4
MODEL_CACHE_DIR=/mnt/models

#============================================
# STORAGE (AWS S3)
#============================================
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
S3_BUCKET=tunetrail-audio-production
CLOUDFRONT_URL=https://cdn.tunetrail.dev

#============================================
# RATE LIMITING & USAGE
#============================================
RATE_LIMIT_ENABLED=true
DEFAULT_RATE_LIMIT=100/hour
USAGE_TRACKING_ENABLED=true
BILLING_ENABLED=true

#============================================
# MONITORING & OBSERVABILITY
#============================================
SENTRY_DSN=https://xxxxx@sentry.io/xxxxx
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1

DATADOG_API_KEY=your_datadog_api_key
DATADOG_APP_KEY=your_datadog_app_key

POSTHOG_API_KEY=your_posthog_api_key
POSTHOG_HOST=https://app.posthog.com

#============================================
# FEATURE FLAGS
#============================================
LAUNCHDARKLY_SDK_KEY=sdk-xxxxx
ENABLE_FEATURE_FLAGS=true

#============================================
# EMAIL (SendGrid/AWS SES)
#============================================
SENDGRID_API_KEY=SG.xxxxx
FROM_EMAIL=noreply@tunetrail.app
SUPPORT_EMAIL=support@tunetrail.app

#============================================
# WEBHOOKS
#============================================
WEBHOOK_SECRET=your_webhook_signing_secret
WEBHOOK_TIMEOUT_SECONDS=30
```

### Step 1.2: Docker Compose Files

The implementation continues with detailed docker-compose configurations, database schemas, service implementations, and deployment strategies.

[Content continues for all phases...]

---

## Quick Start

### Community Edition (5 minutes)

```bash
# 1. Clone and setup
git clone https://github.com/yourusername/tunetrail.git
cd tunetrail

# 2. Copy and configure environment
cp .env.example .env
# Edit .env with your preferred editor

# 3. Run setup script
chmod +x scripts/setup-community.sh
./scripts/setup-community.sh

# 4. Access TuneTrail
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/api/docs
# MinIO Console: http://localhost:9001
```

### Development Setup

```bash
# Use development compose file with hot reload
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Watch logs
docker-compose logs -f api ml-engine
```

---

## Next Steps

1. Read the [API Documentation](docs/API.md)
2. Understand [ML Models](docs/ML_MODELS.md)
3. Follow [Deployment Guide](docs/DEPLOYMENT.md)
4. Join our [Community Discord](https://discord.gg/tunetrail)

---

## Support

- **Community Edition**: GitHub Issues, Discord
- **SaaS Users**: support@tunetrail.app
- **Enterprise**: enterprise@tunetrail.app

---

## License

TuneTrail is dual-licensed:
- **Community Edition**: AGPL-3.0 (open source)
- **Commercial License**: For SaaS and proprietary use

See [LICENSE](LICENSE) for details.

---

**Built with ❤️ by the TuneTrail Team**