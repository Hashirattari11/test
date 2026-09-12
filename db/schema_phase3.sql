-- ============================================================================
-- AutoFix API — Phase 3 database migration (Supabase / PostgreSQL)
-- ============================================================================
-- Apply this in the Supabase SQL editor (or `psql`) AFTER db/schema_phase2.sql.
-- Idempotent: creates tables/indexes/columns only if they don't already exist.
--
-- Phase 3 adds billing/subscription support (Stripe Billing), plan usage tracking,
-- and idempotent webhook event processing.
--
-- Design notes:
--   * users.plan_status tracks subscription state: 'trial' | 'active' | 'past_due' | 'canceled'
--   * users.monitored_api_limit is the plan-enforced cap (10/50/-1 for unlimited)
--   * plan_usage tracks per-billing-period API count for dashboard + enforcement
--   * stripe_webhook_events gives us idempotent webhook handling (dedupe by stripe_event_id)
-- ============================================================================

-- ---------------------------------------------------------------------------
-- users — add billing/subscription columns
-- ---------------------------------------------------------------------------
alter table if exists users
    add column if not exists stripe_customer_id text;

alter table if exists users
    add column if not exists stripe_subscription_id text;

alter table if exists users
    add column if not exists plan_status text default 'trial';

alter table if exists users
    add column if not exists monitored_api_limit int default 10;

-- Helpful indexes for billing queries
create index if not exists idx_users_stripe_customer on users(stripe_customer_id);
create index if not exists idx_users_plan_status on users(plan_status);

-- ---------------------------------------------------------------------------
-- plan_usage — per-billing-period monitored API count
-- ---------------------------------------------------------------------------
create table if not exists plan_usage (
    id                      uuid primary key default gen_random_uuid(),
    user_id                 uuid not null references users(id) on delete cascade,
    monitored_api_count     int not null default 0,
    billing_period_start    date,
    billing_period_end      date,
    updated_at              timestamptz default now(),
    -- one row per user per billing period
    unique (user_id, billing_period_start)
);

create index if not exists idx_plan_usage_user on plan_usage(user_id);

-- ---------------------------------------------------------------------------
-- stripe_webhook_events — idempotent webhook processing
-- ---------------------------------------------------------------------------
create table if not exists stripe_webhook_events (
    id              uuid primary key default gen_random_uuid(),
    stripe_event_id text unique not null,
    event_type      text not null,
    processed_at    timestamptz not null default now(),
    payload         jsonb
);

create index if not exists idx_stripe_webhook_event_id on stripe_webhook_events(stripe_event_id);