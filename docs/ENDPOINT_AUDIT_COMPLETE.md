# Complete Endpoint Audit: Tier Enforcement & ML Data Collection

## Executive Summary

**Total Endpoints**: 88 unique paths (103 handlers with different HTTP methods)
**Tier-Enforced**: 5 endpoints (5.7%) ❌ **NEEDS WORK**
**ML Data Captured**: Good foundation, missing some feedback loops

---

## 🔍 ENDPOINT-BY-ENDPOINT AUDIT

### **AUTHENTICATION & USER (21 endpoints)**

| Endpoint | Method | Tier | ML Data | Issues | Fix |
|----------|--------|------|---------|--------|-----|
| `/auth/register` | POST | ✅ All | ✅ Signup context | ⚠️ Missing device fingerprint | Add signup_device_id |
| `/auth/login` | POST | ✅ All | ⚠️ Basic | ❌ No login tracking | Create login_history table |
| `/auth/me` | GET | ✅ All | ✅ N/A | ✅ Good | None |
| `/auth/forgot-password` | POST | ✅ All | ✅ N/A | ✅ Good | None |
| `/auth/reset-password` | POST | ✅ All | ✅ N/A | ✅ Good | None |
| `/auth/change-password` | PUT | ✅ All | ✅ N/A | ⚠️ No password history | Track in user.password_last_changed |
| `/auth/send-verification-email` | POST | ✅ All | ✅ N/A | ✅ Good | None |
| `/auth/verify-email` | POST | ✅ All | ✅ N/A | ✅ Good | None |
| `/auth/security/status` | GET | ✅ All | ✅ N/A | ✅ Good | None |
| `/auth/security/logout` | POST | ✅ All | ✅ N/A | ⚠️ Stub only | Implement token blacklist |
| `/auth/security/logout-all` | POST | ✅ All | ✅ N/A | ⚠️ Stub only | Implement session management |
| `/onboarding/status` | GET | ✅ All | ✅ Progress tracking | ✅ Good | None |
| `/onboarding/preferences` | POST | ✅ All | ✅✅✅ **CRITICAL ML** | ✅ Excellent | None |
| `/onboarding/complete` | POST | ✅ All | ✅ Completion tracking | ✅ Good | None |
| `/onboarding/skip` | POST | ✅ All | ✅ Skip tracking | ✅ Good | None |
| `/users/me` | GET | ✅ All | ✅ N/A | ✅ Good | None |
| `/users/me` | PUT | ✅ All | ✅ Profile updates | ✅ Good | None |
| `/users/me` | DELETE | ✅ All | ✅ Churn signal | ⚠️ No exit survey | Add deletion_reason field |
| `/users/me/preferences` | GET/PUT | ✅ All | ✅✅ **ML Critical** | ✅ Excellent | None |
| `/users/me/recently-played` | GET | ✅ All | ✅ History | ✅ Good | None |
| `/users/me/favorites` | GET | ✅ All | ✅ Explicit likes | ✅ Good | None |
| `/users/me/library/artists` | GET | ✅ All | ✅ Collection data | ✅ Good | None |
| `/users/me/library/genres` | GET | ✅ All | ✅ Taste profile | ✅ Good | None |

**Auth Summary:**
- ✅ Tier Enforcement: Correct (all should be public)
- ⚠️ ML Data: Good but missing login tracking, device fingerprinting
- ⚠️ Security: Logout is stub, needs implementation

---

### **API KEYS (8 endpoints)**

| Endpoint | Method | Tier | Should Be | Fix |
|----------|--------|------|-----------|-----|
| `/api-keys/` | POST | ✅ All | ✅ All | None |
| `/api-keys/` | GET | ✅ All | ✅ All | None |
| `/api-keys/{id}` | GET | ✅ All | ✅ All | None |
| `/api-keys/{id}` | PATCH | ✅ All | ✅ All | None |
| `/api-keys/{id}` | DELETE | ✅ All | ✅ All | None |
| `/api-keys/{id}/revoke` | POST | ✅ All | ✅ All | None |
| `/api-keys/{id}/rotate` | POST | ✅ All | ✅ All | None |
| `/api-keys/{id}/usage` | GET | ✅ All | ⚠️ **Pro+** | Add tier gate - detailed usage is Pro feature |

**Fix Needed:**
```python
@router.get("/{key_id}/usage", dependencies=[Depends(require_plan(["pro", "enterprise"]))])
# Detailed API usage analytics should be Pro+ only
```

---

### **TRACKS (6 endpoints)**

