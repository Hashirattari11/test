# Project Context — AutoFix Frontend Exploration (READ-ONLY MISSION)

## Mission
Produce a structured map of D:\autofix\frontend (Next.js 14 App Router): routes, lib/api.ts function list, per-page red flags, middleware analysis, env inlining, package.json. DO NOT modify files.

## Environment
- Next.js 14.2.15, React 18.3.1, react-dom 18.3.1, TS 5.5.3 (strict). No test framework, no eslint dep, no tailwind.
- Build: `next build`; dev: `next dev`. Backend: FastAPI at NEXT_PUBLIC_API_BASE_URL (http://127.0.0.1:8000 local / http://localhost:8000 fallback).

## Configs (READ ✅)
- **package.json**: deps ONLY next/react/react-dom; devDeps @types/* + typescript. Scripts: dev/build/start/lint.
- **next.config.js**: reactStrictMode only.
- **middleware.ts**: NO REAL AUTH — publicPaths [/ , /login, /auth/callback, /terms, /privacy, /pricing]; static-asset bypass; otherwise just sets header `x-protected-route: true`; NEVER checks token existence/validity (comment says client handles it).
- **vercel.json**: framework nextjs, region sin1, security headers (nosniff/DENY/strict-origin).
- **.env.local**: NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000; NEXT_PUBLIC_GITHUB_CLIENT_ID=**Ov23liRAu5b41z6Bh7dM** (real GitHub OAuth client ID committed — public by design, but committed to repo).
- **.env.vercel**: ⚠️ **FULL Vercel OIDC JWT (VERCEL_OIDC_TOKEN) committed in plaintext — SECURITY FLAG (readable token, exp 1788174370, contains team/project/user IDs).**
- **tsconfig.json**: strict, @/* path alias.

## lib/ (READ ✅)
- **lib/api.ts** (669 lines): `request()` adds Bearer (localStorage autofix_token), 401→clearSession+`window.location.href="/login"`, ApiError coerces payloads (no [object Object]). Endpoints:
  - POST /auth/github/callback; GET /repos; GET /repos/github; GET /repos/:id; GET /repos/:id/detections; GET /repos/:id/alerts; GET /repos/alerts; POST /repos/:id/scan; POST /repos/:id/simulate-breaking-change; GET /repos/:id/provider-coverage; GET /repos/:id/scan-summary; GET /internal/changelog/notices; POST /repos/connect; POST /billing/create-checkout-session; GET /billing/portal; GET /billing/status; GET /repos/:id/fixes?status=; POST approve/dismiss; GET /health/repo/:id/usage-graph (getUsageGraph uses `request<any>` + normalizes object→array); GET /health/usage/:id; GET /health/rate-limit/:id; GET/POST/DELETE /health/provider-connections(+ /test, /collect/:repoId); GET /health/overview; GET /health/repo/:id; GET /health/provider/:p; GET /health/providers; GET /health/issues?…; GET /health/errors|failures|anomalies?limit=; PATCH /health/issues/:id; POST /health/issues/:id/fix; GET /health/history/:id?days=; GET /repos/:id/scans; GET/PUT /notifications/preferences; POST /notifications/test-email.
  - Mismatch flags: HealthRuntimeList index-signature hack (`[listKey: string]: number | HealthIssue[] | undefined` = unsafe); getUsageGraph any+manual normalize; ChangelogNotice nested changelog_events; FixStatus reused for rule_confidence.
- **lib/auth.ts**: localStorage keys `autofix_token`/`autofix_user`; store/get/clear/isAuthed; NO httpOnly cookie (middleware can't validate).
- **lib/admin.ts**: /admin/overview, /admin/alerts/pending, POST approve/reject, /admin/health, /admin/users.
- **lib/providers/types.ts + registry.ts**: 44-entry static PROVIDER_REGISTRY (+PROVIDER_MAP, getProvider...). ENV **NAMES** only, no values — OK.

## components/ (READ ✅)
- **ui.tsx**: `Nav` (client; getUser; logout=clearSession+push /login), ApiBadge, StatusPill, SeverityBadge, Spinner, formatDate, API_META only 5 providers (stripe/shopify/twilio/sendgrid/github).

## Pages READ ✅ (do not re-read)
- **/** landing: client; redirect if authed; static marketing; hardcoded/fake stats "10,000+ APIs", "500+ teams", "99.9% SLA" (app/page.tsx:256,319-327; login page same); provider grid from REGISTRY; personal email hashirattari73@gmail.com (app/page.tsx:489); NO backend call.
- **/login**: client; OAuth → sessionStorage `oauth_state`, buildGithubAuthUrl; error box if client id missing; fake stats; no backend.
- **/auth/callback**: client; code exchange guard via `exchanged` ref (good); state match check; error state; Spinner loading.
- **/terms, /privacy**: static, no client.
- **/pricing**: client; hardcoded PLANS ($500/$2000/$10000); `handleCheckout` = RAW fetch duplicate of createCheckoutSession (pricing/page.tsx:90-104, uses `process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"`); Enterprise→mailto **sales@autofix.example.com** (broken placeholder, :78); `alert()` errors; no empty/error states needed (static).
- **/authorize/[token]**: client; raw fetch GET /agency/authorize/:token + /agency/public-install-url?client_id= — **NO auth header, public, relies on backend**; has loading/error/invalid/valid states.
- **/dashboard/layout.tsx**: client; auth check useEffect→router.replace /login if !isAuthed; `mounted` SSR guard; 3 expandable nav sections + flat items, Admin link only if user.is_admin; signout clears session.
- **/dashboard** (DashboardClient, dynamic ssr:false): listRepos + **N+1 getFixes per repo** (DashboardClient.tsx:42-44) + getBillingStatus; loading skeleton / empty / error states; connect-modal gating `if billing.plan==="trial"` confirm; **mislabel: totalApis = repos.length** (:67).
- **/dashboard/onboarding**: listRepos+getBillingStatus+getAlerts(first repo only); **BUG line 226: step number renders `step.id.split("_").length`** (connect_repo→"2", first_scan→"2", select_plan→"2", first_alert→"2" — all wrong); uses `data!` non-null assertion; has Nav (independent page).
- **/dashboard/repos**: listRepos/scanRepo/listGithubRepos/connectRepo; loading/empty/error; reconnect link if error matches /expired|reconnect|No GitHub connection/i.
- **/dashboard/repos/[id]**: 5 parallel fetches (detections/alerts/fixes/provider-coverage/scan-summary); `load` deps include `selectedProvider` which load() itself sets → **one redundant re-fetch on first mount** (self-triggering effect, not infinite); scan + simulate buttons; loading/empty/error OK.
- **/dashboard/repos/[id]/fixes**: getFixes tabs; **dead-code line 105 `const repoName = fixes?.[0]?.repo_id ? "" : ""`**; approve/dismiss ok; loading/empty/error.
- **/dashboard/settings**: duplicate local `BillingStatus` type (settings/page.tsx:43-50) shadowing api.ts; loadBilling = raw fetch + `localStorage.getItem("autofix_token")` (:111-112); **handleDisconnect only clears localStorage — UI claims repos revoked/alert history deleted but NO backend call** (:129-143); console.error on failure.
- **/dashboard/billing**: getBillingStatus/portal/checkout; loading/error; **placeholder row "Connected Repositories — Would need to fetch from /repos"** (:222); hardcoded prices.
- **/dashboard/alerts**: listAllAlerts; severity+repo filters; loading/empty/error OK.
- **/dashboard/cli**: **raw fetch to HARDCODED http://localhost:8000/cli/local-scan, NO auth header** (:31-35); copy-commands reference `autofix-cli` npm package (likely fictional); mounted gate.
- **/dashboard/changelog**: getChangelogNotices; reshape logic; loading/empty/error; hardcoded "12 providers" empty text vs 44 registry (:181).
- **/dashboard/changelog/[id]**: **fetches FULL notices list, finds by id client-side** (no per-id endpoint) ([id]/page.tsx:37-38); not-found state.
- **/dashboard/agency**: Suspense+useSearchParams; raw fetch /agency/status + /agency/clients (+POST invite, POST resend, DELETE revoke) w/ localStorage token; **`data.detail` may be object→[object Object] risk** (:87); is_agency gate; loading/error/success.
- **/dashboard/settings/api-keys**: raw fetch /api/public/v1/api-keys GET/POST/DELETE w/ localStorage token; shows full new key once; loading/empty/error.
- **/dashboard/settings/integrations**: Slack /slack/connection GET/DELETE + /slack/install; Suspense; loading/error; connected flags.
- **/dashboard/health**: apiFetch /health/overview, listRepos, scanRepo w/ **setInterval stage timer (cleared on success/error — OK)**, getUsageGraph; loading / `!data` error-state / empty graph states.
- **/dashboard/health/providers**: getHealthOverview+getProviderConnections+getProviders; loading/error/empty; API-key password input, test/save/disconnect; capabilities chips.
- **/dashboard/health/usage**: listRepos auto-first + getHealthUsage; loading/empty. 
- **/dashboard/health/quota**: listRepos + **getHealthUsage reused** (same endpoint as usage page — quota page is not quota-specific); loading/empty.
- **/dashboard/health/rate-limits**: listRepos + getHealthRateLimit; loading/empty; pct calc guard.
- **/dashboard/health/trends**: listRepos + getHealthHistory + getUsageGraph; silent catch → empty arrays (no error UI); empty states.
- **/dashboard/health/errors**: getHealthErrors(500) w/ category filter; resolve=updateHealthIssueStatus; queueFix=createIssueFix; **silent catch → [] (no error banner)**; loading + empty.
- **/dashboard/health/failures**: getHealthFailures(500); resolve; silent catch → []; loading + empty.

## Pages READ in last compaction cycle ✅ (do not re-read)
- **/dashboard/health/issues**: apiFetch GET /health/issues?status=open&severity=&category=; silent catch→[]; loading/empty links to /dashboard/health; severity colors map; risk badges (risk_level/risk_score/risk_factors from `res.issues || []` — assumes res object, falls back [] for arrays).
- **/dashboard/health/issues/[id]**: apiFetch GET /health/issues/:id (res.issue + res.repo.full_name); PATCH /health/issues/:id {status} (setStatus, STATUSES open/acknowledged/in_progress/resolved/ignored); POST /health/issues/:id/fix → res.message + res.fix_id.slice(0,8) ("Create GitHub PR (Auto-fix)"); loading + "Issue not found" states; error msg via String(e); prMessage reused for errors.
- **/dashboard/health/incidents**: getHealthOverview + N+1 getHealthProvider per provider (Promise.all, skip on fail) → incidents merged, sorted, slice(0,100); silent catch→[]; loading/empty states; inline styles (status colors active/ongoing/resolved); formatDate(started_at).
- **/dashboard/health/rate-limit-events**: listRepos auto-first + getHealthRateLimit(repoId).snapshots; events as Record<string,unknown>[] cast; pct = (1 - remaining/limit_value)*100 (NaN-guarded); loading/empty; formatDate(recorded_at). NOTE: reuses getHealthRateLimit (same endpoint as /rate-limits).
- **/dashboard/health/anomalies**: getHealthAnomalies(500) → res.anomalies (or []), summary total/critical/high from res; client filter risk_level high|critical (useMemo); loading/empty "No high-risk anomalies"; imports updateHealthIssueStatus but NEVER uses it (dead import); title "Anomalies"; risk factor chips.
- **/dashboard/health/scanner**: listRepos auto-first + getScans(repoId).scans; runScan: scanRepo + 1200ms setInterval stage ticker (cleared in finally, ref-stored ✅ OK); GET /repos/:id/scans refresh after scan; message string for success/fail; scan history table (status COMPLETED/FAILED/else amber; stats.files_scanned/detections_found/findings_total; error_message); promise returned in onScanComplete={() => {}} is IGNORED (fire-and-forget, unhandled rejection possible); empty "No scans yet".
- **/dashboard/health/sdk**: getHealthIssues({category:"dependency",status:"open",limit:200}) → Array.isArray(res) ? res : []; loading/empty; hardcoded majors in empty text (Stripe 18, SendGrid 8, Supabase 2…).
- **/dashboard/health/deprecated**: Promise.all(getHealthIssues({status open,limit 500}), listAllAlerts()); engineFindings = category configuration|dependency; changelogFindings = change_type containing deprecat|remov|retire (client-parse of alerts); loading/empty per section; AlertWithRepo fields a.severity/a.change_type/a.repo_name/a.file_path/a.line_number/a.source_url.

## PENDING (NOT yet read — read next)
- health/breaks/page.tsx, health/auto-fix/page.tsx, health/code-usage/page.tsx, health/providers/[provider]/page.tsx
- app/admin/layout.tsx, admin/page.tsx, admin/users/page.tsx, admin/health/page.tsx, admin/alerts/pending/page.tsx
- app/globals.css (skim only)
- grep for setInterval/console.log/localStorage/NEXT_PUBLIC across app/ to confirm flags

## KEY CROSS-CUTTING FLAGS SO FAR
1. **middleware.ts** protects NOTHING (no token check; header only) — all client-side redirects.
2. **.env.vercel** contains committed Vercel OIDC JWT (secret!) — top security finding.
3. Duplicate raw-fetch patterns bypassing lib/api.ts (pricing, settings, agency, api-keys, integrations, cli, authorize) — inconsistent 401 handling (no auto-redirect) in those.
4. localStorage JWT (XSS-able; no cookie; middleware can't see it).
5. Fake marketing stats on landing/login; sales@autofix.example.com broken contact on pricing.
6. onboarding step-number bug; changelog detail N+1-ish (full list fetch); settings "disconnect" doesn't call backend.

## Current Status
Phase: EXPLORE — ~49/54 pages read. Remaining unread: health/{breaks,auto-fix,code-usage,providers/[provider]}/page.tsx + all 5 admin pages + globals.css skim. After reading: quick grep cross-check (setInterval/localStorage/raw fetch/NEXT_PUBLIC), then compile FINAL structured report in chat (no file writes to app code). Report must include: full route map, lib/api.ts inventory, per-page red flags, middleware analysis (no real auth), env secret flags (.env.vercel OIDC JWT, localStorage JWT, hardcoded localhost in cli page, duplicate raw fetches, fake stats).