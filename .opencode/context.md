# Project Context

## Environment
- Python FastAPI backend + TypeScript/Next.js frontend; workdir D:\autofix (git, main).
- win32 / PowerShell 5.1 (no heredoc/no `&&`; use `;`/cmd). run_background = cmd.exe: `set V=x&& set V2=y&& python f.py`.
- Python print()+PS redirect = UTF-16LE BOM binary — use temp .py or inline SQL (Supabase MCP tools work fine).
- Vercel CLI 58.7.1 (hashirattari11); token `C:\Users\AAMASH\AppData\Roaming\xdg.data\com.vercel.cli\auth.json` (len 60). Org team_VajkoNE2yGmuAR89Mm13PZx3.
- Projects: backend prj_Zw3MX8LSD6C4I6C4WoknhsHMxzjI (live backend-virid-ten-43.vercel.app), frontend prj_A73XsdB63JtYbfaFrsjrUK9Yhxja, autofix prj_6i3aRh5pWFnWASmzgjfq0T5MzeLM (root .vercel; .vercel.bak=backend link; .vercel.bak2=frontend link).
- Supabase MCP available for prod DB checks.

## MISSION (44-provider real changelog monitoring M1-M8)
- 44 ids: stripe, shopify, twilio, sendgrid, github, openai, anthropic, paypal, resend, slack, supabase, firebase, aws, vercel, cloudinary, googleai, huggingface, elevenlabs, postmark, mailgun, digitalocean, sentry, auth0, clerk, mapbox, algolia, posthog, mixpanel, segment, intercom, discord, telegram, whatsapp, twitter, zoom, pusher, youtube, notion, airtable, mongodb, redis, plaid, openweather, serpapi.
- Brand: user spec `[AutoFix API]` → product `[Breaklytix]` (flag in final report).
- Source kinds: RSS (shopify, github), GITHUB_RELEASES (sentry, redis), HTML_STRICT (others; stripe=HTML_STRICT honest 0 → LIMITED).
- Enums: change_type 15; severity CRITICAL/HIGH/MEDIUM/LOW/INFO/UNKNOWN; confidence HIGH/MEDIUM/LOW/UNKNOWN; review_state unreviewed/reviewed/dismissed.
- No-fabrication invariant: RawEntry requires external_id+title+url+published_at; 60d lookback; undated dropped → LIMITED.
- Alerts: always-email CRITICAL/HIGH; MEDIUM/LOW/INFO only HIGH confidence; UNKNOWN never. Subjects `[Breaklytix] High-Risk API Change Detected — {P}` / `[Breaklytix] API Change Notice — {P}`.
- Impact: "Potential impact detected: …" / "No matching repository usage detected"; NEVER "crash".

