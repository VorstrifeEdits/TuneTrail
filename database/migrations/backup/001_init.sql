-- TuneTrail Database Schema - Initial Migration
-- Date: September 2025
-- Version: 1.0.0

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Organizations table (for multi-tenancy)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    plan VARCHAR(50) NOT NULL DEFAULT 'free' CHECK (plan IN ('free', 'starter', 'pro', 'enterprise')),
    max_tracks INTEGER DEFAULT 1000,
    max_users INTEGER DEFAULT 1,
    features JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_organizations_slug ON organizations(slug);
CREATE INDEX idx_organizations_plan ON organizations(plan);

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255),
    full_name VARCHAR(255),
    avatar_url TEXT,
    role VARCHAR(50) DEFAULT 'user' CHECK (role IN ('user', 'admin', 'owner')),
    is_active BOOLEAN DEFAULT true,
    email_verified BOOLEAN DEFAULT false,
    last_login TIMESTAMP WITH TIME ZONE,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_org_id ON users(org_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);

-- Tracks table
CREATE TABLE tracks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    artist VARCHAR(500),
    album VARCHAR(500),
    genre VARCHAR(100),
    duration_seconds INTEGER,
    release_year INTEGER,
    isrc VARCHAR(50),
    audio_url TEXT,
    cover_url TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_tracks_org_id ON tracks(org_id);
CREATE INDEX idx_tracks_artist ON tracks(artist);
CREATE INDEX idx_tracks_genre ON tracks(genre);
CREATE INDEX idx_tracks_title_search ON tracks USING gin(to_tsvector('english', title));

-- Audio features table
CREATE TABLE audio_features (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    track_id UUID REFERENCES tracks(id) ON DELETE CASCADE,

    -- Basic audio features
    tempo FLOAT,
    key INTEGER,
    mode INTEGER,
    time_signature INTEGER,
    loudness FLOAT,

    -- Spectral features
    spectral_centroid FLOAT,
    spectral_bandwidth FLOAT,
    spectral_rolloff FLOAT,
    zero_crossing_rate FLOAT,

    -- Rhythm features
    beats_per_minute FLOAT,
    rhythm_strength FLOAT,

    -- Harmonic features
    harmonicity FLOAT,
    chroma_features FLOAT[],

    -- Energy features
    energy FLOAT,
    danceability FLOAT,
    valence FLOAT,
    acousticness FLOAT,
    instrumentalness FLOAT,
    liveness FLOAT,
    speechiness FLOAT,

    -- High-dimensional embeddings (512-dim vector)
    embedding vector(512),

    -- MFCC features
    mfcc_features FLOAT[],

    -- Metadata
    extraction_version VARCHAR(50),
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(track_id)
);

CREATE INDEX idx_audio_features_track_id ON audio_features(track_id);
CREATE INDEX idx_audio_features_embedding ON audio_features USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- User interactions table (for collaborative filtering)
CREATE TABLE interactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    track_id UUID REFERENCES tracks(id) ON DELETE CASCADE,
    interaction_type VARCHAR(50) NOT NULL CHECK (interaction_type IN ('play', 'skip', 'like', 'dislike', 'playlist_add', 'share')),
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    play_duration_seconds INTEGER,
    context JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(user_id, track_id, interaction_type, created_at)
);

CREATE INDEX idx_interactions_user_id ON interactions(user_id);
CREATE INDEX idx_interactions_track_id ON interactions(track_id);
CREATE INDEX idx_interactions_type ON interactions(interaction_type);
CREATE INDEX idx_interactions_created_at ON interactions(created_at DESC);

-- Playlists table
CREATE TABLE playlists (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT false,
    cover_url TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_playlists_user_id ON playlists(user_id);
CREATE INDEX idx_playlists_org_id ON playlists(org_id);
CREATE INDEX idx_playlists_is_public ON playlists(is_public);

-- Playlist tracks junction table
CREATE TABLE playlist_tracks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    playlist_id UUID REFERENCES playlists(id) ON DELETE CASCADE,
    track_id UUID REFERENCES tracks(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    added_by UUID REFERENCES users(id) ON DELETE SET NULL,

    UNIQUE(playlist_id, track_id)
);

CREATE INDEX idx_playlist_tracks_playlist_id ON playlist_tracks(playlist_id);
CREATE INDEX idx_playlist_tracks_track_id ON playlist_tracks(track_id);
CREATE INDEX idx_playlist_tracks_position ON playlist_tracks(playlist_id, position);

-- Recommendations table (cache)
CREATE TABLE recommendations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    track_id UUID REFERENCES tracks(id) ON DELETE CASCADE,
    score FLOAT NOT NULL,
    model_type VARCHAR(100) NOT NULL,
    model_version VARCHAR(50),
    context JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,

    UNIQUE(user_id, track_id, model_type)
);

CREATE INDEX idx_recommendations_user_id ON recommendations(user_id);
CREATE INDEX idx_recommendations_score ON recommendations(score DESC);
CREATE INDEX idx_recommendations_expires_at ON recommendations(expires_at);

-- API usage tracking (for billing)
CREATE TABLE api_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER,
    response_time_ms INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_api_usage_org_id ON api_usage(org_id);
CREATE INDEX idx_api_usage_timestamp ON api_usage(timestamp DESC);

-- Model training jobs
CREATE TABLE training_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    model_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    config JSONB DEFAULT '{}',
    metrics JSONB DEFAULT '{}',
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_training_jobs_org_id ON training_jobs(org_id);
CREATE INDEX idx_training_jobs_status ON training_jobs(status);

-- Row-level security policies
ALTER TABLE tracks ENABLE ROW LEVEL SECURITY;
ALTER TABLE interactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE playlists ENABLE ROW LEVEL SECURITY;

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers for updated_at
CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_tracks_updated_at BEFORE UPDATE ON tracks FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_playlists_updated_at BEFORE UPDATE ON playlists FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default organization for community edition
INSERT INTO organizations (name, slug, plan, max_tracks, max_users)
VALUES ('Default Community', 'default', 'free', 999999, 999999)
ON CONFLICT DO NOTHING;