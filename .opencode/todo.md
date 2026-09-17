# Mission: REAL PROVIDER CHANGE MONITORING — ALL 44 PROVIDERS

> Build real, production-grade provider change monitoring: 44 providers registered, official sources only,
> provider-specific adapters, evidence-based change detection (no fabricated data), clean DB schema, alert++
> email pipeline, redesigned Provider Changes UI, monitoring health matrix, tests, live verification, final report.
> PRESERVE all existing features (OAuth, scanner, impact engine, fire drill, auto-fix PR, agency mode, email).

Discovery (Phase 0) is COMPLETE — see .opencode/context.md for full audit. Audit conclusion:
12 generic scrapers produce fabricated criticals (Firebase/Supabase nav text) + re-ingest 2021-2023 history
as new (slack 169, openai 170 rows); 239/491 unknown change_type; 32 unprocessed.

**MISSION STATUS: COMPLETE — all 44 items verified with tool evidence (168 pytest passed, tsc exit 0,
prod matrix 7 ACTIVE/2 ERROR/35 LIMITED = 44, dedup 0, deployed backend-3qivre7qj, report written).**
2026-09-17 incident (backend/ dir deleted) fully recovered; see .opencode/context.md.

---

## M1: Backend provider registry — 44 providers + official sources | status: completed
### T1.1: Provider sources module | agent:Worker
- [x] S1.1.1: Create `backend/app/changelog/sources.py` — 44-provider registry: provider id, display name, category, official changelog URL, feed/API URL if available, source_kind (RSS|JSON|HTML_STRICT|GITHUB_RELEASES|NONE), polling cadence | size:L
- [x] S1.1.2: Wire `settings.changelog_sources` + scheduler to registry (replace hardcoded 12) | size:S
- [x] S1.1.3: backend/provider mirror of the 44 ids matches frontend registry IDs exactly | size:S

## M2: DB schema migration + historical data cleanup | status: completed
### T2.1: Migration | agent:Worker
- [x] S2.1.1: Migration: `provider_monitoring_status` table (provider_id PK, status ACTIVE|LIMITED|SOURCE_UNAVAILABLE|ERROR, source_url, feed_url, last_fetch_at, last_success_at, last_error, consecutive_errors, last_http_status, etag, last_modified, created_at, updated_at) | size:L
- [x] S2.1.2: Migration: changelog_events new columns — provider_status_source text, external_id text, source_type text, fingerprint text, first_seen_at timestamptz, last_seen_at timestamptz, review_state text default 'unreviewed' (unreviewed|reviewed|dismissed), confidence_evidence jsonb, severity_evidence jsonb, change_type constraint/values per new enum | size:L
- [x] S2.1.3: Unique index on (api_name, external_id) + (api_name, fingerprint) partial where fingerprint not null | size:M
### T2.2: Cleanup + backfill | agent:Worker
- [x] S2.2.1: Mark/delete fabricated + history-reingested rows (Firebase/Supabase nav-text entries; pre-2026 slack/openai rows; change_type unknown) — service-role only, keep alerts/E2E safe | size:M
- [x] S2.2.2: Backfill provider_monitoring_status rows for all 44 providers | size:S
- [x] S2.2.3: RLS unchanged (new tables get policies mirroring existing internal tables) | size:S

## M3: Provider adapters + real change-detection pipeline | status: completed
### T3.1: Adapter framework | agent:Worker
- [x] S3.1.1: Rewrite `base.py`: strict adapter interface — `fetch()` returns typed RawEntry {external_id, title, url, published_at, summary, structured: dict|null}; STRICT lookback window (max 60d), per-provider entry cap; NO generic text-div scraping; date required | size:L
- [x] S3.1.2: `normalize.py`: per-provider normalization; `fingerprint.py`: stable change fingerprint (provider+external_id; content_hash fallback only with verified source) | size:M
- [x] S3.1.3: `classify.py`: new change_type enum (BREAKING_CHANGE, DEPRECATION, API_VERSION_CHANGE, ENDPOINT_CHANGE, REQUEST_SCHEMA_CHANGE, RESPONSE_SCHEMA_CHANGE, AUTH_CHANGE, SDK_CHANGE, MODEL_CHANGE, RATE_LIMIT_CHANGE, BEHAVIOR_CHANGE, SECURITY_CHANGE, NEW_FEATURE, BUG_FIX, OTHER) + evidence-based severity (CRITICAL/HIGH/MEDIUM/LOW/INFO/UNKNOWN) + confidence (HIGH/MEDIUM/LOW/UNKNOWN) rules; UNKNOWN confidence requires explicit evidence list | size:L
- [x] S3.1.4: No-fabrication invariant: entry without (external_id AND title AND url AND date) is dropped with reason logged — never stored with defaults | size:M
### T3.2: Provider adapters (structured) | agent:Worker
- [x] S3.2.1: RSS/JSON adapters: stripe (HTML_STRICT — feed.rss fictional 404), shopify (feed.xml), github (github.blog feed + GH releases API), plus any verified RSS | size:XL
- [x] S3.2.2: GITHUB_RELEASES adapters: sentry, redis (official GH releases) | size:M
- [x] S3.2.3: HTML_STRICT adapters (official pages, strict selectors + date parsing + lookback): openai, anthropic, paypal, resend, twilio, sendgrid, firebase, aws, cloudinary, googleai, huggingface, elevenlabs, mailgun, digitalocean, auth0, clerk, mapbox, algolia, posthog, mixpanel, segment, intercom, discord, telegram, whatsapp, twitter, zoom, pusher, youtube, notion, airtable, mongodb, plaid, openweather, serpapi | size:XXL
- [x] S3.2.4: SOURCE_UNAVAILABLE providers: mark honestly in matrix (no fake events) | size:S
- [x] S3.2.5: Register all adapters in FETCHERS + adapters registry | size:S
### T3.3: Scheduler rework | agent:Worker
- [x] S3.3.1: scheduler: iterate registry (44), per-provider isolation (errors never kill run), ETag/If-Modified-Since support, rate-limit politeness (per-provider min interval), budget caps preserved (15s/25s), report timed_out truthfully | size:L
- [x] S3.3.2: Update store_events: fingerprint dedup updates last_seen_at instead of skip; external_id upsert; review_state/status columns | size:M
- [x] S3.3.3: log_health→provider_monitoring_status (consecutive_errors, last_error, status transitions ERROR after N failures) | size:M

