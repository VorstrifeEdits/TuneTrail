# API Gap Analysis - Missing Critical Endpoints

## Current Status: 22 Endpoints Implemented

Based on analysis of the codebase, database schema, and industry best practices for music recommendation platforms, here are the **missing critical features**:

---

## 🎯 1. RECOMMENDATIONS - Critical Gaps

### ✅ What We Have
- Basic genre-based recommendations
- Similar tracks by genre/artist

### ❌ What's Missing

#### **A. Recommendation Feedback Loop**
```
POST /api/v1/recommendations/{recommendation_id}/feedback
- Accept/reject recommendation
- Implicit feedback (user clicked, ignored, etc.)
- Feeds back into ML model training
```

#### **B. Contextual Recommendations**
```
GET /api/v1/recommendations/for-playlist/{playlist_id}
- Recommend tracks to add to a specific playlist
- Based on existing tracks in that playlist

GET /api/v1/recommendations/radio/{track_id}
- Radio station based on seed track
- Infinite playback queue

GET /api/v1/recommendations/daily-mix
- Spotify-style daily mixes by genre/mood
- Personalized radio stations

GET /api/v1/recommendations/discover-weekly
- Weekly personalized playlist
- Fresh tracks user hasn't heard
```

#### **C. Recommendation Explanation**
```
GET /api/v1/recommendations/{track_id}/why
- Detailed explanation of why track was recommended
- Feature importance visualization data
- Similar users who liked this
```

#### **D. Recommendation History & Cache**
```
GET /api/v1/recommendations/history
- View past recommendations
- See which ones user acted on
- Learn from recommendation effectiveness

POST /api/v1/recommendations/refresh
- Force refresh recommendations cache
- Trigger ML model re-run
```

**Impact**: ML models need feedback loops to improve. Currently missing the critical data collection for model refinement.

---

## 🔐 2. AUTH FLOW - Critical Gaps

### ✅ What We Have
- Registration
- Login
- Get current user

### ❌ What's Missing

#### **A. Password Management**
```
POST /api/v1/auth/forgot-password
- Send password reset email
- Generate reset token

POST /api/v1/auth/reset-password
- Reset password with token
- Validate token expiry

PUT /api/v1/auth/change-password
- Change password while logged in
- Require current password
```

#### **B. Email Verification**
```
POST /api/v1/auth/send-verification-email
- Resend verification email

POST /api/v1/auth/verify-email
- Verify email with token
- Mark email_verified = true
```

#### **C. Session Management**
```
POST /api/v1/auth/logout
- Invalidate token (add to blacklist)
- Clear session

POST /api/v1/auth/logout-all
- Logout from all devices
- Invalidate all tokens for user

GET /api/v1/auth/sessions
- List active sessions
- Device info, IP, last active

DELETE /api/v1/auth/sessions/{session_id}
- Revoke specific session
```

#### **D. OAuth/Social Login** (Future/SaaS)
```
GET /api/v1/auth/oauth/{provider}
- OAuth flow (Google, GitHub, Spotify)

POST /api/v1/auth/oauth/callback
- Handle OAuth callback
```

#### **E. Two-Factor Authentication** (Pro/Enterprise)
```
POST /api/v1/auth/2fa/enable
POST /api/v1/auth/2fa/verify
POST /api/v1/auth/2fa/disable
```

**Impact**: Production apps need password reset and email verification. Session management is critical for security.

---

## 📊 3. DATA COLLECTION FOR ML - Critical Gaps

### ✅ What We Have
- Basic interactions (play, like, skip)
- Interaction context field

### ❌ What's Missing

#### **A. Richer Interaction Context**
Currently `context` is just JSON. We should capture:
```
POST /api/v1/interactions (enhanced)
Context should include:
- device_type (mobile, desktop, web)
- platform (iOS, Android, Web)
- playlist_id (if played from playlist)
- recommendation_id (if clicked from recommendations)
- session_id (group interactions into listening sessions)
- location (optional geo data)
- time_of_day
- shuffle_mode (on/off)
- repeat_mode (off, one, all)
- volume_level
- eq_settings (bass boost, etc.)
```

#### **B. Skip Reasons & Detailed Feedback**
```
POST /api/v1/interactions/{interaction_id}/details
- Why did user skip? (don't like genre, bad audio quality, wrong mood)
- Mood/energy level when playing
- Activity (workout, study, sleep, party)
```

