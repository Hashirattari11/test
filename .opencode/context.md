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

## Current Status (M16 + fixes deployed & live-verified)
- **M16 real GitHub login** (deployed): /login (Continue with GitHub + demo), /auth/github (CSRF state -> GitHub authorize), /auth/callback (validate state -> POST /auth/github/callback -> storeSession -> legal-acceptance|dashboard). Landing "Log in" link; dashboard menu "Sign in with GitHub" for demo. GitHub OAuth App callback REGISTERED (authorize 302 no error). Frontend env: NEXT_PUBLIC_API_BASE_URL=backend-virid-ten-43, NEXT_PUBLIC_GITHUB_CLIENT_ID=Ov23liRAu5b41z6Bh7dM. Backend env: GITHUB_CLIENT_ID/SECRET, CRON_SECRET, RESEND_* all set.
- **Auth model change (no auto-demo)**: ensureSession() no longer fetches /auth/demo; startDemoSession() (new, auth.ts) used ONLY by /login demo button. Dashboard layout: no token -> router.replace("/login"); bell effect guarded. handleSignOut -> /login. PricingClient checkout no-token -> /login.
- **Dashboard "Providers 0" fixed**: stat renamed "Connections" (connected.length) + NEW "Monitored APIs" card + "API Usage" panel (real) using backend stats.monitored_api_count (len(MONITORED_APIS), added DashboardStatsOut field; empty-repos branch returns monitored_api_count=12 — verified live =12).
- **Live verified**: all backend endpoints (healthz 200, auth demo/me/consent 200, github/callback 422, dashboard/stats 200 w/ monitored_api_count=12, repos 200, repos/github 400 Unauthorized=expected demo-no-token, internal/changelog/notices 200, health/issues 200, provider-connections 200, errors/failures/incidents/anomalies 200, billing/status 200, admin/* 403 demo-correct); all 17 frontend URLs 200; security headers present (CSP, HSTS, XCTO, XFO, RP, Permissions-Policy, X-XSS-Protection).
- M13 (polish/motion CSS), M14 (security headers), M15 (consent migrations applied prod) — complete.

## Key Files
- frontend/lib/auth.ts (ensureSession/startDemoSession/storeSession/clearSession/getUser/getToken/isAuthed)
- frontend/lib/api.ts (request()->ensureSession NO demo, githubCallback, buildGithubAuthUrl, DashboardStats.monitored_api_count)
- frontend/app/dashboard/layout.tsx (auth gate line ~102, handleSignOut line ~469 -> /login, demo GitHub CTA in menu)
- frontend/app/dashboard/DashboardClient.tsx (Connections/Monitored APIs stat, API Usage panel)
- frontend/components/LoginClient.tsx, AuthCallbackClient.tsx; app/auth/github/page.tsx, app/auth/callback/page.tsx
- backend/app/routers/repos.py (dashboard_stats, monitored_api_count), schemas.py (DashboardStatsOut), auth.py (demo/github_callback/me), consent.py
- backend/app/routers/admin.py (/overview /health /users /alerts/pending), billing.py (/create-checkout-session /portal /status /webhooks)

## Pending / Owner-level
- Real browser OAuth round-trip test (interactive GitHub sign-in) — API chain fully verified, UI live.
- RESEND_FROM_EMAIL verified sender in Resend (email feature needs it for real sends).
- Stripe live keys if billing activated; /authorize/[token] legacy route exists.
- Admin login requires is_admin=true user (demo is 403 — correct).