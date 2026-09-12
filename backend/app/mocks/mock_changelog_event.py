"""Mock changelog events for all 15 Phase A providers — testing/demo only.

Used by the "Simulate Breaking Change" dashboard button. Only contains string
labels and mock descriptions; it never references any secret/API key VALUE.

Security: All mock data uses obviously fake placeholders. No realistic-looking
secret values are ever constructed, stored, or logged.
"""

MOCK_BREAKING_CHANGES: dict[str, dict] = {
    # --- Payment ---
    "stripe": {
        "api_name": "stripe",
        "change_type": "field_renamed",
        "old_value": "source",
        "new_value": "payment_method",
        "description": "Stripe has renamed the 'source' field to 'payment_method' on Charge and PaymentIntent objects.",
        "source_url": "https://stripe.com/docs/changelog",
        "is_test": True,
    },
    "shopify": {
        "api_name": "shopify",
        "change_type": "endpoint_deprecated",
        "old_value": "POST /admin/api/2023-01/orders.json",
        "new_value": "POST /admin/api/2024-01/orders.json",
        "description": "Shopify has deprecated the 2023-01 API version for the Orders endpoint.",
        "source_url": "https://shopify.dev/changelog",
        "is_test": True,
    },
    "paypal": {
        "api_name": "paypal",
        "change_type": "field_removed",
        "old_value": "payment_instruction",
        "new_value": None,
        "description": "PayPal has removed the 'payment_instruction' field from the Order API response.",
        "source_url": "https://developer.paypal.com/docs/release-notes/",
        "is_test": True,
    },

    # --- Communication ---
    "twilio": {
        "api_name": "twilio",
        "change_type": "field_renamed",
        "old_value": "num_media",
        "new_value": "media_count",
        "description": "Twilio has renamed 'num_media' to 'media_count' in the Message resource.",
        "source_url": "https://www.twilio.com/en-us/changelog",
        "is_test": True,
    },
    "sendgrid": {
        "api_name": "sendgrid",
        "change_type": "endpoint_deprecated",
        "old_value": "v3/mail/send/beta",
        "new_value": "v3/mail/send",
        "description": "SendGrid has deprecated the beta mail send endpoint.",
        "source_url": "https://docs.sendgrid.com/for-developers/changelog",
        "is_test": True,
    },
    "resend": {
        "api_name": "resend",
        "change_type": "field_renamed",
        "old_value": "from_email",
        "new_value": "from",
        "description": "Resend has renamed 'from_email' to 'from' in the Email API.",
        "source_url": "https://resend.com/changelog",
        "is_test": True,
    },
    "slack": {
        "api_name": "slack",
        "change_type": "endpoint_deprecated",
        "old_value": "chat.postMessage legacy",
        "new_value": "chat.postMessage with blocks",
        "description": "Slack has deprecated the legacy chat.postMessage format.",
        "source_url": "https://api.slack.com/changelog",
        "is_test": True,
    },

    # --- AI ---
    "openai": {
        "api_name": "openai",
        "change_type": "field_renamed",
        "old_value": "engine",
        "new_value": "model",
        "description": "OpenAI has renamed the 'engine' parameter to 'model' across all endpoints.",
        "source_url": "https://platform.openai.com/docs/changelog",
        "is_test": True,
    },
    "anthropic": {
        "api_name": "anthropic",
        "change_type": "endpoint_deprecated",
        "old_value": "v1/complete",
        "new_value": "v1/messages",
        "description": "Anthropic has deprecated the /v1/complete endpoint in favor of /v1/messages.",
        "source_url": "https://docs.anthropic.com/en/docs/about-claude/changelog",
        "is_test": True,
    },

    # --- DevTools ---
    "github": {
        "api_name": "github",
        "change_type": "field_removed",
        "old_value": "push_event.head_commit.author",
        "new_value": None,
        "description": "GitHub has removed the nested author object from push event head_commit.",
        "source_url": "https://github.blog/changelog/",
        "is_test": True,
    },

    # --- Database ---
    "supabase": {
        "api_name": "supabase",
        "change_type": "field_renamed",
        "old_value": "auth.session",
        "new_value": "auth.getSession",
        "description": "Supabase has renamed auth.session() to auth.getSession().",
        "source_url": "https://supabase.com/changelog",
        "is_test": True,
    },

    # --- Cloud ---
    "firebase": {
        "api_name": "firebase",
        "change_type": "endpoint_deprecated",
        "old_value": "firestore.collection().doc().get()",
        "new_value": "firestore.doc().get()",
        "description": "Firebase has deprecated the nested collection() chaining pattern.",
        "source_url": "https://firebase.google.com/support/releases",
        "is_test": True,
    },
    "aws": {
        "api_name": "aws",
        "change_type": "field_removed",
        "old_value": "s3.listObjects.Contents.ETag",
        "new_value": None,
        "description": "AWS S3 has removed the ETag field from listObjects response in new regions.",
        "source_url": "https://aws.amazon.com/about-aws/whats-new/",
        "is_test": True,
    },
    "vercel": {
        "api_name": "vercel",
        "change_type": "field_renamed",
        "old_value": "deployment.url",
        "new_value": "deployment.inspectorUrl",
        "description": "Vercel has renamed the 'url' field to 'inspectorUrl' in deployment responses.",
        "source_url": "https://vercel.com/changelog",
        "is_test": True,
    },

    # --- Media ---
    "cloudinary": {
        "api_name": "cloudinary",
        "change_type": "field_renamed",
        "old_value": "secure_url",
        "new_value": "url",
        "description": "Cloudinary has renamed 'secure_url' to 'url' (now always HTTPS).",
        "source_url": "https://cloudinary.com/releases",
        "is_test": True,
    },

    # --- Phase C: AI ---
    "googleai": {
        "api_name": "googleai",
        "change_type": "field_renamed",
        "old_value": "text",
        "new_value": "parts",
        "description": "Google AI Gemini has replaced the 'text' response field with a 'parts' array.",
        "source_url": "https://ai.google.dev/gemini-api/docs/changelog",
        "is_test": True,
    },
    "huggingface": {
        "api_name": "huggingface",
        "change_type": "endpoint_deprecated",
        "old_value": "api/v1/generate",
        "new_value": "api/v1/chat",
        "description": "Hugging Face has deprecated the /api/v1/generate endpoint in favor of /api/v1/chat.",
        "source_url": "https://huggingface.co/docs/api-inference/changelog",
        "is_test": True,
    },
    "elevenlabs": {
        "api_name": "elevenlabs",
        "change_type": "field_removed",
        "old_value": "voice_id",
        "new_value": None,
        "description": "ElevenLabs has removed the 'voice_id' field from text-to-speech responses.",
        "source_url": "https://elevenlabs.io/docs/changelog",
        "is_test": True,
    },

    # --- Phase C: Communication ---
    "postmark": {
        "api_name": "postmark",
        "change_type": "endpoint_deprecated",
        "old_value": "POST /messages/outbound",
        "new_value": "POST /email",
        "description": "Postmark has deprecated the /messages/outbound endpoint for a unified /email endpoint.",
        "source_url": "https://postmarkapp.com/changelog",
        "is_test": True,
    },
    "mailgun": {
        "api_name": "mailgun",
        "change_type": "field_renamed",
        "old_value": "recipient-variables",
        "new_value": "v:variables",
        "description": "Mailgun has renamed the 'recipient-variables' field to 'v:variables'.",
        "source_url": "https://www.mailgun.com/changelog/",
        "is_test": True,
    },

    # --- Phase C: Cloud ---
    "digitalocean": {
        "api_name": "digitalocean",
        "change_type": "endpoint_deprecated",
        "old_value": "v2/droplets/{id}/actions",
        "new_value": "v2/droplets/{id}/actions?page=1",
        "description": "DigitalOcean has deprecated unversioned droplet action listing.",
        "source_url": "https://docs.digitalocean.com/release-notes/api/",
        "is_test": True,
    },

    # --- Phase C: DevTools / Observability ---
    "sentry": {
        "api_name": "sentry",
        "change_type": "field_renamed",
        "old_value": "culprit",
        "new_value": "transaction",
        "description": "Sentry has renamed the 'culprit' field to 'transaction' in event payloads.",
        "source_url": "https://develop.sentry.dev/changelog/",
        "is_test": True,
    },
    "auth0": {
        "api_name": "auth0",
        "change_type": "endpoint_deprecated",
        "old_value": "POST /oauth/token (password grant)",
        "new_value": "POST /oauth/token (client_credentials)",
        "description": "Auth0 has deprecated the password grant flow in favor of client_credentials.",
        "source_url": "https://auth0.com/changelog",
        "is_test": True,
    },
    "clerk": {
        "api_name": "clerk",
        "change_type": "field_renamed",
        "old_value": "user.id",
        "new_value": "user.clerk_id",
        "description": "Clerk has renamed the 'id' field to 'clerk_id' on the User resource.",
        "source_url": "https://clerk.com/changelog",
        "is_test": True,
    },
    "mapbox": {
        "api_name": "mapbox",
        "change_type": "endpoint_deprecated",
        "old_value": "v4/geocode",
        "new_value": "v6/geocode",
        "description": "Mapbox has deprecated the v4 geocoding endpoint in favor of v6.",
        "source_url": "https://docs.mapbox.com/changelog/",
        "is_test": True,
    },
    "algolia": {
        "api_name": "algolia",
        "change_type": "field_renamed",
        "old_value": "nbHits",
        "new_value": "totalHits",
        "description": "Algolia has renamed the 'nbHits' field to 'totalHits' in search responses.",
        "source_url": "https://www.algolia.com/changelog/",
        "is_test": True,
    },

    # --- Phase C: Analytics ---
    "posthog": {
        "api_name": "posthog",
        "change_type": "field_removed",
        "old_value": "distinct_id",
        "new_value": None,
        "description": "PostHog has removed the 'distinct_id' field from capture events.",
        "source_url": "https://posthog.com/changelog",
        "is_test": True,
    },
    "mixpanel": {
        "api_name": "mixpanel",
        "change_type": "endpoint_deprecated",
        "old_value": "import?legacy=1",
        "new_value": "import",
        "description": "Mixpanel has deprecated the legacy import endpoint.",
        "source_url": "https://developer.mixpanel.com/changelog",
        "is_test": True,
    },
    "segment": {
        "api_name": "segment",
        "change_type": "field_renamed",
        "old_value": "anonymousId",
        "new_value": "anonymous_id",
        "description": "Segment has renamed 'anonymousId' to 'anonymous_id' across analytics events.",
        "source_url": "https://segment.com/docs/changelog/",
        "is_test": True,
    },
    "intercom": {
        "api_name": "intercom",
        "change_type": "endpoint_deprecated",
        "old_value": "v1/messages",
        "new_value": "v2/conversations",
        "description": "Intercom has deprecated the v1/messages endpoint in favor of v2/conversations.",
        "source_url": "https://developers.intercom.com/changelog/",
        "is_test": True,
    },

    # --- Phase D: 14 detection-only providers ---
    "discord": {
        "api_name": "discord",
        "change_type": "field_renamed",
        "old_value": "intents",
        "new_value": "intents.value",
        "description": "Discord has renamed the gateway 'intents' bitmask field to 'intents.value' in the client options.",
        "source_url": "https://discord.com/developers/docs/change-log",
        "is_test": True,
    },
    "telegram": {
        "api_name": "telegram",
        "change_type": "endpoint_deprecated",
        "old_value": "sendMessage with reply_markup as JSON string",
        "new_value": "sendMessage with inline_keyboard object",
        "description": "Telegram has deprecated sending reply_markup as a JSON string in sendMessage.",
        "source_url": "https://core.telegram.org/bots/api#recent-changes",
        "is_test": True,
    },
    "whatsapp": {
        "api_name": "whatsapp",
        "change_type": "field_removed",
        "old_value": "type=media",
        "new_value": None,
        "description": "WhatsApp Cloud API has removed the generic 'media' message type in favor of explicit media types.",
        "source_url": "https://developers.facebook.com/docs/whatsapp/cloud-api/changelog",
        "is_test": True,
    },
    "twitter": {
        "api_name": "twitter",
        "change_type": "endpoint_deprecated",
        "old_value": "GET /2/users/:id/mentions",
        "new_value": "GET /2/users/:id/mentions with new pagination",
        "description": "Twitter API v2 has deprecated the default pagination on the mentions timeline endpoint.",
        "source_url": "https://developer.x.com/en/docs/x-api/changelog",
        "is_test": True,
    },
    "zoom": {
        "api_name": "zoom",
        "change_type": "field_renamed",
        "old_value": "meeting_id",
        "new_value": "meetingId",
        "description": "Zoom has renamed 'meeting_id' to 'meetingId' in the meeting object responses.",
        "source_url": "https://developers.zoom.us/docs/changelog/",
        "is_test": True,
    },
    "pusher": {
        "api_name": "pusher",
        "change_type": "endpoint_deprecated",
        "old_value": "POST /apps/:app_id/events",
        "new_value": "POST /apps/:app_id/events with new auth",
        "description": "Pusher has deprecated the legacy events endpoint authentication flow.",
        "source_url": "https://pusher.com/docs/changelog/",
        "is_test": True,
    },
    "youtube": {
        "api_name": "youtube",
        "change_type": "endpoint_deprecated",
        "old_value": "videos.list with id in query",
        "new_value": "videos.list with id in request body",
        "description": "YouTube Data API v3 has deprecated passing video id in the videos.list query string.",
        "source_url": "https://developers.google.com/youtube/v3/revision_history",
        "is_test": True,
    },
    "notion": {
        "api_name": "notion",
        "change_type": "field_removed",
        "old_value": "parent.type=database",
        "new_value": None,
        "description": "Notion API has removed the implicit parent type inference for page creation.",
        "source_url": "https://developers.notion.com/changelog",
        "is_test": True,
    },
    "airtable": {
        "api_name": "airtable",
        "change_type": "field_renamed",
        "old_value": "typecast",
        "new_value": "key",
        "description": "Airtable has renamed the 'typecast' option to 'key' in the records create/update API.",
        "source_url": "https://airtable.com/developers/web/api/changelog",
        "is_test": True,
    },
    "mongodb": {
        "api_name": "mongodb",
        "change_type": "endpoint_deprecated",
        "old_value": "db.collection.save()",
        "new_value": "db.collection.replaceOne()",
        "description": "MongoDB has deprecated the collection.save() method in favor of replaceOne/insertOne.",
        "source_url": "https://www.mongodb.com/docs/upcoming/release-notes/",
        "is_test": True,
    },
    "redis": {
        "api_name": "redis",
        "change_type": "field_removed",
        "old_value": "CONFIG parameter appendonly",
        "new_value": None,
        "description": "Redis has removed the legacy appendonly CONFIG parameter in favor of the appendfsync directive.",
        "source_url": "https://raw.githubusercontent.com/redis/redis-doc/master/docs/releases/",
        "is_test": True,
    },
    "plaid": {
        "api_name": "plaid",
        "change_type": "field_renamed",
        "old_value": "transactions.get options.count",
        "new_value": "transactions.get options.limit",
        "description": "Plaid has renamed 'count' to 'limit' in the transactions.get options.",
        "source_url": "https://plaid.com/changelog/",
        "is_test": True,
    },
    "openweather": {
        "api_name": "openweather",
        "change_type": "endpoint_deprecated",
        "old_value": "weather?q=city",
        "new_value": "weather?q=city with units param",
        "description": "OpenWeatherMap has deprecated the untyped units parameter on the current weather endpoint.",
        "source_url": "https://openweathermap.org/changelog",
        "is_test": True,
    },
    "serpapi": {
        "api_name": "serpapi",
        "change_type": "field_removed",
        "old_value": "search engine=google",
        "new_value": None,
        "description": "SerpApi has removed the bare 'google' engine alias in favor of explicit 'google' engine with a version.",
        "source_url": "https://serpapi.com/changelog",
        "is_test": True,
    },
}

# Backward-compatible alias
MOCK_STRIPE_BREAKING_CHANGE = MOCK_BREAKING_CHANGES["stripe"]


def get_mock_for_provider(api_name: str) -> dict:
    """Get mock breaking change event for a provider. Falls back to Stripe."""
    return MOCK_BREAKING_CHANGES.get(api_name, MOCK_BREAKING_CHANGES["stripe"])


def get_all_mock_providers() -> list[str]:
    """Return all provider IDs that have mock fixtures."""
    return list(MOCK_BREAKING_CHANGES.keys())
