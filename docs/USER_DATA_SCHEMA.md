# Comprehensive User Data Schema for ML-Powered Music Platform

## Current vs. Recommended User Fields

### **Identity & Account** (Core)
```python
# CURRENT ✅
- email: EmailStr (unique, required)
- username: str (unique, optional)
- password_hash: str
- full_name: str (single field) ❌

# RECOMMENDED ✅
- email: EmailStr (unique, required)
- username: str (unique, optional)
- password_hash: str
- first_name: str (required)
- last_name: str (required)
- display_name: str (optional, defaults to first_name)
- pronouns: str (optional: he/him, she/her, they/them, custom)
```

### **Profile & Personalization**
```python
# CURRENT
- avatar_url: str ✅
- full_name: str (inadequate)

# RECOMMENDED
- avatar_url: str ✅
- banner_url: str (profile header image)
- bio: text (500 chars, about me)
- location: str (city, country)
- website: str
- birth_date: date (for age-based recs, optional)
- gender: str (optional, for personalization)
- country_code: str (ISO 3166-1 alpha-2)
- language_code: str (ISO 639-1, UI language)
- timezone: str (IANA timezone)
```

### **Account Settings**
```python
# CURRENT
- is_active: bool ✅
- email_verified: bool ✅
- role: str ✅
- last_login: datetime ✅

# RECOMMENDED (ADD)
- account_type: str (free, starter, pro, enterprise)
- subscription_status: str (active, cancelled, past_due)
- trial_ends_at: datetime
- premium_since: datetime
- two_factor_enabled: bool
- password_last_changed: datetime
- last_password_reset: datetime
```

### **Privacy & Consent** (GDPR + Marketing)
```python
# CURRENT
- None ❌

# RECOMMENDED (CRITICAL)
- public_profile: bool (default: false)
- show_listening_history: bool (default: false)
- discoverable: bool (can others find you in search)
- allow_explicit_content: bool (default: true)

# Marketing & Communications
- marketing_emails_consent: bool
- product_updates_consent: bool
- newsletter_subscribed: bool
- push_notifications_enabled: bool
- email_notification_frequency: str (realtime, daily, weekly, never)

# Privacy Controls
- share_listening_data: bool (for public stats)
- allow_personalized_ads: bool
- data_processing_consent: bool
- terms_accepted_at: datetime
- terms_version: str
- privacy_policy_accepted_at: datetime
```

### **ML & Personalization Data**
```python
# CURRENT
- preferences: JSON (good but unstructured) 🟡

# RECOMMENDED (Structured)
user_ml_profile: JSON {
    # Explicit Preferences (from onboarding)
    "favorite_genres": ["Rock", "Electronic", "Jazz"],
    "disliked_genres": ["Country", "Opera"],
    "favorite_artists": ["Queen", "Daft Punk"],
    "favorite_decades": ["1980s", "2000s"],

    # Listening Behavior
    "discovery_mode": 0.5,  # 0.0-1.0 (safe vs. adventurous)
    "preferred_track_length": "3-5min",
    "energy_preference": "medium-high",
    "vocal_preference": "lyrics",  # lyrics, instrumental, mix

    # Context Preferences
    "morning_mood": "energetic",
    "evening_mood": "relaxed",
    "workout_genres": ["EDM", "Rock"],
    "study_genres": ["Lo-fi", "Classical"],

    # Quality Preferences
    "audio_quality": "high",  # low, normal, high, lossless
    "explicit_content_filter": false,

    # Playback Preferences
    "default_shuffle": false,
    "default_repeat": "off",
    "crossfade_duration": 5,
    "normalize_volume": true,
    "gapless_playback": true,
}
```

### **Signup Context** (Analytics & Fraud Prevention)
```python
# CURRENT
- None ❌

# RECOMMENDED
- signup_source: str (web, ios, android, referral, api)
- signup_device_type: str
- signup_ip_address: inet
- signup_user_agent: str
- referral_code: str (who referred them)
- utm_source: str (marketing attribution)
- utm_campaign: str
- utm_medium: str
```

