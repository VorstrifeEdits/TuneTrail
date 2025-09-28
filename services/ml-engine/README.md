# TuneTrail ML Engine

## Overview
Production-ready machine learning recommendation engine for TuneTrail. Implements collaborative filtering, content-based filtering, and deep learning models across three tiers (Free, Starter, Pro).

## Architecture

```
ML Engine (FastAPI Service)
├── Free Tier Models
│   ├── Collaborative Filtering (ALS/Matrix Factorization)
│   ├── Popularity-Based (Trending, Top Tracks)
│   └── Genre-Based (Simple matching)
│
├── Starter Tier Models
│   ├── Content-Based (FAISS audio similarity)
│   ├── Hybrid Simple (CF + Content)
│   └── Daily Mix Generator
│
├── Pro Tier Models
│   ├── Neural Collaborative Filtering (PyTorch)
│   ├── Deep Content Model (Audio embeddings)
│   ├── Hybrid Deep (NCF + Audio)
│   └── Taste Profiler (User analysis)
│
└── Enterprise Tier
    └── Custom Model Training
```

## API Endpoints

### Recommendation Endpoints
- `POST /recommend/user` - Get personalized recommendations
- `POST /recommend/similar` - Find similar tracks
- `POST /daily-mix` - Generate daily mixes (Starter+)
- `POST /radio/generate` - Generate infinite radio
- `POST /taste-profile/{user_id}` - Deep taste analysis (Pro+)

### System Endpoints
- `GET /health` - Health check
- `GET /models/info` - Loaded models info
- `POST /models/reload` - Reload models
- `POST /feedback` - Record user feedback

## Integration with TuneTrail API

The ML Engine is called by `/services/api/routers/public/recommendations.py`:

```python
# API Service → ML Engine
response = httpx.post(
    "http://ml-engine:8001/recommend/user",
    json={
        "user_id": user_id,
        "limit": 20,
        "model_tier": user.plan_tier,
    }
)
```

## Data Flow

```
User Interaction
    ↓
PostgreSQL (interactions table)
    ↓
Nightly Training Pipeline
    ↓
Updated Models
    ↓
ML Engine (FastAPI)
    ↓
Redis Cache
    ↓
API Service
    ↓
Frontend
```

## Model Training

### Quick Start
```bash
# Train all tier models
python scripts/train_all_models.py

# Evaluate models
python scripts/evaluate_models.py

# Build FAISS index
python scripts/build_faiss_index.py
```

### Training Schedule
Models retrain automatically via cron:
- **Free Tier**: Daily at 4am (30 min)
- **Starter Tier**: Daily at 5am (1-2 hours)
- **Pro Tier**: Daily at 7am (2-3 hours)

## Data Requirements

### Minimum Viable Dataset
- **10,000 tracks** with audio features
- **1,000 users** with interaction history
- **50,000 interactions** (plays, likes, skips)

### Production Dataset
- **100,000+ tracks** recommended
- **10,000+ active users**
- **1M+ interactions**

See `datasets/README.md` for data sources.

## Model Performance

### Metrics Tracked
- **Recall@20**: How many relevant tracks in top 20
- **NDCG@20**: Ranking quality
- **MRR**: Mean reciprocal rank
- **CTR**: Click-through rate from impressions

### Expected Performance
| Model | Recall@20 | NDCG@20 | Training Time |
|-------|-----------|---------|---------------|
| Collaborative Filter | 0.15-0.25 | 0.18-0.28 | 10-30 min |
| Content-Based | 0.20-0.30 | 0.22-0.32 | 30-60 min |
| Neural CF | 0.30-0.45 | 0.35-0.50 | 2-3 hours |

## Configuration

### Environment Variables
```bash
DATABASE_URL=postgresql://user:pass@postgres:5432/tunetrail
REDIS_URL=redis://:password@redis:6379/0
MODEL_TIER=basic  # basic, full, or enterprise
ENABLE_GPU=false  # Set to true for GPU acceleration
```

### Model Paths
- `/models/free/` - Free tier models
- `/models/starter/` - Starter tier models
- `/models/pro/` - Pro tier models
- `/models/faiss_indexes/` - FAISS indexes

## Development

### Local Setup
```bash
cd services/ml-engine

# Install dependencies
pip install -r requirements.txt

# Run service
python main.py
```

### Docker
```bash
# Build
docker build -t tunetrail-ml-engine .

# Run
docker run -p 8001:8001 tunetrail-ml-engine
```

### Testing
```bash
pytest tests/

# Specific test
pytest tests/test_collaborative_filter.py
```

## Monitoring

### TensorBoard
```bash
tensorboard --logdir=/models/logs
```

### Metrics Dashboard
- Model training loss
- Validation metrics
- Inference latency
- Cache hit rates

## Troubleshooting

### Models not loading
```bash
# Check model files exist
ls -la /models/free/

# Check logs
docker logs tunetrail-ml-engine
```

### Low performance
- Increase dataset size
- Tune hyperparameters in `config.py`
- Enable GPU acceleration
- Increase FAISS nprobe parameter

### Out of memory
- Reduce batch size in training
- Use FAISS IVF index instead of Flat
- Enable model quantization

## Next Steps

1. **Ingest Data**: See `datasets/README.md`
2. **Extract Audio Features**: Use audio-processor service
3. **Train Models**: Run `scripts/train_all_models.py`
4. **Deploy**: Models auto-loaded on service start
5. **Monitor**: Check TensorBoard and API metrics

## License
AGPL-3.0 (Community Edition)