# AutoFix Cron Jobs

All cron jobs are declared in `backend/vercel.json` and hit internal
endpoints that require the `CRON_SECRET` header (`x-internal-secret`).

## Schedule (UTC)

| Job | Endpoint | Schedule | What it does |
|-----|----------|----------|--------------|
| Changelog fetch | `POST /internal/changelog/fetch` | `0 8 * * *` (08:00) | Fetches changelogs from all monitored providers, stores new events |
| Changelog process | `POST /internal/changelog/process` | `15 8 * * *` (08:15) | Processes new events into alerts; flushes approved alert emails |
| Daily scan | `POST /internal/daily-scan` | `30 8 * * *` (08:30) | Daily repository scans (24h due-check per repo) + impact analysis for recent events |

## Security

- Every endpoint is guarded by `require_internal_secret` in
  `backend/app/deps.py`. Requests without the correct
  `x-internal-secret` header get 401/403.
- Vercel Cron automatically sends the header; set the env var
  `CRON_SECRET` (server-side, never exposed to the browser).

## Observability

Every cron run is recorded in the `cron_run_log` table
(migration `20260910_cron_run_log.sql`):

- job name, started_at / finished_at, duration_ms
- status: `running` → `ok` | `error`
- summary JSONB (aggregate counts only — provider counts, alert counts)
- short sanitized error string (max 200 chars; NO secrets, NO message
  content, NO tokens)

Implementation: `backend/app/cronlog.py` — `run_cron(job, fn)` wraps
each endpoint handler (`backend/app/changelog/router.py`). Logging
failures are non-fatal: the cron job itself still runs.

## Daily scan due-check

`run_daily_scans` (in `backend/app/changelog/scheduler.py`) skips any
repo whose latest `daily_scan_runs.ran_at` is newer than 24h, so
repeated cron invocations do not re-scan everything. Per-repo failures
(token expired, repo deleted, permission revoked) are caught per-repo
and surfaced in the scan run record — never silently dropped.

## Manual runs

```bash
curl -X POST https://backend-virid-ten-43.vercel.app/internal/changelog/fetch \
  -H "x-internal-secret: $CRON_SECRET"
curl -X POST https://backend-virid-ten-43.vercel.app/internal/changelog/process \
  -H "x-internal-secret: $CRON_SECRET"
curl -X POST https://backend-virid-ten-43.vercel.app/internal/daily-scan \
  -H "x-internal-secret: $CRON_SECRET"
```

Health check (no side effects):

```bash
curl https://backend-virid-ten-43.vercel.app/internal/changelog/health \
  -H "x-internal-secret: $CRON_SECRET"
```