-- Phase B: Changelog Monitoring Database Migration
-- RUN STATUS: Executed via Supabase Management API (2026-09-04)

-- NOTE: system_health table ALREADY EXISTS with schema (id, job_name, status,
-- duration_ms, error_message, ran_at). Our scheduler writes to the EXISTING
-- schema, so we do NOT recreate it here.

-- 1. changelog_events new columns (DONE via API)
-- ALTER TABLE changelog_events ADD COLUMN IF NOT EXISTS content_hash TEXT;
-- ALTER TABLE changelog_events ADD COLUMN IF NOT EXISTS admin_approved BOOLEAN DEFAULT FALSE;
-- ALTER TABLE changelog_events ADD COLUMN IF NOT EXISTS approved_by UUID;
-- ALTER TABLE changelog_events ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ;
-- ALTER TABLE changelog_events ADD COLUMN IF NOT EXISTS disabled BOOLEAN DEFAULT FALSE;
-- ALTER TABLE changelog_events ADD COLUMN IF NOT EXISTS disabled_by UUID;
-- ALTER TABLE changelog_events ADD COLUMN IF NOT EXISTS disabled_at TIMESTAMPTZ;
-- ALTER TABLE changelog_events ADD COLUMN IF NOT EXISTS disabled_reason TEXT;
-- ALTER TABLE changelog_events ADD COLUMN IF NOT EXISTS affected_endpoints JSONB;
-- ALTER TABLE changelog_events ADD COLUMN IF NOT EXISTS affected_sdks JSONB;
-- ALTER TABLE changelog_events ADD COLUMN IF NOT EXISTS affected_versions JSONB;

-- 2. alerts confidence column (DONE via API)
-- ALTER TABLE alerts ADD COLUMN IF NOT EXISTS confidence TEXT DEFAULT 'medium';

-- 3. Indexes for deduplication + pending (DONE via API)
-- CREATE INDEX IF NOT EXISTS idx_changelog_events_dedup
--   ON changelog_events (api_name, source_url, content_hash);
-- CREATE INDEX IF NOT EXISTS idx_changelog_events_pending
--   ON changelog_events (processed_at) WHERE processed_at IS NULL;

-- ===========================================================================
-- REMAINING (if re-running from scratch on a fresh DB) — uncomment below:
-- ===========================================================================
-- CREATE TABLE IF NOT EXISTS system_health (
--     id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
--     job_name TEXT NOT NULL,
--     status TEXT NOT NULL,
--     duration_ms INTEGER,
--     error_message TEXT,
--     ran_at TIMESTAMPTZ DEFAULT NOW()
-- );
-- CREATE INDEX IF NOT EXISTS idx_system_health_job ON system_health (job_name, ran_at DESC);
