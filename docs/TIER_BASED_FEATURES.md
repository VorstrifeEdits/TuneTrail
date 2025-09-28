# TuneTrail Tier-Based Features & Open Core Strategy

## Overview

TuneTrail follows the **Open Core** model (like GitLab, Elasticsearch):
- **Community Edition**: Full source code on GitHub (AGPL-3.0)
- **Commercial Tiers**: Advanced features, hosted infrastructure, premium ML models

**All code is open source**, but features are gated by:
- Plan/tier checking
- Usage limits
- Model access control
- Infrastructure availability

---

## 🎯 Feature Matrix

| Feature | Community | Starter ($9/mo) | Pro ($29/mo) | Enterprise ($99+/mo) |
|---------|-----------|-----------------|--------------|---------------------|
| **Deployment** | Self-hosted | Cloud | Cloud | Cloud or On-premise |
| **Users** | Unlimited | 5 | 25 | Unlimited |
| **Tracks** | Unlimited | 10,000 | 100,000 | Unlimited |
| **API Calls/Day** | Unlimited (local) | 1,000 | 10,000 | Unlimited |
| **ML Models** | Basic Content | + Collaborative | + Neural CF | + Custom Models |
| **Audio Analysis** | Unlimited (local) | 100/day | 1,000/day | Unlimited |
| **Webhooks** | ❌ | ❌ | ✅ | ✅ |
| **Advanced Analytics** | ❌ | ❌ | ✅ | ✅ |
| **A/B Testing** | ❌ | ❌ | ❌ | ✅ |
| **White Label** | ✅ (AGPL) | ❌ | ❌ | ✅ (Commercial) |
| **Support** | Community | Email | Priority | Dedicated |

---

## 📊 Currently Missing: Tier Enforcement

### **CRITICAL GAPS:**

#### **1. No Feature Gating Middleware** ❌
```python
# Currently: All endpoints accessible to everyone
# Should: Check user's plan before allowing access

# Example of what's missing:
@router.get("/advanced-analytics")
async def get_advanced_analytics(...):
    # ❌ No tier check!
    # Anyone can call this, even free tier
```

#### **2. No Usage Limits Enforcement** ❌
```python
# Should track and enforce:
# - API calls per day (by plan)
# - Audio analysis per day
# - Model training jobs per month
# - Webhook deliveries per month
```

#### **3. No Model Access Control** ❌
```python
# Community: Basic content-based filtering
# Starter: + Collaborative filtering
# Pro: + Neural CF, LightGCN
# Enterprise: + Custom model training

# Currently: No check on which model user can use!
```

#### **4. Audio Features Table Exists But No Endpoints** ❌
```sql
-- Table exists in migration:
CREATE TABLE audio_features (
    embedding vector(512),  -- For similarity search
    tempo, energy, danceability, etc.
)

-- But no Python model or endpoints!
```

---

## 🔧 What Needs To Be Built

### **1. Tier-Based Middleware**

```python
# services/api/middleware/tier.py

from functools import wraps
from fastapi import HTTPException, Depends

async def require_plan(required_plans: List[str]):
    \"\"\"
    Dependency to check user's plan.

    Usage:
        @router.get("/premium-feature", dependencies=[Depends(require_plan(["pro", "enterprise"]))])
    \"\"\"
    async def check_plan(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
        org = await db.get(Organization, current_user.org_id)

        if org.plan not in required_plans:
            raise HTTPException(
                status_code=402,  # Payment Required
                detail=f"This feature requires {', '.join(required_plans)} plan. Current plan: {org.plan}. Upgrade at https://tunetrail.app/pricing"
            )
        return current_user

    return check_plan


# Usage in router:
@router.get("/webhooks", dependencies=[Depends(require_plan(["pro", "enterprise"]))])
async def list_webhooks(...):
    # Only Pro/Enterprise can access
```

### **2. Usage Tracking & Limits**

