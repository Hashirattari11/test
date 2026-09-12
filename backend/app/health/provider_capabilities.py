"""Provider capability registry — the single source of truth for what each
provider exposes, declared HONESTLY (Session-8: all 44 providers).

Rules:
- `supported=True`  => the provider's official APIs expose this metric at all.
- `status=`         => the REAL current availability for a connected credential:
    SUPPORTED (live adapter exists) / NOT_SUPPORTED (no such API) /
    REQUIRES_PERMISSION (API exists, needs extra scope) /
    REQUIRES_ADMIN_ACCESS (org/admin credentials required) /
    NOT_AVAILABLE_WITH_THIS_CREDENTIAL (API exists but this key type can't) /
    TEMPORARILY_UNAVAILABLE.
- A capability is NEVER converted into a fabricated 0 / 100% / fake number.
  If the provider exposes the metric we implement a live adapter; otherwise we
  say exactly why we cannot, with the official API source.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Capability(str, Enum):
    """All supported provider capabilities."""
    CHANGELOG_MONITORING = "changelog_monitoring"
    CODE_DETECTION = "code_detection"
    DOCUMENTATION_MONITORING = "documentation_monitoring"
    USAGE_MONITORING = "usage_monitoring"
    QUOTA_MONITORING = "quota_monitoring"
    RATE_LIMIT_MONITORING = "rate_limit_monitoring"
    INCIDENT_MONITORING = "incident_monitoring"
    SCHEMA_VALIDATION = "schema_validation"
    AUTO_FIX = "auto_fix"
    ERROR_INTELLIGENCE = "error_intelligence"
    HEALTH_CHECKS = "health_checks"


class CapabilityStatus(str, Enum):
    """Honest availability of a capability for a provider + connected credential.

    This is the single source of truth for "can we get this metric TODAY?" It is
    NEVER converted into a fabricated 0 / 100% / fake number.
    """
    SUPPORTED = "SUPPORTED"                                      # live adapter exists
    NOT_SUPPORTED = "NOT_SUPPORTED"                              # provider has no such API
    REQUIRES_PERMISSION = "REQUIRES_PERMISSION"                  # API exists, needs extra scope
    REQUIRES_ADMIN_ACCESS = "REQUIRES_ADMIN_ACCESS"              # API exists, needs org/admin key
    NOT_AVAILABLE_WITH_THIS_CREDENTIAL = "NOT_AVAILABLE_WITH_THIS_CREDENTIAL"  # API exists but this key type can't
    TEMPORARILY_UNAVAILABLE = "TEMPORARILY_UNAVAILABLE"          # provider API down/rate-limited


@dataclass
class ProviderCapability:
    """A single capability declaration for a provider."""
    capability: Capability
    supported: bool
    status: CapabilityStatus = CapabilityStatus.NOT_SUPPORTED
    api_base: str | None = None
    notes: str | None = None
    permissions: str | None = None
    config: dict = field(default_factory=dict)

    @classmethod
    def live(cls, capability: Capability, api_base: str | None = None,
             notes: str | None = None, permissions: str | None = None) -> "ProviderCapability":
        """SUPPORTED — a live adapter exists."""
        return cls(capability, True, CapabilityStatus.SUPPORTED, api_base, notes, permissions)

    @classmethod
    def missing(cls, capability: Capability, notes: str | None = None) -> "ProviderCapability":
        """NOT_SUPPORTED — provider exposes no such metric."""
        return cls(capability, False, CapabilityStatus.NOT_SUPPORTED, None, notes)

    @classmethod
    def admin(cls, capability: Capability, api_base: str | None = None,
              notes: str | None = None, permissions: str | None = None) -> "ProviderCapability":
        """REQUIRES_ADMIN_ACCESS — API exists but needs org/admin credentials."""
        return cls(capability, True, CapabilityStatus.REQUIRES_ADMIN_ACCESS, api_base, notes, permissions)

    @classmethod
    def permission(cls, capability: Capability, api_base: str | None = None,
                   notes: str | None = None, permissions: str | None = None) -> "ProviderCapability":
        """REQUIRES_PERMISSION — API exists but needs extra scope."""
        return cls(capability, True, CapabilityStatus.REQUIRES_PERMISSION, api_base, notes, permissions)


@dataclass
class ProviderProfile:
    """Full capability profile for a provider."""
    provider_id: str
    display_name: str
    category: str  # payment, communication, ai, cloud, etc.
    capabilities: list[ProviderCapability] = field(default_factory=list)
    website: str | None = None
    docs_url: str | None = None
    status_url: str | None = None
    sdk_package: str | None = None  # npm/pip package name
    sdk_language: str | None = None  # node, python, etc.

    def has(self, cap: Capability) -> bool:
        return any(c.capability == cap and c.supported for c in self.capabilities)

    def status_of(self, cap: Capability) -> CapabilityStatus | None:
        for c in self.capabilities:
            if c.capability == cap:
                return c.status
        return None

    def capability_list(self) -> list[dict]:
        return [
            {
                "capability": c.capability.value,
                "supported": c.supported,
                "status": c.status.value,
                "notes": c.notes,
                "permissions": c.permissions,
                "api_base": c.api_base,
            }
            for c in self.capabilities
        ]


def _caps(*, changelog: ProviderCapability | None = None,
          usage: ProviderCapability | None = None,
          quota: ProviderCapability | None = None,
          rate: ProviderCapability | None = None,
          incidents: ProviderCapability | None = None,
          auto_fix: bool = False, health: bool = False,
          code: bool = True,
          notes_code: str | None = None) -> list[ProviderCapability]:
    """Build the standard capability list. Anything not provided defaults to the
    honest NOT_SUPPORTED state (never fabricate)."""
    caps = [
        changelog if changelog is not None else ProviderCapability.missing(Capability.CHANGELOG_MONITORING),
        ProviderCapability.live(Capability.CODE_DETECTION, notes=notes_code) if code
        else ProviderCapability.missing(Capability.CODE_DETECTION, notes=notes_code),
        usage if usage is not None else ProviderCapability.missing(Capability.USAGE_MONITORING),
        quota if quota is not None else ProviderCapability.missing(Capability.QUOTA_MONITORING),
        rate if rate is not None else ProviderCapability.missing(Capability.RATE_LIMIT_MONITORING),
        incidents if incidents is not None else ProviderCapability.missing(Capability.INCIDENT_MONITORING),
        ProviderCapability.live(Capability.AUTO_FIX) if auto_fix else ProviderCapability.missing(Capability.AUTO_FIX),
        ProviderCapability.live(Capability.HEALTH_CHECKS) if health else ProviderCapability.missing(Capability.HEALTH_CHECKS),
    ]
    return caps


def _statushub(url: str) -> ProviderCapability:
    """INCIDENT_MONITORING SUPPORTED via the provider's StatusHub/status-page feed."""
    return ProviderCapability.live(Capability.INCIDENT_MONITORING, url,
                                   "Real incidents from the official provider status page")


