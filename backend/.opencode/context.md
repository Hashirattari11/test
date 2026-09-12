# Project Context

## Mission
RESEARCH-ONLY: Map the FastAPI backend at D:\autofix\backend. No file modifications.
Requested deliverables: (1) full endpoint inventory, (2) red flags with file:line, (3) db.py analysis, (4) deps.py analysis, (5) schemas.py model, (6) billing analysis, (7) public_api.py analysis.

## Environment
- Stack: Python FastAPI + Supabase (PostgREST service-role key) + Resend email + Stripe + GitHub OAuth/App
- Env files present: .env, .env.example, .env.local, .env.vercel (win32, NOT a git repo at root; backend has .git)
- NOT a git repo at D:\autofix (workspace root)

## Current Status (READ COMPLETE ✔)
Files fully read (all routers + core modules + health modules):
- app/db.py, deps.py, schemas.py, crypto.py, github_client.py, github_app.py
- app/alerts.py, billing.py, digest.py, email.py, email_service.py, email_client.py
- app/main.py, config.py
- app/routers/: auth, billing, cli, fixes, internal, repos, slack, public_api, agency, admin, health, notifications
- app/health/: engine, bridge, collectors, dependencies, forecast, issues, key_validation, provider_capabilities, redact, risk, usage_graph, __init__