| Endpoint | Method | Tier | ML Data | Issues | Fix |
|----------|--------|------|---------|--------|-----|
| `/tracks/` | POST | ✅ All | ✅ Upload tracking | ⚠️ No upload source | Add source field |
| `/tracks/` | GET | ✅ All | ✅ Browse patterns | ✅ Good | None |
| `/tracks/{id}` | GET | ✅ All | ✅ View tracking | ❌ **NOT TRACKED** | Track view events |
| `/tracks/{id}` | PATCH | ✅ All | ✅ Edit tracking | ✅ Good | None |
| `/tracks/{id}` | DELETE | ✅ All | ✅ Deletion tracking | ⚠️ No reason | Add deletion_reason |
| `/tracks/stats/summary` | GET | ✅ All | ✅ N/A | ✅ Good | None |

**Missing Critical ML Data:**
```python
# Track views aren't being tracked!
POST /api/v1/tracks/{id}/view
  - Track when user views track details
  - Different from play
  - Indicates interest

# No track impressions
POST /api/v1/tracks/impressions
  - Batch record which tracks user saw
  - Recommendation impressions
  - Click-through rate data
```

---

### **ALBUMS & ARTISTS (13 endpoints)**

| Endpoint | Method | Tier | Issues | Fix |
|----------|--------|------|--------|-----|
| `/albums/{id}` | GET | ✅ All | ❌ No view tracking | Track album views |
| `/albums/{id}/tracks` | GET | ✅ All | ✅ Good | None |
| `/albums/` | GET | ✅ All | ✅ Good | None |
| `/albums/me/saved` | POST/DELETE/GET | ✅ All | ✅ Good | None |
| `/artists/{id}` | GET | ✅ All | ❌ No view tracking | Track artist page views |
| `/artists/{id}/tracks` | GET | ✅ All | ✅ Good | None |
| `/artists/{id}/top-tracks` | GET | ✅ All | ✅ Good | None |
| `/artists/me/following` | POST/DELETE/GET | ✅ All | ✅✅ **Excellent** | None |

**Missing:**
```python
# Artist page impressions
POST /api/v1/artists/{id}/view
  - Track artist page views
  - Click-through from search
  - Engagement metric

# Album play-through rate
GET /api/v1/albums/{id}/analytics
  - How many users play full album vs. skip around
  - Album cohesion score
```

---

### **PLAYLISTS (8 endpoints)**

| Endpoint | Method | Tier | ML Data | Issues |
|----------|--------|------|---------|--------|
| `/playlists/` | POST | ✅ All | ✅ Creation context | ✅ Good |
| `/playlists/` | GET | ✅ All | ✅ Browse | ✅ Good |
| `/playlists/{id}` | GET | ✅ All | ❌ No view tracking | **FIX** |
| `/playlists/{id}` | PATCH | ✅ All | ✅ Edit tracking | ✅ Good |
| `/playlists/{id}` | DELETE | ✅ All | ✅ Deletion | ⚠️ No reason |
| `/playlists/{id}/tracks` | POST | ✅ All | ✅ Add tracking | ✅ Good |
| `/playlists/{id}/tracks/{track_id}` | DELETE | ✅ All | ✅ Remove tracking | ⚠️ No reason |
| `/playlists/{id}/tracks/reorder` | POST | ✅ All | ✅ Reorder | ✅ Good |

**Tier Issue:**
- Collaborative playlists should be **Pro+ only**
- Community: personal playlists only

---

### **INTERACTIONS (3 endpoints)**

| Endpoint | Method | Tier | ML Data Quality | Grade |
|----------|--------|------|-----------------|-------|
| `/interactions/` | POST | ✅ All | ✅✅✅ **EXCELLENT** | A+ |
| `/interactions/` | GET | ✅ All | ✅ History | A |
| `/interactions/stats` | GET | ✅ All | ✅ Stats | A |

**Perfect!** Already has rich context (15+ fields). No changes needed.

---

### **RECOMMENDATIONS (9 endpoints)**

| Endpoint | Method | Tier | Should Be | Issues | Fix |
|----------|--------|------|-----------|--------|-----|
| `/recommendations/` | GET | ✅ All | ✅ All | ⚠️ Basic algo | Upgrade to ML when ready |
| `/recommendations/similar/{id}` | GET | ✅ All | ✅ All | ⚠️ Genre-based only | Add audio similarity |
| `/ml/recommendations/feedback` | POST | ✅ All | ✅ All | ✅✅ **Excellent** | None |
| `/ml/daily-mix` | GET | ✅ All | ⚠️ **Starter+** | ❌ Not enforced | Add tier gate |
| `/ml/radio` | POST | ✅ All | ⚠️ **Starter+** | ❌ Not enforced | Add tier gate |
| `/ml/taste-profile` | GET | ✅ All | ⚠️ **Pro+** | ❌ Not enforced | Add tier gate |
| `/ml/top/tracks` | GET | ✅ All | ✅ All | ✅ Good | None |

