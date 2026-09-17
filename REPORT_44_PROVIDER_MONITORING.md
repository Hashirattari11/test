# Report — 44-Provider Real Changelog Monitoring (Breaklytix)

**Date:** 2026-09-17
**Product:** Breaklytix (the change-monitoring product on the dauto.ai engineering platform; alert subjects use the `[Breaklytix]` brand)

---

## 1. Summary

Replaced the legacy 12-generic-scraper changelog monitoring with a **production-grade, real 44-provider monitoring system**. Every provider is fetched from its **official** source only (vendor RSS/Atom feed, official GitHub Releases API, or a strictly-parseable official changelog HTML page). A hard **no-fabrication invariant** is enforced in code: an entry can only be stored if it carries a real `external_id`, `title`, `url` and a real `published_at` date within the 60-day lookback window. Sources that cannot provide machine-readable, dated entries are reported **honestly as LIMITED**, never faked.

The system captures real events for providers whose sources expose dated machine-readable data (e.g. Shopify 43, Redis 18, GitHub 10, SerpApi 9, Slack 8, Clerk 6, Sentry 4), deduplicates by fingerprint, classifies severity/confidence with evidence, gates alert emails by risk and confidence, and surfaces everything in the frontend dashboard (event list/detail, monitoring matrix, review & dismiss).

---

## 2. What Was Built (Mechanism → File Map)

| # | Requirement mechanism | Implementation |
|---|---|---|
| 1 | 44-provider registry (ids align with `frontend/lib/providers/registry.ts`) | `backend/app/changelog/sources.py` — `PROVIDER_SOURCES` tuple of `ProviderSource` (id, display name, category, source_kind, official changelog_url, feed_url, lookback_days=60, max_entries=50) |
| 2 | Source-type dispatch | `backend/app/changelog/adapters.py` — `AdapterFactory` registers `RSSAdapter`, `GithubReleasesAdapter`, `HTMLStrictAdapter`; per-provider adapter extension points |
| 3 | RSS/Atom parsing (Shopify, GitHub) | `RSSAdapter` in `adapters.py` (feedparser-backed, strict date/extract validation) |
| 4 | GitHub Releases API (Sentry, Redis) | `GithubReleasesAdapter` in `adapters.py` (official `api.github.com/repos/{owner}/{repo}/releases`) |
| 5 | Strict HTML changelog parsing (the other 40) | `HTMLStrictAdapter` in `adapters.py` — strict per-provider container/date extraction; zero entries parsed → honest LIMITED, never hallucinated |
| 6 | No-fabrication invariant (external_id/title/url/published_at, 60d lookback) | `backend/app/changelog/base.py` (`RawEntry` + `validate_raw_entry`, `_iter_entries` gating) + per-adapter filters |
| 7 | Evidence-based classification (15 change types; severity; confidence) | `backend/app/changelog/classify.py` — keyword/evidence-driven classifier with `UNKNOWN` catch-all |
| 8 | Fingerprint dedup (stable hash across exact-duplicate feeds) | `backend/app/changelog/fingerprint.py` |
| 9 | Isolated scheduler (per-provider worker, env-tunable budgets, DB-retry, bulk dedup store, real duration_ms) | `backend/app/changelog/scheduler.py` — `fetch_all_providers()` with `FETCH_TIMEOUT_SECONDS` (12), `FETCH_MAX_WORKERS` (4), `TOTAL_BUDGET_SECONDS` (25); `_db_retry` on transport errors; single bulk lookup per provider (external_id + fingerprint sets); 23505 → duplicate, not error; `_update_status` prints failures; timed-out-inside-budget no longer marks providers ERROR (keeps last completed status) |
| 10 | Guarded API routes (list/get/review/dismiss/internal) | `backend/app/changelog/router.py` — public read routes for all users; `POST /review`, `POST /dismiss` gated by `get_current_user_id` (current-user-only); `/internal/...` gated by `require_internal_secret` (401 without the Vercel env secret) |
| 11 | SSRF guard + official-host allowlist | `backend/app/changelog/base.py` — `_assert_allowed_url(host)` refuses non-http(s) and hosts outside the provider's `ProviderSource.host` allowlist |
| 12 | Alert gating (always email CRITICAL/HIGH; MEDIUM/LOW/INFO only HIGH confidence; UNKNOWN never) | `backend/app/alerts.py` — subject `[Breaklytix] High-Risk API Change Detected — {Provider}` / `[Breaklytix] API Change Notice — {Provider}` |
| 13 | Impact analysis with "Potential impact detected: …" / "No matching repository usage detected" (never "crash") | `backend/app/impact/analyzer.py` |
| 14 | Database migrations (10 new `changelog_events` columns, partial unique index `(api_name, external_id)`, `provider_monitoring_status` + `duration_ms`, RLS) | `backend/migrations/` (see §3) |
| 15 | Frontend: changelog event list, event detail, monitoring matrix, review/dismiss | `frontend/app/dashboard/changelog/`, `frontend/app/dashboard/providers/`, `frontend/lib/api.ts`, `frontend/lib/providers/types.ts` |

**Source types (44 providers):**
- `RSS` (2): shopify (`https://shopify.dev/changelog/feed.xml`), github (`https://github.blog/changelog/feed/`)
- `GITHUB_RELEASES` (2): sentry (`getsentry/sentry`), redis (`redis/redis`)
- `HTML_STRICT` (40): the rest — honest parse; zero dated entries ⇒ LIMITED.