#### **C. Listening Sessions**
```
POST /api/v1/sessions/start
- Start listening session
- Returns session_id

POST /api/v1/sessions/{session_id}/end
- End session with summary stats

GET /api/v1/sessions/
- List past sessions
- Useful for "continue where you left off"
```

#### **D. Batch Interaction Recording**
```
POST /api/v1/interactions/batch
- Submit multiple interactions at once
- Reduce API calls from mobile apps
- Better for offline sync
```

#### **E. Track-Level Analytics**
```
GET /api/v1/tracks/{track_id}/analytics
- Play count
- Skip rate
- Average completion rate
- Peak listening times
- Demographic data (if available)

GET /api/v1/tracks/{track_id}/listeners
- Who else listened to this track
- Find similar users (for collaborative filtering)
```

**Impact**: ML models need rich contextual data. Current interactions are too basic - missing session context, device info, skip reasons, mood/activity data.

---

## 👤 4. USER INFORMATION - Critical Gaps

### ✅ What We Have
- Basic user profile (email, username, full_name)
- Preferences JSON field

### ❌ What's Missing

#### **A. User Profile Management**
```
PUT /api/v1/users/me
- Update profile (avatar, bio, location)

GET /api/v1/users/me/settings
PUT /api/v1/users/me/settings
- App settings (theme, language, notifications)
- Privacy settings (public profile, show listening history)
- Playback settings (crossfade, normalize volume)

GET /api/v1/users/me/export
- GDPR compliance - export all user data

DELETE /api/v1/users/me
- Account deletion (GDPR right to be forgotten)
```

#### **B. User Preferences for ML**
```
PUT /api/v1/users/me/preferences
Capture:
- favorite_genres: []
- favorite_artists: []
- disliked_genres: []
- mood_preferences: {}
- energy_level_preference: (low, medium, high)
- explicit_content: (allow, block)
- language_preferences: []
- discovery_vs_familiar: 0.0-1.0 (exploration factor)
```

#### **C. Social Features**
```
GET /api/v1/users/{user_id}/public-profile
- View other user's public profile (if enabled)

POST /api/v1/users/{user_id}/follow
DELETE /api/v1/users/{user_id}/unfollow
GET /api/v1/users/me/followers
GET /api/v1/users/me/following

GET /api/v1/users/me/listening-activity
- Recent plays (if public)
- Top tracks this week/month
```

#### **D. Onboarding Flow**
```
POST /api/v1/users/me/onboarding/genres
- Select favorite genres during onboarding
- Initialize recommendation engine

POST /api/v1/users/me/onboarding/artists
- Select favorite artists

POST /api/v1/users/me/onboarding/complete
- Mark onboarding complete
- Trigger initial recommendation generation
```

**Impact**: Poor personalization without explicit user preferences. ML models perform better with declared preferences + implicit behavior.

---

## 🎨 5. USER EXPERIENCE - Critical Gaps

### ✅ What We Have
- CRUD operations
- Basic stats

### ❌ What's Missing

#### **A. Search & Discovery**
```
GET /api/v1/search
- Unified search (tracks, playlists, artists, albums)
- Fuzzy matching
- Autocomplete suggestions

GET /api/v1/search/autocomplete
- Real-time search suggestions
- Typo tolerance

GET /api/v1/browse/genres
- Browse by genre

GET /api/v1/browse/new-releases
- Latest tracks in library

GET /api/v1/browse/trending
- Most played tracks this week
```

#### **B. Recently Played & History**
```
GET /api/v1/me/recently-played
- Last N tracks played
- With timestamps

GET /api/v1/me/history
- Complete play history
- Exportable for analytics

GET /api/v1/me/favorites
- All liked tracks
- Quick access to favorites
```

#### **C. Queue Management**
```
GET /api/v1/me/queue
- Current playback queue

POST /api/v1/me/queue
- Add tracks to queue

DELETE /api/v1/me/queue/{track_id}
- Remove from queue

POST /api/v1/me/queue/clear
- Clear queue

PUT /api/v1/me/queue/reorder
- Reorder queue
```

#### **D. Playback State (Real-time)**
```
GET /api/v1/me/playback/state
- Current playing track
- Position in track
- Shuffle/repeat state

PUT /api/v1/me/playback/play
PUT /api/v1/me/playback/pause
POST /api/v1/me/playback/next
POST /api/v1/me/playback/previous
PUT /api/v1/me/playback/seek
- Playback controls (like Spotify API)

WebSocket /ws/playback
- Real-time playback state sync across devices
```

