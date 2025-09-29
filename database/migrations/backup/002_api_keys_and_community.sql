-- TuneTrail API Keys and Community Features Migration
-- Date: September 2025
-- Version: 2.0.0

-- API Keys table
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,

    -- Key details
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    key_prefix VARCHAR(20) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,

    -- Scopes and permissions
    scopes TEXT[] DEFAULT ARRAY[]::TEXT[],
    permissions JSONB DEFAULT '{}',

    -- Environment
    environment VARCHAR(50) DEFAULT 'production' CHECK (environment IN ('development', 'staging', 'production')),

    -- Rate limiting
    rate_limit_requests_per_minute INTEGER DEFAULT 60,
    rate_limit_requests_per_hour INTEGER DEFAULT 1000,
    rate_limit_requests_per_day INTEGER DEFAULT 10000,

    -- Usage tracking
    total_requests INTEGER DEFAULT 0,
    last_used_at TIMESTAMP WITH TIME ZONE,

    -- Status
    is_active BOOLEAN DEFAULT true,
    expires_at TIMESTAMP WITH TIME ZONE,

    -- Metadata
    ip_whitelist TEXT[],
    user_agent_whitelist TEXT[],
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    revoked_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT valid_rate_limits CHECK (
        rate_limit_requests_per_minute > 0 AND
        rate_limit_requests_per_hour > 0 AND
        rate_limit_requests_per_day > 0
    )
);

CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_org_id ON api_keys(org_id);
CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_key_prefix ON api_keys(key_prefix);
CREATE INDEX idx_api_keys_is_active ON api_keys(is_active);

-- API Key usage logs
CREATE TABLE api_key_usage_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    api_key_id UUID REFERENCES api_keys(id) ON DELETE CASCADE,

    -- Request details
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER,
    response_time_ms INTEGER,

    -- Client info
    ip_address INET,
    user_agent TEXT,
    referer TEXT,

    -- Usage metrics
    request_size_bytes INTEGER,
    response_size_bytes INTEGER,

    -- Error tracking
    error_message TEXT,
    error_type VARCHAR(100),

    -- Metadata
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_api_key_usage_logs_api_key_id ON api_key_usage_logs(api_key_id);
CREATE INDEX idx_api_key_usage_logs_timestamp ON api_key_usage_logs(timestamp DESC);
CREATE INDEX idx_api_key_usage_logs_endpoint ON api_key_usage_logs(endpoint);
CREATE INDEX idx_api_key_usage_logs_status_code ON api_key_usage_logs(status_code);

-- Partition by month for better performance
CREATE TABLE api_key_usage_logs_partitioned (
    LIKE api_key_usage_logs INCLUDING ALL
) PARTITION BY RANGE (timestamp);

-- Webhooks table
CREATE TABLE webhooks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,

    -- Webhook details
    name VARCHAR(100) NOT NULL,
    url TEXT NOT NULL,
    secret VARCHAR(255) NOT NULL,

    -- Events to listen for
    events TEXT[] NOT NULL,

    -- Status
    is_active BOOLEAN DEFAULT true,

    -- Retry configuration
    retry_on_failure BOOLEAN DEFAULT true,
    max_retries INTEGER DEFAULT 3,
    retry_delay_seconds INTEGER DEFAULT 60,

    -- Statistics
    total_deliveries INTEGER DEFAULT 0,
    successful_deliveries INTEGER DEFAULT 0,
    failed_deliveries INTEGER DEFAULT 0,
    last_delivery_at TIMESTAMP WITH TIME ZONE,
    last_success_at TIMESTAMP WITH TIME ZONE,
    last_failure_at TIMESTAMP WITH TIME ZONE,

    -- Metadata
    headers JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_webhooks_user_id ON webhooks(user_id);
CREATE INDEX idx_webhooks_org_id ON webhooks(org_id);
CREATE INDEX idx_webhooks_is_active ON webhooks(is_active);

-- Webhook delivery logs
CREATE TABLE webhook_deliveries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    webhook_id UUID REFERENCES webhooks(id) ON DELETE CASCADE,

    -- Event details
    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,

    -- Delivery details
    status VARCHAR(50) NOT NULL CHECK (status IN ('pending', 'success', 'failed', 'retrying')),
    http_status_code INTEGER,
    response_body TEXT,
    error_message TEXT,

    -- Timing
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    next_retry_at TIMESTAMP WITH TIME ZONE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    delivered_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_webhook_deliveries_webhook_id ON webhook_deliveries(webhook_id);
CREATE INDEX idx_webhook_deliveries_status ON webhook_deliveries(status);
CREATE INDEX idx_webhook_deliveries_event_type ON webhook_deliveries(event_type);
CREATE INDEX idx_webhook_deliveries_next_retry_at ON webhook_deliveries(next_retry_at) WHERE status = 'retrying';

-- Community features: Model sharing
CREATE TABLE shared_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    org_id UUID REFERENCES organizations(id) ON DELETE SET NULL,

    -- Model details
    name VARCHAR(255) NOT NULL,
    description TEXT,
    model_type VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,

    -- Files
    model_url TEXT NOT NULL,
    config_url TEXT,
    weights_size_bytes BIGINT,

    -- Performance metrics
    accuracy FLOAT,
    precision_score FLOAT,
    recall_score FLOAT,
    f1_score FLOAT,
    training_metrics JSONB DEFAULT '{}',

    -- Community engagement
    downloads_count INTEGER DEFAULT 0,
    stars_count INTEGER DEFAULT 0,
    forks_count INTEGER DEFAULT 0,

    -- Visibility
    is_public BOOLEAN DEFAULT false,
    license VARCHAR(100) DEFAULT 'MIT',

    -- Tags for discovery
    tags TEXT[],
    category VARCHAR(100),

    -- Metadata
    training_data_info JSONB DEFAULT '{}',
    requirements TEXT[],
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    published_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_shared_models_user_id ON shared_models(user_id);
CREATE INDEX idx_shared_models_is_public ON shared_models(is_public);
CREATE INDEX idx_shared_models_model_type ON shared_models(model_type);
CREATE INDEX idx_shared_models_tags ON shared_models USING gin(tags);
CREATE INDEX idx_shared_models_stars_count ON shared_models(stars_count DESC);
CREATE INDEX idx_shared_models_downloads_count ON shared_models(downloads_count DESC);

