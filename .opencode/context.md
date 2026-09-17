# Project Context

## Environment
- Python FastAPI backend + TypeScript/Next.js frontend; workdir D:\autofix (git, main).
- win32 / PowerShell 5.1 (no heredoc/no `&&`; use `;`/cmd).
- Vercel CLI 58.7.1 (hashirattari11); token `C:\Users\AAMASH\AppData\Roaming\xdg.data\com.vercel.cli\auth.json` (len 60). Org team_VajkoNE2yGmuAR89Mm13PZx3.
- Projects: backend prj_Zw3MX8LSD6C4I6C4WoknhsHMxzjI (live backend-virid-ten-43.vercel.app), frontend prj_A73XsdB63JtYbfaFrsjrUK9Yhxja, autofix prj_6i3aRh5pWFnWASmzgjfq0T5MzeLM (root .vercel; .vercel.bak=backend; .vercel.bak2=frontend).
- Supabase MCP available for prod DB checks.

## MISSION (44-provider real changelog monitoring M1-M8)
- 44 ids: stripe, shopify, twilio, sendgrid, github, openai, anthropic, paypal, resend, slack, supabase, firebase, aws, vercel, cloudinary, googleai, huggingface, elevenlabs, postmark, mailgun, digitalocean, sentry, auth0, clerk, mapbox, algolia, posthog, mixpanel, segment, intercom, discord, telegram, whatsapp, twitter, zoom, pusher, youtube, notion, airtable, mongodb, redis, plaid, openweather, serpapi.
- Brand: user spec `[AutoFix API]` → product `[Breaklytix]` (flag in final report).
- Source kinds: RSS (shopify, github), GITHUB_RELEASES (sentry, redis), HTML_STRICT (others; stripe=HTML_STRICT honest 0 → LIMITED).
- Enums: change_type 15; severity CRITICAL/HIGH/MEDIUM/LOW/INFO/UNKNOWN; confidence HIGH/MEDIUM/LOW/UNKNOWN; review_state unreviewed/reviewed/dismissed.
- No-fabrication invariant: RawEntry requires external_id+title+url+published_at; 60d lookback; undated dropped → LIMITED.
- Alerts: always-email CRITICAL/HIGH; MEDIUM/LOW/INFO only HIGH confidence; UNKNOWN never. Subjects `[Breaklytix] High-Risk API Change Detected — {P}` / `[Breaklytix] API Change Notice — {P}`.
- Impact: "Potential impact detected: …" / "No matching repository usage detected"; NEVER "crash".

## ⚠️ INCIDENT (2026-09-17) — FULLY RESOLVED
- `cmd /c "rmdir /s /q D:\autofix\backend\$null"` → PS expanded $null=empty → deleted backend/. RECOVERY: `git restore --worktree backend/` (HEAD pre-mission) + Vercel dep file download via `GET /v13/deployments/{id}/files` (list) + `GET /v8/deployments/{id}/files/{fileId}` → base64 (content) from **dpl_Dpbta9WELtUKuCHSzVfeaLgJNnNc**. Downloader `C:\Users\AAMASH\AppData\Local\Temp\opencode\vercel_fetch.ps1` → `...\vercel_restore\src\` → copied back to backend/.
- WIPED local-only fixes REPLAYED: (1) scheduler.py env budgets + `_db_retry` + bulk store + 23505 dup + real duration_ms + fetched count; (2) 15 URL corrections (fix_urls.py, survived); (3) stripe RSS→HTML_STRICT; (4) paypal URL → https://developer.paypal.com/api/rest/ (200 live); (5) **NEW FIX: budget-expired providers no longer written as ERROR** (was corrupting ACTIVE providers when Vercel cron's 25s budget expired — keep last completed status, report timed_out only in results); (6) test_default_status_map updated (stripe default LIMITED).

## ✅ VERIFIED FINAL STATE
- **Prod matrix: 7 ACTIVE / 2 ERROR / 35 LIMITED = 44** ✓ ACTIVE: clerk, github, redis, sentry, serpapi, shopify, slack. ERROR: telegram (network block), segment (403) — both external.
- Real stored events: shopify 43, redis 18, github 10, serpapi 9, slack 8, clerk 6, sentry 4 (all external_id). Dedup 0. SOURCE_UNAVAILABLE 0.
- **Backend tests: 168 passed** (5.85s). **Frontend tsc --noEmit: exit 0.**
- **Commits**: `89ef8a5` (recovery + scheduler fixes), `a04a939` (URL fixes + stripe/paypal + budget-expiry fix). Code SAFE in git.
- **Backend deployed**: `backend-3qivre7qj` Ready Production (correct backend project via standalone temp dir `C:\Users\AAMASH\AppData\Local\Temp\opencode\backend_deploy` w/ own .vercel). Live backend-virid-ten-43.vercel.app → 401 on /internal/changelog/health.
- Root D:\autofix\.vercel restored (autofix project).

## PENDING — FINISH MISSION (final steps only)
1. Write **D:\autofix\REPORT_44_PROVIDER_MONITORING.md** (S8.2.1) — Worker agents truncated 4x (task_904e2cc9, task_a7c3d219, task_c55c0c21, task_b9a67167) — Commander writes directly. Sections: Summary, What Was Built (mechanism→file map per requirements), DB Migrations, Live Verification Results, Test Results (168+tsc0), Limitations & Honest Notes ([Breaklytix] brand flag; HTML_STRICT→LIMITED; telegram/segment external ERRORs; Vercel cron 30s budget may timeout (now non-destructive); deployed INTERNAL_SECRET ≠ local .env → live internal 401; live verification via local-fetch-against-prod-DB), Files Changed (from git log/stat).
2. Mark **.opencode/todo.md** [x]: S7.1.7, S7.2.1, S7.2.2, S8.1.1, S8.1.2, S8.1.3, S8.1.4 → propagate M7/T7.1/T7.2 + M8/T8.1 complete. NOT S8.2.x (Worker deliverables — report is done by Commander; if S8.2.x exist leave or mark done with report).
3. Append verification summary to **.opencode/integration-status.md**, update work-log.md with final rows.
4. Conclude — final summary to user with all flags. Do NOT commit .env / INTERNAL_SECRET.

## Temp tools (survived)
- fix_urls.py, fetch_all_runner2.py, probe_paypal2.py, gen_matrix.py, e2e_provider.py, verify_brand.py, live_smoke.py, parity_check.py. backend_deploy dir = deployable snapshot (current).
- Sweep outputs: .opencode/sweep2.json, sweep3.json (committed — fine to keep).