#### **E. Playlist Collaboration**
```
POST /api/v1/playlists/{id}/collaborators
- Add collaborators to playlist

DELETE /api/v1/playlists/{id}/collaborators/{user_id}
- Remove collaborator

GET /api/v1/playlists/{id}/activity
- Who added/removed what tracks
- Playlist edit history
```

#### **F. Library Organization**
```
GET /api/v1/me/library/artists
- All artists in user's library
- With track counts

GET /api/v1/me/library/albums
- All albums in user's library

GET /api/v1/me/library/genres
- All genres with counts

POST /api/v1/me/library/import
- Bulk import tracks from file (CSV, JSON)
- Import from other services
```

#### **G. Audio Player Features**
```
GET /api/v1/tracks/{track_id}/lyrics
- Synchronized lyrics (if available)

GET /api/v1/tracks/{track_id}/credits
- Artist credits, producers, etc.

POST /api/v1/tracks/{track_id}/report
- Report issues (broken link, wrong metadata)
```

**Impact**: Users expect Spotify-level UX. Missing queue management, real-time playback sync, search, and social features.

---

## 📈 Priority Matrix

### **Must Have (P0) - Blocking MVP**
1. ✅ Password reset/forgot password
2. ✅ Email verification
3. ✅ Search (at minimum: track search)
4. ✅ Recently played
5. ✅ User profile update

### **Should Have (P1) - Needed for Launch**
6. ✅ Listening sessions
7. ✅ Queue management
8. ✅ Richer interaction context
9. ✅ Browse/discovery endpoints
10. ✅ Onboarding flow

### **Nice to Have (P2) - Post-Launch**
11. ⭕ Social features (follow, public profiles)
12. ⭕ Collaborative playlists
13. ⭕ WebSocket playback sync
14. ⭕ Advanced analytics
15. ⭕ OAuth/social login

### **Enterprise (P3) - Premium Features**
16. ⭕ 2FA
17. ⭕ SSO integration
18. ⭕ Advanced permissions
19. ⭕ Audit logs

---

## 🔥 Critical Missing Features Summary

### **For Recommendations** (ML Model Needs)
- ❌ Recommendation feedback loop
- ❌ Richer interaction context (device, platform, session)
- ❌ Skip reasons and mood/activity data
- ❌ Listening sessions grouping
- ❌ Track popularity metrics

### **For Auth Flow** (Security & UX)
- ❌ Password reset
- ❌ Email verification
- ❌ Session management
- ❌ Token blacklisting

### **For Data Collection** (ML Training)
- ❌ Session tracking
- ❌ Device/platform info
- ❌ Contextual data (mood, activity, time of day)
- ❌ Skip reasons
- ❌ Batch interaction recording

### **For User Information** (Personalization)
- ❌ Explicit preferences (favorite genres/artists)
- ❌ User profile updates
- ❌ Onboarding flow
- ❌ Privacy settings
- ❌ Data export (GDPR)

### **For User Experience** (Core UX)
- ❌ **Search** (CRITICAL)
- ❌ **Recently played** (CRITICAL)
- ❌ Queue management
- ❌ Browse/discovery
- ❌ Favorites quick access
- ❌ Real-time playback state

---

## 📋 Recommended Implementation Order

### **Phase 1: Critical UX (This Week)**
1. Search endpoint (fuzzy search across tracks/artists/playlists)
2. Recently played / history
3. User profile update
4. Password reset flow
5. Email verification

### **Phase 2: ML Data Collection (Next Week)**
6. Enhanced interaction context (device, session_id, etc.)
7. Listening sessions (start/end)
8. Skip reasons / mood tracking
9. Track analytics (play count, skip rate)
10. Onboarding preference collection

### **Phase 3: Enhanced UX (Week 3)**
11. Queue management
12. Browse endpoints (genres, new releases, trending)
13. Favorites collection
14. Batch operations

### **Phase 4: Advanced Features (Week 4+)**
15. WebSocket real-time playback
16. Social features
17. Collaborative playlists
18. Advanced recommendation types

---

## 💡 Quick Wins (High Impact, Low Effort)

### **1. Search** ⚡ HIGH PRIORITY
```python
@router.get("/search")
async def search(
    q: str = Query(..., min_length=1),
    type: str = Query("all", regex="^(all|track|playlist|artist)$"),
    limit: int = 20
):
    # PostgreSQL full-text search
    # Returns unified results
```
**Why**: Users can't find anything without search. This is table stakes.