-- Model stars/likes
CREATE TABLE model_stars (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id UUID REFERENCES shared_models(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(model_id, user_id)
);

CREATE INDEX idx_model_stars_model_id ON model_stars(model_id);
CREATE INDEX idx_model_stars_user_id ON model_stars(user_id);

-- Community discussions/forum
CREATE TABLE discussions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,

    -- Discussion details
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(100) NOT NULL,

    -- Status
    is_pinned BOOLEAN DEFAULT false,
    is_locked BOOLEAN DEFAULT false,
    is_resolved BOOLEAN DEFAULT false,

    -- Engagement
    views_count INTEGER DEFAULT 0,
    replies_count INTEGER DEFAULT 0,
    upvotes_count INTEGER DEFAULT 0,

    -- Tags
    tags TEXT[],

    -- Related resources
    related_model_id UUID REFERENCES shared_models(id) ON DELETE SET NULL,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_discussions_user_id ON discussions(user_id);
CREATE INDEX idx_discussions_category ON discussions(category);
CREATE INDEX idx_discussions_is_pinned ON discussions(is_pinned);
CREATE INDEX idx_discussions_tags ON discussions USING gin(tags);
CREATE INDEX idx_discussions_last_activity_at ON discussions(last_activity_at DESC);

-- Discussion replies
CREATE TABLE discussion_replies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    discussion_id UUID REFERENCES discussions(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    parent_reply_id UUID REFERENCES discussion_replies(id) ON DELETE CASCADE,

    -- Reply content
    content TEXT NOT NULL,

    -- Status
    is_accepted_answer BOOLEAN DEFAULT false,
    is_edited BOOLEAN DEFAULT false,

    -- Engagement
    upvotes_count INTEGER DEFAULT 0,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_discussion_replies_discussion_id ON discussion_replies(discussion_id);
CREATE INDEX idx_discussion_replies_user_id ON discussion_replies(user_id);
CREATE INDEX idx_discussion_replies_parent_reply_id ON discussion_replies(parent_reply_id);

-- User projects showcase
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    -- Project details
    name VARCHAR(255) NOT NULL,
    description TEXT,
    tagline VARCHAR(500),

    -- Links
    url TEXT,
    github_url TEXT,
    demo_url TEXT,

    -- Media
    cover_image_url TEXT,
    screenshots TEXT[],
    video_url TEXT,

    -- Technology
    tech_stack TEXT[],
    used_models TEXT[],

    -- Engagement
    upvotes_count INTEGER DEFAULT 0,
    views_count INTEGER DEFAULT 0,

    -- Visibility
    is_featured BOOLEAN DEFAULT false,
    is_public BOOLEAN DEFAULT true,

    -- Metadata
    tags TEXT[],
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_projects_is_featured ON projects(is_featured);
CREATE INDEX idx_projects_is_public ON projects(is_public);
CREATE INDEX idx_projects_tags ON projects USING gin(tags);
CREATE INDEX idx_projects_upvotes_count ON projects(upvotes_count DESC);

-- Service status for status page
CREATE TABLE service_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_name VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL CHECK (status IN ('operational', 'degraded', 'partial_outage', 'major_outage', 'maintenance')),
    message TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_service_status_service_name ON service_status(service_name);
CREATE INDEX idx_service_status_started_at ON service_status(started_at DESC);

-- API scopes definition
CREATE TABLE api_scopes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scope VARCHAR(100) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(100) NOT NULL,
    is_premium BOOLEAN DEFAULT false,
    required_plan VARCHAR(50) CHECK (required_plan IN ('free', 'starter', 'pro', 'enterprise')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default API scopes
INSERT INTO api_scopes (scope, description, category, is_premium, required_plan) VALUES
    ('read:tracks', 'Read track information', 'tracks', false, 'free'),
    ('write:tracks', 'Create and update tracks', 'tracks', false, 'free'),
    ('delete:tracks', 'Delete tracks', 'tracks', false, 'free'),
    ('read:recommendations', 'Get music recommendations', 'recommendations', false, 'free'),
    ('read:playlists', 'Read playlist information', 'playlists', false, 'free'),
    ('write:playlists', 'Create and update playlists', 'playlists', false, 'free'),
    ('delete:playlists', 'Delete playlists', 'playlists', false, 'free'),
    ('read:audio_features', 'Read audio feature analysis', 'audio', false, 'starter'),
    ('write:audio_features', 'Process audio and extract features', 'audio', true, 'starter'),
    ('train:models', 'Train custom ML models', 'ml', true, 'pro'),
    ('read:analytics', 'Access analytics and insights', 'analytics', true, 'pro'),
    ('admin:webhooks', 'Manage webhooks', 'admin', true, 'pro'),
    ('admin:billing', 'Access billing information', 'admin', true, 'starter')
ON CONFLICT DO NOTHING;

-- Add triggers
CREATE TRIGGER update_api_keys_updated_at BEFORE UPDATE ON api_keys FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_webhooks_updated_at BEFORE UPDATE ON webhooks FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_shared_models_updated_at BEFORE UPDATE ON shared_models FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_discussions_updated_at BEFORE UPDATE ON discussions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();