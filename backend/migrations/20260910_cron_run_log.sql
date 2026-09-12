-- Cron run observability (M8).
-- Records every internal cron invocation: which job, when, how long,
-- counts, and errors. NO secrets — summary counts only.
CREATE TABLE IF NOT EXISTS cron_run_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_name TEXT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ,
  duration_ms INTEGER,
  status TEXT NOT NULL DEFAULT 'running',  -- running | ok | error
  summary JSONB,
  error TEXT
);

CREATE INDEX IF NOT EXISTS idx_cron_run_log_started_at
  ON cron_run_log (started_at DESC);

CREATE INDEX IF NOT EXISTS idx_cron_run_log_job
  ON cron_run_log (job_name, started_at DESC);