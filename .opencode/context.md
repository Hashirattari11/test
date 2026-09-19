# Project Context — AutoFix API (Breaklytix)

## Environment
- Backend: Python + FastAPI, Supabase (PostgREST) prod DB, deployed Vercel (backend-virid-ten-43.vercel.app)
- Frontend: Next.js App Router + TS, deployed Vercel
- Shell: win32 PowerShell 5.1; no heredoc/&&; agent delegation truncates — terse prompts only
- Tests: backend `python -m pytest tests -q` (baseline 168); frontend `npx tsc --noEmit`
- Backend/DB is source of truth for repo identity; never expose secrets; no fake data

## MISSION 2 (ACTIVE): Production-readiness — Repository-Aware Real Code Intelligence
User's 55-req master task: repo isolation, issue verification, impact engine correctness, fire drill ALL 44 providers, security (IDOR/secrets), alerts w/ repo context, scan comparison, no fabricated data. Final deliverable = REPORT_REPO_AWARE_INTELLIGENCE.md (sections A-L) + 4-repo E2E test. Rules: don't rebuild app, no parallel architecture, don't remove features.
Phase 0 audit DONE. Fix list G1–G7 in `.opencode/todo.md` (20 subtasks).

## Current Status (compaction #3, 2026-09-17 ~10:04)
WAVE-1 (all 5 Workers COMPLETED, changes CONFIRMED via git status):
- T1.1 (task_8b21ce33): redact.py NEW, runner.py M, health/bridge.py M, repos.py M, schemas.py M, migration 20260917_findings_verification.sql, test_security_redaction.py + test_finding_status.py NEW
- T1.2 (task_1985d6d3): engine/rules/registry.py M, engine/rules/matcher.py M, test_rules_overclaim.py NEW
- T1.3 (task_4e2d9b59): impact/analyzer.py M, routers/impact.py M (POST /impact/fire-drill-matrix), test_impact_verification.py NEW
- T1.4 (task_08f9ad7c): routers/repos.py M (GET /repos/{repo_id}/scan-comparison?since_scan_id=), test_scan_comparison.py NEW
- T2.1 (task_9182f119): frontend/app/dashboard/DashboardClient.tsx M (repo full_name on issues + error bars)
- 4 new test files confirmed untracked (??): test_impact_verification.py, test_rules_overclaim.py, test_scan_comparison.py, test_security_redaction.py

WAVE-2 (spawned 10:04, RUNNING):
- task_d9f649a7 (Worker): T2.2 frontend fire drill 44 — page.tsx COMMON_PROVIDERS→full MONITORED_APIS (backend/app/signatures.py keys), matrix button → POST /impact/fire-drill-matrix, render {provider: active|inactive|unknown}; npx tsc --noEmit must pass
- task_623bfca1 (Reviewer): M3 backend verification — git diff review of all wave-1 files, verify redact() in _persist_findings/_persist_api_detections, taxonomy, registry overclaim fixes, analyzer verification_status, fire-drill-matrix, scan-comparison; run pytest (168+4 new); report only, NO todo marks yet

git log: a3f5ffe (M1-M8 doc), a04a939, 89ef8a5 (44-provider), 3d0233b (Breaklytix rebrand), a852021.

## Pending Tasks
1. Get results of task_d9f649a7 (Wave-2 frontend) + task_623bfca1 (backend verify). Fix any pytest/tsc failures via targeted Worker edits.
2. Launch final Reviewer pass (M3): frontend `npx tsc --noEmit`, cross-repo isolation test (2 repos, findings of repo A never in repo B responses), mark ALL [x] in todo.md, write D:\autofix\REPORT_REPO_AWARE_INTELLIGENCE.md (sections A-L).
3. Conclude only after: ALL 20 todo items [x], py>=172+ tests pass, tsc clean, sync-issues.md empty.

## Key Files
- Routers: backend/app/routers/{repos,health,impact,internal,fixes,admin,agency,public_api}.py
- Scanner: backend/app/engine/scanner/{runner,ast_scan}.py; engine/rules/{registry,matcher}.py; app/detection.py; app/signatures.py (MONITORED_APIS=44)
- Impact: backend/app/impact/{analyzer,severity,fix_generator}.py
- Frontend: frontend/app/dashboard/impact/fire-drill/page.tsx (COMMON_PROVIDERS L25); frontend/app/dashboard/DashboardClient.tsx
- Schema: db/*.sql + Supabase prod DB (users, repos, api_detections, changelog_events, alerts, findings(+scan_id,rule_id,confidence), scans(+stats jsonb), reliability_issues(+content_hash,evidence), impact_analyses, health_scores, health_history, provider_incidents, fixes, fix_rules, provider_connections, plan_usage, stripe_webhook_events)
- Shared state: .opencode/todo.md (20 items), work-log.md, sync-issues.md (0)

## Known Gaps (Phase 0 audit)
G1 secrets persisted → redact (DONE wave-1); G2 findings taxonomy DETECTED/POTENTIAL/VERIFIED/FALSE_POSITIVE/UNKNOWN/RESOLVED (DONE); G3 analyzer verification_status (DONE); G4 fire drill 12→44 (IN PROGRESS wave-2); G5 rules overclaim (DONE); G6 frontend repo identity (DONE); G7 scan comparison (DONE).
38 tables referenced; 14 have NO DDL (scans, findings, scan_events, impact_analyses, agency_clients, code_health_issues, daily_scan_runs, pull_requests, provider_connections, notification_preferences, slack_connections, email_deliveries, api_keys, provider_monitoring_status) — schema drift; prod DB is source of truth (do NOT create migrations for these unless required; migrations only for new findings columns via 20260917 file).

## Anomaly note
Repeated "low information density" flags occurred during Phase-0 report delivery; mitigation = terse output, avoid long reports in chat; final report goes to REPORT file instead.