**Critical Tier Fixes:**
```python
# Community: Basic genre-based recommendations
# Starter+: Collaborative filtering
# Pro+: Neural CF, deep taste profiling

@router.get("/ml/daily-mix", dependencies=[Depends(require_plan(["starter", "pro", "enterprise"]))])
@router.post("/ml/radio", dependencies=[Depends(require_plan(["starter", "pro", "enterprise"]))])
@router.get("/ml/taste-profile", dependencies=[Depends(require_plan(["pro", "enterprise"]))])
```

**Missing:**
```python
# No impression tracking!
POST /api/v1/recommendations/impressions
  track_ids: [...]  # Which recommendations were shown
  # Critical for CTR (click-through rate) calculation
```

---

### **SEARCH & BROWSE (7 endpoints)**

| Endpoint | Method | Tier | ML Data | Issues |
|----------|--------|------|---------|--------|
| `/search/` | GET | ✅ All | ⚠️ No tracking | **Track search queries!** |
| `/search/autocomplete` | GET | ✅ All | ⚠️ No tracking | Track autocomplete |
| `/browse/genres` | GET | ✅ All | ✅ Good | None |
| `/browse/genres/{genre}/tracks` | GET | ✅ All | ✅ Good | None |
| `/browse/new-releases` | GET | ✅ All | ✅ Good | None |
| `/browse/trending` | GET | ✅ All | ✅ Good | None |
| `/browse/popular` | GET | ✅ All | ✅ Good | None |

**Critical Missing:**
```python
# Search queries aren't being saved!
# Every search should create a record:

CREATE TABLE search_queries (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    query TEXT,
    search_type VARCHAR(50),  -- track, artist, album, all
    results_count INT,
    clicked_result_id UUID,  -- Which result user clicked
    clicked_position INT,    -- Position in results (1st, 2nd, etc.)
    timestamp TIMESTAMP
);

# ML Value:
# - Understand user intent
# - Improve search ranking
# - Failed searches = missing content
# - Click position = relevance feedback
```

---

### **PLAYER CONTROL (15 endpoints)**

| Endpoint | Method | Tier | ML Data | Status |
|----------|--------|------|---------|--------|
| `/me/player/state` | GET | ✅ All | ✅ Good | ✅ |
| `/me/player/play` | PUT | ✅ All | ✅✅ **Context captured** | ✅ |
| `/me/player/pause` | PUT | ✅ All | ⚠️ No pause reason | ⚠️ |
| `/me/player/next` | POST | ✅ All | ✅ Skip recorded | ✅ |
| `/me/player/previous` | POST | ✅ All | ✅ Good | ✅ |
| `/me/player/seek` | PUT | ✅ All | ❌ **No seek tracking** | ❌ |
| `/me/player/shuffle` | PUT | ✅ All | ✅ Setting tracked | ✅ |
| `/me/player/repeat` | PUT | ✅ All | ✅ Setting tracked | ✅ |
| `/me/player/volume` | PUT | ✅ All | ✅ Good | ✅ |
| `/me/player/currently-playing` | GET | ✅ All | ✅ Good | ✅ |
| `/me/player/queue/*` | Various | ✅ All | ✅ Good | ✅ |

**Missing ML Data:**
```python
# Seek events aren't tracked!
# Should record:
POST /api/v1/player/events/seek
  position_from_ms: int
  position_to_ms: int
  track_id: UUID
  # ML Value: User skips intro, seeks to chorus = preference signal

# Pause context
PUT /api/v1/me/player/pause
  reason: Optional[str]  # "taking_call", "done_listening", "interruption"
  # Helps distinguish intentional vs. accidental pauses
```

---

### **SESSIONS (6 endpoints)**

| Endpoint | Method | Tier | ML Data | Status |
|----------|--------|------|---------|--------|
| `/sessions/start` | POST | ✅ All | ✅✅✅ **Perfect** | ✅ |
| `/sessions/{id}/heartbeat` | PUT | ✅ All | ✅ Activity tracking | ✅ |
| `/sessions/{id}/end` | POST | ✅ All | ✅✅ **Excellent** | ✅ |
| `/sessions/` | GET | ✅ All | ✅ Good | ✅ |
| `/sessions/{id}` | GET | ✅ All | ✅ Good | ✅ |
| `/sessions/stats/summary` | GET | ✅ All | ✅ Good | ✅ |

