# TuneTrail ML Engine - Training Scripts

This directory contains production-ready scripts for training, evaluating, and managing ML models.

## 🚀 Quick Start

### 1. Train All Models
```bash
# Train all tiers with evaluation
python scripts/train_all_models.py --tier all --evaluate

# Train specific tier
python scripts/train_all_models.py --tier free
python scripts/train_all_models.py --tier starter
python scripts/train_all_models.py --tier pro

# Force retrain existing models
python scripts/train_all_models.py --force
```

### 2. Ingest Training Data
```bash
# Download FMA small dataset (8K tracks, Creative Commons)
python scripts/ingest_dataset.py fma --subset small --extract-features

# Ingest Spotify preview tracks (requires API keys)
export SPOTIFY_CLIENT_ID="your_client_id"
export SPOTIFY_CLIENT_SECRET="your_client_secret"
python scripts/ingest_dataset.py spotify --tracks 1000 --extract-features
```

### 3. Evaluate Models
```bash
# Evaluate all models
python scripts/evaluate_models.py

# Evaluate specific models
python scripts/evaluate_models.py --models collaborative_filter,neural_cf

# Compare models side-by-side
python scripts/evaluate_models.py --models collaborative_filter,neural_cf --compare
```

### 4. Build FAISS Indexes
```bash
# Auto-select best index type
python scripts/build_faiss_index.py

# Use GPU acceleration
python scripts/build_faiss_index.py --gpu --index-type ivf

# Force rebuild
python scripts/build_faiss_index.py --force
```

## 📊 Scripts Overview

### `train_all_models.py`
**Complete training pipeline for all recommendation models**

- **Free Tier**: Collaborative Filtering (ALS), Popularity, Genre-Based
- **Starter Tier**: Content-Based (FAISS), Daily Mix Generator
- **Pro Tier**: Neural Collaborative Filtering, Taste Profiler

**Features:**
- Tier-based training with dependencies
- PyTorch Lightning integration for Neural CF
- Comprehensive logging and metrics
- Model checkpointing and early stopping
- Training report generation

**Example Output:**
```
🚀 Starting TuneTrail ML Training Pipeline
📊 Loading training data...
Loaded 50,000 training interactions
Loaded 5,000 tracks

🆓 Training Free Tier Models
✅ Collaborative Filtering training completed
✅ Popularity Model training completed
✅ Genre-Based Model training completed

💎 Training Pro Tier Models
✅ Neural CF training completed
Best validation loss: 0.234

📈 Running Model Evaluation
🏆 Best performing models:
  recall@20: pro_neural_cf (score: 0.3456)
```

### `evaluate_models.py`
**Comprehensive model evaluation and comparison**

**Metrics Computed:**
- Recall@K (5, 10, 20)
- NDCG@K (normalized ranking quality)
- MRR (mean reciprocal rank)
- MAP (mean average precision)
- Catalog coverage

**Features:**
- Tier-wise evaluation reports
- Model comparison matrices
- Performance benchmarking
- JSON report generation

**Example Output:**
```
📊 EVALUATION RESULTS
🎯 FREE TIER
📈 collaborative_filter
  recall@20: 0.2341
  ndcg@20: 0.2756
  mrr: 0.1234

🏆 SUMMARY COMPARISON
Best performing models:
  recall@20: neural_cf (0.3456)
  ndcg@20: neural_cf (0.3721)
```

### `ingest_dataset.py`
**Dataset ingestion from multiple sources**

**Supported Datasets:**
- **FMA (Free Music Archive)**: 8K-25K Creative Commons tracks
- **Spotify Web API**: Preview tracks + metadata
- **Million Song Dataset**: Metadata + audio features
- **MusicBrainz**: Comprehensive metadata

**Features:**
- Automatic download and extraction
- Database ingestion with deduplication
- Progress tracking
- Error handling and retry logic

**Example Usage:**
```bash
# Download FMA small (8K tracks, 7.2GB)
python scripts/ingest_dataset.py fma --subset small

# Results in database:
# - 8,000 tracks with metadata
# - Creative Commons licensed
# - Genre classifications
# - Ready for feature extraction
```

### `build_faiss_index.py`
**FAISS similarity search index builder**

**Index Types:**
- **IndexFlatIP**: Exact search (<1K vectors)
- **IndexIVFFlat**: Approximate search (1K+ vectors)
- **Auto-selection**: Chooses optimal type

**Features:**
- GPU acceleration support
- Performance benchmarking
- Recall testing (for approximate indexes)
- Index optimization

