# Project Context (COMPACTED 2026-09-14 ~05:42 — ALL USER TASKS COMPLETE)

## Environment
- Frontend: Next.js 14.2.15 (TS) `D:\autofix\frontend` — prod alias frontend-eight-phi-60.vercel.app; repo Hashirattari11/autofix-frontend (frontend@ROOT) synced @42ea7e2
- Backend: FastAPI py3.12 `D:\autofix\backend` — prod alias backend-virid-ten-43.vercel.app; repo Hashirattari11/autofix-backend (backend@ROOT) synced @f455e4b (was b55bfb9)
- DB Supabase MCP; win32 PS5.1: no `&&`, `gh api --jq` FAILS (use `| ConvertFrom-Json`), run_background=cmd.exe (no `$env:` — use bash tool for deploys), robocopy exit 0-7 OK, anomaly notices FALSE POSITIVES ignore
- Git: D:\autofix origin=Hashirattari11/test (WORKFLOW+SECRETS HOME only). Real homes: autofix-frontend + autofix-backend.

## Gates
- Frontend: `npx tsc --noEmit` + `npm run build` — PASS 82 pages
- Backend: `$env:PYTHONPATH="D:\autofix\backend"; python -m pytest -q` — 144 passed
- Deploy SEQUENTIAL via bash tool: `$env:VERCEL_ORG_ID="team_VajkoNE2yGmuAR89Mm13PZx3"` + `$env:VERCEL_PROJECT_ID` (backend prj_Zw3MX8LSD6C4I6C4WoknhsHMxzjI / frontend prj_A73XsdB63JtYbfaFrsjrUK9Yhxja) then `vercel deploy --prod --yes` from folder. Root .vercel renamed .vercel.bak2 — KEEP. Never run_background a deploy ($env: fails in cmd.exe).

## ALL TASKS COMPLETE (user approved "karo complete")
1. **Connect-repo hang FIXED** — repos.py connect_repo → async `start_scan(id, full_name, default_branch, token)` (not sync scan_repo). Deployed dpl_HRXWzPLNqWNutfwSS97PzFmXgK8P; live /repos→401, /docs→200.
2. **Responsive pass** — repos/page.tsx (minWidth→flex 1 1 0; buttons flexWrap; modal clamp padding), repos/[id]/page.tsx (footprint table +responsive-cards +data-labels; expanded td data-label=""), agency/page.tsx (invite grid auto-fit minmax(200px,1fr)), globals.css safety net appended END (img/svg/video max-width 100%; pre/code overflow-x; html,body overflow-x hidden; td[data-label=""]::before display none; ≤640px inline grid collapse 1fr !important + page-header/mc-panel h3 wrap). Deployed dpl_HJCsk1TrYRzGKVaJuyxhwam51MQ9 → frontend-grk0qtu2t; live repos/login/root/agency 200. Pushed 42ea7e2.
3. **Backend repo sync** — remote b55bfb9 was a DIFFERENT lineage (user pushed granular Sep 8 history; local = single "production ready" commit lineage w/ newer routers impact/consent/notifications + deployed state). Did NOT blindly overwrite: verified route inventories (local has /incidents, /provider-connections CRUD; remote had /providers, /usage/{id}, repo-free collect, /provider/{provider} — evolved/replaced), only forecast.py genuinely obsolete (no imports). Synced local→remote as commit f455e4b (preserved .env.example; dropped forecast.py). `b55bfb9..f455e4b main -> main` PUSHED. NOTE: remote-only files kept where useful; git history preserves everything.
4. **Daily digest enabled** — `UPDATE users SET notify_daily_status=true WHERE id='3d206f17-...'` → owner hashirattari73@gmail.com now notify_email_alerts=true, notify_daily_status=true. Emails now send daily (not just when issues found).
5. Temp clones cleaned.

## Infrastructure facts (stable, do not re-verify unless asked)
- GH Action workflow `stripe-changelog-cron.yml` lives ONLY in test repo (e2bfb2e, curls have -L); cron 06:00 UTC: fetch→process→daily-scan. Secrets: BACKEND_URL=https://backend-virid-ten-43.vercel.app; INTERNAL_SECRET value = see GH Actions secrets on test repo (do NOT write the literal value into public files).
- Backend auth: X-Internal-Secret header = settings.cron_secret = CRON_SECRET or INTERNAL_SECRET (deps.py L70-77). Verified E2E live 09-14 (run 34837416096 SUCCESS; 2× daily_status emails SENT 200).
- Owner id 3d206f17-7abc-4857-be29-00c8406ce16f (hashirattari73@gmail.com). Demo 85c03e20-6557-4df7-8c4a-7d72d7a55f37. Resend sandbox: non-owner 403 until domain verified.

## Key Files (current production state)
- backend/app/routers/repos.py (async connect), backend/app/engine/scanner/runner.py
- backend/vercel.json (maxDuration 60), app/main.py, app/health/* (no forecast.py)
- frontend/app/globals.css (safety net END), premium.css, dashboard/repos/*, agency/page.tsx
- frontend/lib/api.ts, lib/auth.ts

## PENDING (only user-actionable)
- Owner browser test: connect repo live (should return instantly now) + mobile viewport check of dashboard pages.
- RESEND_FROM_EMAIL verified sender for real emails (sandbox blocks non-owner).
- Stripe live keys if billing activated.