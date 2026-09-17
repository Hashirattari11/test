"""Provider source registry — ALL 44 monitored providers with official sources.

Purpose: single source of truth for provider monitoring. Every provider has:
  * an official changelog/release-notes URL,
  * a source kind describing HOW we monitor it:
      - RSS              -> official RSS/Atom feed (machine-readable)
      - JSON             -> official JSON API/endpoint
      - GITHUB_RELEASES  -> official GitHub Releases API (owner/repo)
      - HTML_STRICT      -> official HTML page, parsed with STRICT per-provider
                            selectors + date parsing + lookback window. Never
                            generic text-div scraping.
      - NONE             -> no reliable official source -> marked
                            SOURCE_UNAVAILABLE, produces NO events.

No-fabrication rule: an entry is only stored when ALL of the following come
from the official source: external_id (feed entry id / release id / URL),
title, permalink, and published date. Anything less is dropped with a reason.

Provider ids MUST match the frontend registry (frontend/lib/providers/registry.ts).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Source kinds (how we obtain changes for a provider)
# ---------------------------------------------------------------------------
RSS = "RSS"
JSON = "JSON"
GITHUB_RELEASES = "GITHUB_RELEASES"
HTML_STRICT = "HTML_STRICT"
NONE = "NONE"

SOURCE_KINDS = (RSS, JSON, GITHUB_RELEASES, HTML_STRICT, NONE)

# Runtime monitoring status values (mirrors provider_monitoring_status.status)
STATUS_ACTIVE = "ACTIVE"
STATUS_LIMITED = "LIMITED"
STATUS_SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
STATUS_ERROR = "ERROR"
MONITORING_STATUSES = (STATUS_ACTIVE, STATUS_LIMITED, STATUS_SOURCE_UNAVAILABLE, STATUS_ERROR)


@dataclass(frozen=True)
class ProviderSource:
    provider_id: str
    display_name: str
    category: str
    source_kind: str                      # RSS | JSON | GITHUB_RELEASES | HTML_STRICT | NONE
    changelog_url: str                    # official human changelog/release-notes page
    feed_url: Optional[str] = None        # machine-readable feed/API URL (RSS/JSON/GITHUB_RELEASES)
    lookback_days: int = 60               # never report entries older than this
    max_entries: int = 50                 # per-provider cap per fetch
    polling: str = "daily"                # cadence hint
    # HTML_STRICT only: container selector relative to the entry document.
    # Each adapter still defines its own strict extraction; these are hints.
    entry_selector: Optional[str] = None
    notes: str = ""

    @property
    def default_status(self) -> str:
        """The status a healthy fetch implies for this source kind."""
        if self.source_kind == NONE:
            return STATUS_SOURCE_UNAVAILABLE
        if self.source_kind in (RSS, JSON, GITHUB_RELEASES):
            return STATUS_ACTIVE
        return STATUS_LIMITED

    @property
    def host(self) -> str:
        """Official host for this provider's sources (SSRF allowlist)."""
        from urllib.parse import urlparse
        parsed = urlparse(self.changelog_url)
        return parsed.hostname or ""


