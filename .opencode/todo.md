# Mission: REAL PROVIDER CHANGE MONITORING — ALL 44 PROVIDERS

> Build real, production-grade provider change monitoring: 44 providers registered, official sources only,
> provider-specific adapters, evidence-based change detection (no fabricated data), clean DB schema, alert++
> email pipeline, redesigned Provider Changes UI, monitoring health matrix, tests, live verification, final report.
> PRESERVE all existing features (OAuth, scanner, impact engine, fire drill, auto-fix PR, agency mode, email).

Discovery (Phase 0) is COMPLETE — see .opencode/context.md for full audit. Audit conclusion:
12 generic scrapers produce fabricated criticals (Firebase/Supabase nav text) + re-ingest 2021-2023 history
as new (slack 169, openai 170 rows); 239/491 unknown change_type; 32 unprocessed.

---

## M1: Backend provider registry — 44 providers + official sources | status: pending
### T1.1: Provider sources module | agent:Worker
- [ ] S1.1.1: Create `backend/app/changelog/sources.py` — 44-provider registry: provider id, display name, category, official changelog URL, feed/API URL if available, source_kind (RSS|JSON|HTML_STRICT|GITHUB_RELEASES|NONE), polling cadence | size:L
- [ ] S1.1.2: Wire `settings.changelog_sources` + scheduler to registry (replace hardcoded 12) | size:S
- [ ] S1.1.3: backend/provider mirror of the 44 ids matches frontend registry IDs exactly | size:S

## M2: DB schema migration + historical data cleanup | status: pending
### T2.1: Migration | agent:Worker
- [ ] S2.1.1: Migration: `provider_monitoring_status` table (provider_id PK, status ACTIVE|LIMITED|SOURCE_UNAVAILABLE|ERROR, source_url, feed_url, last_fetch_at, last_success_at, last_error, consecutive_errors, last_http_status, etag, last_modified, created_at, updated_at) | size:L
- [ ] S2.1.2: Migration: changelog_events new columns — provider_status_source text, external_id text, source_type text, fingerprint text, first_seen_at timestamptz, last_seen_at timestamptz, review_state text default 'unreviewed' (unreviewed|reviewed|dismissed), confidence_evidence jsonb, severity_evidence jsonb, change_type constraint/values per new enum | size:L
- [ ] S2.1.3: Unique index on (api_name, external_id) + (api_name, fingerprint) partial where fingerprint not null | size:M
### T2.2: Cleanup + backfill | agent:Worker
- [ ] S2.2.1: Mark/delete fabricated + history-reingested rows (Firebase/Supabase nav-text entries; pre-2026 slack/openai rows; change_type unknown) — service-role only, keep alerts/E2E safe | size:M
- [ ] S2.2.2: Backfill provider_monitoring_status rows for all 44 providers | size:S
- [ ] S2.2.3: RLS unchanged (new tables get policies mirroring existing internal tables) | size:S

