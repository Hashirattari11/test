-- ============================================================================
-- Breaklytix — API Digital Twin (additive migration)
-- ============================================================================
-- Digital Twin = "Simulate the future provider state against THIS repository
-- and show the exact impact."
--
-- Scoping rules (CRITICAL, mirrors the rest of the schema):
--   * Provider monitoring stays GLOBAL (provider_monitoring_status untouched).
--   * digital_twin_runs / digital_twin_analyses are ALWAYS repository-scoped:
--     every row carries repository_id and every query must filter by it.
--   * No fabricated data: rows are only written when a real changelog event
--     was matched against real api_detections rows from an actual scan.
--   * Source URLs are stored only when the provider event carried one —
--     never invented.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- digital_twin_runs: one row per "Run Future Simulation" execution for a repo
-- ---------------------------------------------------------------------------
create table if not exists digital_twin_runs (
  id              uuid primary key default gen_random_uuid(),
  repository_id   uuid not null references repos(id) on delete cascade,
  triggered_by    text not null default 'user',        -- user | cron
  status          text not null default 'completed',   -- completed | failed
  events_considered int not null default 0,
  analyses_created  int not null default 0,
  no_match_count    int not null default 0,
  error_message     text,
  created_at      timestamptz not null default now()
);

create index if not exists idx_dt_runs_repository on digital_twin_runs(repository_id);

-- ---------------------------------------------------------------------------
-- digital_twin_analyses: one row per (real provider event, real detected usage)
-- matching pair for a repository.  Null affected_* fields mean "usage matched
-- the provider, but exact file/symbol evidence is unavailable" — reported
-- truthfully, never fabricated.
-- ---------------------------------------------------------------------------
create table if not exists digital_twin_analyses (
  id                uuid primary key default gen_random_uuid(),
  repository_id     uuid not null references repos(id) on delete cascade,
  provider_id       text not null,                     -- matches api_name/changelog_events.api_name
  change_event_id   uuid not null references changelog_events(id) on delete cascade,
  impact_status     text not null,                     -- NO_MATCH | SAFE | POTENTIAL IMPACT | HIGH RISK | BREAKING RISK | UNKNOWN
  severity          text not null,                     -- breaking | high | medium | low | safe | unknown
  confidence        numeric not null default 0,        -- 0.0 - 1.0
  affected_file     text,
  affected_symbol   text,
  line_number       integer,
  usage_context     text,                              -- the real detected snippet (evidence)
  explanation       text not null,
  recommended_change text,
  source_url        text,
  api_detection_id  uuid references api_detections(id) on delete cascade,
  alert_id          uuid references alerts(id) on delete set null,
  run_id            uuid references digital_twin_runs(id) on delete cascade,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),
  -- Never analyze the same (repo, event, usage) pair twice — idempotent runs.
  unique (repository_id, change_event_id, api_detection_id)
);

create index if not exists idx_dt_analyses_repository on digital_twin_analyses(repository_id);
create index if not exists idx_dt_analyses_provider   on digital_twin_analyses(provider_id);
create index if not exists idx_dt_analyses_event      on digital_twin_analyses(change_event_id);
