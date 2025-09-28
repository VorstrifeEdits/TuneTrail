-- TuneTrail Sample Data for Development
-- Date: September 2025

-- Sample users
INSERT INTO users (id, org_id, email, username, full_name, role, email_verified)
VALUES
    (uuid_generate_v4(), (SELECT id FROM organizations WHERE slug = 'default'), 'admin@tunetrail.dev', 'admin', 'Admin User', 'owner', true),
    (uuid_generate_v4(), (SELECT id FROM organizations WHERE slug = 'default'), 'user1@tunetrail.dev', 'musiclover1', 'Music Lover', 'user', true),
    (uuid_generate_v4(), (SELECT id FROM organizations WHERE slug = 'default'), 'user2@tunetrail.dev', 'djmaster', 'DJ Master', 'user', true)
ON CONFLICT DO NOTHING;

-- Sample tracks (placeholder data)
INSERT INTO tracks (id, org_id, title, artist, album, genre, duration_seconds, release_year)
VALUES
    (uuid_generate_v4(), (SELECT id FROM organizations WHERE slug = 'default'), 'Sample Track 1', 'Artist A', 'Album X', 'Electronic', 240, 2024),
    (uuid_generate_v4(), (SELECT id FROM organizations WHERE slug = 'default'), 'Sample Track 2', 'Artist B', 'Album Y', 'Rock', 180, 2023),
    (uuid_generate_v4(), (SELECT id FROM organizations WHERE slug = 'default'), 'Sample Track 3', 'Artist A', 'Album Z', 'Electronic', 200, 2024)
ON CONFLICT DO NOTHING;