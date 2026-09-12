-- ============================================================================
-- AutoFix API — Phase 2 database migration (Supabase / PostgreSQL)
-- ============================================================================
-- Apply this in the Supabase SQL editor (or `psql`) AFTER db/schema.sql.
-- Idempotent: creates tables/indexes only if they don't already exist.
--
-- Phase 2 adds the pattern-based auto-fix + PR engine. Two tables:
--   * fix_rules — the curated, hand-verified breaking-change rules. This table
--     is a MIRROR of backend/app/stripe_fix_rules.py (the config file is the
--     source of truth; POST /internal/fix-rules/sync upserts it here so `fixes`
--     can FK to a rule and the dashboard/PR body can read rule metadata).
--   * fixes — one generated fix per (repo, rule, file): its diff preview, PR
--     status, and PR URL/number.
--
-- Design notes (consistent with Phase 1's schema-hardening choices):
--   * rule_key (UNIQUE) lets `sync` upsert rules idempotently from the config.
--   * We store display fields (title/description/old_value/new_value/source_url)
--     on fix_rules so the dashboard and PR bodies don't need the Python config.
--   * `enabled` lets you switch a rule off WITHOUT deleting it or editing code.
--   * changelog_event_id is OPTIONAL provenance (fix generation is driven by
--     detections × rules, not by events) and uses ON DELETE SET NULL so pruning
--     an event never destroys a rule.
--   * fixes.api_detection_id uses ON DELETE SET NULL: re-scans upsert detections
--     (never delete), but even if one is removed we keep the fix/PR history.
--   * UNIQUE (repo_id, fix_rule_id, file_path) makes generation idempotent
--     (one fix per rule per file; re-running /internal/fixes/generate is safe).
-- ============================================================================

-- ---------------------------------------------------------------------------
-- fix_rules — curated, verified breaking-change rules (mirror of the config)
-- ---------------------------------------------------------------------------
create table if not exists fix_rules (
  id                 uuid primary key default gen_random_uuid(),
  -- stable id from the curated config; UNIQUE => `sync` upserts, never dups.
  rule_key           text unique not null,
  -- optional provenance: the changelog entry that justifies this rule.
  changelog_event_id uuid references changelog_events(id) on delete set null,
  api_name           text not null default 'stripe',
  rule_type          text not null,                 -- 'regex_replace' | 'ast_rename_field' | 'ast_rename_method'
  pattern            text not null,                 -- regex (or AST matcher spec)
  replacement        text not null,
  language           text not null,                 -- 'python' | 'javascript' | 'typescript' | 'ruby' | 'php' | 'go'
  confidence         text not null default 'high',  -- 'high' | 'medium' | 'low' — informational + drives PR warnings
  title              text,                          -- human title (used in PR title)
  description        text,                          -- explanation shown in PR body + dashboard
  old_value          text,                          -- e.g. 'stripe.Charge.create'
  new_value          text,                          -- e.g. 'stripe.PaymentIntent.create'
  source_url         text,                          -- link to the Stripe migration doc
  enabled            boolean not null default true, -- kill-switch without code changes
  created_at         timestamptz not null default now()
);

create index if not exists idx_fix_rules_api      on fix_rules(api_name);
create index if not exists idx_fix_rules_language  on fix_rules(language);
create index if not exists idx_fix_rules_enabled   on fix_rules(enabled) where enabled;

-- ---------------------------------------------------------------------------
-- fixes — one generated fix per (repo, rule, file)
-- ---------------------------------------------------------------------------
create table if not exists fixes (
  id               uuid primary key default gen_random_uuid(),
  repo_id          uuid not null references repos(id) on delete cascade,
  fix_rule_id      uuid not null references fix_rules(id) on delete cascade,
  -- representative detection that pointed us at this file (informational).
  api_detection_id uuid references api_detections(id) on delete set null,
  file_path        text not null,
  diff_preview     text not null,                 -- unified diff (before/after)
  pr_url           text,
  pr_number        int,
  -- 'pending'      : diff generated, no PR yet (auto-PR disabled or PR failed)
  -- 'needs_review' : held for manual PR creation from the dashboard
  -- 'pr_created'   : a PR is open
  -- 'merged'       : PR merged (set by the GitHub webhook)
  -- 'rejected'     : PR closed without merge (set by the GitHub webhook)
  status           text not null default 'pending',
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  -- one fix per rule per file => generation is idempotent (safe to re-run).
  unique (repo_id, fix_rule_id, file_path)
);

create index if not exists idx_fixes_repo   on fixes(repo_id);
create index if not exists idx_fixes_status  on fixes(status);
create index if not exists idx_fixes_rule    on fixes(fix_rule_id);
-- the PR-status webhook looks fixes up by their PR url.
create index if not exists idx_fixes_pr_url  on fixes(pr_url);
