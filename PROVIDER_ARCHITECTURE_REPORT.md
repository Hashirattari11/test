# Provider Architecture Fix — Report

**Date:** 2026-09-08
**Scope:** Provider monitoring must be per-provider-connection and MUST NOT depend on repositories. Repositories own only code-level intelligence. No redesign; reuse existing endpoints; real data only.

---

## 1. Root Cause (verified)

**Bug:** "Usage takes me to Repository"

1. The sidebar pages `Usage`, `Quota`, `Rate Limits`, and `Trends` all called `listRepos()` and defaulted to the **first repository** in the list.
2. They then called the repo-scoped endpoints `getHealthUsage(repoId)`, `getHealthRateLimit(repoId)`, and `getHealthHistory(repoId)`.
3. Result: the "Usage" navigation item (and friends) always opened a **repository's** data, with a repo dropdown — never the provider connection's data.

**Secondary bug:** `GET /health/provider/{provider}` early-returned `{provider, scores: [], incidents: []}` when the user had no repos — dropping even provider-**global** incidents (211 rows exist in `provider_incidents`).

**Schema gap:** the snapshot tables (`usage_snapshots`, `rate_limit_snapshots`) had `provider` NOT NULL, nullable `repo_id`, but **no `user_id`** — a provider connection with zero repos could not attribute its data to the owning user (leakage risk).

---

## 2. Design Decision

- Added nullable `user_id` to `usage_snapshots` + `rate_limit_snapshots` (migration: `add_user_id_to_provider_snapshots`, applied via Supabase migration).
- Repo-free rows store `user_id` (repo_id = NULL).
- Queries are dual-scoped: `repo_id IN (user's repos) OR user_id = me` when repos exist; otherwise `user_id = me`.
- `provider_incidents` remain provider-**global** (they have no `user_id` column, which is correct — incidents are provider-wide, e.g. "GitHub API outage").
- `reliability_issues` stay repo-scoped (code-level intelligence belongs to repos, per the user directive).
- `quota` is honestly `null` — no machine-readable quota source exists; we do not fabricate numbers.
- Adapter registry: `USAGE_ADAPTERS = {"openai"}`, `RATE_LIMIT_ADAPTERS = {"github"}`. Unsupported providers return an honest 400.

---

## 3. Files Changed

### Backend
| File | Change |
|------|--------|
| `backend/app/health/collectors.py` | Adapter maps (`USAGE_ADAPTERS` / `RATE_LIMIT_ADAPTERS`); `record_github_rate_limit(repo_id: str\|None, token, user_id=None)`; `record_openai_usage(repo_id: str\|None, api_key, user_id=None)` — include `repo_id`/`user_id` only when set |
| `backend/app/routers/health.py` | Extracted `_registry_caps(profile)` module-level; rewrote `provider_health` (capabilities, adapters, connection, incidents always, latest_score + score_history repo-joined, usage/rate_limits dual-scoped, quota = null, errors repo-scoped limit 10); repo-scoped collect persists `user_id`; **new** `POST /health/provider-connections/{provider}/collect` |

### Frontend
| File | Change |
|------|--------|
| `frontend/lib/api.ts` | `collectProviderUsage(provider, repoId?)` — repoId optional (URL omits it when absent); new `ProviderConnectionStatus` / `ProviderRateLimitSnapshot` types; `ProviderHealthDetail` extended (capabilities, adapters, connection, usage + recorded_at, rate_limits, quota, errors); `HealthProviderScore` += `overall?` + typed `checks` |
| `frontend/app/dashboard/health/providers/[provider]/page.tsx` | **Rewritten**: capability chips, connection toolbar (Refresh / Test Connection / Connect / Disconnect with confirm), Usage / Quota / Rate Limits sections capability- and adapter-driven ("Not available from provider" honesty), Health + Score History, Errors, Incidents. **No repo selector, no `listRepos()`.**
| `frontend/app/dashboard/health/usage/page.tsx` | Provider-scoped via `getProviderConnections()` + `getHealthProvider()`; no repo dropdown |
| `frontend/app/dashboard/health/quota/page.tsx` | Same |
| `frontend/app/dashboard/health/rate-limits/page.tsx` | Same |
| `frontend/app/dashboard/health/trends/page.tsx` | Provider-scoped `score_history` |

---

## 4. Endpoints

### Used (existing, extended)
- `GET /health/provider/{provider}` — **extended** response: `capabilities`, `adapters`, `connection` (status + last_error), `usage` (dual-scoped, with recorded_at), `rate_limits` (dual-scoped, limit 20), `quota` (null), `errors` (repo-scoped), `incidents` (always fetched — no early return).

### Created
- `POST /health/provider-connections/{provider}/collect` — repo-free collection:
  - Provider not in adapter registry → **400**
  - No connection → **400**
  - `openai` → records into `usage_snapshots`
  - `github` → records into `rate_limit_snapshots`
  - Collector error → updates `provider_connections.last_error`, returns **502**
  - Success → clears `last_error`

---

## 5. Capability Handling ("Not available from provider")

- Pages render sections **only when the provider's capability map says so**.
- `usage` shown when the provider is in `USAGE_ADAPTERS`; `rate_limits` when in `RATE_LIMIT_ADAPTERS`; `quota` renders **"Not available from provider"** (quota is null — no fabricated numbers).
- Unsupported providers get honest "Not available" states instead of broken/empty charts.

## 6. Delete / Disconnect

- Disconnect is performed from the provider detail page toolbar with a **confirmation dialog** (no accidental deletes), via the existing provider-connection delete endpoint. `last_error` is surfaced from `provider_connections` and cleared on successful re-collect.

---

## 7. Tests

| Check | Result |
|-------|--------|
| Backend `python -m pytest -q` | **107 passed** (route registration + handlers incl. new collect endpoint) |
| Frontend `npx tsc --noEmit` | **Clean** (exit 0) |
| Frontend `npm run build` | **Exit 0, 45/45 static pages** (incl. local + Vercel production builds) |
| Live curl (prod) | App live, auth-gated: `GET /` → login page (200); `GET /health/provider/openai` → auth redirect; `POST /health/provider-connections/openai/collect` → intercepted by auth (405 on /login); `/openapi.json` → auth redirect. Authenticated behavior verified via the 107-test suite; interactive UI flows need a real session cookie. |
| Deployments | Backend `dpl_vnyVwEioFn4DhhBhRWircR4JJWsW` READY; Frontend `dpl_3icG6tBN8bXfnHjk8N1x6kQvHEQ8` READY |

---

## 8. Remaining Provider Limitations (honest)

1. **Usage adapter: OpenAI only** — other providers show "Not available" until adapters are added.
2. **Rate-limit adapter: GitHub only** — same.
3. **Quota is always null** — no provider exposes machine-readable quota; UI shows "Not available from provider".
4. **Health scores & errors remain repo-computed** — a connection with zero repos has no scores/history (by design: those metrics come from code intelligence).
5. **Incidents are provider-global** — correct for provider-wide outages; per-connection incidents are not modeled.

## 9. Notes for the User (not changed — out of scope)

- Supabase security advisory: 15–16 tables have **no RLS** enabled.
- GitHub OAuth needs re-connect; Resend domain verification pending; `/docs` exposure decision; duplicate `users` rows; Stripe live checkout; `next@14.2.15` has a known security advisory (upgrade recommended).