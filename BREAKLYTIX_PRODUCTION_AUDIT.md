# BREAKLYTIX PRODUCTION AUDIT

Date: 2026-10-07 · Auditor: Buffy (Codebuff) · Scope: full codebase + production environment
Production: frontend `https://breaklytix.site` (Vercel `autofix`), backend `https://backend-virid-ten-43.vercel.app` (Vercel `backend`)
Repo: `github.com/Hashirattari11/test`, branch `main`

---

## 1. Executive Summary

Full repository inspection (backend 60+ Python modules, 16 routers, frontend 90+ TS/TSX files, db/, .github/workflows, Vercel/Supabase config, tests) plus live production verification.

**Fixed this session (committed `34c4c56`, pushed, both projects deployed):**
1. `users.is_admin` / `users.is_agency` are referenced by admin code but were created by **no migration file** — schema drift that yields `PGRST204` → unhandled 500 on `/admin/users` whenever a production DB lacks ad-hoc columns. Consolidated idempotent migration added ([migration_admin_columns.sql](db/migration_admin_columns.sql)).
2. `/admin/users` scanned the **entire `repos` table** and `/admin/overview` loaded **every alerts row** into Python — unbounded queries that time out as data grows. Now chunked `in_(user_id)` fetches and server-side exact counts, with regression tests ([admin.py](backend/app/routers/admin.py)).
3. OAuth scope `public_repo` → `repo` (private-repo scanning), deployed and verified live.
4. `/admin/alerts/pending` N+1 owner-email lookups → one batched query.

**Verified live:** OAuth flow correct (`Iv23limLGl5AHmFqR9Xv`, redirect_uri pinned, app "Autofixes", new scope baked into chunk `page-30f7e33cd53f99e7`), apex/www/robots/healthz/CORS all 200, security headers present.

**Update (same day, after initial report):** the root cause was **confirmed at runtime** from Vercel logs of the user's live traffic: the `users` select including `is_admin,is_agency` is answered by PostgREST with `400 Bad Request` (column does not exist), caught by no handler at `admin.py:262 admin_users .execute()`, and surfaced as the generic 500 — while `/admin/overview`, `/admin/alerts/pending`, `/admin/health` all returned 200. The fix (§17 step 1, apply the migration in Supabase) is the one remaining user action.

**Verdict: READY WITH WARNINGS** (§18).

## 2. Current Admin Panel Error

