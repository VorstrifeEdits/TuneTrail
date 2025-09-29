# 🚀 TuneTrail Quickstart Guide

Get TuneTrail running in 3 commands. Perfect for developers who want to start immediately.

## ⚡ One-Minute Setup

```bash
git clone https://github.com/tunetrail/tunetrail.git
cd tunetrail
make quickstart
```

**Done!** Your music recommendation platform is now running.

## 🎯 What Just Happened?

The `make quickstart` command automatically:

1. **🔍 Checked** Docker and prerequisites
2. **🔧 Generated** secure passwords and configuration
3. **🚀 Started** all 6 services with health monitoring
4. **🗄️ Initialized** PostgreSQL with pgvector extensions
5. **🪣 Created** MinIO storage buckets for files and models
6. **✅ Verified** everything is working correctly

## 🌐 Access Your Platform

| Service | URL | Purpose |
|---------|-----|---------|
| **Frontend** | http://localhost:3000 | Main user interface |
| **API Docs** | http://localhost:8000/docs | Interactive API documentation |
| **Storage Console** | http://localhost:9001 | File storage management |
| **Health Check** | http://localhost:8000/health | System status |

## 🎵 Next Steps

### 1. Create Your First Account
Visit http://localhost:3000 and create an account to start using TuneTrail.

### 2. Explore the API
- Open http://localhost:8000/docs
- Try the authentication endpoints
- Upload your first track
- Get personalized recommendations

### 3. Monitor Your System
```bash
# View real-time logs
make logs

# Check service health
make health

# View running containers
docker compose ps
```

## 🛠️ Useful Commands

```bash
# Start/stop services
make up          # Start all services
make down        # Stop all services
make restart     # Restart everything

# Development
make logs        # View all logs
make logs-api    # View API logs only
make logs-ml     # View ML engine logs

# Database
make db-shell    # Open PostgreSQL shell
make migrate     # Run database migrations

# Maintenance
make clean       # Stop and remove everything
make build       # Rebuild Docker images
```

## 🔧 Customization

### Environment Variables
Edit `.env` to customize:
- Database credentials
- Storage settings
- ML model configuration
- Feature flags

### Development Mode
```bash
# Start with hot reload for development
make dev
```

## 🚨 Troubleshooting

### Services Won't Start
```bash
# Check Docker daemon
docker info

# Check for port conflicts
netstat -tulpn | grep :3000
netstat -tulpn | grep :8000
```

### Database Connection Issues
```bash
# Check PostgreSQL health
docker compose exec postgres pg_isready -U tunetrail

# View database logs
docker compose logs postgres
```

### Storage Issues
```bash
# Check MinIO status
curl http://localhost:9000/minio/health/ready

# Access MinIO console
# URL: http://localhost:9001
# Login: minioadmin / [password from .env]
```

### Need Help?
- 📖 **Full Documentation**: [README.md](../README.md)
- 🏗️ **Production Scaling**: [SCALING.md](SCALING.md)
- 🐛 **Report Issues**: https://github.com/tunetrail/tunetrail/issues
- 💬 **Community**: https://discord.gg/tunetrail

## 🎉 Success!

You now have a fully functional music recommendation platform with:
- ✅ Modern React frontend
- ✅ FastAPI backend with auto-generated docs
- ✅ PostgreSQL database with vector search
- ✅ Redis caching layer
- ✅ S3-compatible storage
- ✅ ML-ready architecture

Start uploading music and discover the power of AI-driven recommendations! 🎵