## M3: Provider adapters + real change-detection pipeline | status: pending
### T3.1: Adapter framework | agent:Worker
- [ ] S3.1.1: Rewrite `base.py`: strict adapter interface — `fetch()` returns typed RawEntry {external_id, title, url, published_at, summary, structured: dict|null}; STRICT lookback window (max 60d), per-provider entry cap; NO generic text-div scraping; date required | size:L
- [ ] S3.1.2: `normalize.py`: per-provider normalization; `fingerprint.py`: stable change fingerprint (provider+external_id; content_hash fallback only with verified source) | size:M
- [ ] S3.1.3: `classify.py`: new change_type enum (BREAKING_CHANGE, DEPRECATION, API_VERSION_CHANGE, ENDPOINT_CHANGE, REQUEST_SCHEMA_CHANGE, RESPONSE_SCHEMA_CHANGE, AUTH_CHANGE, SDK_CHANGE, MODEL_CHANGE, RATE_LIMIT_CHANGE, BEHAVIOR_CHANGE, SECURITY_CHANGE, NEW_FEATURE, BUG_FIX, OTHER) + evidence-based severity (CRITICAL/HIGH/MEDIUM/LOW/INFO/UNKNOWN) + confidence (HIGH/MEDIUM/LOW/UNKNOWN) rules; UNKNOWN confidence requires explicit evidence list | size:L
- [ ] S3.1.4: No-fabrication invariant: entry without (external_id AND title AND url AND date) is dropped with reason logged — never stored with defaults | size:M
### T3.2: Provider adapters (structured) | agent:Worker
- [ ] S3.2.1: RSS/JSON adapters: stripe (feed.rss), shopify (feed.xml), github (github.blog feed + GH releases API), plus any verified RSS (slack/postmark/posthog/supabase/vercel if feeds exist) | size:XL
- [ ] S3.2.2: GITHUB_RELEASES adapters: sentry, redis (official GH releases) | size:M
- [ ] S3.2.3: HTML_STRICT adapters (official pages, strict selectors + date parsing + lookback): openai, anthropic, paypal, resend, twilio, sendgrid, firebase, aws, cloudinary, googleai, huggingface, elevenlabs, mailgun, digitalocean, auth0, clerk, mapbox, algolia, posthog, mixpanel, segment, intercom, discord, telegram, whatsapp, twitter, zoom, pusher, youtube, notion, airtable, mongodb, plaid, openweather, serpapi | size:XXL
- [ ] S3.2.4: SOURCE_UNAVAILABLE providers: mark honestly in matrix (no fake events) | size:S
- [ ] S3.2.5: Register all adapters in FETCHERS + adapters registry | size:S
### T3.3: Scheduler rework | agent:Worker
- [ ] S3.3.1: scheduler: iterate registry (44), per-provider isolation (errors never kill run), ETag/If-Modified-Since support, rate-limit politeness (per-provider min interval), budget caps preserved (15s/25s), report timed_out truthfully | size:L
- [ ] S3.3.2: Update store_events: fingerprint dedup updates last_seen_at instead of skip; external_id upsert; review_state/status columns | size:M
- [ ] S3.3.3: log_health→provider_monitoring_status (consecutive_errors, last_error, status transitions ERROR after N failures) | size:M

## M4: Alert engine + email + dedup | status: pending
### T4.1: Alert rework | agent:Worker
- [ ] S4.1.1: alerts.py: gate by change_type (new_feature/bug_fix/INFO still non-alert), severity threshold (>=MEDIUM for high-confidence; CRITICAL/HIGH always), UNKNOWN severity/confidence never emailed (dashboard-only) | size:L
- [ ] S4.1.2: Dedup upgrade: fingerprint-based across events; alert row unique (changelog_event_id, api_detection_id) preserved; no duplicate emails (existing email_service fingerprint kept) | size:M
- [ ] S4.1.3: Email subject per spec: `[Breaklytix] High-Risk API Change Detected — {Provider}` (severity-based variant for lower tiers) — user example used [AutoFix API]; brand is Breaklytix (flag in report) — render_alert_email update | size:M
- [ ] S4.1.4: Impact Engine phrasing: "Potential impact detected" / "No matching repository usage detected" (analyzer._build_impact_reason) — never "Your code is broken" | size:S

## M5: API routes + monitoring health | status: pending
### T5.1: New/changed endpoints | agent:Worker
- [ ] S5.1.1: GET /internal/changelog/events — list/detail for events with ALL-44 provider filter (incl. providers w/o events), filters: provider, change_type, severity, confidence, status, date range; pagination | size:L
- [ ] S5.1.2: GET /internal/changelog/events/{id} — detail incl. evidence, source, impact summary | size:M
- [ ] S5.1.3: GET /internal/changelog/monitoring — 44-provider matrix (status, source, last fetch, error) | size:M
- [ ] S5.1.4: POST /internal/changelog/events/{id}/review + /dismiss (user state) | size:S
- [ ] S5.1.5: Keep existing /fetch /process /daily-scan internal cron + /notices for compat; extend /health to include per-provider status | size:M
- [ ] S5.1.6: Security: SSRF guard (adapter URLs allowlisted per provider, no user-supplied URLs), XSS-safe output (no raw HTML echo; escape in UI), sanitize descriptions | size:M

