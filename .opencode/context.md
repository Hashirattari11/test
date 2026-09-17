# Project Context

## Environment
- Python FastAPI backend + TypeScript/Next.js frontend; workdir D:\autofix (git, branch main, origin sync at 3d0233b).
- win32 / PowerShell 5.1 (no heredoc, no `&&`; use `;` / cmd). run_background uses cmd.exe: `set V=x&& set V2=y&& python f.py`.
- Python print()+PS redirect = UTF-16LE BOM binary — write temp .py or pass SQL inline.
- Vercel CLI 58.7.1 (user hashirattari11); **token file: `C:\Users\AAMASH\AppData\Roaming\xdg.data\com.vercel.cli\auth.json`** (len 60). Org team_VajkoNE2yGmuAR89Mm13PZx3.
- Backend project prj_Zw3MX8LSD6C4I6C4WoknhsHMxzjI (live backend-virid-ten-43.vercel.app); frontend prj_A73XsdB63JtYbfaFrsjrUK9Yhxja (frontend-eight-phi-60.vercel.app). .vercel.bak=backend, .vercel.bak2=frontend, root .vercel=autofix.
- Supabase MCP tools available (execute_sql, list_tables) for prod DB verification.

## MISSION (44-provider real changelog monitoring M1-M8)
- 44 ids: stripe, shopify, twilio, sendgrid, github, openai, anthropic, paypal, resend, slack, supabase, firebase, aws, vercel, cloudinary, googleai, huggingface, elevenlabs, postmark, mailgun, digitalocean, sentry, auth0, clerk, mapbox, algolia, posthog, mixpanel, segment, intercom, discord, telegram, whatsapp, twitter, zoom, pusher, youtube, notion, airtable, mongodb, redis, plaid, openweather, serpapi.
- Brand: user spec `[AutoFix API]` → product `[Breaklytix]` (flag in final report).
- Source kinds: RSS (shopify, github), GITHUB_RELEASES (sentry, redis), HTML_STRICT (others; stripe feed.rss fictional 404 → HTML_STRICT honest 0 → LIMITED).
- Enums: change_type 15; severity CRITICAL/HIGH/MEDIUM/LOW/INFO/UNKNOWN; confidence HIGH/MEDIUM/LOW/UNKNOWN; review_state unreviewed/reviewed/dismissed.
- No-fabrication: RawEntry requires external_id+title+url+published_at; 60d lookback; undated/boilerplate dropped → LIMITED.
- Alerts: always-email CRITICAL/HIGH; MEDIUM/LOW/INFO only HIGH confidence; UNKNOWN never. Subjects `[Breaklytix] High-Risk API Change Detected — {P}` / `[Breaklytix] API Change Notice — {P}`.
- Impact phrasing: "Potential impact detected: …" / "No matching repository usage detected"; NEVER "crash"/"will crash".