# ---------------------------------------------------------------------------
# Provider Registry — THE source of truth for provider capabilities (44)
# ---------------------------------------------------------------------------
PROVIDERS: dict[str, ProviderProfile] = {
    "stripe": ProviderProfile(
        provider_id="stripe", display_name="Stripe", category="payment",
        website="https://stripe.com", docs_url="https://stripe.com/docs",
        status_url="https://status.stripe.com", sdk_package="stripe", sdk_language="node",
        capabilities=_caps(
            changelog=ProviderCapability.live(Capability.CHANGELOG_MONITORING),
            usage=ProviderCapability.live(Capability.USAGE_MONITORING,
                "https://api.stripe.com/v1/balance",
                "Real available balance from the balance API (billing intelligence)"),
            rate=ProviderCapability.live(Capability.RATE_LIMIT_MONITORING,
                "https://api.stripe.com/v1/balance",
                "Real RateLimit-Limit/RateLimit-Remaining headers on API responses",
                permissions="None (any secret key)"),
            incidents=_statushub("https://status.stripe.com/api/v2/summary.json"),
            auto_fix=True, health=True,
        ),
    ),
    "openai": ProviderProfile(
        provider_id="openai", display_name="OpenAI", category="ai",
        website="https://openai.com", docs_url="https://platform.openai.com/docs",
        status_url="https://status.openai.com", sdk_package="openai", sdk_language="node",
        capabilities=_caps(
            changelog=ProviderCapability.live(Capability.CHANGELOG_MONITORING),
            usage=ProviderCapability.admin(Capability.USAGE_MONITORING,
                "https://api.openai.com/v1/organization/usage/completions",
                "Live adapter exists; org usage endpoints only answer with an ADMIN key",
                permissions="Admin key (sk-admin...) or org owner/usage read"),
            quota=ProviderCapability.admin(Capability.QUOTA_MONITORING,
                "https://api.openai.com/v1/organization/limits",
                "Quota is an organization-level concept; needs admin key",
                permissions="Admin key"),
            rate=ProviderCapability.live(Capability.RATE_LIMIT_MONITORING,
                "https://api.openai.com/v1/models",
                "Real x-ratelimit-* response headers"),
            incidents=_statushub("https://status.openai.com/api/v2/summary.json"),
            auto_fix=True, health=True,
        ),
    ),
    "anthropic": ProviderProfile(
        provider_id="anthropic", display_name="Anthropic", category="ai",
        website="https://anthropic.com", docs_url="https://docs.anthropic.com",
        status_url="https://status.anthropic.com", sdk_package="@anthropic-ai/sdk", sdk_language="node",
        capabilities=_caps(
            changelog=ProviderCapability.live(Capability.CHANGELOG_MONITORING),
            usage=ProviderCapability.admin(Capability.USAGE_MONITORING,
                "https://api.anthropic.com/v1/organizations/usage_report/messages",
                "Live adapter exists; usage report needs an ADMIN key",
                permissions="Admin key (sk-ant-admin01-...), OAuth org:admin, or non-workspace service key"),
            quota=ProviderCapability.admin(Capability.QUOTA_MONITORING,
                "https://api.anthropic.com/v1/organizations/cost_report",
                "Quota is organization-level; needs admin key",
                permissions="Admin key"),
            rate=ProviderCapability.live(Capability.RATE_LIMIT_MONITORING,
                "https://api.anthropic.com/v1/models",
                "Real anthropic-ratelimit-*/x-ratelimit-* response headers"),
            incidents=_statushub("https://status.anthropic.com/api/v2/summary.json"),
            auto_fix=True, health=True,
        ),
    ),
    "twilio": ProviderProfile(
        provider_id="twilio", display_name="Twilio", category="communication",
        website="https://twilio.com", docs_url="https://www.twilio.com/docs",
        status_url="https://status.twilio.com", sdk_package="twilio", sdk_language="node",
        capabilities=_caps(
            changelog=ProviderCapability.live(Capability.CHANGELOG_MONITORING),
            usage=ProviderCapability.live(Capability.USAGE_MONITORING,
                "https://api.twilio.com/2010-04-01/Accounts/{sid}/Usage/Records.json",
                "Real usage records (calls/sms/data usage) via Basic auth (sid:token)"),
            quota=ProviderCapability.missing(Capability.QUOTA_MONITORING,
                "No public quota endpoint — plan limits are dashboard-only"),
            rate=ProviderCapability.missing(Capability.RATE_LIMIT_MONITORING,
                "No rate-limit headers exposed; 429s carry Retry-After only"),
            incidents=_statushub("https://status.twilio.com/api/v2/summary.json"),
            auto_fix=True, health=True,
        ),
    ),
    "sendgrid": ProviderProfile(
        provider_id="sendgrid", display_name="SendGrid", category="email",
        website="https://sendgrid.com", docs_url="https://docs.sendgrid.com",
        status_url="https://status.sendgrid.com", sdk_package="@sendgrid/mail", sdk_language="node",
        capabilities=_caps(
            changelog=ProviderCapability.live(Capability.CHANGELOG_MONITORING),
            usage=ProviderCapability.live(Capability.USAGE_MONITORING,
                "https://api.sendgrid.com/v3/user/stats",
                "Real email stats (requests/delivered/bounced) via Bearer key"),
            quota=ProviderCapability.missing(Capability.QUOTA_MONITORING,
                "No public quota endpoint — plan sending limits are dashboard-only"),
            rate=ProviderCapability.missing(Capability.RATE_LIMIT_MONITORING,
                "No public rate-limit headers on standard endpoints"),
            incidents=_statushub("https://status.sendgrid.com/api/v2/summary.json"),
            auto_fix=True, health=True,
        ),
    ),
    "github": ProviderProfile(
        provider_id="github", display_name="GitHub", category="cloud",
        website="https://github.com", docs_url="https://docs.github.com",
        status_url="https://www.githubstatus.com", sdk_package="@octokit/rest", sdk_language="node",
        capabilities=_caps(
            changelog=ProviderCapability.live(Capability.CHANGELOG_MONITORING),
            quota=ProviderCapability.live(Capability.QUOTA_MONITORING,
                "https://api.github.com/rate_limit",
                "Real REST/GraphQL hourly quotas (default 5000/hr, 5000/hr)",
                permissions="None (any token)"),
            rate=ProviderCapability.live(Capability.RATE_LIMIT_MONITORING,
                "https://api.github.com/rate_limit",
                "Real X-RateLimit-* headers + /rate_limit endpoint"),
            incidents=_statushub("https://www.githubstatus.com/api/v2/summary.json"),
            auto_fix=True, health=True,
        ),
    ),
    "vercel": ProviderProfile(
        provider_id="vercel", display_name="Vercel", category="cloud",
        website="https://vercel.com", docs_url="https://vercel.com/docs",
        status_url="https://www.vercel-status.com", sdk_package="vercel", sdk_language="node",
        capabilities=_caps(
            changelog=ProviderCapability.live(Capability.CHANGELOG_MONITORING),
            usage=ProviderCapability.missing(Capability.USAGE_MONITORING,
                "No public usage API — usage is dashboard-only"),
            quota=ProviderCapability.missing(Capability.QUOTA_MONITORING,
                "No public quota/limits API"),
            rate=ProviderCapability.missing(Capability.RATE_LIMIT_MONITORING,
                "No public rate-limit headers"),
            incidents=_statushub("https://www.vercel-status.com/api/v2/summary.json"),
            auto_fix=True, health=True,
        ),
    ),
    "supabase": ProviderProfile(
        provider_id="supabase", display_name="Supabase", category="database",
        website="https://supabase.com", docs_url="https://supabase.com/docs",
        status_url="https://status.supabase.com", sdk_package="@supabase/supabase-js", sdk_language="node",
        capabilities=_caps(
            changelog=ProviderCapability.live(Capability.CHANGELOG_MONITORING),
            usage=ProviderCapability.missing(Capability.USAGE_MONITORING,
                "Dashboard only — no public usage API"),
            quota=ProviderCapability.missing(Capability.QUOTA_MONITORING,
                "Dashboard only — no public quota API"),
            rate=ProviderCapability.missing(Capability.RATE_LIMIT_MONITORING,
                "No public rate-limit headers"),
            incidents=_statushub("https://status.supabase.com/api/v2/summary.json"),
            auto_fix=True, health=True,
        ),
    ),
    "firebase": ProviderProfile(
        provider_id="firebase", display_name="Firebase", category="cloud",
        website="https://firebase.google.com", docs_url="https://firebase.google.com/docs",
        status_url="https://status.firebase.google.com", sdk_package="firebase", sdk_language="node",
        capabilities=_caps(
            changelog=ProviderCapability.live(Capability.CHANGELOG_MONITORING),
            usage=ProviderCapability.admin(Capability.USAGE_MONITORING,
                "https://firebase.googleapis.com/v1beta1/projects/{project}",
                "Needs a Google Cloud service account (JSON) — not a plain API key",
                permissions="GCP service account + Cloud Billing/Usage access"),
            quota=ProviderCapability.admin(Capability.QUOTA_MONITORING,
                "https://firebase.googleapis.com/v1beta1/projects/{project}",
                "Per-service quotas via GCP service account",
                permissions="GCP service account"),
            rate=ProviderCapability.missing(Capability.RATE_LIMIT_MONITORING,
                "No simple public rate-limit endpoint"),
            incidents=_statushub("https://status.firebase.google.com/api/v2/summary.json"),
            auto_fix=False, health=True,
        ),
    ),
    "slack": ProviderProfile(
        provider_id="slack", display_name="Slack", category="communication",
        website="https://slack.com", docs_url="https://api.slack.com/docs",
        status_url="https://status.slack.com", sdk_package="@slack/web-api", sdk_language="node",
        capabilities=_caps(
            changelog=ProviderCapability.live(Capability.CHANGELOG_MONITORING),
            usage=ProviderCapability.missing(Capability.USAGE_MONITORING,
                "No public usage API"),
            quota=ProviderCapability.missing(Capability.QUOTA_MONITORING,
                "No public quota API"),
            rate=ProviderCapability.missing(Capability.RATE_LIMIT_MONITORING,
                "Retry-After only on 429 — no continuous limit headers"),
            incidents=_statushub("https://status.slack.com/api/v2/summary.json"),
            auto_fix=True, health=True,
        ),
    ),
    "resend": ProviderProfile(
        provider_id="resend", display_name="Resend", category="email",
        website="https://resend.com", docs_url="https://resend.com/docs",
        status_url="https://status.resend.com", sdk_package="resend", sdk_language="node",
        capabilities=_caps(
            changelog=ProviderCapability.live(Capability.CHANGELOG_MONITORING),
            usage=ProviderCapability.missing(Capability.USAGE_MONITORING,
                "No public usage API — dashboard only"),
            quota=ProviderCapability.missing(Capability.QUOTA_MONITORING,
                "No public quota API — plan limits are dashboard-only"),
            rate=ProviderCapability.missing(Capability.RATE_LIMIT_MONITORING,
                "No public rate-limit headers"),
            incidents=_statushub("https://status.resend.com/api/v2/summary.json"),
            auto_fix=False, health=True,
        ),
    ),
    "shopify": ProviderProfile(
        provider_id="shopify", display_name="Shopify", category="ecommerce",
        website="https://shopify.com", docs_url="https://shopify.dev/docs",
        status_url="https://www.shopifystatus.com", sdk_package="@shopify/shopify-api", sdk_language="node",
        capabilities=_caps(
            changelog=ProviderCapability.live(Capability.CHANGELOG_MONITORING),
            usage=ProviderCapability.missing(Capability.USAGE_MONITORING,
                "No account-level usage API — only per-shop admin"),
            quota=ProviderCapability.missing(Capability.QUOTA_MONITORING,
                "No public quota endpoint"),
            rate=ProviderCapability.live(Capability.RATE_LIMIT_MONITORING,
                "https://{shop}.myshopify.com/admin/api/2024-01/shop.json",
                "Real X-Shopify-Shop-Api-Call-Limit header on admin API calls",
                permissions="Storefront admin token (shop domain + access token)"),
            incidents=_statushub("https://www.shopifystatus.com/api/v2/summary.json"),
            auto_fix=False, health=True,
        ),
    ),
    # ------------------------------------------------------------------
    # NEW providers (Session-8) — 32 more, honest capability statuses
    # ------------------------------------------------------------------
    "paypal": ProviderProfile(
        provider_id="paypal", display_name="PayPal", category="payment",
        website="https://paypal.com", docs_url="https://developer.paypal.com",
        status_url="https://www.paypal-status.com", sdk_package="@paypal/checkout-server-sdk", sdk_language="node",
        capabilities=_caps(
            usage=ProviderCapability.permission(Capability.USAGE_MONITORING,
                "https://api-m.paypal.com/v1/reporting/transactions",
                "Transactions reporting API exists but needs an OAuth app credential + transaction scope",
                permissions="OAuth2 client_id + secret with billing/transaction read scope"),
            incidents=_statushub("https://www.paypal-status.com"),
        ),
    ),
    "aws": ProviderProfile(
        provider_id="aws", display_name="AWS", category="cloud",
        website="https://aws.amazon.com", docs_url="https://docs.aws.amazon.com",
        status_url="https://health.aws.amazon.com", sdk_package="aws-sdk", sdk_language="node",
        capabilities=_caps(
            usage=ProviderCapability.permission(Capability.USAGE_MONITORING,
                "https://monitoring.us-east-1.amazonaws.com/",
                "CloudWatch metrics need SigV4-signed IAM credentials — not a plain API key",
                permissions="IAM user/role with cloudwatch:GetMetricData"),
            quota=ProviderCapability.permission(Capability.QUOTA_MONITORING,
                "https://servicequotas.amazonaws.com/",
                "Service Quotas API needs SigV4 IAM credentials",
                permissions="IAM with servicequotas:GetServiceQuota"),
            incidents=_statushub("https://health.aws.amazon.com"),
        ),
    ),
    "cloudinary": ProviderProfile(
        provider_id="cloudinary", display_name="Cloudinary", category="media",
        website="https://cloudinary.com", docs_url="https://cloudinary.com/documentation",
        status_url="https://status.cloudinary.com", sdk_package="cloudinary", sdk_language="node",
        capabilities=_caps(
            usage=ProviderCapability.live(Capability.USAGE_MONITORING,
                "https://api.cloudinary.com/v1_1/{cloud}/usage",
                "Real account usage (credits / storage / bandwidth / transforms)",
                permissions="cloud name + api key + api secret (cloud:key:secret)"),
            incidents=_statushub("https://status.cloudinary.com"),
        ),
    ),
    "google_ai": ProviderProfile(
        provider_id="google_ai", display_name="Google AI (Gemini)", category="ai",
        website="https://ai.google.dev", docs_url="https://ai.google.dev/gemini-api/docs",
        status_url="https://status.cloud.google.com", sdk_package="@google/generative-ai", sdk_language="node",
        capabilities=_caps(
            usage=ProviderCapability.permission(Capability.USAGE_MONITORING,
                "https://generativelanguage.googleapis.com/v1beta/models",
                "No per-API-key usage endpoint; real usage needs a GCP project/service account",
                permissions="GCP service account + Cloud Billing"),
            incidents=_statushub("https://status.cloud.google.com"),
        ),
    ),
    "huggingface": ProviderProfile(
        provider_id="huggingface", display_name="Hugging Face", category="ai",
        website="https://huggingface.co", docs_url="https://huggingface.co/docs",
        status_url="https://status.huggingface.co", sdk_package="@huggingface/inference", sdk_language="node",
        capabilities=_caps(
            usage=ProviderCapability.missing(Capability.USAGE_MONITORING,
                "No per-token usage API — account credits are billing, not usage"),
            incidents=_statushub("https://status.huggingface.co"),
        ),
    ),
    "elevenlabs": ProviderProfile(
        provider_id="elevenlabs", display_name="ElevenLabs", category="ai",
        website="https://elevenlabs.io", docs_url="https://elevenlabs.io/docs",
        status_url="https://status.elevenlabs.io", sdk_package="elevenlabs", sdk_language="node",
        capabilities=_caps(
            usage=ProviderCapability.live(Capability.USAGE_MONITORING,
                "https://api.elevenlabs.io/v1/user/usage",
                "Real character usage via Bearer key"),
            quota=ProviderCapability.live(Capability.QUOTA_MONITORING,
                "https://api.elevenlabs.io/v1/user/subscription",
                "Real plan character limit / used from subscription object",
                permissions="None (any API key)"),
            incidents=_statushub("https://status.elevenlabs.io"),
        ),
    ),
    "postmark": ProviderProfile(
        provider_id="postmark", display_name="Postmark", category="email",
        website="https://postmarkapp.com", docs_url="https://postmarkapp.com/developer",
        status_url="https://status.postmarkapp.com", sdk_package="postmark", sdk_language="node",
        capabilities=_caps(
            usage=ProviderCapability.live(Capability.USAGE_MONITORING,
                "https://api.postmarkapp.com/server/{id}/stats/outbound",
                "Real outbound email stats (sent/bounced/opened) via server token"),
            quota=ProviderCapability.missing(Capability.QUOTA_MONITORING,
                "No public quota endpoint — plan limits dashboard-only"),
            incidents=_statushub("https://status.postmarkapp.com"),
        ),
    ),
    "mailgun": ProviderProfile(
        provider_id="mailgun", display_name="Mailgun", category="email",
        website="https://www.mailgun.com", docs_url="https://documentation.mailgun.com",
        status_url="https://status.mailgun.com", sdk_package="mailgun.js", sdk_language="node",
        capabilities=_caps(
            usage=ProviderCapability.live(Capability.USAGE_MONITORING,
                "https://api.mailgun.net/v3/{domain}/stats/total",
                "Real email stats (accepted/delivered/failed) via api:domain key",
                permissions="API key + sending domain (api:domain)"),
            quota=ProviderCapability.missing(Capability.QUOTA_MONITORING,
                "No public quota endpoint"),
            incidents=_statushub("https://status.mailgun.com"),
        ),
    ),
    "digitalocean": ProviderProfile(
        provider_id="digitalocean", display_name="DigitalOcean", category="cloud",
        website="https://www.digitalocean.com", docs_url="https://docs.digitalocean.com",
        status_url="https://status.digitalocean.com", sdk_package="do-wrapper", sdk_language="node",
        capabilities=_caps(
            usage=ProviderCapability.live(Capability.USAGE_MONITORING,
                "https://api.digitalocean.com/v2/balance",
                "Real account balance + monthly usage from the billing API",
                permissions="None (any read token)"),
            rate=ProviderCapability.live(Capability.RATE_LIMIT_MONITORING,
                "https://api.digitalocean.com/v2/account",
                "Real RateLimit-Limit/RateLimit-Remaining headers on API responses"),
            incidents=_statushub("https://status.digitalocean.com"),
        ),
    ),
    "sentry": ProviderProfile(
        provider_id="sentry", display_name="Sentry", category="devtools",
        website="https://sentry.io", docs_url="https://docs.sentry.io",
        status_url="https://status.sentry.io", sdk_package="@sentry/node", sdk_language="node",
        capabilities=_caps(
            usage=ProviderCapability.permission(Capability.USAGE_MONITORING,
                "https://sentry.io/api/0/organizations/{slug}/usage/",
                "Usage API exists but needs organization + owner/manager scope",
                permissions="org:read + owner/manager on the org"),
            quota=ProviderCapability.permission(Capability.QUOTA_MONITORING,
                "https://sentry.io/api/0/organizations/{slug}/usage/",
                "Quota included in the usage API; needs org scope",
                permissions="org:read + owner/manager"),
            incidents=_statushub("https://status.sentry.io"),
        ),
    ),
    "auth0": ProviderProfile(
        provider_id="auth0", display_name="Auth0", category="auth",
        website="https://auth0.com", docs_url="https://auth0.com/docs",
        status_url="https://status.auth0.com", sdk_package="auth0", sdk_language="node",
        capabilities=_caps(
            usage=ProviderCapability.missing(Capability.USAGE_MONITORING,
                "No usage API via management token"),
            rate=ProviderCapability.live(Capability.RATE_LIMIT_MONITORING,
                "https://{tenant}.auth0.com/api/v2/tenants/settings",
                "Real RateLimit-* headers on the management API",
                permissions="Management token (client_id + client_secret)"),
            incidents=_statushub("https://status.auth0.com"),
        ),
    ),
    "clerk": ProviderProfile(
        provider_id="clerk", display_name="Clerk", category="auth",
        website="https://clerk.com", docs_url="https://clerk.com/docs",
        status_url="https://status.clerk.com", sdk_package="@clerk/clerk-sdk-node", sdk_language="node",
        capabilities=_caps(
            usage=ProviderCapability.permission(Capability.USAGE_MONITORING,
                "https://api.clerk.com/v1/instance",
                "Instance/users-count are real; detailed usage needs the usage-export admin endpoint",
                permissions="Admin API key (sk_test_/sk_live_) with usage-export permission"),
            incidents=_statushub("https://status.clerk.com"),
        ),
    ),
    "mapbox": ProviderProfile(
        provider_id="mapbox", display_name="Mapbox", category="maps",
        website="https://www.mapbox.com", docs_url="https://docs.mapbox.com",
        status_url="https://status.mapbox.com", sdk_package="mapbox-gl", sdk_language="node",
        capabilities=_caps(
            usage=ProviderCapability.permission(Capability.USAGE_MONITORING,
                "https://api.mapbox.com/account/usage/tokens/v1/{token}",
                "Usage API exists but needs a SECRET token with usage scope",
                permissions="Secret token (sk.) with usage scope"),
            quota=ProviderCapability.permission(Capability.QUOTA_MONITORING,
                "https://api.mapbox.com/account/quotas/v1/",
                "Quota API needs a secret token with usage scope",
                permissions="Secret token (sk.)"),
            incidents=_statushub("https://status.mapbox.com"),
        ),
    ),
    "algolia": ProviderProfile(
        provider_id="algolia", display_name="Algolia", category="search",
        website="https://www.algolia.com", docs_url="https://www.algolia.com/doc",
        status_url="https://status.algolia.com", sdk_package="algoliasearch", sdk_language="node",
        capabilities=_caps(
            usage=ProviderCapability.permission(Capability.USAGE_MONITORING,
                "https://{app}.algolia.net/1/indexes/{index}/stats",
                "Per-index stats need an ADMIN API key with ops scope",
                permissions="Admin API key (not search-only)"),
            incidents=_statushub("https://status.algolia.com"),
        ),
    ),
    "posthog": ProviderProfile(
        provider_id="posthog", display_name="PostHog", category="analytics",
        website="https://posthog.com", docs_url="https://posthog.com/docs",
        status_url="https://status.posthog.com", sdk_package="posthog-js", sdk_language="node",
        capabilities=_caps(
            usage=ProviderCapability.permission(Capability.USAGE_MONITORING,
                "https://us.i.posthog.com/api/projects/@current/",
                "Project APIs are real with a personal API key; usage/billing needs the billing org API",
                permissions="Personal API key (phx_...) with billing read"),
            quota=ProviderCapability.permission(Capability.QUOTA_MONITORING,
                "https://us.i.posthog.com/api/billing/",
                "Billing/quota API needs a personal API key with billing scope",
                permissions="Personal API key (phx_...)"),
            incidents=_statushub("https://status.posthog.com"),
        ),
    ),
    "mixpanel": ProviderProfile(
        provider_id="mixpanel", display_name="Mixpanel", category="analytics",
        website="https://mixpanel.com", docs_url="https://developer.mixpanel.com",
        status_url="https://status.mixpanel.com", sdk_package="mixpanel", sdk_language="node",
        capabilities=_caps(
            usage=ProviderCapability.permission(Capability.USAGE_MONITORING,
                "https://mixpanel.com/api/2.0/engage",
                "Engage/export APIs need a service account credential; usage is plans-derived",
                permissions="Service account (service account credential)"),
            incidents=_statushub("https://status.mixpanel.com"),
        ),
    ),
    "segment": ProviderProfile(
        provider_id="segment", display_name="Segment", category="analytics",
        website="https://segment.com", docs_url="https://segment.com/docs",
        status_url="https://status.segment.com", sdk_package="@segment/analytics-node", sdk_language="node",
        capabilities=_caps(
            usage=ProviderCapability.permission(Capability.USAGE_MONITORING,
                "https://api.segment.io/v1/",
                "Write keys cannot read usage; the Unified API needs a workspace token + profile scope",
                permissions="Workspace token with profile read"),
            incidents=_statushub("https://status.segment.com"),
        ),
    ),
    "intercom": ProviderProfile(
        provider_id="intercom", display_name="Intercom", category="support",
        website="https://www.intercom.com", docs_url="https://developers.intercom.com",
        status_url="https://status.intercom.com", sdk_package="intercom-client", sdk_language="node",
        capabilities=_caps(
            usage=ProviderCapability.missing(Capability.USAGE_MONITORING,
                "No public usage API"),
            incidents=_statushub("https://status.intercom.com"),
        ),
    ),
    "discord": ProviderProfile(
        provider_id="discord", display_name="Discord", category="chat",
        website="https://discord.com", docs_url="https://discord.com/developers/docs",
        status_url="https://discordstatus.com", sdk_package="discord.js", sdk_language="node",
        capabilities=_caps(
            usage=ProviderCapability.missing(Capability.USAGE_MONITORING,
                "No public bot usage API"),
            rate=ProviderCapability.live(Capability.RATE_LIMIT_MONITORING,
                "https://discord.com/api/v10/applications/@me",
                "Real x-ratelimit-* headers on API responses",
                permissions="Bot token"),
            incidents=_statushub("https://discordstatus.com"),
        ),
    ),
    "telegram": ProviderProfile(
        provider_id="telegram", display_name="Telegram", category="chat",
        website="https://telegram.org", docs_url="https://core.telegram.org/bots/api",
        sdk_package="telegraf", sdk_language="node",
        capabilities=_caps(
            usage=ProviderCapability.missing(Capability.USAGE_MONITORING,
                "No usage API — bot API exposes no quotas"),
            code=False, notes_code="No SDK manifest entry",
        ),
    ),
    "whatsapp": ProviderProfile(
        provider_id="whatsapp", display_name="WhatsApp (Meta)", category="chat",
        website="https://developers.facebook.com/docs/whatsapp",
        docs_url="https://developers.facebook.com/docs/whatsapp",
        status_url="https://metastatus.com", sdk_package="whatsapp-web.js", sdk_language="node",
        capabilities=_caps(
            usage=ProviderCapability.permission(Capability.USAGE_MONITORING,
                "https://graph.facebook.com/v19.0/{waba_id}",
                "Business Management API usage needs a WABA-scoped system user token",
                permissions="Meta system user token with whatsapp_business_management"),
            incidents=_statushub("https://metastatus.com"),
        ),
    ),
    "twitter": ProviderProfile(
        provider_id="twitter", display_name="Twitter / X", category="social",
        website="https://developer.x.com", docs_url="https://developer.x.com",
        status_url="https://api.twitterstat.us", sdk_package="twitter-api-v2", sdk_language="node",
        capabilities=_caps(
            usage=ProviderCapability.permission(Capability.USAGE_MONITORING,
                "https://api.x.com/2/users/me",
                "Usage is OAuth2-only; request/usage analytics is a paid add-on",
                permissions="OAuth2 user context or app-only Bearer"),
            rate=ProviderCapability.live(Capability.RATE_LIMIT_MONITORING,
                "https://api.x.com/2/users/me",
                "Real x-rate-limit-* headers on API v2 responses",
                permissions="OAuth2 Bearer token"),
            incidents=_statushub("https://api.twitterstat.us"),
        ),
    ),
    "zoom": ProviderProfile(
        provider_id="zoom", display_name="Zoom", category="video",
        website="https://zoom.us", docs_url="https://developers.zoom.us",
        status_url="https://status.zoom.us", sdk_package="@zoom/meetingsdk", sdk_language="node",
        capabilities=_caps(
            usage=ProviderCapability.permission(Capability.USAGE_MONITORING,
                "https://api.zoom.us/v2/usage/meetings",
                "Dashboard usage reports need an account owner/admin + OAuth2",
                permissions="OAuth2 app with report:read:admin"),
            incidents=_statushub("https://status.zoom.us"),
        ),
    ),
    "pusher": ProviderProfile(
        provider_id="pusher", display_name="Pusher", category="realtime",
        website="https://pusher.com", docs_url="https://pusher.com/docs",
        status_url="https://status.pusher.com", sdk_package="pusher", sdk_language="node",
        capabilities=_caps(
            usage=ProviderCapability.missing(Capability.USAGE_MONITORING,
                "No per-app usage API"),
            incidents=_statushub("https://status.pusher.com"),
        ),
    ),
    "youtube": ProviderProfile(
        provider_id="youtube", display_name="YouTube", category="video",
        website="https://developers.google.com/youtube",
        docs_url="https://developers.google.com/youtube",
        status_url="https://status.cloud.google.com", sdk_package="googleapis", sdk_language="node",
        capabilities=_caps(
            usage=ProviderCapability.permission(Capability.USAGE_MONITORING,
                "https://youtubeanalytics.googleapis.com/v2/reports",
                "Quota usage reports need OAuth2 + YouTube Analytics API",
                permissions="OAuth2 with yt-analytics.readonly"),
            quota=ProviderCapability.permission(Capability.QUOTA_MONITORING,
                "https://youtubeanalytics.googleapis.com/v2/reports",
                "Daily quota via YouTube Reporting/Analytics needs OAuth2",
                permissions="OAuth2 with yt-analytics.readonly"),
            incidents=_statushub("https://status.cloud.google.com"),
        ),
    ),
    "notion": ProviderProfile(
        provider_id="notion", display_name="Notion", category="productivity",
        website="https://www.notion.so", docs_url="https://developers.notion.com",
        status_url="https://status.notion.site", sdk_package="@notionhq/client", sdk_language="node",
        capabilities=_caps(
            usage=ProviderCapability.missing(Capability.USAGE_MONITORING,
                "No usage API — integration tokens expose no quotas"),
            incidents=_statushub("https://status.notion.site"),
        ),
    ),
    "airtable": ProviderProfile(
        provider_id="airtable", display_name="Airtable", category="productivity",
        website="https://airtable.com", docs_url="https://airtable.com/developers",
        status_url="https://status.airtable.com", sdk_package="airtable", sdk_language="node",
        capabilities=_caps(
            usage=ProviderCapability.missing(Capability.USAGE_MONITORING,
                "No usage API — personal tokens expose no quotas"),
            incidents=_statushub("https://status.airtable.com"),
        ),
    ),
    "mongodb": ProviderProfile(
        provider_id="mongodb", display_name="MongoDB Atlas", category="database",
        website="https://www.mongodb.com", docs_url="https://www.mongodb.com/docs/atlas",
        status_url="https://status.mongodb.com", sdk_package="mongodb", sdk_language="node",
        capabilities=_caps(
            usage=ProviderCapability.permission(Capability.USAGE_MONITORING,
                "https://cloud.mongodb.com/api/atlas/v1.0/groups",
                "Atlas API is real (digest auth) but usage/measurements need project access",
                permissions="Org/project API key (public:private) with project read"),
            quota=ProviderCapability.permission(Capability.QUOTA_MONITORING,
                "https://cloud.mongodb.com/api/atlas/v1.0/groups",
                "Atlas measurement API needs project access",
                permissions="Org/project API key"),
            incidents=_statushub("https://status.mongodb.com"),
        ),
    ),
    "redis": ProviderProfile(
        provider_id="redis", display_name="Redis", category="database",
        website="https://redis.com", docs_url="https://redis.io/docs",
        status_url="https://status.redis.com", sdk_package="redis", sdk_language="node",
        capabilities=_caps(
            usage=ProviderCapability.permission(Capability.USAGE_MONITORING,
                "https://api.redislabs.com/v1/",
                "Redis Cloud org API exposes subscriptions; usage metrics need an org admin key",
                permissions="Redis Cloud org API key (admin)"),
            incidents=_statushub("https://status.redis.com"),
        ),
    ),
    "plaid": ProviderProfile(
        provider_id="plaid", display_name="Plaid", category="fintech",
        website="https://plaid.com", docs_url="https://plaid.com/docs",
        status_url="https://status.plaid.com", sdk_package="plaid", sdk_language="node",
        capabilities=_caps(
            usage=ProviderCapability.missing(Capability.USAGE_MONITORING,
                "No per-client usage API — consumption is billing-only"),
            incidents=_statushub("https://status.plaid.com"),
        ),
    ),
    "openweather": ProviderProfile(
        provider_id="openweather", display_name="OpenWeather", category="weather",
        website="https://openweathermap.org", docs_url="https://openweathermap.org/api",
        sdk_package=None, sdk_language=None,
        capabilities=_caps(
            usage=ProviderCapability.missing(Capability.USAGE_MONITORING,
                "No usage API — plan call limits are dashboard-only"),
            rate=ProviderCapability.missing(Capability.RATE_LIMIT_MONITORING,
                "Retry-After only on 429; no continuous limit headers"),
            code=False, notes_code="No SDK manifest entry",
        ),
    ),
    "serpapi": ProviderProfile(
        provider_id="serpapi", display_name="SerpApi", category="search",
        website="https://serpapi.com", docs_url="https://serpapi.com/search-api",
        sdk_package="google-search-results-nodejs", sdk_language="node",
        capabilities=_caps(
            usage=ProviderCapability.live(Capability.USAGE_MONITORING,
                "https://serpapi.com/account",
                "Real searches-this-month / plan usage from the account API"),
            quota=ProviderCapability.live(Capability.QUOTA_MONITORING,
                "https://serpapi.com/account",
                "Real plan limit + remaining searches from the account API",
                permissions="None (any API key)"),
        ),
    ),
}


def get_provider(provider_id: str) -> ProviderProfile | None:
    return PROVIDERS.get(provider_id)


def list_providers() -> list[ProviderProfile]:
    return list(PROVIDERS.values())


def providers_with_capability(cap: Capability) -> list[ProviderProfile]:
    return [p for p in PROVIDERS.values() if p.has(cap)]


def capability_matrix() -> list[dict]:
    """Machine-readable 44-provider capability matrix (Session-8 audit).

    One row per provider; per-capability keys carry the honest status plus the
    OFFICIAL provider API source and the permissions required to unlock it.
    This is what the final audit table is generated from.
    """
    rows: list[dict] = []
    for pid in sorted(PROVIDERS):
        p = PROVIDERS[pid]
        row: dict = {
            "provider": pid,
            "name": p.display_name,
            "category": p.category,
            "docs": p.docs_url,
            "status_url": p.status_url,
        }
        for c in p.capabilities:
            row[c.capability.value] = {
                "status": c.status.value,
                "source": c.api_base,
                "permissions": c.permissions,
                "notes": c.notes,
            }
        rows.append(row)
    return rows