**PERFECT!** Sessions are well-designed for ML. No changes needed.

---

### **AUDIO FEATURES (4 endpoints)** ⭐ **NEW**

| Endpoint | Method | Tier | Current | Should Be | Fix |
|----------|--------|------|---------|-----------|-----|
| `/audio/features/{id}` | GET | ✅ All | ✅ All | ✅ Correct | None |
| `/audio/analyze` | POST | ✅ All | ⚠️ **Starter+** | ❌ Not enforced | **ADD TIER GATE** |
| `/audio/similarity-search` | POST | ✅ All | ⚠️ **Starter+** | ❌ Not enforced | **ADD TIER GATE** |
| `/audio/batch-analyze` | POST | ✅ **Starter+** | ✅ Enforced | ✅ Good | None |

**Critical Fixes:**
```python
# Audio analysis is compute-heavy, should be gated:

@router.post("/analyze")
async def analyze_track(
    ...,
    _tier_check: User = Depends(check_usage_limit("audio_analysis_per_day"))
):
    # Enforce daily limits

@router.post("/similarity-search", dependencies=[Depends(require_plan(["starter", "pro", "enterprise"]))])
# Vector search is expensive, Starter+ only
```

---

### **ADVANCED ANALYTICS (4 endpoints)** ⭐ **PRO+**

| Endpoint | Method | Tier | Enforced | Status |
|----------|--------|------|----------|--------|
| `/analytics/users/similar` | GET | ⚠️ **Pro+** | ✅ Yes | ✅ Good |
| `/analytics/correlations/genres` | GET | ⚠️ **Pro+** | ✅ Yes | ✅ Good |
| `/analytics/patterns/temporal` | GET | ⚠️ **Pro+** | ✅ Yes | ✅ Good |
| `/analytics/insights/wrapped` | GET | ⚠️ **Pro+** | ✅ Yes | ✅ Good |

**Perfect!** All properly gated to Pro+ tier.

---

## 🎯 MISSING CRITICAL ENDPOINTS

### **1. Impression Tracking** ❌ (CRITICAL FOR ML)

```python
POST /api/v1/impressions/recommendations
  recommendation_ids: [UUID]
  context: "home_page" | "playlist_detail" | "artist_page"
  # Which recommendations were SHOWN (not clicked)
  # ML needs this for CTR calculation!

POST /api/v1/impressions/tracks
  track_ids: [UUID]
  context: "search_results" | "browse_genre" | "trending"
  position: [int]  # Position in list
  # Track what user SAW vs. what they CLICKED
```

**Impact**: **Can't calculate recommendation accuracy without impression data!**

---

### **2. Search Query Logging** ❌ (CRITICAL)

```python
# Currently: Search works but queries aren't saved!

# Should create on every search:
search_log = {
    user_id: UUID,
    query: "bohemian rhapsody",
    search_type: "track",
    results_count: 5,
    clicked_result_id: UUID,
    clicked_position: 2,  # User clicked 2nd result
    timestamp: datetime
}

# ML Value:
# - Failed searches (0 results) = missing content
# - Click position = ranking quality
# - Query patterns = user intent
```

---

### **3. Track View Events** ❌

```python
POST /api/v1/tracks/{id}/view
  source: "search" | "recommendations" | "artist_page"
  # User viewed track details but didn't play
  # Interest signal even without play
```

---

### **4. Recommendation Impressions** ❌ (BLOCKING ML EVALUATION)

```python
POST /api/v1/recommendations/{id}/impression
  shown_at: datetime
  context: "home_page"
  position: 3

# Then when user clicks:
POST /api/v1/recommendations/{id}/click
  clicked_at: datetime

# ML Metrics:
# CTR = clicks / impressions
# Position bias = do users click top results more?
# Time to click = how long user considered?
```

---

### **5. Playback Events (Fine-Grained)** ⚠️

```python
# Currently: Only start/stop tracked via interactions
# Missing: Granular playback events

POST /api/v1/player/events
  event_type: "seek" | "buffer" | "error" | "quality_change"
  track_id: UUID
  position_ms: int
  metadata: {...}

# ML Value:
# - Seek patterns = skip intros, seek to chorus
# - Buffering issues = quality problems
# - Errors = broken tracks
```

---

## 🔧 TIER ENFORCEMENT FIXES NEEDED

### **Endpoints Missing Tier Gates:**