# ---------------------------------------------------------------------------
# The 44-provider registry (ids align with frontend/lib/providers/registry.ts)
# ---------------------------------------------------------------------------
PROVIDER_SOURCES: tuple[ProviderSource, ...] = (
    # -- payment -------------------------------------------------------------
    ProviderSource("stripe", "Stripe", "payment", HTML_STRICT,
                   "https://docs.stripe.com/changelog",
                   entry_selector="article"),
    ProviderSource("shopify", "Shopify", "payment", RSS,
                   "https://shopify.dev/changelog",
                   feed_url="https://shopify.dev/changelog/feed.xml",
                   entry_selector="article"),
    ProviderSource("paypal", "PayPal", "payment", HTML_STRICT,
                   "https://developer.paypal.com/api/rest/",
                   entry_selector="article, .release-note"),
    ProviderSource("plaid", "Plaid", "payment", HTML_STRICT,
                   "https://plaid.com/docs/changelog/",
                   entry_selector="article, .changelog-entry"),
    # -- communication --------------------------------------------------------
    ProviderSource("twilio", "Twilio", "communication", HTML_STRICT,
                   "https://www.twilio.com/en-us/changelog",
                   entry_selector="article, .changelog-entry"),
    ProviderSource("sendgrid", "SendGrid", "communication", HTML_STRICT,
                   "https://www.twilio.com/docs/sendgrid",
                   entry_selector="article, .changelog-entry"),
    ProviderSource("resend", "Resend", "communication", HTML_STRICT,
                   "https://resend.com/changelog",
                   entry_selector="article, [class*=changelog-item]"),
    ProviderSource("slack", "Slack", "communication", HTML_STRICT,
                   "https://api.slack.com/changelog",
                   entry_selector="article, .changelog-entry"),
    ProviderSource("discord", "Discord", "communication", HTML_STRICT,
                   "https://discord.com/developers/docs/change-log",
                   entry_selector="article, .change-log-entry"),
    ProviderSource("telegram", "Telegram", "communication", HTML_STRICT,
                   "https://core.telegram.org/bots/api",
                   entry_selector=".recent-changes, .dev_page_block"),
    ProviderSource("whatsapp", "WhatsApp", "communication", HTML_STRICT,
                   "https://developers.facebook.com/docs/whatsapp/changelog",
                   entry_selector="article, .changeLog"),
    ProviderSource("twitter", "Twitter (X)", "communication", HTML_STRICT,
                   "https://developer.x.com/en/docs/x-api/changelog",
                   entry_selector="article, .changelog-entry"),
    ProviderSource("zoom", "Zoom", "communication", HTML_STRICT,
                   "https://developers.zoom.us/changelog",
                   entry_selector="article, .changelog-entry"),
    ProviderSource("pusher", "Pusher", "communication", HTML_STRICT,
                   "https://pusher.com/docs/",
                   entry_selector="article, .changelog-entry"),
    ProviderSource("postmark", "Postmark", "communication", HTML_STRICT,
                   "https://postmarkapp.com",
                   entry_selector="article, .changelog-entry"),
    ProviderSource("mailgun", "Mailgun", "communication", HTML_STRICT,
                   "https://www.mailgun.com/blog/",
                   entry_selector="article, .changelog-entry"),
    # -- cloud ---------------------------------------------------------------
    ProviderSource("aws", "AWS", "cloud", HTML_STRICT,
                   "https://aws.amazon.com/releasenotes/",
                   entry_selector=".release-note, article"),
    ProviderSource("vercel", "Vercel", "cloud", HTML_STRICT,
                   "https://vercel.com/changelog",
                   entry_selector="article, [data-changelog-entry]"),
    ProviderSource("cloudinary", "Cloudinary", "cloud", HTML_STRICT,
                   "https://cloudinary.com/documentation/",
                   entry_selector="article, .changelog-entry"),
    ProviderSource("firebase", "Firebase", "cloud", HTML_STRICT,
                   "https://firebase.google.com/support/releases",
                   entry_selector="main .devsite-article-body tr, article"),
    ProviderSource("digitalocean", "DigitalOcean", "cloud", HTML_STRICT,
                   "https://docs.digitalocean.com/release-notes/",
                   entry_selector="article, .release-note"),
    # -- ai ------------------------------------------------------------------
    ProviderSource("openai", "OpenAI", "ai", HTML_STRICT,
                   "https://platform.openai.com/docs/changelog",
                   entry_selector="article, .changelog-entry"),
    ProviderSource("anthropic", "Anthropic", "ai", HTML_STRICT,
                   "https://docs.anthropic.com/en/release-notes",
                   entry_selector="article, .release-note"),
    ProviderSource("googleai", "Google AI / Gemini", "ai", HTML_STRICT,
                   "https://ai.google.dev/gemini-api/docs/changelog",
                   entry_selector="article, .changelog-entry"),
    ProviderSource("huggingface", "Hugging Face", "ai", HTML_STRICT,
                   "https://huggingface.co/docs/api-inference",
                   entry_selector="article, .changelog-entry"),
    ProviderSource("elevenlabs", "ElevenLabs", "ai", HTML_STRICT,
                   "https://elevenlabs.io/docs/changelog",
                   entry_selector="article, .changelog-entry"),
    # -- analytics ------------------------------------------------------------
    ProviderSource("posthog", "PostHog", "analytics", HTML_STRICT,
                   "https://posthog.com/changelog",
                   entry_selector="article, .changelog-entry"),
    ProviderSource("mixpanel", "Mixpanel", "analytics", HTML_STRICT,
                   "https://mixpanel.com/docs/",
                   entry_selector="article, .changelog-entry"),
    ProviderSource("segment", "Segment", "analytics", HTML_STRICT,
                   "https://segment.com/docs/changelog/",
                   entry_selector="article, .changelog-entry"),
    ProviderSource("intercom", "Intercom", "analytics", HTML_STRICT,
                   "https://developers.intercom.com/",
                   entry_selector="article, .changelog-entry"),
    # -- devtools --------------------------------------------------------------
    ProviderSource("github", "GitHub", "devtools", RSS,
                   "https://github.blog/changelog/",
                   feed_url="https://github.blog/changelog/feed/",
                   entry_selector="article"),
    ProviderSource("sentry", "Sentry", "devtools", GITHUB_RELEASES,
                   "https://develop.sentry.dev/changelog/",
                   feed_url="https://api.github.com/repos/getsentry/sentry/releases",
                   entry_selector=None),
    ProviderSource("auth0", "Auth0", "devtools", HTML_STRICT,
                   "https://auth0.com/changelog",
                   entry_selector="article, .changelog-entry"),
    ProviderSource("clerk", "Clerk", "devtools", HTML_STRICT,
                   "https://clerk.com/changelog",
                   entry_selector="article, .changelog-entry"),
    ProviderSource("algolia", "Algolia", "devtools", HTML_STRICT,
                   "https://www.algolia.com/doc/changelog/",
                   entry_selector="article, .changelog-entry"),
    ProviderSource("mapbox", "Mapbox", "other", HTML_STRICT,
                   "https://docs.mapbox.com/",
                   entry_selector="article, .changelog-entry"),
    # -- database --------------------------------------------------------------
    ProviderSource("supabase", "Supabase", "database", HTML_STRICT,
                   "https://supabase.com/changelog",
                   entry_selector="article, [class*=changelog]"),
    ProviderSource("mongodb", "MongoDB", "database", HTML_STRICT,
                   "https://www.mongodb.com/docs/upcoming/release-notes/",
                   entry_selector="article, .release-note"),
    ProviderSource("redis", "Redis", "database", GITHUB_RELEASES,
                   "https://github.com/redis/redis/releases",
                   feed_url="https://api.github.com/repos/redis/redis/releases",
                   entry_selector=None),
    ProviderSource("airtable", "Airtable", "database", HTML_STRICT,
                   "https://airtable.com/developers/web/api/changelog",
                   entry_selector="article, .changelog-entry"),
    # -- media ----------------------------------------------------------------
    ProviderSource("youtube", "YouTube", "media", HTML_STRICT,
                   "https://developers.google.com/youtube/v3/revision_history",
                   entry_selector=".devsite-article-body, article"),
    # -- other -----------------------------------------------------------------
    ProviderSource("notion", "Notion", "other", HTML_STRICT,
                   "https://www.notion.so/changelog",
                   entry_selector="article, .changelog-entry"),
    ProviderSource("openweather", "OpenWeather", "other", HTML_STRICT,
                   "https://openweathermap.org/faq",
                   entry_selector="article, .changelog-entry"),
    ProviderSource("serpapi", "SerpApi", "other", HTML_STRICT,
                   "https://serpapi.com/blog/",
                   entry_selector="article, .changelog-entry"),
)

PROVIDER_SOURCES_BY_ID: dict[str, ProviderSource] = {p.provider_id: p for p in PROVIDER_SOURCES}

ALL_PROVIDER_IDS: tuple[str, ...] = tuple(p.provider_id for p in PROVIDER_SOURCES)


def get_provider_source(provider_id: str) -> Optional[ProviderSource]:
    """Return the source config for a provider id, or None if unknown."""
    return PROVIDER_SOURCES_BY_ID.get(provider_id)


def monitored_provider_ids() -> list[str]:
    """Providers that have any monitoring source configured (all 44)."""
    return list(ALL_PROVIDER_IDS)


def source_kind_counts() -> dict[str, int]:
    """How many providers per source kind (for the monitoring matrix UI)."""
    counts: dict[str, int] = {}
    for p in PROVIDER_SOURCES:
        counts[p.source_kind] = counts.get(p.source_kind, 0) + 1
    return counts