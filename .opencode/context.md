# opencode Context

## Mission
M3: repo-scoped data isolation (IDOR-safe) across the autofix platform. Goal:
select a repository in the dashboard; every health/alerts/impact view must show
ONLY that repo's data. Backend must not leak cross-repo data (404 on unowned
repositories). Then verify + deploy backend & frontend.

## Last Known Good State (confirmed by tool output)

### Code (committed + pushed to GitHub main)
- HEAD = 782adfa "feat: repo-scoped data isolation M3 ..." (pushed to origin/main).
- Backend: all M3 changes committed. 215 tests pass (incl. IDOR/repo-isolation).
- Frontend: M3 client pages rewritten (RepositorySelector + repository_id param).
- Both repos on D:\autofix (backend\, frontend\). Frontend cwd D:\autofix\frontend.

### Deploys
- Backend deployed to Vercel: BUILD COMPLETED (autofix project, /vercel/output).
- Frontend deploy (next build via Vercel) FAILS:

## THE ACTIVE BLOCKER (verified via fresh cold build fb_summary.txt, EXIT=1)
Next.js 15 prerender error on 9 dashboard pages:
"useSearchParams() should be wrapped in a suspense boundary at page X"
Pages (9): /dashboard/alerts, /dashboard/impact,
  /dashboard/health/anomalies, /dashboard/health/breaks,
  /dashboard/health/deprecated, /dashboard/health/errors,
  /dashboard/health/failures, /dashboard/health/issues, /dashboard/health/sdk

- `export const dynamic = "force-dynamic"` was added to all 11 pages but
  apparently does NOT suppress the prerender bailout (build still fails).
- Proved fix demanded by error text: wrap the component in a <Suspense> boundary.

### Suspense wrap ready (script written, NOT yet run)
- File: D:\autofix\frontend\scripts\suspense_wrap.py (targets all page.tsx under
  app/dashboard/**; renames inner default fn, appends
  `export default function Page(){ return <Suspense fallback={<div/>}>{Inner}</Suspense>; }`,
  adds Suspense to react import). VERIFY its content before running.
- scripts/fresh_build.py = cold build tool, writes fb_summary.txt (see above).
- Run order: (1) run suspense_wrap.py, (2) run fresh_build.py, (3) check
  fb_summary.txt == EXIT=0 & 0 prerender lines, (4) then redeploy frontend.

## File paths (from repo root D:\autofix)
- frontend\app\dashboard\*\page.tsx (the 9 pages above)
- frontend\scripts\suspense_wrap.py, frontend\scripts\fresh_build.py
- frontend\build_log.txt / build_log.txt were UTF-16 redirects; avoid; use
  fresh_build.py -> fb_summary.txt (UTF-8 direct file write, trusted).

## CLI / Env Notes (win)
- Shell powershell 5.1 / python 3.12; use `python scripts\x.py` with workdir
  D:\autofix\frontend. Prefer writing scripts to files over -c strings.
- Vercel: repo linked, two projects (backend->/backend, frontend->/frontend).

## Current Status
- M3 code: DONE, committed, pushed.
- Backend deploy: DONE (built, deployed).
- Frontend build: BLOCKED (useSearchParams prerender). Suspense wrap script
  written; RUN IT, rebuild, verify, then `vercel --prod` from D:\autofix\frontend.

## Pending Tasks
1. run scripts\suspense_wrap.py (verify/inspect first)
2. run scripts\fresh_build.py -> confirm EXIT=0, 0 prerender errors
3. `npx vercel --prod --yes` in D:\autofix\frontend
4. verify deployed pages (no 404, repo filter works) + report to user