---

## 3. Database Migrations

Applied to production Supabase:

- `changelog_events`: added `severity`, `confidence`, `change_type`, `review_state`, `reviewed_by`, `impact_summary`, `fingerprint`, `fetched_at`, `source_type`, `raw_payload` (10 columns)
- Partial unique index on `(api_name, external_id)` where `external_id IS NOT NULL` — primary dedup guard
- `provider_monitoring_status`: full 44-row registry; added `duration_ms` (sweep latency per provider)
- RLS enabled with authenticated-read policy on `changelog_events`
- Historical cleanup: legacy undated/duplicate rows reduced 491 → 363

---

## 4. Live Verification Results (Production)

Verified against the **production Supabase database** via a fixed local fetch-sweep pointed at the prod DB (the Vercel-deployed `INTERNAL_SECRET` differs from the local `.env`, so live `/internal/*` probes return 401 by design — the secret guard is active):

- **Provider matrix: 7 ACTIVE / 2 ERROR / 35 LIMITED = 44 rows.**
  - ACTIVE: clerk, github, redis, sentry, serpapi, shopify, slack
  - ERROR: telegram (network-level connection block from this environment), segment (HTTP 403 from Cloudflare) — both are **external** transport blocks, not code failures
  - LIMITED (35): fetched successfully but no dated machine-readable entries within the 60-day window (honest "we cannot confirm changes" — no fabrication)
- **Real stored events (all have external_id):** shopify 43, redis 18, github 10, serpapi 9, slack 8, clerk 6, sentry 4
- **Dedup check:** 0 duplicate `(api_name, external_id)` pairs
- **SOURCE_UNAVAILABLE rows:** 0
- **15 URL corrections** applied after live probing (plaid, sendgrid, whatsapp, zoom, pusher, postmark, mailgun, cloudinary, mixpanel, intercom, algolia, mapbox, notion, openweather, serpapi); **stripe** confirmed to have no machine-readable feed (fictional `feed.rss`) → moved to honest `HTML_STRICT`; **paypal** moved to the live `https://developer.paypal.com/api/rest/` page (previous release-notes URL 404s).
- **Deploys:** backend `backend-3qivre7qj` (prod, Ready) in the correct `backend` Vercel project; live alias `backend-virid-ten-43.vercel.app` serves the fixed code (401 guard confirmed).

---

## 5. Test Results

- **Backend:** `python -m pytest tests -q` → **168 passed** (1 warning — pytest-asyncio deprecation)
- **Frontend:** `npx tsc --noEmit` → **exit 0**
- Post-incident recovery commits: `89ef8a5` (recovery + scheduler hardening) and `a04a939` (URL corrections + stripe/paypal + budget-expiry non-destructive fix) — code safe in git.

---

## 6. Limitations & Honest Notes

- **Brand note:** the user spec said `[AutoFix API]`; the shipped product brand is **Breaklytix** — alert subjects use `[Breaklytix] …`. Flag for product naming alignment.
- **HTML_STRICT providers (35 LIMITED)** are honestly reported as LIMITED: their official changelog pages are client-rendered or provide no dated, machine-readable entries. We do **not** guess — no fabricated entries exist in the DB.
- **telegram / segment** show ERROR only because of **external** transport/HTTP blocks (connection reset; 403), not application bugs.
- **Vercel cron budget (30s serverless limit vs 25s total fetch budget):** with 4 workers only ~8+ providers can complete per tick; the rest report `timed_out`. Since the fix, **budget expiry no longer overwrites a provider's last good status with ERROR** — the matrix stays truthful.
- **Live internal endpoints** return 401 without the Vercel-deployed `INTERNAL_SECRET` (deliberate), so live probing of `/internal/changelog/*` was not possible from the dev machine; the pipeline was verified end-to-end by running the same scheduler code locally against the production DB.

---

## 7. Files Changed (key, from git history)

- `backend/app/changelog/sources.py` — 44-provider registry + URL corrections
- `backend/app/changelog/adapters.py` — adapter factory (RSS / GITHUB_RELEASES / HTML_STRICT)
- `backend/app/changelog/classify.py` — evidence-based classification
- `backend/app/changelog/fingerprint.py` — dedup fingerprints
- `backend/app/changelog/scheduler.py` — budget/env/retry/bulk-store/duration fixes
- `backend/app/changelog/router.py` — guarded routes
- `backend/app/changelog/base.py` — RawEntry invariant + SSRF allowlist
- `backend/app/alerts.py` — gated alerting (`[Breaklytix]` subjects)
- `backend/app/impact/analyzer.py` — impact analysis (phrasing verified)
- `backend/migrations/` — schema/migration files
- `backend/tests/test_changelog_monitoring.py`, `backend/tests/test_impact.py` — 168 backend tests
- `frontend/app/dashboard/changelog/`, `frontend/app/dashboard/providers/`, `frontend/lib/api.ts`, `frontend/lib/providers/types.ts` — frontend
- Root: `REPORT_44_PROVIDER_MONITORING.md` (this file)

---

*Prepared at the conclusion of the 44-provider changelog monitoring mission (M1–M8).*