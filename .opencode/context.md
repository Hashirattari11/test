# Project Context

## Environment
- Frontend: Next.js 14.2.15 (TS, App Router) `D:\autofix\frontend` — dev URL: frontend-eight-phi-60.vercel.app
- Backend: FastAPI (Python 3.12) `D:\autofix\backend` — prod: backend-virid-ten-43.vercel.app
- DB: Supabase (MCP tools; service_role key bypasses RLS - DO NOT enable RLS blindly)
- Platform: win32 PowerShell 5.1 (no &&, foreground bash only; run_background=cmd.exe fails $env:)

## Gates
- Frontend: `npx tsc --noEmit` + `npm run build` (workdir frontend) — PASS (82 pages)
- Backend: `$env:PYTHONPATH="D:\autofix\backend"; python -m pytest -q` foreground — 144 passed
- Deploy (env-var, SEQUENTIAL never parallel): `VERCEL_ORG_ID=team_VajkoNE2yGmuAR89Mm13PZx3` + `VERCEL_PROJECT_ID` (backend prj_Zw3MX8LSD6C4I6C4WoknhsHMxzjI / frontend prj_A73XsdB63JtYbfaFrsjrUK9Yhxja) `vercel deploy --prod --yes` from folder. Root .vercel renamed .vercel.bak2 — KEEP RENAMED. Stray autofix project prj_6i3aRh5pWFnWASmzgjfq0T5MzeLM polluted (avoid).

## Current Status (M19 repo-picker fix in progress — deployed & live-verified)
- **M19 GitHub repo picker fix** (frontend-only, NOT yet deployed as of this write): ROOT CAUSE of "picker missing after GitHub connect" = navigation gap, NOT a code bug. Picker page /dashboard/repos fully intact (button always rendered, picker modal fetches /repos/github, connected ✓, connect upsert on_conflict user_id+github_repo_id, no 3-repo limit). BUT sidebar had NO "Repositories" item AND dashboard CTAs ("Connect a GitHub repository" empty-state + "+ Connect Provider or Repository") pointed to /dashboard/settings/integrations = SLACK-ONLY page (no GitHub picker). FIXED: layout.tsx added "Repositories" nav item (flatItems, after Overview) + ReposIconSVG; DashboardClient.tsx both CTAs -> /dashboard/repos; repos/page.tsx picker modal -> 401="GitHub authorization needs to be renewed."+Reconnect GitHub(/auth/github), other err="Unable to load your GitHub repositories."+Retry, empty->honest empty state (was blank). Backend /repos/github verified healthy live (demo no-token -> 400 fail-closed; owner DB github_access_token present -> real list; types align str). OWNER ACTION needed later: browser click-through to connect the 4th repo (agent has no GitHub session).
- **M18 real-account-only + 10-day unlimited trial** (deployed): /auth/demo now requires X-Internal-Secret (public 401, internal 200, GET method); LoginClient demo button removed; /login 2kB; billing.py TRIAL_DAYS=10 + in_unlimited_trial() -> effective monitored_api_limit=-1 (unlimited) during window; owner hashirattari73@gmail.com (3d206f17-7abc-4857-be29-00c8406ce16f) monitored_api_limit=-1 permanent; /billing/status live -> {"plan":"trial","monitored_api_limit":-1}.
- **M17 FINAL PRODUCTION AUDIT** (complete): GH Actions daily-stripe pipeline (.github/workflows/stripe-changelog-cron.yml: fetch->process->daily-scan 06:00 UTC; needs exactly 2 secrets BACKEND_URL + INTERNAL_SECRET — BOTH CONFIGURED by user, repo pushed; do NOT modify this workflow or secrets), changelog_events title/severity/deadline fixed, run_daily_scan detections->api_detections fixed, process_new_events bounded 120, impact analysis 60.4s->2.8s, cron_run_log=10, daily_scan_runs=3, changelog_events=353, alerts=8, impact_analyses=85, REAL emails to owner (Resend sandbox: non-owner sends 403 until domain verified). Fire drill + auto-fix PR pipeline REAL and live-guarded.
- Auth model: ensureSession() is a NO-OP now (no demo); dashboard layout no-token -> /login; real flow /auth/github -> callback -> storeSession -> legal-acceptance|dashboard. /auth/demo GET + X-Internal-Secret only (internal tests).
- Live: backend backend-virid-ten-43.vercel.app (healthz 200); frontend frontend-eight-phi-60.vercel.app (/login / / /pricing /docs 200). Deployment via VERCEL_PROJECT_ID env-var, SEQUENTIAL, from each folder (root .vercel renamed .vercel.bak2 — KEEP; stray prj_6i3aRh5pWFnWASmzgjfq0T5MzeLM polluted — avoid).

## Key Files
- frontend/app/dashboard/layout.tsx (sidebar flatItems incl NEW "Repositories"; ReposIconSVG; auth gate ~L102; account menu; sign-out -> /login)
- frontend/app/dashboard/repos/page.tsx (+ Connect Repository picker modal: 401/Retry/empty states; connect upsert; auto-scan on connect)
- frontend/app/dashboard/DashboardClient.tsx (both repo CTAs -> /dashboard/repos; Connections/Monitored APIs stats)
- frontend/app/dashboard/health/scanner/page.tsx (dropdown scan; NOTE: connect picker lives on /dashboard/repos, NOT here)
- frontend/lib/api.ts (request()/ApiError{status}, listRepos/listGithubRepos/connectRepo, githubCallback)
- frontend/lib/auth.ts (getToken/getUser/storeSession/clearSession; ensureSession no-op)
- backend/app/routers/repos.py (L106 /repos/github picker endpoint — token->list_user_repos, 401->expired msg, 502 infra; L130 list_connected; L259 /repos/connect upsert on_conflict=user_id,github_repo_id; L313 scan)
- backend/app/github_client.py (L136 list_user_repos — GET /user/repos per_page 100 paginated, github_repo_id=str(id))
- backend/app/billing.py (TRIAL_DAYS=10, in_unlimited_trial, get_user_plan_info)
- backend/app/routers/auth.py (/demo GET guarded by require_internal_secret; /github/callback)
- .github/workflows/stripe-changelog-cron.yml — DO NOT MODIFY (daily-scan infra, 2 secrets set)
- .opencode/todo.md M17/M18 complete, M19 in progress

## Pending / Owner-level
- M19 frontend deploy (in progress — after gates PASS) then live /dashboard/repos 200 check.
- Browser click-through to connect 4th repo (owner action — agent has no GitHub session; everything code/Db/API-side verified).
- Real browser OAuth round-trip test (interactive GitHub sign-in) — API chain fully verified, UI live.
- RESEND_FROM_EMAIL verified sender in Resend (email feature needs it for real sends; currently sandbox -> non-owner 403).
- Stripe live keys if billing activated; /authorize/[token] legacy route exists.
- Admin login requires is_admin=true user (demo is 403 — correct).