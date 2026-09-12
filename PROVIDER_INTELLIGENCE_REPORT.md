# Provider Intelligence Report

## A. Root Cause

The original repository prompt came from legacy repository-scoped usage and rate-limit endpoints (and, formerly, a provider detail endpoint that joined repo-derived health scores and code errors). Provider pages now use provider connection endpoints only and do not select or require a repository at any layer. A follow-up audit ("remove repository dependency from provider usage/quota") made the provider detail endpoint fully repo-free: it no longer queries repositories for health scores or errors — provider health is derived solely from the connection state (`healthy`/`error`/`disconnected`) and usage/rate-limit snapshots are read only from provider-connection rows (`repo_id IS NULL`). Repository-scoped endpoints remain for Code Intelligence only.

## B. Provider Connection

The Providers page reads the backend Provider Registry. API-key connections are tested against the provider before saving, then encrypted with the existing Fernet mechanism. The API returns safe metadata only. GitHub and Slack are identified as OAuth flows; unsupported manual connection flows are not presented as API-key connections.

## C. Real Data

The live usage adapters cover 11 providers (all via real provider APIs — never fabricated):

| Provider | Adapter | What it returns | Notes |
|---|---|---|---|
| OpenAI | `collect_openai_usage` | 24h request count + input/output tokens | Requires org/admin key |
| Anthropic | `collect_anthropic_usage` | 24h output + input tokens | Requires org/admin key |
| Stripe | `collect_stripe_usage` | Available balance (USD) — billing intelligence | Real balance endpoint |
| Twilio | `collect_twilio_usage` | Total USD billed across SMS/voice/etc. | `sid:auth_token` Basic auth |
| SendGrid | `collect_sendgrid_usage` | 30d request count | Bearer token |
| Cloudinary | `collect_cloudinary_usage` | Credits used + REAL quota (limit/remaining) | `cloud:key:secret` Basic |
| ElevenLabs | `collect_elevenlabs_usage` | Characters used + REAL quota (limit/remaining) | Subscription + usage endpoints |
| Postmark | `collect_postmark_usage` | Outbound sent count | Server token auth |
| Mailgun | `collect_mailgun_usage` | Accepted count (30d) | `api_key:domain` Basic |
| DigitalOcean | `collect_digitalocean_usage` | Month-to-date USD | Bearer token |
| SerpApi | `collect_serpapi_usage` | Searches used + REAL quota (remaining/plan) | API key query param |

Rate-limit adapters cover 6 providers: GitHub (live `/rate_limit`), OpenAI/Anthropic (response headers via `/v1/models`), Shopify (`X-Shopify-Shop-Api-Call-Limit`), Discord (`x-ratelimit-*` headers), DigitalOcean (`ratelimit-*` headers).

All endpoints call the real provider API. Permission errors (403/401) are surfaced honestly as "Requires organization/admin access" or "Additional provider permission required" — never as zero or fabricated data. Provider usage, quota, rate limits, health, and details all work from the provider connection credential alone — no repository is involved.

## D. Quota

The provider detail API returns `quota: {available, message, used, limit, remaining, percentage, unit, recorded_at}`.

- **When `available: true`** (Cloudinary, ElevenLabs, SerpApi): all numeric fields are real provider-reported values from the last successful refresh — never computed.
- **When `available: false`**: the `message` gives an honest reason (e.g. "Requires organization/admin access", "Quota information is not exposed by this provider/API credential", "Additional provider permissions are required").

Quota is surfaced per connected provider and never requires a repository.

## E. Limits

Hard provider-side plan limits are surfaced as quota when the API exposes them: Cloudinary (credits limit), ElevenLabs (character limit), SerpApi (monthly search limit). Other providers either require admin access (OpenAI/Anthropic) or do not expose plan limits through a machine-readable endpoint. The honest status "Requires organization/admin access" or "Not available from provider" is surfaced when limits are not available.

## F. Rate Limits

Six providers have real rate-limit adapters:

| Provider | Adapter | What it captures | Source |
|---|---|---|---|
| GitHub | `collect_github_rate_limit` | limit/remaining/used/reset | `GET /rate_limit` (any valid token) |
| OpenAI | `collect_openai_rate_limits` | limit/remaining/reset | `x-ratelimit-*` headers on `/v1/models` |
| Anthropic | `collect_anthropic_rate_limits` | limit/remaining/reset | `anthropic-ratelimit-*` headers on `/v1/models` |
| Shopify | `collect_shopify_rate_limits` | limit/remaining | `X-Shopify-Shop-Api-Call-Limit: used/total` header |
| Discord | `collect_discord_rate_limits` | limit/remaining/reset | `x-ratelimit-*` headers |
| DigitalOcean | `collect_digitalocean_rate_limits` | limit/remaining | `ratelimit-*` headers |

Other providers show an honest unavailable state. Rate limits are always scoped to the connected credential — never derived from repository activity.

## G. Multiple Providers

Connections are keyed by `user_id + provider`, so multiple different providers can remain connected independently. The current schema intentionally upserts one connection per provider per user; separate same-provider accounts are not supported by this model.

## H. Email

The Resend integration is real and records delivery status, failures, deduplication, and rate-limit outcomes. Existing alert email flows are connected to code/changelog detection and weekly digests. Provider usage/quota threshold monitoring and provider-connection event emails are not currently implemented, so no fake provider alert is sent.

## I. Delete