### **2. Recently Played** ⚡ HIGH PRIORITY
```python
@router.get("/me/recently-played")
async def get_recently_played(limit: int = 50):
    # Query interactions where type=play
    # Order by created_at desc
    # Return tracks with play timestamps
```
**Why**: Users expect to continue where they left off.

### **3. Enhanced Interaction Context** ⚡ HIGH PRIORITY
```python
# Just add these fields to InteractionCreate:
class InteractionCreate(BaseModel):
    # ... existing fields ...
    device_type: Optional[str] = None  # mobile, desktop, web
    session_id: Optional[UUID] = None  # group related plays
    playlist_id: Optional[UUID] = None  # played from which playlist
    recommendation_id: Optional[UUID] = None  # if from recommendations
```
**Why**: Free data collection that massively improves ML models.

### **4. User Profile Update** ⚡ MEDIUM PRIORITY
```python
@router.put("/users/me")
async def update_profile(data: UserUpdate):
    # Update avatar, bio, preferences
```
**Why**: Basic user expectation.

### **5. Favorites Endpoint** ⚡ MEDIUM PRIORITY
```python
@router.get("/me/favorites")
async def get_favorites():
    # All tracks with interaction_type=like
```
**Why**: One line of code, huge UX improvement.

---

## 🎯 Data Model Enhancements

### **Interaction Model** (CRITICAL)
Add to context field:
- `session_id` - Group interactions into sessions
- `device_type` - mobile/desktop/web/car
- `platform` - iOS/Android/Windows/Mac/Linux
- `source` - playlist/search/recommendations/radio/artist_page
- `source_id` - ID of the source playlist/recommendation
- `mood` - happy/sad/energetic/calm/focused
- `activity` - workout/study/sleep/commute/party
- `skip_reason` - dont_like_song/wrong_mood/bad_quality/heard_too_much

### **User Model** (IMPORTANT)
Add to preferences field:
- `favorite_genres` - Explicit preferences
- `disliked_genres` - Negative signals
- `favorite_artists` - Artist preferences
- `explicit_content_filter` - Content filtering
- `discovery_mode` - How adventurous for recommendations (0.0-1.0)
- `crossfade_duration` - Playback preferences
- `normalize_volume` - Audio settings

### **Track Model** (NICE TO HAVE)
Additional metadata:
- `popularity_score` - Calculated from play counts
- `skip_rate` - Skip count / play count
- `average_completion_rate` - How often users finish the track
- `mood_tags` - happy, sad, energetic, calm
- `activity_tags` - workout, study, sleep, party

---

## 🚀 Immediate Action Items

**I recommend implementing these 8 endpoints NOW** (before any frontend work):

1. ✅ `POST /api/v1/auth/forgot-password` - Password reset
2. ✅ `POST /api/v1/auth/reset-password` - Complete reset flow
3. ✅ `PUT /api/v1/users/me` - Update profile
4. ✅ `GET /api/v1/search` - Unified search
5. ✅ `GET /api/v1/me/recently-played` - Recent history
6. ✅ `GET /api/v1/me/favorites` - Liked tracks
7. ✅ Enhance `InteractionCreate` with session/device context
8. ✅ `GET /api/v1/browse/genres` - Genre browsing

**Estimated time**: 2-3 hours
**Impact**: Unlocks frontend development + massively better ML data

---

## 📊 Current vs. Industry Standard

| Feature | TuneTrail | Spotify | YouTube Music | Gap |
|---------|-----------|---------|---------------|-----|
| **Search** | ❌ | ✅ | ✅ | CRITICAL |
| **Recently Played** | ❌ | ✅ | ✅ | CRITICAL |
| **Queue** | ❌ | ✅ | ✅ | HIGH |
| **Radio/Mixes** | ❌ | ✅ | ✅ | MEDIUM |
| **Social** | ❌ | ✅ | ❌ | LOW |
| **Lyrics** | ❌ | ✅ | ✅ | LOW |
| **Offline** | ❌ | ✅ | ✅ | FUTURE |

---

## 🎯 Final Recommendation

**Build these 8 endpoints next** (in order):

1. **Search** - Can't use the app without it
2. **Recently Played** - Basic UX expectation
3. **Favorites** - One query, huge value
4. **Profile Update** - Basic user management
5. **Enhanced Interactions** - Just add fields, massive ML value
6. **Password Reset** - Security requirement
7. **Browse Genres** - Discovery mechanism
8. **Email Verification** - Production requirement

After these, your backend will be **production-ready** for an MVP launch.

**Want me to implement these now?**