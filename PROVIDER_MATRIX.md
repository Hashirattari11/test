# PROVIDER INTELLIGENCE MATRIX

> Source of truth: `backend/app/health/provider_capabilities.py` `capability_matrix()` — machine-generated, never hand-edited.
> 44 providers. All capability statuses are HONEST (SUPPORTED / NOT_SUPPORTED / REQUIRES_PERMISSION / REQUIRES_ADMIN_ACCESS / NOT_AVAILABLE_WITH_THIS_CREDENTIAL / TEMPORARILY_UNAVAILABLE). No fabricated data.
> Repository is NOT involved in any provider flow — monitoring is connection-scoped.

| Provider | Verification | Usage | Quota | Rate Limits | Health | Trends | Status |
|----------|--------------|-------|-------|-------------|--------|--------|--------|
| airtable | real probe | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | incident history | SUPPORTED |
| algolia | real probe | REQ_PERM | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | incident history | SUPPORTED |
| anthropic | real probe | REQ_ADMIN | REQ_ADMIN | SUPPORTED | SUPPORTED | real/usage/rate | SUPPORTED |
| auth0 | real probe | NOT_SUPPORTED | NOT_SUPPORTED | SUPPORTED | NOT_SUPPORTED | incident history | SUPPORTED |
| aws | permission-gated | REQ_PERM | REQ_PERM | NOT_SUPPORTED | NOT_SUPPORTED | incident history | SUPPORTED |
| clerk | real probe | REQ_PERM | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | incident history | SUPPORTED |
| cloudinary | real probe | SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | real/usage | SUPPORTED |
| digitalocean | real probe | SUPPORTED | NOT_SUPPORTED | SUPPORTED | NOT_SUPPORTED | real/usage/rate | SUPPORTED |
| discord | real probe | NOT_SUPPORTED | NOT_SUPPORTED | SUPPORTED | NOT_SUPPORTED | real/rate | SUPPORTED |
| elevenlabs | real probe | SUPPORTED | SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | real/usage | SUPPORTED |
| firebase | permission-gated | REQ_ADMIN | REQ_ADMIN | NOT_SUPPORTED | SUPPORTED | incident history | SUPPORTED |
| github | real probe | NOT_SUPPORTED | SUPPORTED | SUPPORTED | SUPPORTED | real/rate | SUPPORTED |
| google_ai | real probe | REQ_PERM | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | incident history | SUPPORTED |
| huggingface | real probe | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | incident history | SUPPORTED |
| intercom | real probe | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | incident history | SUPPORTED |
| mailgun | real probe | SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | real/usage | SUPPORTED |
| mapbox | real probe | REQ_PERM | REQ_PERM | NOT_SUPPORTED | NOT_SUPPORTED | incident history | SUPPORTED |
| mixpanel | real probe | REQ_PERM | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | incident history | SUPPORTED |
| mongodb | real probe | REQ_PERM | REQ_PERM | NOT_SUPPORTED | NOT_SUPPORTED | incident history | SUPPORTED |
| notion | real probe | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | incident history | SUPPORTED |
| openai | real probe | REQ_ADMIN | REQ_ADMIN | SUPPORTED | SUPPORTED | real/usage/rate | SUPPORTED |
| openweather | real probe | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | — | NOT_SUPPORTED |
| paypal | real probe | REQ_PERM | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | incident history | SUPPORTED |
| plaid | real probe | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | incident history | SUPPORTED |
| posthog | real probe | REQ_PERM | REQ_PERM | NOT_SUPPORTED | NOT_SUPPORTED | incident history | SUPPORTED |
| postmark | real probe | SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | real/usage | SUPPORTED |
| pusher | real probe | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | incident history | SUPPORTED |
| redis | permission-gated | REQ_PERM | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | incident history | SUPPORTED |
| resend | — | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | SUPPORTED | incident history | SUPPORTED |
| segment | permission-gated | REQ_PERM | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | incident history | SUPPORTED |
| sendgrid | real probe | SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | SUPPORTED | real/usage | SUPPORTED |
| sentry | real probe | REQ_PERM | REQ_PERM | NOT_SUPPORTED | NOT_SUPPORTED | incident history | SUPPORTED |
| serpapi | real probe | SUPPORTED | SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | real/usage | NOT_SUPPORTED |
| shopify | — | NOT_SUPPORTED | NOT_SUPPORTED | SUPPORTED | SUPPORTED | real/rate | SUPPORTED |
| slack | — | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | SUPPORTED | incident history | SUPPORTED |
| stripe | real probe | SUPPORTED | NOT_SUPPORTED | SUPPORTED | SUPPORTED | real/usage | SUPPORTED |
| supabase | permission-gated | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | SUPPORTED | incident history | SUPPORTED |
| telegram | real probe | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | — | NOT_SUPPORTED |
| twilio | real probe | SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | SUPPORTED | real/usage | SUPPORTED |
| twitter | real probe | REQ_PERM | NOT_SUPPORTED | SUPPORTED | NOT_SUPPORTED | incident history | SUPPORTED |
| vercel | — | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | SUPPORTED | incident history | SUPPORTED |
| whatsapp | real probe | REQ_PERM | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | incident history | SUPPORTED |
| youtube | real probe | REQ_PERM | REQ_PERM | NOT_SUPPORTED | NOT_SUPPORTED | incident history | SUPPORTED |
| zoom | real probe | REQ_PERM | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | incident history | SUPPORTED |

## Legend

- **Verification**: `real probe` = live key validation reached the provider API; `permission-gated` = validation requires a permission/credential we do not fabricate.
- **Status vocabulary**: SUPPORTED / NOT_SUPPORTED / REQ_PERM (REQUIRES_PERMISSION) / REQ_ADMIN (REQUIRES_ADMIN_ACCESS) / N/A_CRED (NOT_AVAILABLE_WITH_THIS_CREDENTIAL) / TEMP (TEMPORARILY_UNAVAILABLE).
- **Trends**: `real/usage`, `real/rate` = machine-readable snapshots persisted over time; `incident history` = status-page incident history; `—` = none exposed.