### **Account State & Metadata**
```python
# CURRENT
- created_at: datetime ✅
- updated_at: datetime ✅

# RECOMMENDED (ADD)
- profile_completed_at: datetime (onboarding done)
- onboarding_step: str (current step if incomplete)
- total_listening_time_seconds: int (cached for perf)
- total_tracks_played: int (cached)
- account_status: str (active, suspended, deleted, banned)
- suspension_reason: str
- deletion_requested_at: datetime (GDPR 30-day grace)
- last_active_at: datetime (different from last_login)
```

---

## 🎯 Enhanced Registration Flow

### **Current Registration:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "username": "optional",
  "full_name": "optional"
}
```

### **Recommended Multi-Step Registration:**

#### **Step 1: Account Creation**
```json
{
  "email": "user@example.com",
  "password": "StrongPassword123!",
  "first_name": "John",
  "last_name": "Doe",
  "username": "johndoe",
  "birth_date": "1990-01-15",  // optional
  "country_code": "US",
  "language_code": "en",
  "timezone": "America/Los_Angeles",

  // Consent (GDPR)
  "terms_accepted": true,
  "privacy_policy_accepted": true,
  "marketing_consent": false,

  // Context
  "signup_source": "web",
  "referral_code": "FRIEND123"
}
```

#### **Step 2: Music Preferences (Onboarding)**
```json
POST /api/v1/onboarding/preferences
{
  "favorite_genres": ["Rock", "Electronic", "Jazz"],
  "favorite_artists": ["Queen", "Daft Punk", "Miles Davis"],
  "discovery_mode": 0.7,  // how adventurous
  "listening_contexts": ["workout", "study", "commute"]
}
```

#### **Step 3: Import Existing Library (Optional)**
```json
POST /api/v1/onboarding/import
{
  "source": "spotify",  // spotify, apple_music, youtube_music
  "import_playlists": true,
  "import_favorites": true,
  "import_listening_history": false
}
```

---

## 🔐 Missing Auth Endpoints

### **Current Auth Endpoints:**
1. `POST /auth/register` ✅
2. `POST /auth/login` ✅
3. `GET /auth/me` ✅
4. `POST /auth/forgot-password` ✅
5. `POST /auth/reset-password` ✅
6. `PUT /auth/change-password` ✅
7. `POST /auth/send-verification-email` ✅
8. `POST /auth/verify-email` ✅

### **Missing Critical Auth Endpoints:**

```python
# Token Management
POST /api/v1/auth/refresh-token      # Refresh access token
POST /api/v1/auth/logout             # Invalidate token
POST /api/v1/auth/logout-all-devices # Revoke all sessions

# Session Management
GET  /api/v1/auth/sessions           # List active sessions
DELETE /api/v1/auth/sessions/{id}    # Revoke specific session
DELETE /api/v1/auth/sessions/others  # Logout other devices

# Account Security
GET  /api/v1/auth/security           # Security status
GET  /api/v1/auth/login-history      # Login attempts & locations
POST /api/v1/auth/2fa/setup          # Enable 2FA
POST /api/v1/auth/2fa/verify         # Verify 2FA code
DELETE /api/v1/auth/2fa              # Disable 2FA

# OAuth (Future/SaaS)
GET  /api/v1/auth/oauth/{provider}/authorize
GET  /api/v1/auth/oauth/callback
POST /api/v1/auth/oauth/link         # Link social account
DELETE /api/v1/auth/oauth/unlink

# Account Status
GET  /api/v1/auth/account-status     # Verification status, warnings
POST /api/v1/auth/request-deletion   # GDPR right to be forgotten (30-day delay)
POST /api/v1/auth/cancel-deletion    # Cancel deletion request
```

---

## 🎯 Recommended Implementation

**I'll create:**

1. **Enhanced User Model** with proper name fields
2. **Onboarding Flow** endpoints (3-step process)
3. **Privacy/Consent** management
4. **Account Security** endpoints
5. **Better UserCreate schema** with all fields

**Should I implement these enhancements now?** This will give you:
- ✅ Proper user data for personalization
- ✅ ML-ready user profiles
- ✅ GDPR compliance
- ✅ Professional onboarding
- ✅ Better fraud prevention