## ⚠️ INCIDENT (2026-09-17) — RESOLVED + REPLAY OF WIPED FIXES
- `cmd /c "rmdir /s /q D:\autofix\backend\$null"` → PS expanded $null=empty → deleted backend/. RECOVERY: `git restore --worktree backend/` (HEAD pre-mission) + **Vercel dep file download** via `GET /v13/deployments/{id}/files` (list) + `GET /v8/deployments/{id}/files/{fileId}` → base64 (content). Dep **dpl_Dpbta9WELtUKuCHSzVfeaLgJNnNc**. Downloader `C:\Users\AAMASH\AppData\Local\Temp\opencode\vercel_fetch.ps1` → `...\vercel_restore\src\` (119/120 ok) → copied back to D:\autofix\backend.
- ⚠️ **IMPORTANT: the WIPED local-only fixes were NOT in the Vercel dep (pre-fix snapshot). Identified + are being REPLAYED:**
  1. scheduler.py fixes — ALREADY RE-APPLIED & verified: env budgets (FETCH_TIMEOUT_SECONDS/MAX_WORKERS/TOTAL_BUDGET_SECONDS), `_db_retry`, bulk-lookup store_entries, 23505 dup handling, duration_ms real, fetched count, _update_status prints failures. Committed in `89ef8a5`.
  2. **15 URL fixes — RE-APPLIED TODAY via `fix_urls.py` (survived in temp): plaid→/docs/changelog/, sendgrid→/docs/sendgrid, whatsapp→/docs/whatsapp/changelog, zoom→/changelog, pusher→/docs/, postmark→/, mailgun→/blog/, cloudinary→/documentation/, mixpanel→/docs/, intercom→/, algolia→/doc/changelog/, mapbox→/, notion→/changelog, openweather→/faq, serpapi→/blog/. (15/15 applied.)**
  3. **stripe RSS→HTML_STRICT — RE-APPLIED TODAY** (removed fictional feed.rss; entry_selector article).
- **Backend REDEPLOYED correctly**: root .vercel (autofix) overrode backend link; fix = move root .vercel aside → deploy from standalone temp dir `C:\Users\AAMASH\AppData\Local\Temp\opencode\backend_deploy` (own .vercel→backend) → **backend-cv8k3n5zg** Ready Production. Root .vercel restored after. NOTE: dep backend-cv8k3n5zg contains scheduler fixes but NOT the URL/stripe fixes (applied after deploy). **A RE-DEPLOY IS STILL REQUIRED after replay completes.**
- Live backend-virid-ten-43.vercel.app → 401 on /internal/changelog/health (guard active).

## CURRENT MATRIX (prod DB direct, 11:30 UTC sweep pre-URL-replay)
- Was polluted by cron (pre-fix 25s budget → ~19-20 ERROR "timed out"). Post-full-sweep: 6 ACTIVE / 19 ERROR (mostly 404s from OLD URLs) / 19 LIMITED — this CHANGES after URL replay.
- Real stored events confirmed: shopify 43, redis 18, github 10, serpapi 9, slack 8, clerk 6, sentry 4 (all with external_id). Dedup 0. SOURCE_UNAVAILABLE 0. Total providers 44.
- Expected post-replay: ~7 ACTIVE (clerk, github, redis, sentry, serpapi, shopify, slack) / 2 ERROR (telegram net-block, segment 403) / 35 LIMITED.

## PENDING — FINISH MISSION
1. **Re-run full-budget sweep** (env FETCH_TIMEOUT_SECONDS=45, FETCH_MAX_WORKERS=8, TOTAL_BUDGET_SECONDS=35; fetch_all_runner2.py) — verify matrix returns ~7/2/35.
2. **pytest 168 + tsc 0 re-run** (after URL edits).
3. **Commit URL+stripe fixes** (new commit).
4. **Re-deploy backend** via backend_deploy temp dir (carry .vercel) → new prod dep; confirm 401 still.
5. **Final report** `D:\autofix\REPORT_44_PROVIDER_MONITORING.md` — Worker agents (task_904e2cc9 ses_f50e19640ffeXrgKanVLeYzCaa, task_a7c3d219, task_c55c0c21 ses_f50e1832effeJjQhp8eYgj9WRr) TRUNCATED all 3 times — Commander writes it directly (S8.2.1).
6. **Mark todo.md [x]** S7.1.7, S7.2.1, S7.2.2, S8.1.1-S8.1.4 (NOT S8.2.x) + propagate M7/M8 parents; append verification summary to .opencode/integration-status.md. Do this with tools directly (agents unreliable).
7. Conclude — flag brand [Breaklytix] vs [AutoFix API]; limitations (HTML_STRICT honest LIMITED; telegram/segment ERRORs external; Vercel cron 30s budget timed_out; deployed INTERNAL_SECRET ≠ local .env → live internal probes 401; live verification via local-fetch-against-prod-DB).
- Do NOT git restore backend again. Do NOT commit .env / INTERNAL_SECRET.
- git: `89ef8a5` committed (scheduler fixes + recovery). Uncommitted now: sources.py URL+stripe edits.

## Temp tools that survived (reusable)
- `fix_urls.py` (15 fixes, idempotent), `fetch_all_runner2.py` (full sweep), `gen_matrix.py`, `probe_*.py`, `e2e_provider.py`, `verify_brand.py`, `live_smoke.py`, `parity_check.py`, `append_tests.py`.
- backend_deploy dir = deployable backend snapshot (refresh after final commit).