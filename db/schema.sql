-- ============================================================================
-- AutoFix API — Phase 1 MVP database schema (Supabase / PostgreSQL)
-- ============================================================================
-- Apply this in the Supabase SQL editor (or `psql`) once per project.
-- It is idempotent-ish: it creates tables/indexes only if they don't exist.
--
-- Design notes (Phase 1):
--   * access_token in `repos` stores a Fernet-ENCRYPTED GitHub token. The
--     backend encrypts before insert and decrypts on read. Never store plaintext.
--   * `changelog_events.content_hash` gives us cheap dedupe so the daily scraper
--     only inserts genuinely new entries.
--   * `changelog_events.processed_at` lets /internal/alerts/process pick up only
--     rows it hasn't handled yet (an event may legitimately produce 0 alerts, so
--     "has no alerts" is NOT a reliable "unprocessed" signal).
--   * UNIQUE constraints make every writer idempotent (safe to re-run scans/cron).
--   * RLS is intentionally left OFF: the FastAPI backend talks to Supabase with
--     the service-role key and is the only client. Enabling RLS + per-user
--     policies is a Phase 2 hardening item.
-- ============================================================================

create extension if not exists "pgcrypto";  -- for gen_random_uuid()

-- ---------------------------------------------------------------------------
-- users
-- ---------------------------------------------------------------------------
create table if not exists users (
  id          uuid primary key default gen_random_uuid(),
  email       text unique not null,
  github_id   text unique,
  github_login text,
  -- Fernet-encrypted GitHub OAuth token. GitHub tokens are per-USER (not per-repo),
  -- so we keep the operational copy here; repos.access_token mirrors it per the spec.
  github_access_token text,
  plan        text not null default 'free',
  created_at  timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- repos
-- ---------------------------------------------------------------------------
create table if not exists repos (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references users(id) on delete cascade,
  github_repo_id  text not null,
  full_name       text not null,               -- e.g. "hashir/my-app"
  default_branch  text not null default 'main',
  access_token    text not null,               -- Fernet-encrypted at rest
  connected_at    timestamptz not null default now(),
  last_scanned_at timestamptz,
  -- a given GitHub repo is connected once per user
  unique (user_id, github_repo_id)
);

create index if not exists idx_repos_user_id on repos(user_id);

-- ---------------------------------------------------------------------------
-- api_detections
-- ---------------------------------------------------------------------------
create table if not exists api_detections (
  id              uuid primary key default gen_random_uuid(),
  repo_id         uuid not null references repos(id) on delete cascade,
  api_name        text not null,               -- 'stripe' | 'shopify' | 'twilio' | 'sendgrid' | 'github'
  file_path       text not null,
  line_number     int,
  matched_snippet text,
  -- normalized tokens (e.g. 'Charge','PaymentIntent') extracted from the match,
  -- used to cross-reference against changelog events. comma-separated, lowercased.
  symbols         text,
  detected_at     timestamptz not null default now(),
  -- one row per (repo, api, file, line) so re-scans upsert instead of duplicating
  unique (repo_id, api_name, file_path, line_number)
);

create index if not exists idx_detections_repo    on api_detections(repo_id);
create index if not exists idx_detections_api      on api_detections(api_name);
create index if not exists idx_detections_repo_api on api_detections(repo_id, api_name);

-- ---------------------------------------------------------------------------
-- changelog_events
-- ---------------------------------------------------------------------------
create table if not exists changelog_events (
  id           uuid primary key default gen_random_uuid(),
  api_name     text not null default 'stripe',
  change_type  text not null,                  -- 'field_renamed' | 'endpoint_deprecated' | 'field_removed' | 'other'
  old_value    text,
  new_value    text,
  description  text,
  source_url   text,
  -- hash of normalized entry text; UNIQUE => scraper never inserts a dup
  content_hash text not null,
  -- normalized tokens the event refers to (e.g. 'charge,source'), used for matching
  symbols      text,
  detected_at  timestamptz not null default now(),
  -- NULL until /internal/alerts/process has cross-referenced this event
  processed_at timestamptz,
  unique (api_name, content_hash)
);

create index if not exists idx_changelog_unprocessed on changelog_events(processed_at) where processed_at is null;

-- ---------------------------------------------------------------------------
-- alerts
-- ---------------------------------------------------------------------------
create table if not exists alerts (
  id                 uuid primary key default gen_random_uuid(),
  repo_id            uuid not null references repos(id) on delete cascade,
  changelog_event_id uuid not null references changelog_events(id) on delete cascade,
  api_detection_id   uuid not null references api_detections(id) on delete cascade,
  email_sent         boolean not null default false,
  sent_at            timestamptz,
  created_at         timestamptz not null default now(),
  -- never alert twice for the same (event, detection) pairing
  unique (changelog_event_id, api_detection_id)
);

create index if not exists idx_alerts_repo  on alerts(repo_id);
create index if not exists idx_alerts_event on alerts(changelog_event_id);
