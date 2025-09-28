# 🎵 TuneTrail

> **Dual-Model Music Recommendation Platform** - Open Source Community Edition & Commercial SaaS

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Next.js](https://img.shields.io/badge/next.js-15.0-black.svg)](https://nextjs.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.5-red.svg)](https://pytorch.org/)
[![License](https://img.shields.io/badge/license-AGPL%203.0-green.svg)](LICENSE)

TuneTrail is a production-ready music recommendation system combining state-of-the-art machine learning models with a modern, scalable architecture. Built for both self-hosted community use and commercial SaaS deployment.

## ✨ Features

### 🎯 Machine Learning Models
- **Content-Based Filtering**: Librosa + Essentia audio feature extraction
- **Collaborative Filtering**: LightGCN graph neural networks
- **Neural Collaborative Filtering**: Deep learning recommendations (Pro+)
- **Hybrid Models**: Best-of-breed ensemble recommendations

### 🏗️ Architecture
- **FastAPI Backend**: High-performance async Python API
- **Next.js Frontend**: Modern React 19 with TypeScript 5.6
- **PostgreSQL + pgvector**: Vector similarity search at scale
- **Redis**: Caching and task queue
- **Docker**: Containerized microservices

### 🔐 Security & API Management
- **API Key Management**: Scoped permissions, rate limiting, rotation
- **JWT Authentication**: Secure user authentication
- **Multi-tenancy**: Organization-based isolation
- **Rate Limiting**: Token bucket with Redis

### 📊 Editions

| Feature | Community (Free) | Starter ($9/mo) | Pro ($29/mo) | Enterprise ($99+/mo) |
|---------|------------------|------------------|--------------|---------------------|
| Deployment | Self-hosted | Cloud | Cloud | Cloud/On-premise |
| Tracks | Unlimited | 10,000 | 100,000 | Unlimited |
| ML Models | Basic | + Collaborative | + Neural CF | + Custom |
| Support | Community | Email | Priority | Dedicated |

## 🚀 Quick Start

### Prerequisites
- Docker 24.0+
- Docker Compose v2.20+
- 8GB+ RAM
- 50GB+ free disk space

### Installation (5 minutes)

```bash
# Clone the repository
git clone https://github.com/yourusername/tunetrail.git
cd tunetrail

# Copy environment file
cp .env.example .env

# Edit .env with your configuration (optional for dev)
# nano .env

# Start all services
make up
# or: docker-compose up -d

# Check service health
make health
```

### Access Points
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **API (Interactive)**: http://localhost:8000/redoc
- **MinIO Console**: http://localhost:9001

## 📦 Tech Stack

### Backend (Python 3.12+)
- **FastAPI 0.115**: Modern async web framework
- **SQLAlchemy 2.0**: ORM with async support
- **PyTorch 2.5**: Deep learning models
- **PostgreSQL 16 + pgvector**: Vector database
- **Redis 7.4**: Caching & task queue
- **Celery 5.4**: Distributed task processing

### Frontend (Node.js 20 LTS)
- **Next.js 15**: React framework with App Router
- **React 19**: Latest React features
- **TypeScript 5.6**: Type-safe JavaScript
- **TailwindCSS 3.4**: Utility-first CSS
- **Radix UI**: Accessible component primitives

### ML/Audio
- **Librosa 0.10**: Audio feature extraction
- **Essentia 2.1**: Music information retrieval
- **scikit-learn 1.5**: Classical ML algorithms
- **FAISS**: Efficient similarity search

## 🏗️ Project Structure

```
tunetrail/
├── services/
│   ├── api/                 # FastAPI backend ✅
│   │   ├── models/          # SQLAlchemy models
│   │   ├── routers/         # API endpoints
│   │   ├── middleware/      # Auth & rate limiting
│   │   └── tests/           # Unit tests
│   ├── frontend/            # Next.js frontend 🔄
│   ├── ml-engine/           # ML models (coming soon)
│   └── audio-processor/     # Audio features (coming soon)
├── core/                    # Shared Python modules
├── database/
│   ├── migrations/          # SQL migration files
│   └── seeds/               # Sample data
├── docs/                    # Documentation
└── docker-compose.yml       # Service orchestration
```

## 🔧 Development

### Setup Development Environment

```bash
# Use dev compose with hot reload
make dev
# or: docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Watch logs
make logs

# Run tests
make test

# Format code
make format

# Lint code
make lint
```

### Available Commands

```bash
make help          # Show all available commands
make up            # Start all services
make down          # Stop all services
make logs          # View logs
make test          # Run all tests
make lint          # Run linters
make format        # Format code
make docs          # Generate API documentation
make sdk           # Generate client SDKs
make api-docs      # Open interactive API docs
make shell-api     # Open shell in API container
make db-shell      # Open PostgreSQL shell
```

## 📚 Documentation

- [Implementation Guide](IMPLEMENTATION_GUIDE.md) - Complete setup guide
- [API Keys Guide](docs/API_KEYS.md) - API key management
- [Community Portal](docs/COMMUNITY_PORTAL.md) - Portal architecture
- [Automated Docs](docs/AUTOMATED_DOCUMENTATION.md) - Documentation system
- [Documentation Strategy](docs/DOCUMENTATION_STRATEGY.md) - Public vs private docs

## 🎯 Current Status

### ✅ Completed (v0.1.0)
- [x] Project structure and configuration
- [x] Database models (User, Organization, Track, APIKey)
- [x] Authentication system (JWT + API keys)
- [x] API endpoints (auth, tracks, API keys)
- [x] Rate limiting middleware
- [x] Automatic OpenAPI documentation
- [x] Docker Compose setup
- [x] Basic tests

### 🔄 In Progress
- [ ] Frontend implementation
- [ ] ML model integration
- [ ] Audio feature extraction
- [ ] Community portal

### 📋 Roadmap
- [ ] V0.2: ML models integration
- [ ] V0.3: Audio processing pipeline
- [ ] V0.4: Frontend MVP
- [ ] V1.0: Production-ready release

## 🧪 Testing

```bash
# Run all tests
make test

# Run specific test file
docker-compose exec api pytest tests/test_main.py

# Run with coverage
docker-compose exec api pytest --cov=. --cov-report=html
```

## 📖 API Documentation

### Interactive Docs
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Example API Calls

```bash
# Register a new user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123",
    "username": "musiclover"
  }'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }'

# Create a track (requires auth token)
curl -X POST http://localhost:8000/api/v1/tracks \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Bohemian Rhapsody",
    "artist": "Queen",
    "album": "A Night at the Opera",
    "duration_seconds": 354
  }'
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](docs/CONTRIBUTING.md) for details.

```bash
# Fork the repo, create a branch
git checkout -b feature/amazing-feature

# Make changes, run tests
make test

# Format and lint
make format
make lint

# Commit with conventional commits
git commit -m "feat: add amazing feature"

# Push and create PR
git push origin feature/amazing-feature
```

## 📄 License

TuneTrail is dual-licensed:
- **Community Edition**: AGPL-3.0 (open source, self-hosted)
- **Commercial License**: Proprietary (SaaS & enterprise)

See [LICENSE](LICENSE) for details.

## 💬 Support

- **Community**: [GitHub Discussions](https://github.com/yourusername/tunetrail/discussions)
- **Issues**: [GitHub Issues](https://github.com/yourusername/tunetrail/issues)
- **Discord**: [Join our community](https://discord.gg/tunetrail)
- **Email**: support@tunetrail.dev

## 🙏 Acknowledgments

Built with ❤️ using:
- [FastAPI](https://fastapi.tiangolo.com/)
- [Next.js](https://nextjs.org/)
- [PyTorch](https://pytorch.org/)
- [PostgreSQL](https://www.postgresql.org/)
- [SQLAlchemy](https://www.sqlalchemy.org/)

---

**[Website](https://tunetrail.app)** • **[Documentation](https://docs.tunetrail.dev)** • **[Twitter](https://twitter.com/tunetrail)**

Made with 🎵 by the TuneTrail Team