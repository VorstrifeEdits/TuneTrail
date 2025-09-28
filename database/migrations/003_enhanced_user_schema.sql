-- Enhanced User Schema for ML & Personalization
-- Date: September 2025
-- Version: 3.0.0

-- Add new columns to users table
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS first_name VARCHAR(255),
    ADD COLUMN IF NOT EXISTS last_name VARCHAR(255),
    ADD COLUMN IF NOT EXISTS display_name VARCHAR(255),
    ADD COLUMN IF NOT EXISTS pronouns VARCHAR(50),
    ADD COLUMN IF NOT EXISTS bio TEXT,
    ADD COLUMN IF NOT EXISTS location VARCHAR(255),
    ADD COLUMN IF NOT EXISTS website VARCHAR(500),
    ADD COLUMN IF NOT EXISTS birth_date DATE,
    ADD COLUMN IF NOT EXISTS gender VARCHAR(50),
    ADD COLUMN IF NOT EXISTS country_code VARCHAR(2),
    ADD COLUMN IF NOT EXISTS language_code VARCHAR(5) DEFAULT 'en',
    ADD COLUMN IF NOT EXISTS timezone VARCHAR(100),

    -- Account settings
    ADD COLUMN IF NOT EXISTS account_type VARCHAR(50) DEFAULT 'free',
    ADD COLUMN IF NOT EXISTS subscription_status VARCHAR(50) DEFAULT 'active',
    ADD COLUMN IF NOT EXISTS trial_ends_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS premium_since TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS two_factor_enabled BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS password_last_changed TIMESTAMP WITH TIME ZONE,

    -- Privacy & consent
    ADD COLUMN IF NOT EXISTS public_profile BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS show_listening_history BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS discoverable BOOLEAN DEFAULT true,
    ADD COLUMN IF NOT EXISTS allow_explicit_content BOOLEAN DEFAULT true,
    ADD COLUMN IF NOT EXISTS marketing_emails_consent BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS newsletter_subscribed BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS terms_accepted_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS privacy_accepted_at TIMESTAMP WITH TIME ZONE,

    -- Signup context
    ADD COLUMN IF NOT EXISTS signup_source VARCHAR(50),
    ADD COLUMN IF NOT EXISTS signup_device_type VARCHAR(50),
    ADD COLUMN IF NOT EXISTS signup_ip_address INET,
    ADD COLUMN IF NOT EXISTS referral_code VARCHAR(100),
    ADD COLUMN IF NOT EXISTS utm_source VARCHAR(255),
    ADD COLUMN IF NOT EXISTS utm_campaign VARCHAR(255),

    -- Account state
    ADD COLUMN IF NOT EXISTS profile_completed_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS onboarding_step VARCHAR(50),
    ADD COLUMN IF NOT EXISTS last_active_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS deletion_requested_at TIMESTAMP WITH TIME ZONE;

-- Create indexes for new columns
CREATE INDEX IF NOT EXISTS idx_users_first_name ON users(first_name);
CREATE INDEX IF NOT EXISTS idx_users_last_name ON users(last_name);
CREATE INDEX IF NOT EXISTS idx_users_country_code ON users(country_code);
CREATE INDEX IF NOT EXISTS idx_users_account_type ON users(account_type);
CREATE INDEX IF NOT EXISTS idx_users_onboarding_step ON users(onboarding_step);

-- Create user_sessions table for auth session management
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    token_hash VARCHAR(255) NOT NULL UNIQUE,
    device_id VARCHAR(255),
    device_name VARCHAR(255),
    device_type VARCHAR(50),

    ip_address INET,
    user_agent TEXT,
    location VARCHAR(255),

    is_active BOOLEAN DEFAULT true,
    last_used_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT user_sessions_user_id_idx FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_token_hash ON user_sessions(token_hash);
CREATE INDEX idx_user_sessions_is_active ON user_sessions(is_active);
CREATE INDEX idx_user_sessions_expires_at ON user_sessions(expires_at);

-- Create login_history table for security audit
CREATE TABLE IF NOT EXISTS login_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    success BOOLEAN NOT NULL,
    failure_reason VARCHAR(255),

    ip_address INET,
    user_agent TEXT,
    device_type VARCHAR(50),
    location VARCHAR(255),

    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_login_history_user_id ON login_history(user_id);
CREATE INDEX idx_login_history_timestamp ON login_history(timestamp DESC);
CREATE INDEX idx_login_history_success ON login_history(success);

-- Migrate existing full_name to first_name/last_name
UPDATE users
SET
    first_name = SPLIT_PART(full_name, ' ', 1),
    last_name = NULLIF(SUBSTRING(full_name FROM POSITION(' ' IN full_name) + 1), '')
WHERE full_name IS NOT NULL AND first_name IS NULL;

-- Set display_name to first_name for existing users
UPDATE users
SET display_name = first_name
WHERE display_name IS NULL AND first_name IS NOT NULL;