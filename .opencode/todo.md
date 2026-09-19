# Mission: Repository-Aware Real Code Intelligence — Production Readiness Pass (AutoFix API)

Audit COMPLETE. Fix list G1–G7 (see .opencode/context.md). Reduced-scope, single-wave plan.

## M1: Backend Security + Verification Core | agent:Worker (implemented by Commander directly — delegation returned no-ops; verified on disk)
### T1.1: Secret redaction at persist + findings verification taxonomy | agent:Worker
- [x] S1.1.1: `backend/app/redact.py` — redact_snippet/redact_object (sk_live_, sk-{20,}, SG., xox[baprs], AIza, AC{32}, AKIA, ghp_, github_pat_, Bearer via `\1`+placeholder) | VERIFIED: file exists, 11 tests pass
- [x] S1.1.2: runner.py `_persist_findings` + `_persist_api_detections` apply redact(); findings get `verification_status` "detected" + `status` stays "open" | VERIFIED: grep + tests
- [x] S1.1.3: Migration applied to prod: findings += `verification_status text`, `evidence_url text`, `content_hash text` | VERIFIED: information_schema query; bridge.py redacts evidence
- [x] S1.1.4: repos.py PATCH /findings/{id} — `_resolve_finding_status` mapping (verified→open, resolved→fixed, false_positive→dismissed, unknown→non-destructive); schemas.py FindingOut/FindingUpdateIn updated | VERIFIED: code + LSP clean
- [x] S1.1.5: pytest test_security_redaction.py (11 tests) — redaction + status mapping | VERIFIED: 204 suite pass
### T1.2: Rules overclaim fixes | agent:Worker
- [x] S1.2.1: registry.py — raw-http-client → "advisory", severity low, confidence 0.6; firebase-database-mixed → "advisory"; stripe patterns tightened (no `\bcharge\b`) | VERIFIED: code + tests
- [x] S1.2.2: matcher.py — rule-enriched findings get `verification_status` "potential"; message prefix "Potential: " for non-verified rule matches | VERIFIED: code + tests
- [x] S1.2.3: pytest test_rules_overclaim.py (6 tests) — no endpoint_changed claim w/o endpoint match | VERIFIED: 204 suite pass
### T1.3: Impact verification + Fire Drill 44 | agent:Worker
- [x] S1.3.1: impact/analyzer.py `compute_verification_status` — verified (endpoint|sdk match OR removed/renamed/secret_leak) / potential (usage matched, version unknown, has `reason`) / not_found / unknown; wired into analyze_changelog_event + fire-drill path | VERIFIED: code + LSP clean
- [x] S1.3.2: impact.py `POST /impact/fire-drill-matrix` (repo_id) — all 44 providers from PROVIDER_SOURCES, classifies active/at_risk/unknown/inactive from real detections+events, no persistence | VERIFIED: code + LSP clean
- [x] S1.3.3: pytest test_impact_verification.py (8 tests) | VERIFIED: 204 suite pass
### T1.4: Scan-to-scan comparison | agent:Worker
- [x] S1.4.1: repos.py `GET /{repo_id}/scan-comparison` — added/removed/unchanged/resolved/regressed keyed (file,line,message) | VERIFIED: code + LSP clean
- [x] S1.4.2: pytest test_scan_comparison.py (5 tests) | VERIFIED: 204 suite pass

## M2: Frontend Repo Isolation | agent:Worker (implemented by Commander directly — delegation returned no-ops; verified via tsc)
### T2.1: DashboardClient repo identity | agent:Worker
- [x] S2.1.1: DashboardClient — repo full_name on "Open Health Issues" rows + API-error activity feed | VERIFIED: tsc clean
- [x] S2.1.2: health issue list/detail pages (issues, issues/[id], errors, failures, anomalies, sdk, breaks, deprecated) — repo_full_name badge; lib/api.ts HealthIssue type extended | VERIFIED: tsc clean
### T2.2: Fire Drill all 44 | agent:Worker
- [x] S2.2.1: fire-drill page — ALL_PROVIDERS (44, mirrors PROVIDER_SOURCES), QUICK_PICK chips, matrix run against /fire-drill-matrix + table (active-first, MATRIX_TONE) | VERIFIED: code + tsc clean
- [x] S2.2.2: tsc --noEmit passes | VERIFIED: clean ×2

## M3: Verification | agent:Reviewer (delegated task_e6e341b5 returned no file changes; Commander verified with direct tool evidence)
### T3.1: Full System Verification | agent:Reviewer
- [x] S3.1.1: backend pytest = **204 passed** (168 baseline + 36 new); frontend `npx tsc --noEmit` clean; LSP clean on repos.py + impact.py | VERIFIED: tool output
- [x] S3.1.2: cross-repo isolation spot check (prod DB): 5 repos (882/170/49/25 detections partitioned by repo_id), findings (clip=225) + reliability_issues (295/176/38) repo-scoped; routers use `_owned_repo` + `.in_("repo_id", owned)` | VERIFIED: SQL output
- [x] S3.1.3: production report written to D:\autofix\REPORT_REPO_AWARE_INTELLIGENCE.md (sections A-L) | VERIFIED: file exists