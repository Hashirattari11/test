# Mission: Repository-Scoped Data Isolation (Full-Stack Root-Cause Fix)

## M1: Backend — enforce repository scoping on aggregate endpoints | status: in_progress
### T1.1: health.py — repo filter on errors/failures/anomalies/issues | agent:Commander
- [x] S1.1.1: Add repository_id Query param + _owned_repo(404) to list_errors, list_failures, list_anomalies, list_issues
- [x] S1.1.2: Refactor _all_open_issues(user_id, repository_id=None) to scope query

### T1.2: impact.py + repos.py + changelog — repo filter on summary/alerts/notices | agent:Commander
- [x] S1.2.1: /impact/summary accepts repository_id + ownership
- [x] S1.2.2: /repos/alerts accepts repository_id + ownership
- [x] S1.2.3: /internal/changelog/notices accepts repository_id

### T1.3: DB indexes (idempotent) | agent:Commander
- [x] S1.3.1: CREATE INDEX IF NOT EXISTS on reliability_issues(repo_id), alerts(repo_id), impact_analyses(repo_id), scans(repo_id), api_detections(repo_id), findings(repo_id)

## M2: Frontend — reusable selector + URL state + repo-scoped pages | status: pending
### T2.1: lib/api.ts — repositoryId params | agent:Commander
- [x] S2.1.1: getHealthErrors/Failures/Anomalies(limit, repositoryId?); getHealthIssues params.repositoryId; getImpactSummary(repositoryId?); listAllAlerts(repositoryId?)

### T2.2: RepositorySelector component | agent:Commander
- [x] S2.2.1: components/RepositorySelector.tsx — loads listRepos, syncs ?repository_id= URL, allowAll prop, auto-select first, empty state

### T2.3: Repo-scoped pages (default to selected repo, never All) | agent:Commander
- [x] S2.3.1: errors, failures, anomalies pages → selector + URL + refetch + scoped empty state
- [x] S2.3.2: sdk, deprecated, breaks pages → selector + URL + refetch + scoped empty state
- [x] S2.3.3: impact page → shared selector + URL + scoped summary/analyses

### T2.4: Aggregate pages (explicit All + grouping by repo) | agent:Commander
- [x] S2.4.1: issues page → All default + group by repo
- [x] S2.4.2: alerts page → All default + group by repo

## M3: Verification | status: pending
### T3.1: Regression + isolation tests | agent:Commander
- [x] S3.1.1: test_repo_isolation.py — backend scoping + IDOR 404 + no-mixing evidence
- [x] S3.1.2: Full backend pytest suite green (no regressions)
- [x] S3.1.3: Frontend tsc clean + LSP diagnostics clean
- [x] S3.1.4: DB index migration applied + verified
- [x] S3.1.5: Multi-repo isolation data proof (per-repo counts, no cross-repo rows)