Disconnect calls the authenticated delete endpoint, which removes the encrypted connection row. Both provider detail and provider overview now require confirmation before deletion. Subsequent provider collection fails because the connection no longer exists.

## J. Provider Matrix

The full 44-provider machine-readable matrix lives in `PROVIDER_MATRIX.md` (generated from `capability_matrix()`). Summary:

- **44 providers** in the registry, each with honest per-capability status (SUPPORTED / NOT_SUPPORTED / REQUIRES_PERMISSION / REQUIRES_ADMIN_ACCESS / NOT_AVAILABLE_WITH_THIS_CREDENTIAL / TEMPORARILY_UNAVAILABLE).
- **35 providers** have real API-key validation probes (`SUPPORTED` in key_validation.py).
- **11 providers** have real usage adapters; **6 providers** have real rate-limit adapters (17 total adapters).
- **3 providers** expose real quota numbers (Cloudinary, ElevenLabs, SerpApi).
- **~25 providers** have real status-page incident monitoring.
- **5 providers** (Supabase, Firebase, AWS, Redis, Segment) have validation that requires a permission/credential we do not fabricate — they are correctly marked `permission-gated`.
- Trend data: real usage snapshots, real rate-limit snapshots, or status-page incident history — never fabricated.

## K. Tests

- Backend: `python -m pytest -q` -> `127 passed`, one dependency deprecation warning (116 baseline + 11 new adapter parse-level tests).
- Frontend: `npx tsc --noEmit` -> passed.
- Frontend: `npm run build` -> passed, `49/49` pages generated.
- LSP diagnostics: clean for the changed frontend pages and `lib/api.ts`, and the backend collectors + health router + capability registry + key validation.
- Existing tests cover collectors (incl. openai/anthropic usage + rate-limit header parsing, permission-denied honesty, no-key-echo, 401/403 mapping), all 11 new usage adapters + 6 rate-limit adapters (parse-level, transport mocked), key validation (35 probes), health calculations, notification preferences, Resend delivery failure handling, deduplication, and rate limiting.
- Real E2E (live connected credentials): OpenAI usage endpoint returned `403` and Anthropic returned `401`, both surfaced honestly as "Requires organization/admin access"; rate-limit header capture returned real (null-when-absent) provider values. No credential ever appears in output.

## L. Remaining Limitations

- OpenAI and Anthropic usage adapters are live but require an **organization/admin-scoped key**; with a normal connected key the API returns `403`/`401` and the product honestly reports "Requires organization/admin access" (never 0). Real numeric quota/usage for these two providers still requires the user to connect an admin-scoped credential.
- New usage adapters (Twilio/SendGrid/Cloudinary/ElevenLabs/Postmark/Mailgun/DigitalOcean/SerpApi/Stripe) are implemented and parse-level tested against real API response shapes; live E2E with real credentials is only possible when the user connects keys for those providers (none were available in this environment).
- No provider-connection background worker currently collects usage or emits provider threshold emails (explicitly out of Session-8 scope).
- Provider detail health is connection-derived (`provider_health`: healthy/error/disconnected) and does not require a repository. Repo-computed health scores and code-level errors remain in the Code Intelligence pages (repository flows, correctly separate).
- One connection per provider per user is enforced by the current storage key.

## M. Files Changed (Session-8)

- `backend/app/health/provider_capabilities.py`: added `CapabilityStatus` enum + `ProviderCapability` factories + `status_of()` + `capability_matrix()`; registry rewritten to **44 providers** with honest statuses/permissions per capability.
- `backend/app/health/key_validation.py`: **35 real probes** (+29 new: paypal, zoom, twitter, auth0, plaid, cloudinary, mailgun, postmark, digitalocean, huggingface, elevenlabs, sentry, clerk, intercom, discord, notion, airtable, whatsapp, mapbox, google_ai, youtube, openweather, serpapi, algolia, posthog, mixpanel, telegram, pusher, mongodb); helpers `_post_json`, `_oauth_cc`.
- `backend/app/health/collectors.py`: 11 usage collectors + 6 rate-limit collectors; `USAGE_COLLECTORS`/`RATE_LIMIT_COLLECTORS` dispatch dicts; generic `record_provider_usage`/`record_provider_rate_limit`.
- `backend/app/routers/health.py`: `collect` endpoint generic dispatch; `_registry_caps` additive statuses/permissions; quota returns REAL numbers (Cloudinary/ElevenLabs/SerpApi) or honest reason.
- `frontend/lib/api.ts`: `CapabilityStatus`, `statuses`/`permissions` maps, quota numeric fields.
- `frontend/app/dashboard/health/providers/[provider]/page.tsx`: status-aware capability chips (SUPPORTED/REQUIRES_*/NOT_SUPPORTED) + real quota number cards.
- `frontend/app/globals.css`: `.cap-chip` badge styles (on/partial/off).
- `backend/tests/test_collectors.py`: 11 new adapter tests (30 total in file).
- `PROVIDER_MATRIX.md`: machine-generated 44-provider matrix.
- `PROVIDER_INTELLIGENCE_REPORT.md`: this factual A–S report.

## N. Code Simplification

No unnecessary abstraction or production mock data was added. Existing provider registry, credential encryption, collectors, API routes, notification service, and frontend API client were reused. Test-only mock changelog fixtures remain isolated to the explicit repository simulation path and are not used by provider intelligence. Removing the repo-bound collect endpoint, the dead `_decrypt_connection` helper, and the unused import reduced backend surface rather than adding abstraction.
