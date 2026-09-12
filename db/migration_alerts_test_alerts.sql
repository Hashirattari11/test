-- ============================================================================
-- Phase 1 Alerting migration — alerts table columns for Test Alerts
-- ============================================================================
-- Usage: run this in the Supabase SQL editor (as with seed_test_event.sql).
-- Each statement is additive and safe to run as-is. `changelog_event_id` is
-- made nullable because simulated/test alerts have no real changelog_events row.
-- ============================================================================

-- 1. Allow simulated alerts (no real changelog event) to be created.
alter table alerts
  alter column changelog_event_id drop not null;

-- 2. Add columns used by the alerting UI / test-alert flow.
--    (If `severity` already exists from a prior phase, PostgreSQL will error on
--     duplicate column — check first via the table inspector, or wrap in a guard:
--     `alter table alerts add column if not exists severity text default 'medium';`
--     The `if not exists` form is safe to run repeatedly.)
alter table alerts add column if not exists severity text default 'medium';
alter table alerts add column if not exists severity_reason text;
alter table alerts add column if not exists provider text default 'resend';
alter table alerts add column if not exists status text default 'sent';   -- 'sent' | 'failed'
alter table alerts add column if not exists is_test boolean default false;

-- 3. Index for the repo-based alert history query (already present as
--    idx_alerts_repo in schema.sql; re-adding is a no-op). Kept for clarity.
create index if not exists idx_alerts_repo on alerts(repo_id);