**Example Output:**
```
🔍 Building FAISS Indexes
Building IndexIVFFlat (approximate search)...
Using nlist=100 for 5,000 vectors
🧪 Testing index performance...
K=20: 2.34ms per query
Average Recall@10: 0.987
✅ IVF index built successfully in 12.34s
```

## 🎯 Training Pipeline

### Data Requirements
**Minimum Viable:**
- 1,000+ tracks with metadata
- 500+ users with interactions
- 10,000+ interactions (plays, likes, skips)

**Production Recommended:**
- 10,000+ tracks with audio features
- 5,000+ active users
- 100,000+ interactions

### Training Schedule
```
04:00 - Free tier models     (30 min)
05:00 - Starter tier models  (1-2 hours)
07:00 - Pro tier models      (2-3 hours)
10:00 - Model evaluation     (45 min)
12:00 - FAISS index rebuild  (15 min)
```

### Model Dependencies
```
Free Tier (Independent):
├── Collaborative Filter
├── Popularity
└── Genre-Based

Starter Tier:
├── Content-Based (requires audio features)
└── Daily Mix → depends on: [Genre-Based]

Pro Tier:
├── Neural CF → depends on: [Collaborative Filter]
└── Taste Profiler → depends on: [CF, Content-Based]
```

## 📈 Expected Performance

### Training Times
| Model | Tier | Duration | GPU Benefit |
|-------|------|----------|-------------|
| Collaborative Filter | Free | 10-30 min | No |
| Popularity | Free | 5-10 min | No |
| Genre-Based | Free | 5-15 min | No |
| Content-Based | Starter | 30-60 min | Yes |
| Neural CF | Pro | 2-3 hours | Yes |

### Model Accuracy
| Model | Recall@20 | NDCG@20 | Notes |
|-------|-----------|---------|-------|
| Popularity | 0.10-0.15 | 0.12-0.18 | Baseline |
| Collaborative Filter | 0.15-0.25 | 0.18-0.28 | Good |
| Content-Based | 0.20-0.30 | 0.22-0.32 | Audio similarity |
| Neural CF | 0.30-0.45 | 0.35-0.50 | Best performance |

## 🛠️ Configuration

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@postgres:5432/tunetrail
REDIS_URL=redis://:password@redis:6379/0

# ML Training
MODEL_TIER=basic          # basic, full, enterprise
ENABLE_GPU=false          # true for GPU acceleration
TORCH_HOME=/models        # Model cache directory

# Spotify API (optional)
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
```

### Model Paths
```
/models/
├── free/                 # Free tier models
│   ├── collaborative_filter_als.pkl
│   ├── popularity.pkl
│   └── genre_based.pkl
├── starter/              # Starter tier models
│   ├── content_based.pkl
│   ├── content_based.faiss
│   └── daily_mix.pkl
├── pro/                  # Pro tier models
│   ├── neural_cf.pt
│   ├── neural_cf_mappings.pkl
│   └── taste_profiler.pkl
└── faiss_indexes/        # FAISS similarity indexes
    ├── audio_embeddings.index
    ├── track_id_mapping.pkl
    └── index_metadata.json
```

## 🔧 Troubleshooting

### Common Issues

**"No training data available"**
```bash
# Ingest a dataset first
python scripts/ingest_dataset.py fma --subset small
```

**"No audio features found"**
```bash
# Extract features using audio-processor service
# or ingest with --extract-features flag
python scripts/ingest_dataset.py fma --subset small --extract-features
```

**PyTorch GPU issues**
```bash
# Check GPU availability
python -c "import torch; print(torch.cuda.is_available())"

# Train on CPU if GPU unavailable
ENABLE_GPU=false python scripts/train_all_models.py
```

**Out of memory errors**
```bash
# Reduce batch size in config.py
# or use smaller model dimensions
```

### Monitoring Training

**TensorBoard logs:**
```bash
tensorboard --logdir=/models/logs
```

**Training logs:**
```bash
tail -f /models/training.log
```

**Model evaluation reports:**
```bash
ls /models/evaluation_*.json
cat /models/evaluation_report_latest.json | jq '.results.summary'
```

## 🚀 Next Steps

1. **Start with FMA Small**: `python scripts/ingest_dataset.py fma --subset small`
2. **Train Free Models**: `python scripts/train_all_models.py --tier free`
3. **Extract Audio Features**: Enable audio-processor service
4. **Train All Tiers**: `python scripts/train_all_models.py --tier all --evaluate`
5. **Monitor Performance**: Check evaluation reports and TensorBoard

The training infrastructure is production-ready! 🎉