## Key Findings (condensed)
### Endpoints (register in main.py: auth, billing, cli, fixes, repos, internal, slack, public_api, agency, changelog, admin, health, notifications)
- /auth/github/callback POST (public, OAuth) → users upsert; /auth/me GET (JWT)
- /repos/* : github list, connect, scan, detections, alerts, simulate-breaking-change, provider-coverage, scan-summary, scans, findings, dashboard/stats, health — all Depends(get_current_user_id)
- /billing/*: create-checkout-session, portal, status (JWT), /webhooks/stripe/billing POST (Stripe sig)
- /fixes via /repos/{repo_id}/fixes (create/list/approve/dismiss) — JWT
- /internal/*: scan-stripe/sendgrid/github/shopify/twilio, alerts/process, digest/send-weekly, migrate-phase-b — require_internal_secret
- /slack/*: install, oauth/callback (public), connection GET/DELETE, interactions POST (sig-verified)
- /api/public/v1/*: detections, alerts, fixes (Bearer afx_live_), api-keys CRUD (JWT)
- /agency/*: status, clients CRUD, authorize/{token} (public), install-url, public-install-url, github-install-callback, authorize/{token}/complete (public)
- /admin/*: overview, alerts/pending, approve/reject, health, users — require_admin
- /health/*: many — all JWT (+agency/overview requires is_agency)
- /notifications/*: preferences GET/PUT, test-email — JWT
- Meta: /, /healthz, /debug/oauth, /debug/crypto, /debug/email (internal secret)
- NOT yet read: app/changelog/router.py (changelog_router), app/changelog/admin.py, app/mocks/mock_changelog_event.py, app/slack_integration.py, app/scraper.py (referenced)

### RED FLAGS found so far (file:line)
1. main.py:19-23 ALLOWED_ORIGINS hardcoded set ≠ config.settings.cors_origins (config.py:141-143 includes https://frontend-*.vercel.app wildcard) — CORS DRIFT
2. deps.py:75 `x_internal_secret != expected` — plain string comparison, NOT secrets.compare_digest (timing attack)
3. github_app.py:52, 87 bare `except Exception: pass` swallowing errors → returns None/[] (fake failure)
4. github_client.py:190-193 trees truncated → pass (silent partial scan)
5. schema: internal.py uses exec_sql rpc (migrate-phase-b) — raw SQL via RPC
6. alerts.py:46-48 bare except pass (Slack), alerts.py:179-180 except → return "low"
7. billing.py routers: billing.py:50-51 & 70-71 `detail=f"Stripe error: {exc}"` — leaks Stripe exception detail (may include internal info) to client; 500 "Webhook processing failed: {exc}"
8. billing.py:51 HTTPException 502 with str(exc) — Stripe error leak
9. routers/billing.py:106-107: current_period_end=None + cancel_at_period_end=False hardcoded (TODO) — fake/incomplete billing status
10. repos.py:232-234 connect auto-scan failure swallowed silently; fixes.py:173-174 bare except pass on PR insert
11. repos.py:968 `get_cipher().decrypt(repo["access_token"])` — no token fallback unlike scan (could KeyError)
12. public_api.py:21 _rate_limits in-memory dict — per-process, not distributed; no persistence (multi-instance bypass)
13. public_api.py:190-206 api_name filter uses `.ilike` on alerts (column may not exist → error)
14. slack.py:150-175 interactions — approve action lookups by channel, no per-user auth but sig-verified; `_approve_fix_via_slack` swallows GitHubError
15. agency.py:559-560, 655-656 bare except pass (repo connect failures skipped silently)
16. agency.py:579-580 complete_authorization stores RAW github_token on agency_clients (unencrypted! vs crypto elsewhere) — SECRET AT REST PLAINTEXT
17. admin.py:117-118 bare except pass (email preview render)
18. email_service.py:101-102 except Exception → return prefs (swallowed); 147-149 except pass on delivery log; 189-190 except → len(rows)
19. db.py: `_patched()` monkeypatches supabase re module to accept sb_secret_ keys (db.py:22-57) — fragile hack
20. cli.py:137-138 bare except pass on file reads; cli local-scan has no file path restriction (arbitrary server FS read via /cli/local-scan — path traversal! user gives path, server reads local dirs)
21. github_client.py:100,103,115,147,168,187 error text includes resp.text — could echo GitHub error bodies (moderate)
22. auth.py:24-28 `detail=f"{exc}; redirect_uri={body.redirect_uri!r}"` — echoes redirect_uri (user input) back
23. repos.py:300-302 GitHubError on blob fetch → continue (silently skips files) ; repos.py:446-452 except Exception → log
24. fixes.py:329 `await _create_fix_pr` — async def calling sync httpx in threadpool (async def used with blocking calls, no await inside except call) — incorrect async usage: async def with sync blocking work
25. internal.py:251-252 migrate error surfaced `str(e)[:100]` — may leak SQL/RPC internals; 500/502 with str(exc) includes requests errors with URL bodies
26. slack_integration usage: main debug/email echo resend_key_prefix (partial secret) — main.py:143 partial key prefix echoed (minor)
27. deps.py:61 hardcoded admin user UUID "3d206f17-..." backdoor owner bypass — hardcoded admin fallback
28. health.py:534 returns raw DB row for reliability_issues (no shape validation); update_issue accepts arbitrary body dict (only status handled)
29. health.py:805-806 test_provider_connection accepts api_key and returns message from validation — validation message doesn't include key, OK
30. email.py send_invite_email: auth_link built from raw token — fine
31. repos.py:150 list_all_alerts / 571 get_alerts query `.in_("repo_id", repo_ids)` where repo_ids could be empty — handled (returns [] if no repos in list_all_alerts)
32. digest.py:184 uses settings.frontend_origins.split(",")[0] — OK
33. admin.py:61-71 approve_alert: even when email fails, marks status sent (fake success-ish) — admin.py:192-196: `email_sent` False but status="sent"
34. internal.py:215 send_approved_alerts() called unconditionally ignoring result
35. billing.py:44-46 ValueError raised with unknown plan (surfaced 400 by router); Stripe customer create stores metadata OK. Stripe IS real (not stubbed) — uses stripe SDK, webhook construct_event, idempotency table.
36. billing.py:108-115 process_stripe_webhook: `raise ValueError(f"Webhook signature verification failed: {exc}")` router returns 400 with exc detail (400-level)
37. billing.py:173 PLAN_LIMITS.get(plan, 10)
38. billing/get_user_plan_info: reads plan_usage rows only within current period — count default 0
39. public_api rate limit: dict keyed by user_id; limit values; window 3600; 429 on exceed
40. public_api auth: `Header(...)` required Authorization; sha256 hash comparison via DB eq on key_hash — timing safe enough (DB lookup); afx_live_ prefix check
41. auth me: /auth/me returns user — JWT; deps get_current_user_id reads payload only, does NOT check user exists (some endpoints using user_id only)
42. github_app.py:92-94 build_install_url state=client_id plaintext (CSRF-ish; state not signed)
43. fixes.py:182-183 POST /{repo_id}/fixes creates fixes w/o plan check
44. repos.py:1055-1058 dashboard_stats providers_planned=0 hardcoded
45. billing router /status: plan inference from limit values only (10/50/-1) — fragile; current_period_end=None hardcoded — INCOMPLETE/FAKE-ish response fields
46. main.py:63 prints full traceback to stdout (not log) — no logger; leaks stack to logs (server-side only per comment)

## db.py analysis
- db.py:60-67 @lru_cache db() builds supabase Client with settings.supabase_url + settings.supabase_service_role_key (SERVICE ROLE = full DB access)
- db.py:22-57 _patched() monkeypatch widening key regex to accept sb_secret_ keys (replaces module-level re for supabase._sync.client)
- NO mock/_ChainDB/_RespDB fallback in app code — db() raises RuntimeError if env missing (db.py:62-65 fail closed)
- fetch_one helper (db.py:70-77) via select/eq/limit

## deps.py analysis
- get_current_user_id: HTTPBearer(auto_error=False) → jwt.decode HS256 with settings.jwt_secret (deps.py:29-46)
- issue_session_token: JWT with sub/iat/exp (ttl 720h from config)
- require_admin (deps.py:53-63): DB check users.is_admin + hardcoded owner UUID fallback
- require_internal_secret (deps.py:69-76): header X-Internal-Secret vs settings.cron_secret (CRON_SECRET or INTERNAL_SECRET) — PLAIN == COMPARISON (insecure, timing attack)
- No API-key dependency in deps; public_api has own _authenticate_bearer

## schemas.py (models listed in file)
Auth: GitHubCallbackIn, UserOut, AuthOut; Repos: RepoConnectIn, RepoOut, GitHubRepoOut, ScanResultOut; Detections: DetectionOut, ApiFootprintGroup, DetectionsOut; Alerts: AlertOut, AlertWithRepoOut, SimulatedAlertLocation, SimulateBreakingChangeOut; Internal: ScrapeResultOut, ProcessResultOut; Billing: CheckoutSessionIn/Out, BillingPortalOut, BillingStatusOut; Fixes: FixOut, FixesListOut, FixActionIn/Out; Scans: ScanStats, ScanOut, ScansListOut; Findings: FindingOut, FindingsListOut, FindingUpdateIn; PRs: PullRequestOut, PRsListOut; FixCreateIn/Out; DashboardStatsOut; RepoHealthOut

## Pending Tasks (must read before final report)
1. app/changelog/router.py + app/changelog/admin.py (changelog_router mounted in main.py)
2. app/mocks/mock_changelog_event.py (MOCK_BREAKING_CHANGES used by repos.simulate_breaking_change — hardcoded mock data served as real?)
3. app/slack_integration.py (verify_slack_signature, exchange_install_code, save_connection)
4. app/scraper.py (used by internal endpoints)
5. Grep for _ChainDB/_RespDB/fake usage in app code (verify none)
6. Grep for bare except/flags to confirm
7. WRITE FINAL STRUCTURED REPORT to user (compact list, file:line specifics)

## Conventions observed
- Sync def route handlers (FastAPI threadpool); a few async def (slack interactions, stripe webhook, approve_fix) with blocking calls inside
- Fernet encryption for GitHub tokens at rest; raw token stored plaintext in agency_clients.github_access_token (agency.py:612)
- All DB via supabase-py fluent API; no ORM; service role key
- .opencode/ dir now exists (this file)