## M6: Frontend — Provider Changes UI redesign | status: pending
### T6.1: Data layer | agent:Worker
- [ ] S6.1.1: api.ts: types + getProviderEvents, getProviderEvent, getMonitoringMatrix, review/dismiss calls; keep getChangelogNotices compat | size:M
- [ ] S6.1.2: registry.ts/types.ts: monitoringSource fields (sourceKind, feedUrl), status type extended (active/limited/source_unavailable/error) | size:M
### T6.2: Pages | agent:Worker
- [ ] S6.2.1: /dashboard/changelog (list): provider filter = ALL 44 (from registry, not just events), status filters (severity/confidence/review state), columns: Provider, Change type, Severity, Confidence, Source, Published, Status; empty states ("Monitoring {N} providers", per-provider "Source unavailable" badge); error/loading states | size:L
- [ ] S6.2.2: /dashboard/changelog/[id] (detail): title, provider, type/severity/confidence badges, description, official source link, evidence list, impact section ("Potential impact detected" / "No matching repository usage detected"), Review/Dismiss actions | size:L
- [ ] S6.2.3: /dashboard/providers (monitoring matrix): 44 rows with status badge, source, last fetch, error; ACTIVE/LIMITED/SOURCE_UNAVAILABLE/ERROR states | size:L
- [ ] S6.2.4: Wire nav links (changelog + providers) if not present | size:S

## M7: Tests | status: pending
### T7.1: Backend tests | agent:Worker
- [ ] S7.1.1: registry: exactly 44 providers, ids match frontend registry, every provider has official source or SOURCE_UNAVAILABLE | size:M
- [ ] S7.1.2: normalization/fingerprint/dedup: stable fingerprint, last_seen_at update, no dup rows | size:M
- [ ] S7.1.3: classification: all 15 change_types map, severity/confidence evidence rules (no UNKNOWN without evidence), no-fabrication invariant | size:L
- [ ] S7.1.4: adapter tests: official source URL validity (HTTP 200/feed parse), lookback window enforced, per-provider isolation, ETag handling | size:L
- [ ] S7.1.5: alerts: severity gating, dedup, email subject format, UNKNOWN never emailed, review/dismiss state | size:M
- [ ] S7.1.6: security: SSRF guard, XSS escaping | size:S
- [ ] S7.1.7: Full pytest suite passes (incl. existing 144) | size:M
### T7.2: Frontend | agent:Worker
- [ ] S7.2.1: tsc + npm run build exit 0 | size:M
- [ ] S7.2.2: mojibake/brand grep = 0 | size:S

## M8: Real verification + deploy + final report | status: pending
### T8.1: Live verification | agent:Reviewer
- [ ] S8.1.1: Reviewer: audit trail check — zero fabricated rows post-fix, zero unknown provider, source_url official domains | size:M
- [ ] S8.1.2: Reviewer: run cron fetch+process on live backend; verify real events stored, matrix populated, no errors | size:M
- [ ] S8.1.3: Reviewer: test email path (subject format), review/dismiss flow, frontend live checks | size:M
- [ ] S8.1.4: Reviewer: full pytest + build pass; existing features regression (alerts page, impact page, agency) | size:L
### T8.2: Deliverables | agent:Worker
- [ ] S8.2.1: Final report: files changed, mechanisms per requirement 1-26, monitored/limited/unavailable matrix, migrations, test results, limitations, brand-note re email subject | size:L
- [ ] S8.2.2: Commit backend + frontend + test repos, deploy both apps | size:M