## M4: Alert engine + email + dedup | status: completed
### T4.1: Alert rework | agent:Worker
- [x] S4.1.1: alerts.py: gate by change_type, severity threshold (>=MEDIUM for high-confidence; CRITICAL/HIGH always), UNKNOWN severity/confidence never emailed (dashboard-only) | size:L
- [x] S4.1.2: Dedup upgrade: fingerprint-based across events; alert row unique preserved; no duplicate emails | size:M
- [x] S4.1.3: Email subject per spec: `[Breaklytix] High-Risk API Change Detected — {Provider}` (severity-based variant for lower tiers) — brand flag noted (user example [AutoFix API]) in report | size:M
- [x] S4.1.4: Impact Engine phrasing: "Potential impact detected" / "No matching repository usage detected" — never "Your code is broken" | size:S

## M5: API routes + monitoring health | status: completed
### T5.1: New/changed endpoints | agent:Worker
- [x] S5.1.1: GET /internal/changelog/events — list/detail with ALL-44 provider filter, filters: provider, change_type, severity, confidence, status, date range; pagination | size:L
- [x] S5.1.2: GET /internal/changelog/events/{id} — detail incl. evidence, source, impact summary | size:M
- [x] S5.1.3: GET /internal/changelog/monitoring — 44-provider matrix | size:M
- [x] S5.1.4: POST /internal/changelog/events/{id}/review + /dismiss (user state) | size:S
- [x] S5.1.5: Keep existing /fetch /process /daily-scan internal cron + /notices for compat; extend /health | size:M
- [x] S5.1.6: Security: SSRF guard (adapter URLs allowlisted per provider), XSS-safe output, sanitize descriptions | size:M

## M6: Frontend — Provider Changes UI redesign | status: completed
### T6.1: Data layer | agent:Worker
- [x] S6.1.1: api.ts: types + getProviderEvents, getProviderEvent, getMonitoringMatrix, review/dismiss calls | size:M
- [x] S6.1.2: registry.ts/types.ts: monitoringSource fields (sourceKind, feedUrl), status type extended | size:M
### T6.2: Pages | agent:Worker
- [x] S6.2.1: /dashboard/changelog (list): provider filter = ALL 44, status filters, columns; empty states; error/loading states | size:L
- [x] S6.2.2: /dashboard/changelog/[id] (detail): badges, description, official source link, evidence list, impact section, Review/Dismiss | size:L
- [x] S6.2.3: /dashboard/providers (monitoring matrix): 44 rows with status badge, source, last fetch, error | size:L
- [x] S6.2.4: Wire nav links (changelog + providers) | size:S

## M7: Tests | status: completed
### T7.1: Backend tests | agent:Worker
- [x] S7.1.1: registry: exactly 44 providers, ids match frontend registry, every provider has official source | size:M
- [x] S7.1.2: normalization/fingerprint/dedup: stable fingerprint, last_seen_at update, no dup rows | size:M
- [x] S7.1.3: classification: all 15 change_types map, severity/confidence evidence rules, no-fabrication invariant | size:L
- [x] S7.1.4: adapter tests: official source URL validity (HTTP 200/feed parse), lookback window, isolation, ETag | size:L
- [x] S7.1.5: alerts: severity gating, dedup, email subject format, UNKNOWN never emailed, review/dismiss state | size:M
- [x] S7.1.6: security: SSRF guard, XSS escaping | size:S
- [x] S7.1.7: Full pytest suite passes (168 passed) | size:M
### T7.2: Frontend | agent:Worker
- [x] S7.2.1: tsc exit 0 | size:M
- [x] S7.2.2: mojibake/brand grep = 0 | size:S

## M8: Real verification + deploy + final report | status: completed
### T8.1: Live verification | agent:Reviewer
- [x] S8.1.1: Audit trail check — zero fabricated rows, zero unknown provider, source_url official domains | size:M
- [x] S8.1.2: Run cron fetch+process; verify real events stored (shopify 43, redis 18, github 10, serpapi 9, slack 8, clerk 6, sentry 4), matrix populated (7 ACTIVE/2 ERROR/35 LIMITED), dedup 0 | size:M
- [x] S8.1.3: Email path subject format (verified in alerts.py + tests), review/dismiss flow, frontend checks (tsc 0) | size:M
- [x] S8.1.4: Full pytest (168) + build pass; existing features regression — all pass | size:L
### T8.2: Deliverables | agent:Worker
- [x] S8.2.1: Final report written: `D:\autofix\REPORT_44_PROVIDER_MONITORING.md` (files changed, mechanisms per requirement, matrix, migrations, test results, limitations, brand-note) | size:L
- [x] S8.2.2: Commits `89ef8a5` + `a04a939`; backend deployed `backend-3qivre7qj` (prod), frontend deployed; tests committed | size:M