```python
# 1. ML Advanced Features (should be Starter+)
@router.get("/ml/daily-mix", dependencies=[Depends(require_plan(["starter", "pro", "enterprise"]))])
@router.post("/ml/radio", dependencies=[Depends(require_plan(["starter", "pro", "enterprise"]))])

# 2. Deep Taste Profiling (should be Pro+)
@router.get("/ml/taste-profile", dependencies=[Depends(require_plan(["pro", "enterprise"]))])

# 3. Audio Analysis (should have usage limits)
@router.post("/audio/analyze", dependencies=[Depends(check_usage_limit("audio_analysis_per_day"))])

# 4. Detailed API Usage (should be Pro+)
@router.get("/api-keys/{id}/usage", dependencies=[Depends(require_plan(["pro", "enterprise"]))])

# 5. Similarity Search (Starter+, computationally expensive)
@router.post("/audio/similarity-search", dependencies=[Depends(require_plan(["starter", "pro", "enterprise"]))])
```

---

## 📊 COMPLETE ENDPOINT CATEGORIZATION

### **Community (Free) - 70 endpoints**
✅ All auth, user profile, basic playback
✅ Tracks, albums, artists (CRUD)
✅ Playlists (personal only)
✅ Basic genre-based recommendations
✅ Search, browse
✅ Player controls, queue
✅ Interactions (data collection)

### **Starter (\$9/mo) - +10 endpoints**
✅ Hosted infrastructure
✅ Audio feature analysis (100/day)
✅ Collaborative filtering
✅ Daily mixes
✅ Radio generation
✅ Batch processing

### **Pro (\$29/mo) - +8 endpoints**
✅ Advanced analytics (user similarity, patterns)
✅ Deep taste profiling
✅ Neural CF recommendations
✅ Webhooks (future)
✅ Higher limits (1000/day audio)
✅ Wrapped insights

### **Enterprise (\$99+/mo) - +Unlimited**
✅ Unlimited everything
✅ Custom model training
✅ White-label
✅ On-premise deployment
✅ Dedicated support

---

## 🎯 IMMEDIATE ACTION ITEMS

### **Priority 1: Add Missing ML Data Collection** (2-3 hours)

```python
# 1. Search Query Logging
POST /api/v1/search/queries/log
  - Save every search
  - Track click-through

# 2. Impression Tracking
POST /api/v1/impressions
  - Track what user SAW
  - Not just what they clicked

# 3. View Events
POST /api/v1/views/track/{id}
POST /api/v1/views/artist/{id}
POST /api/v1/views/album/{id}
  - Interest signals even without play

# 4. Granular Player Events
POST /api/v1/player/events
  - Seek, buffer, errors
  - Quality change events
```

### **Priority 2: Add Tier Enforcement** (1 hour)

```python
# Add to these endpoints:
1. /ml/daily-mix → Starter+
2. /ml/radio → Starter+
3. /ml/taste-profile → Pro+
4. /audio/analyze → Usage limits
5. /audio/similarity-search → Starter+
6. /api-keys/{id}/usage → Pro+
```

### **Priority 3: Missing Recommendation Features** (2 hours)

```python
# Recommendation engine completeness:
GET /api/v1/recommendations/for-playlist/{id}  # Recommend tracks for playlist
GET /api/v1/recommendations/based-on-time      # Time-aware
POST /api/v1/recommendations/for-mood          # Mood-based
GET /api/v1/recommendations/discover-weekly    # Weekly fresh picks
```

---

## 📈 FINAL TIER MATRIX

| Feature Category | Community | Starter | Pro | Enterprise |
|-----------------|-----------|---------|-----|------------|
| **Core Features** | ✅ All 70 | ✅ All | ✅ All | ✅ All |
| **Audio Analysis** | Self-hosted | 100/day | 1000/day | Unlimited |
| **ML Models** | Basic | + Collaborative | + Neural | + Custom |
| **Analytics** | Basic | Basic | Advanced | Advanced |
| **API Limits** | Unlimited* | 10K/day | 100K/day | Unlimited |
| **Webhooks** | ❌ | ❌ | ✅ | ✅ |
| **Support** | Community | Email | Priority | Dedicated |

*Unlimited when self-hosted

---

## ✅ RECOMMENDATIONS

**DO THIS NOW:**

1. ✅ Add tier gates to ML endpoints (5 endpoints)
2. ✅ Implement search query logging
3. ✅ Add impression tracking
4. ✅ Add view events for tracks/artists/albums
5. ✅ Track granular player events (seek, buffer)

**Estimated Time**: 4-5 hours
**Impact**: Complete ML feedback loop + proper monetization

**Should I implement these critical additions now?**