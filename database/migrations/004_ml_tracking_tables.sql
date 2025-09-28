-- ML Tracking Tables for Superior Recommendation Engine
-- Date: September 2025
-- Version: 4.0.0

-- Search query logging (critical for search improvement)
CREATE TABLE IF NOT EXISTS search_queries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    -- Query details
    query TEXT NOT NULL,
    search_type VARCHAR(50) NOT NULL,
    filters JSONB DEFAULT '{}',

    -- Results
    results_count INTEGER DEFAULT 0,
    clicked_result_id UUID,
    clicked_result_type VARCHAR(50),
    clicked_position INTEGER,
    time_to_click_ms INTEGER,

    -- Context
    source VARCHAR(50),
    device_type VARCHAR(50),
    session_id UUID,

    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_search_queries_user_id ON search_queries(user_id);
CREATE INDEX idx_search_queries_timestamp ON search_queries(timestamp DESC);
CREATE INDEX idx_search_queries_query ON search_queries USING gin(to_tsvector('english', query));
CREATE INDEX idx_search_queries_clicked ON search_queries(clicked_result_id) WHERE clicked_result_id IS NOT NULL;

-- Recommendation impressions (critical for CTR calculation)
CREATE TABLE IF NOT EXISTS recommendation_impressions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    track_id UUID REFERENCES tracks(id) ON DELETE CASCADE,

    -- Recommendation context
    recommendation_id UUID,
    model_type VARCHAR(100) NOT NULL,
    model_version VARCHAR(50),
    score FLOAT,
    reason TEXT,

    -- Impression details
    position INTEGER NOT NULL,
    context_type VARCHAR(50),
    context_id UUID,

    -- Outcome
    was_clicked BOOLEAN DEFAULT false,
    clicked_at TIMESTAMP WITH TIME ZONE,
    was_played BOOLEAN DEFAULT false,
    was_liked BOOLEAN DEFAULT false,
    was_saved BOOLEAN DEFAULT false,

    -- Timing
    shown_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    time_visible_ms INTEGER
);

CREATE INDEX idx_recommendation_impressions_user_id ON recommendation_impressions(user_id);
CREATE INDEX idx_recommendation_impressions_track_id ON recommendation_impressions(track_id);
CREATE INDEX idx_recommendation_impressions_shown_at ON recommendation_impressions(shown_at DESC);
CREATE INDEX idx_recommendation_impressions_was_clicked ON recommendation_impressions(was_clicked);
CREATE INDEX idx_recommendation_impressions_model_type ON recommendation_impressions(model_type);

-- View events (interest signals without play)
CREATE TABLE IF NOT EXISTS content_views (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    -- What was viewed
    content_type VARCHAR(50) NOT NULL CHECK (content_type IN ('track', 'album', 'artist', 'playlist', 'user_profile')),
    content_id UUID NOT NULL,

    -- View context
    source VARCHAR(50),
    source_id UUID,
    session_id UUID,

    -- Engagement
    time_spent_ms INTEGER,
    scrolled_to_bottom BOOLEAN DEFAULT false,

    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_content_views_user_id ON content_views(user_id);
CREATE INDEX idx_content_views_content_type ON content_views(content_type);
CREATE INDEX idx_content_views_content_id ON content_views(content_id);
CREATE INDEX idx_content_views_timestamp ON content_views(timestamp DESC);

-- Player events (granular playback tracking)
CREATE TABLE IF NOT EXISTS player_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    track_id UUID REFERENCES tracks(id) ON DELETE CASCADE,
    session_id UUID,

    -- Event details
    event_type VARCHAR(50) NOT NULL CHECK (event_type IN ('seek', 'buffer_start', 'buffer_end', 'error', 'quality_change', 'volume_change', 'scrub')),
    position_ms INTEGER,

    -- Seek-specific
    seek_from_ms INTEGER,
    seek_to_ms INTEGER,

    -- Buffer-specific
    buffer_duration_ms INTEGER,

    -- Error-specific
    error_code VARCHAR(50),
    error_message TEXT,

    -- Event metadata
    event_metadata JSONB DEFAULT '{}',

    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_player_events_user_id ON player_events(user_id);
CREATE INDEX idx_player_events_track_id ON player_events(track_id);
CREATE INDEX idx_player_events_event_type ON player_events(event_type);
CREATE INDEX idx_player_events_timestamp ON player_events(timestamp DESC);
CREATE INDEX idx_player_events_session_id ON player_events(session_id);

-- Click-through tracking (for any clickable element)
CREATE TABLE IF NOT EXISTS click_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    -- What was clicked
    element_type VARCHAR(50) NOT NULL,
    element_id UUID,
    element_text TEXT,

    -- Context
    page_type VARCHAR(50),
    page_id UUID,
    position INTEGER,

    -- A/B testing
    variant VARCHAR(50),
    experiment_id UUID,

    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_click_events_user_id ON click_events(user_id);
CREATE INDEX idx_click_events_element_type ON click_events(element_type);
CREATE INDEX idx_click_events_timestamp ON click_events(timestamp DESC);

-- Batch interaction events (for offline sync)
CREATE TABLE IF NOT EXISTS interaction_batch_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    -- Batch details
    device_id VARCHAR(255),
    batch_size INTEGER,
    events JSONB NOT NULL,

    -- Processing
    processed BOOLEAN DEFAULT false,
    processed_at TIMESTAMP WITH TIME ZONE,

    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_interaction_batch_queue_processed ON interaction_batch_queue(processed) WHERE NOT processed;