-- ============================================================================
-- AutoFix / Breaklytix — Admin & account-management schema alignment
-- ============================================================================
-- WHY THIS FILE EXISTS
--   `backend/app/routers/admin.py` selects users.is_admin / users.is_agency and
--   the suspend columns, `deps.require_admin` reads users.is_admin, and
--   email/billing code writes email_deliveries / notification_preferences /
--   stripe_webhook_events. None of the older migration files create the admin
--   flags, and the support-table SQL was only ever applied ad-hoc. A missing
--   column makes PostgREST reject the whole select (PGRST204) which surfaces to
--   the Admin Panel as an unhandled 500 "Internal server error".
--
--   Every statement here is idempotent (IF NOT EXISTS / DO-block guarded), so
--   applying it on an already-aligned database is a no-op. Safe to re-run.
--
-- Apply via: Supabase SQL editor, or Supabase Management API database/query.
-- ============================================================================

-- 1. Admin & agency flags on users (referenced by admin.py, deps.py,
--    changelog/admin.py, consent.py, dashboard layout)
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin  boolean NOT NULL DEFAULT false;
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_agency boolean NOT NULL DEFAULT false;
CREATE INDEX IF NOT EXISTS idx_users_is_admin ON users(is_admin) WHERE is_admin;

-- 2. Account suspension management (referenced by admin.py, auth.py, deps.py)
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_suspended     boolean NOT NULL DEFAULT false;
ALTER TABLE users ADD COLUMN IF NOT EXISTS suspended_at     timestamptz;
ALTER TABLE users ADD COLUMN IF NOT EXISTS suspended_reason text;
CREATE INDEX IF NOT EXISTS idx_users_suspended ON users(is_suspended);

-- 3. system_health (referenced by routers/admin.py /admin/health, cronlog.py)
CREATE TABLE IF NOT EXISTS system_health (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    job_name      text NOT NULL,
    status        text NOT NULL,
    duration_ms   integer,
    error_message text,
    ran_at        timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_system_health_job ON system_health (job_name, ran_at DESC);

-- 4. email_deliveries (referenced by email_service.py, digital_twin.py)
CREATE TABLE IF NOT EXISTS email_deliveries (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            uuid,
    alert_id           uuid,
    alert_type         text,
    recipient          text,
    subject            text,
    status             text NOT NULL DEFAULT 'queued',
    provider           text NOT NULL DEFAULT 'resend',
    provider_message_id text,
    error_category     text,
    http_status        integer,
    fingerprint        text,
    created_at         timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_email_deliveries_fingerprint ON email_deliveries (fingerprint, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_deliveries_user        ON email_deliveries (user_id, created_at DESC);

-- 5. notification_preferences (referenced by email_service.py, routers/notifications.py)
CREATE TABLE IF NOT EXISTS notification_preferences (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       uuid NOT NULL,
    category      text NOT NULL,
    email_enabled boolean NOT NULL DEFAULT true,
    updated_at    timestamptz,
    UNIQUE (user_id, category)
);

-- 6. stripe_webhook_events (referenced by billing.py webhook idempotency)
CREATE TABLE IF NOT EXISTS stripe_webhook_events (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    stripe_event_id text UNIQUE NOT NULL,
    event_type      text,
    payload         jsonb DEFAULT '{}',
    created_at      timestamptz DEFAULT now()
);

-- 7. Grant the service role full access on newly created tables (Supabase
--    defaults to no grants on tables created via SQL editor for non-owner
--    roles; the backend uses the service role).
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['system_health','email_deliveries','notification_preferences','stripe_webhook_events']
  LOOP
    IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname='public' AND tablename=t) THEN
      EXECUTE format('GRANT ALL ON TABLE public.%I TO service_role', t);
    END IF;
  END LOOP;
END $$;

-- ============================================================================
-- 8. Alert read-state (alert lifecycle: UNREAD/READ backed by the database)
-- ============================================================================
-- `read_at IS NULL` => UNREAD, `read_at NOT NULL` => READ. Idempotent, additive,
-- keeps the existing status model (sent/pending/dismissed) untouched.
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS read_at timestamptz;
CREATE INDEX IF NOT EXISTS idx_alerts_unread ON alerts (repo_id, read_at) WHERE read_at IS NULL;
