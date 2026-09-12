# Mission: API Reliability & Health Intelligence

## What Exists (reusable)
- GitHub OAuth + repo connection (auth.py, repos.py)
- Provider detection (signatures.py, detection.py, engine/scanner/)
- Changelog monitoring (changelog/) — 12 providers
- Auto-fix engine (engine/fixer/, engine/rules/)
- Findings system (findings table + engine/scanner/runner.py)
- Agency Mode (agency.py, agency_clients table)
- Email alerts (email_client.py, alerts table)
- Billing (billing.py, stripe)
- API keys (api_keys.py)
- system_health table (job monitoring)

## New Features (20)
1. Health Engine — configurable scoring per integration
2. Code-level problem detection — extended scanner patterns
3. Quota/Usage monitoring — provider adapters
4. Quota forecasting — historical + extrapolation
5. Rate limit monitoring — detection + alerts
6. API error intelligence — category normalization
7. Provider status/incidents — status page integration
8. Health check categories — standardized model
9. Unified issue model — reliability_issues table
10. Dashboard — API Health page
11. Alerting extensions — new alert types + dedup
12. Auto-fix integration — connect health issues to fixer
13. GitHub scan enhancement — provider→SDK→endpoint→file→env mapping
14. Provider registry expansion — capability declarations
15. Provider capability UI — capability badges per provider
16. Historical health — health_history table + trend charts
17. Risk engine — explainable scoring
18. Production-aware priority — dev/staging/prod labels
19. Agency Mode health — client-wide health view
20. Client-facing explanations — plain-language findings

## New DB Tables
- provider_capabilities (provider, capability, supported, config)
- health_checks (integration, check_type, status, score, evidence)
- health_scores (integration, overall_score, breakdown_json, timestamp)
- health_history (integration, score, timestamp, snapshot)
- reliability_issues (unified issue model, dedup via content_hash)
- usage_snapshots (provider, quota, used, remaining, timestamp)
- rate_limit_snapshots (provider, limit, remaining, reset_at)
- provider_incidents (provider, title, status, impact, started_at)

## Implementation Phases
- C: Core backend (health engine, provider capabilities, issue model)
- D: Scanner extension (code-level reliability checks)
- E: Provider data adapters (usage/quota/status)
- F: DB migrations
- G: API endpoints
- H: Frontend dashboard
- I: Alerting
- J: Auto-fix integration
- K: Agency Mode
- L: Tests
- M: Security review
- N: Production hardening

## Status
- Phase A (audit): IN PROGRESS
- Phase B (design): PENDING
- Phases C-N: PENDING