```python
# services/api/middleware/usage.py

TIER_LIMITS = {
    "free": {
        "api_calls_per_day": 1000,
        "audio_analysis_per_day": 10,
        "model_training_per_month": 0,
    },
    "starter": {
        "api_calls_per_day": 10000,
        "audio_analysis_per_day": 100,
        "model_training_per_month": 1,
    },
    "pro": {
        "api_calls_per_day": 100000,
        "audio_analysis_per_day": 1000,
        "model_training_per_month": 10,
    },
    "enterprise": {
        "api_calls_per_day": None,  # Unlimited
        "audio_analysis_per_day": None,
        "model_training_per_month": None,
    },
}

async def check_usage_limit(user, resource_type, db, redis):
    org = await get_organization(user.org_id)
    limit = TIER_LIMITS[org.plan][resource_type]

    if limit is None:  # Unlimited
        return True

    current_usage = await get_usage_from_redis(org.id, resource_type)

    if current_usage >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Usage limit exceeded. {resource_type} limit: {limit}/day. Upgrade your plan."
        )

    await increment_usage(org.id, resource_type)
```

### **3. Audio Features (CRITICAL MISSING!)**

```python
# services/api/models/audio_features.py

class AudioFeatures(Base):
    __tablename__ = "audio_features"

    track_id = Column(UUID, ForeignKey("tracks.id"), primary_key=True)

    # Spotify-style features
    tempo = Column(Float)  # BPM
    key = Column(Integer)  # Musical key (0-11)
    mode = Column(Integer)  # Major (1) or Minor (0)
    time_signature = Column(Integer)
    loudness = Column(Float)  # dB

    # Perceptual features
    energy = Column(Float, index=True)  # 0.0-1.0
    danceability = Column(Float, index=True)
    valence = Column(Float)  # Musical positiveness
    acousticness = Column(Float)
    instrumentalness = Column(Float)
    liveness = Column(Float)
    speechiness = Column(Float)

    # ML embeddings (512-dim vector for similarity)
    embedding = Column(Vector(512))

    # Spectral features (arrays)
    mfcc_features = Column(ARRAY(Float))
    chroma_features = Column(ARRAY(Float))

# Endpoints needed:
GET /api/v1/tracks/{id}/audio-features
POST /api/v1/tracks/{id}/analyze  # Trigger analysis
GET /api/v1/tracks/similar-by-audio/{id}  # Vector similarity search
POST /api/v1/audio/batch-analyze  # Batch processing
```

### **4. Missing Data Correlations**

```python
# User-to-User Similarity (Collaborative Filtering)
GET /api/v1/ml/users/similar
  - Find users with similar taste
  - Used for "Users who liked X also liked Y"
  - Collaborative filtering foundation

# Track-to-Track Similarity Matrix
GET /api/v1/ml/tracks/similarity-matrix
  - Pre-computed similarity scores
  - Faster recommendations
  - Cache for real-time queries

# Genre Co-occurrence
GET /api/v1/ml/correlations/genres
  - Which genres users listen to together
  - Cross-genre recommendations
  - "If you like Rock, try Electronic"

# Temporal Patterns
GET /api/v1/ml/patterns/temporal
  - Time of day listening habits
  - Day of week patterns
  - Seasonal trends

# Context Correlations
GET /api/v1/ml/correlations/context
  - Workout songs → high BPM + energy
  - Study music → low energy + instrumental
  - Sleep music → ambient + low tempo
```

---

## 🚀 Implementation Priority

### **Phase 1: Tier System (CRITICAL)**
1. ✅ Create tier middleware
2. ✅ Implement usage tracking
3. ✅ Add plan checking to premium endpoints
4. ✅ Document tier differences

### **Phase 2: Audio Features (ML BLOCKER)**
5. ✅ Create AudioFeatures model
6. ✅ Add audio analysis endpoints
7. ✅ Implement vector similarity search
8. ✅ Connect to audio processor service

### **Phase 3: Advanced ML Correlations**
9. ✅ User-to-user similarity
10. ✅ Genre co-occurrence analysis
11. ✅ Temporal pattern detection
12. ✅ Context correlation mining

**Should I implement all of these now?** This will give you:
- ✅ Proper tier separation (Community vs. Commercial)
- ✅ Audio feature foundation (ML critical)
- ✅ Advanced correlations (better recommendations)
- ✅ Production-ready monetization