## ⚠️ INCIDENT + RECOVERY (2026-09-17) — READ CAREFULLY
- ROOT CAUSE: `cmd /c "rmdir /s /q D:\autofix\backend\$null"` — PS expanded `$null`→empty → cmd got `D:\autofix\backend\` → DELETED ENTIRE backend/.
- STEP 1 DONE: `git restore --worktree backend/` → tracked files back to HEAD (PRE-mission state).
- STEP 2 DONE — RECOVERED MISSION CODE FROM VERCEl DEPLOYMENT:
  - **File-content API is `/v8/deployments/{id}/files/{fileId}`** → `{"data":"<base64>"}`. (v13 list works; content NOT v13.)
  - Dep: **dpl_Dpbta9WELtUKuCHSzVfeaLgJNnNc** = backend-m7a2r4kho-hashirattari11s-projects.vercel.app (latest prod, created 02:20).
  - Downloader script: `C:\Users\AAMASH\AppData\Local\Temp\opencode\vercel_fetch.ps1` (walks v13 tree, fetches v8 base64, decodes → `C:\Users\AAMASH\AppData\Local\Temp\opencode\vercel_restore\src\...`). 119/120 ok (only out/api/index.py build-artifact failed — irrelevant).
  - Copied BACK to D:\autofix\backend: app/, api/, tests/, scripts/, migrations/, requirements.txt, vercel.json, .env, .env.example, CRON.md, Dockerfile, render.yaml (src .gitignore absent — fine). Legacy 13 parsers gone (parsers/ = __init__.py only). All mission files verified present: sources.py 13822B, adapters.py 4122B, classify.py 11033B, fingerprint.py 1362B, scheduler.py 22821B, router.py 10592B, base.py 12497B, config.py 8886B, alerts.py 21990B, impact/analyzer.py 14524B, tests/test_changelog_monitoring.py 10687B, tests/test_impact.py 8656B, requirements.txt, vercel.json, api/index.py 132B, .env 2701B.

## ⚠️ CRITICAL FINDING — deployed snapshot is PRE-FIX
The recovered scheduler.py is the OLD version shipped to prod. Still to RE-APPLY (rewrite on disk now):
1. **duration_ms bug** (scheduler.py L204-207): `duration_ms = int((_time.time() - _time.time()) * 0) or 1` → always 1. Fix: `_work` returns duration; compute `int((now - start) * 1000)`.
2. **No `_db_retry`** anywhere in repo (grep: 0). Add helper (3 attempts, backoff, retry on "Server disconnected"/connection errors) wrapping DB calls (or at least store/_update_status).
3. **store_entries is per-entry 3 queries** (old): select by external_id, select by fingerprint, then update/insert (L57-122). Optimize to ONE bulk lookup per provider (select ids where api_name=provider and external_id in (...) and fingerprint in (...)).
4. **No env-tunable budget**: L30-32 hardcoded FETCH_TIMEOUT_SECONDS=12, FETCH_MAX_WORKERS=4, TOTAL_BUDGET_SECONDS=25 — make os.getenv with those defaults.
5. **fetched count in per-provider result**: _fetch_with_timeout returns entries; results should include fetched=len(entries) (currently stats only has stored/duplicates/skipped/errors).
6. **23505 unique violation** = duplicate (catch IntegrityError/lookup in insert path → count duplicate not error).
7. **_update_status silent pass on error** — should print failures (check current L125-160).
- test impact of fixes: shopify store 47s→16s expectation; duration_ms column real values in provider_monitoring_status.

## Other verification to redo (post-restore)
- tests: earlier reviewer run showed **166 passed + 2 FAILED in test_impact.py** (`test_build_impact_reason_no_match` expects "No stripe usage" but code says "No matching repository usage detected"; `test_build_potential_failure` expects "crash"). Restored test_impact.py likely has STALE assertions → align to NEW phrasing (update the 2 assertions to match analyzer.py; do NOT regress analyzer).
- test_default_status_map: stripe must be LIMITED (default map) — confirm in restored test_changelog_monitoring.py.
- Run `python -m pytest tests -q` in D:\autofix\backend (PYTHONPATH) → target 168 passed.
- Frontend SURVIVED intact (changelog pages, providers/ dir, lib/api.ts, types.ts). Run `npx tsc --noEmit` then `npm run build` in D:\autofix\frontend.
- Prod DB intact (Supabase): verify matrix 7 ACTIVE (clerk, github, redis, sentry, serpapi, shopify, slack) / 2 ERROR (telegram net-block, segment 403) / 35 LIMITED = 44 rows; real events shopify 43, redis 18, github 10, slack 8, clerk 6, sentry 4, serpapi; dedup 0 dups (api_name,external_id).

## Verification facts pre-incident (still valid for DB/live)
- 168 pytest passed (incl 24 new changelog tests); frontend tsc+build exit 0; matrix 7/2/35 live; /internal/changelog/health|monitoring|events → 401 without creds (guards active; deployed INTERNAL_SECRET ≠ local .env secret — live internal probes blocked, local-fetch-against-prod-DB was the verification path).
- 15 URL fixes (all 200): stripe→docs.stripe.com/changelog, paypal→developer.paypal.com/api/rest/, plaid, sendgrid, whatsapp, zoom, pusher, postmark, mailgun, cloudinary, mixpanel, intercom, algolia, mapbox, notion, openweather, serpapi (blog URLs). Stripe = HTML_STRICT.

## READ FIRST next session
- .opencode/todo.md (checkbox state), work-log.md, status.md. This file is authoritative for incident state.

## Current Status
- backend/ = recovered mission code (pre-fix scheduler); git sees: backend restored-to-HEAD files now differ from deployment snapshot? NO — git status should show unstaged deletions/modifications vs HEAD for all new mission files (expected; HEAD is pre-mission). DO NOT git restore again. Commit AFTER fixes+tests pass.
- TODO now: re-apply scheduler fixes, fix stale test_impact assertions, run full pytest (168), frontend tsc/build, optionally redeploy backend so fixed code is live (current prod = pre-fix! if fixes were desired live; note Vercel cron runs the pre-fix code today).
- Pending: final report (REPORT_44_PROVIDER_MONITORING.md), commits (backend+frontend+migrations; never commit secrets), Reviewer final verification + mark M8 todos [x], conclude.