- **Root cause (CONFIRMED at runtime — Vercel logs, user's live traffic 15:51–15:52 UTC):** `backend/app/routers/admin.py` selects `is_admin, is_agency` from `users` explicitly. A repo-wide grep shows **no SQL migration anywhere** creates those columns, and the production database confirms their absence: the log shows `GET /rest/v1/users?select=...,is_admin,is_agency,... → "HTTP/2 400 Bad Request"` (PostgREST PGRST204 column-not-exists in body), then `UNHANDLED ERROR` with the traceback ending at `admin.py", line 262, in admin_users / .execute()`, returned as `500 "Internal server error"` — exactly what the Admin UI displays. In the same session `/admin/overview`, `/admin/alerts/pending` and `/admin/health` returned 200 because their queries touch only existing columns.
- **Affected files:** [backend/app/routers/admin.py](backend/app/routers/admin.py) (`/admin/users` select, line ~246), [backend/app/deps.py](backend/app/deps.py) (`require_admin` reads `is_admin`), [db/migration_admin_columns.sql](db/migration_admin_columns.sql) (new fix).
- **Affected API:** `GET /admin/users` (router-level `Depends(require_admin)`; `require_admin` itself tolerates a missing column via owner-UUID fallback + broad except, so the 500 fires inside the endpoint query, after authz passes).
- **Affected DB operation:** `db().table("users").select("id,email,github_login,plan,is_admin,is_agency,created_at,is_suspended,suspended_at,suspended_reason").order("created_at").limit(...)` — PostgREST rejects the whole select when any named column is absent.
- **Exact fix:** (a) new consolidated idempotent migration [db/migration_admin_columns.sql](db/migration_admin_columns.sql) adding `is_admin`/`is_agency` (+ suspend columns + support tables) — *must be applied to prod Supabase, see §17 step 1*; (b) hardening: chunked/bounded queries in `admin.py` so large datasets can't reproduce the 500 via timeouts; (c) 3 regression tests added.
- **Contributing perf bug fixed:** `/admin/users` previously fetched ALL repos (`select(...).execute()` unbounded) to bucket by user — replaced with chunked `in_("user_id", …)` queries (test-pinned).

## 3. Critical Issues Found

1. **Schema drift: `users.is_admin`/`is_agency` absent from every migration file** — fixed in code (migration file added; apply to prod, §17). Consequence when missing: Admin Panel 500. Severity of the drift itself: CRITICAL → now MITIGATED in repo, pending prod apply.
2. **3 credentials were leaked in chat earlier and remain unrotated** (GitHub OAuth client secret, Vercel token, Supabase access token). Not rotated per your instruction; an attacker with them can read/modify the entire DB and deploy code. HIGH–CRITICAL until rotated (you, via dashboards).

## 4. High Priority Issues

1. **Vercel env API vs running instance secret mismatch** — `decrypt=true` values for `JWT_SECRET`/`CRON_SECRET` are rejected by the live backend (tested before and after a fresh deploy). Either the platform stores different values than returned, or values were updated without a subsequent successful redeploy at the time. Impact: I could not mint sessions; GH Actions crons succeeded Oct 6, so the *runtime* secrets are functional. Monitoring, not blocking.
2. **GitHub Actions cron secret at risk after your Oct 5 `INTERNAL_SECRET` rotation** — workflows use repo secret `INTERNAL_SECRET`; if the GH copy wasn't updated, daily Changelog Monitor (06:00 UTC) starts failing 401. Latest run (Oct 6) success; today's run pending. Action: compare/re-set GH repo secret.
3. **RLS disabled on all tables** (architecture decision, documented in prior audit) — isolation enforced purely at the API layer. It holds today (see §6 tests) but defense-in-depth is absent. Recommend per-user policies as a follow-up.

## 5. Medium/Low Issues

- **M1** `posts (...)` unbounded tables have no DB-level uniqueness on `email_deliveries.fingerprint` (dedup is query-based) — acceptable at current scale.
- **M2** 20 silent `except Exception: pass` blocks (mostly email logging where intentional); acceptable but worth converting to debug logs.
- **M3** `backend/.env.dt*` redacted env copies in the backend dir (not git-tracked) — delete to avoid confusion.
- **L1** `debug/*` endpoints expose only prefixes/booleans (verified) — fine.
- **L2** Duplicate users rows for the owner (documented in prior audit) — merge is destructive, left to you.
- **L3** pytest-asyncio deprecation warning (unchanged from before).

## 6. Security Audit

- No hardcoded secrets in source (regex sweep: `sk_live/sbp_/ghp_/vcp_/re_/github_pat_`) — only detection *patterns* in the scanner registry.
- No `.env` or secret files git-tracked; no env/secret filenames ever added in the last 500 commits; `.gitignore` covers `.env*`.
- Fernet encryption for GitHub tokens and provider API keys at rest; keys never returned by any endpoint (only `has_key` + `last_error`).
- Sessions: HS256 JWT (30-day TTL), validated against DB each request, suspended-account check in `get_current_user_id`; bearer tokens in localStorage (no cookies → no CSRF surface; state-changing CORS restricted).
- Security headers middleware on every response (CSP, HSTS, X-Frame-Options DENY, nosniff, referrer-policy); admin UI hidden links are cosmetic — server-side `require_admin` is the gate.
- Internal endpoints fail closed (503 if secret unset, 401 on mismatch) with constant-time compare.
- OAuth error mapping prevents reflection of redirect_uri/secrets; unhandled-exception handler returns generic 500 with server-side-only traceback.
- Leaked-in-chat credentials: **rotation pending (yours)** — see §3.2.

## 7. Database Audit

- Single Supabase project; backend-only service-role access; the browser never receives DB credentials (`NEXT_PUBLIC_*` vars are API base URL, GitHub client ID, legal/support strings only).
- Base schema [db/schema.sql](db/schema.sql) + phase migrations + [migration_all_pending.sql](db/migration_all_pending.sql) + digital-twin migration (applied Oct, 6/6 statements) + **new** [migration_admin_columns.sql](db/migration_admin_columns.sql).
- Prod schema verified indirectly via runtime logs: `users.is_admin`/`is_agency` are **confirmed missing in production** (PostgREST 400 on the column list, §2). Apply §17 step 1 (idempotent migration) to align.
- Indexes present for the hot paths (repos.user_id, alerts.repo_id/event, changelog dedup/pending, system_health, email_deliveries fingerprint/user). RLS: intentionally OFF (§4.3).
- `digital_twin_runs`/`digital_twin_analyses` exist with 0 rows (no simulation run yet — honest empty state, no fake data).

## 8. Frontend Audit

- `tsc --noEmit` clean; `next build` clean (42 routes, exit 0).
- `API_BASE` from `NEXT_PUBLIC_API_BASE_URL` (prod value confirmed by working CORS preflight against the prod backend); no localhost/127.0.0.1 outside the intentional isLocal OAuth regex.
- OAuth client: `buildGithubAuthUrl` + pinned `redirect_uri` verified live in the served chunk; old `Ov23li…` ID absent from all served chunks.
- Admin UI surfaces backend `detail` verbatim (honest errors, no fake data); loading/empty/error states present; hydration-safe styles from earlier commit.
- Repository switching is URL-param driven with refetch; alerts/impact/fire-drill/auto-fix pages all request scoped data (backend enforces ownership).

## 9. Backend Audit

- 16 routers mounted; every `/admin/*` route behind `Depends(require_admin)`; every `/internal/*` route behind `require_internal_secret` (fail-closed).
- Global exception handler: full traceback to server logs, generic message to client (verified live: 401/403/500 paths return structured JSON).
- `db.py` transient-retry layer (3 attempts, backoff, idempotent methods only) for the burst-connection 500 class; `_patched()` widens supabase-py key regex for `sb_secret_` keys.
- Ownership: `_owned_repo()` → 404 on foreign repos, used consistently by repos/fixes/health/impact/digital-twin routers (see isolation tests).
- 105 `except Exception` blocks, of which ~20 swallow silently — mostly intentional delivery-log paths; flagged as M2, none hide auth/authz failures.

## 10. Authentication/OAuth Audit

- Flow: GitHub OAuth → `/auth/github/callback` (code+redirect_uri) → token exchange → Fernet-encrypt → upsert user → JWT. Scope now `read:user user:email repo` (deployed live; you must re-login to grant).
- Both `NEXT_PUBLIC_GITHUB_CLIENT_ID` (frontend) and `GITHUB_CLIENT_ID/SECRET` (backend) point to the same classic app "Autofixes" (`Iv23li…`); live authorize URL verified (correct app + callback; no "Be careful" warning).
- State parameter generated and validated client-side per login; redirect_uri pinned to `SITE_URL` except explicit localhost.
- Admin authorization is DB-driven (`users.is_admin`) with a hardcoded owner-UUID fallback (documented; acceptable for single-owner phase, remove when multi-admin).
- Suspended accounts: blocked at token validation and at login.

## 11. GitHub/Git Audit

- `main` == `origin/main` at `34c4c56` (push verified: `6d7c8d3..34c4c56`). Working tree clean except your pre-existing untracked logs/scripts and the unstaged `vercel.json` deletion — untouched.
- 27 backend test files; 3 new regression tests added this session.
- GitHub Actions: both workflows secret-gated; runs green through Oct 6; cron-secret risk flagged in §4.2.
- No secrets in tracked files or recent history (name-based scan of last 500 commits).

## 12. Deployment Audit

- Backend deployed this session from `34c4c56` → `backend-24tpk2rpi` READY and aliased to `backend-virid-ten-43.vercel.app` (verified via API). Frontend deployed → `autofix-g7cexc13i` READY, aliased to `breaklytix.site` (new OAuth chunk served — verified).
- Live checks: apex 200, www 200, robots 200, `/healthz` 200, unauthenticated `/admin/users` 401, CORS preflight 200 with correct `Access-Control-Allow-Origin: https://breaklytix.site`.
- Runtimes: Next 14.2.15 / React 18.3.1 / FastAPI 0.115.6 / supabase-py 2.11.0 / httpx 0.28.1; Python runtime via `@vercel/python`; no Node version pin found in `frontend/vercel.json` (uses platform default — L-risk only).
- No localhost URLs in production bundles; SEO files (42-URL sitemap, manifest, OG) verified earlier and re-checked.

## 13. Environment/Secrets Audit

Matrix (values never printed):

| Variable | Used by | Where | Secret | Prod set | Notes |
|---|---|---|---|---|---|
| NEXT_PUBLIC_API_BASE_URL | FE | build | no | yes | points to prod backend |
| NEXT_PUBLIC_GITHUB_CLIENT_ID | FE | build | no | yes | `Iv23li…` verified live |
| NEXT_PUBLIC_LEGAL_ADDRESS/ENTITY/SUPPORT_EMAIL | FE | build | no | yes | static legal info |
| SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY | BE | runtime | **yes** | yes | service role, server-only |
| TOKEN_ENCRYPTION_KEY | BE | runtime | **yes** | yes | Fernet for stored tokens |
| JWT_SECRET | BE | runtime | **yes** | yes | session signing |
| GITHUB_CLIENT_ID / GITHUB_CLIENT_SECRET | BE | runtime | **yes** | yes | matches frontend app |
| INTERNAL_SECRET / CRON_SECRET | BE + GH Actions | runtime | **yes** | yes | rotation pending in GH (§4.2) |
| RESEND_API_KEY / RESEND_FROM_EMAIL | BE | runtime | **yes** | yes | owned domain sender |
| STRIPE_* (secret/webhook/prices) | BE | runtime | **yes** | yes* | *present in config; live checkout not exercised |
| GITHUB_APP_ID / PRIVATE_KEY / SLACK_* | BE | runtime | **yes** | partial | agency/Slack features dormant |

Issues: three leaked credentials pending rotation (§3.2); runtime-vs-API secret mismatch (§4.1); everything else consistent across code, config, and deploys.

## 14. Feature Regression Results

| Feature | Status | Evidence |
|---|---|---|
| Admin authentication/authorization | PASS (unit) | 8 `require_admin` tests + owner fallback test, 248/248 suite |
| Admin users endpoint logic | PASS (local) / **FAIL (prod) → fix pending user migration** | chunked-query tests; prod 500 root-caused at runtime (missing columns) — resolves after §17 step 1 |
| Login/OAuth flow | PASS (live) | browser: correct app, redirect, "Sign in to continue to Autofixes"; old client_id gone |
| New `repo` scope | PASS (live) | chunk `page-30f7e33cd53f99e7` contains `read:user user:email repo`; your re-login pending |
| CORS | PASS (live) | preflight 200, correct allow-origin/methods/headers |
| Repo isolation (IDOR) | PASS | `_owned_repo` 404 pattern + `test_repo_isolation.py` suite |
| Provider monitoring | PARTIAL | dashboard honestly renders real state; staleness stems from expired GitHub token + duplicate user rows (user actions) |
| Findings/Alerts pipeline | PASS (local) | unit suites; live alerts path unchanged since last verified deploy |
| Impact Engine / Fire Drill | UNVERIFIED (live) | code paths intact + tests; needs your session to exercise |
| Digital Twin | PASS (local) / UNVERIFIED (live) | tables migrated (0 rows, honest); graceful-degradation shipped |
| Auto-Fix safety gate | PASS (local) | validator/PR-flow tests; PR creation needs valid GitHub token (yours expired — re-login) |
| Email pipeline | UNVERIFIED (live) | Resend key configured; sender domain set; no live send attempted this session |
| GitHub Actions crons | PARTIAL | green through Oct 6; today's run pending after your secret rotation |
| 24h scheduled scans | PARTIAL | cron wired; depends on the cron secret issue above |
| Frontend build | PASS | `next build` exit 0, 42 routes |
| Backend startup | PASS (live) | `/healthz` 200 on fresh deploy |

## 15. Tests Executed

| Command | Result | Evidence |
|---|---|---|
| `python -m pytest -q` (backend) | **248 passed** (245 + 3 new) in ~4.6s | terminal output, exit 0 |
| `npx tsc --noEmit` (frontend) | clean, exit 0 | no output |
| `npm run build` (frontend) | exit 0, 42 routes | build summary |
| `curl https://backend…/healthz` | 200 | sweep output |
| `curl -X OPTIONS …/admin/users` (CORS) | 200 + correct ACA headers | headers captured |
| `curl https://breaklytix.site/` (+ www, robots) | 200/200/200 | sweep output |
| OAuth chunk inspection (live JS) | `Iv23li…` + `read:user user:email repo`, no `Ov23li…` | chunk hash `page-30f7e33cd53f99e7` |
| Browser OAuth flow (live) | GitHub authorize page: "Autofixes", correct callback | preview snapshot |
| Minted-JWT `/admin/users` (prod) | 401 "Invalid session token" | runtime secret mismatch — superseded by live-traffic log capture below |
| **Live-traffic log capture** (`vercel logs --json` during user's Admin visit) | **500 root cause CONFIRMED**: `users` select with `is_admin,is_agency` → PostgREST `400 Bad Request` → unhandled → 500 at `admin.py:262`; sibling admin endpoints 200 | log excerpts in §2 |
| `vercel logs --json` (2 deploys) | retained windows clean (no 500s in window; old logs expired) | log dumps |
| Secret scan (source + git history names) | no hits | grep outputs |

## 16. Files Changed

- [db/migration_admin_columns.sql](db/migration_admin_columns.sql) — **new**: consolidated idempotent schema-alignment migration (admin flags, suspend columns, support tables, grants).
- [backend/app/routers/admin.py](backend/app/routers/admin.py) — chunked bounded repos fetch in `/admin/users`; server-side exact counts in `/admin/overview`; batched owner-email lookup in `/admin/alerts/pending`.
- [backend/tests/test_admin_queries.py](backend/tests/test_admin_queries.py) — **new**: 3 regression tests pinning the bounded-query behavior.
- [frontend/lib/api.ts](frontend/lib/api.ts) — OAuth scope `public_repo` → `repo`.
- Commit `34c4c56` pushed to `origin/main`; backend + frontend deployed to production.

## 17. Remaining Risks & Your Action List

1. **Apply the migration to prod (5 min, required):** Supabase SQL editor → paste [db/migration_admin_columns.sql](db/migration_admin_columns.sql) → Run. Idempotent; then open the Admin Panel — if `is_admin` was the missing column, users load immediately.
2. **Rotate the 3 leaked credentials** (GitHub OAuth client secret, Vercel token, Supabase access token) — dashboard-only operation, not done by me per your instruction.
3. **Update `INTERNAL_SECRET` in GitHub repo secrets** to match the Oct 5 Vercel rotation (else crons 401).
4. **Re-login with GitHub** to grant the new `repo` scope, then reconnect/scan repos — also resolves the "0 monitored repositories / Degraded" staleness.
5. If the Admin Panel still 500s after step 1, send me the word — the traceback will now be in Vercel logs and I can pinpoint any second cause immediately.

## 18. Production Readiness

**READY WITH WARNINGS.**

Why not READY: prod DB schema alignment is one user step away (§17.1 — run the migration; the 500's root cause is now runtime-confirmed, so this is a known-quantity fix); three credentials remain unrotated after leaking in chat; cron secret sync pending.

Why not NOT READY: all fixes are committed/pushed/deployed and tested (248/248, clean builds); live surface verified healthy (auth flow, CORS, security headers, health endpoints, correct OAuth identity); no fake data, no weakened security, no disabled controls anywhere; isolation tests pass; remaining items are configuration/user actions, not code defects.
