"""Deterministic API-usage signatures + provider registry (Phase A).

Phase A is 100% pattern matching — no AI, no changelog monitoring.
Adding a new provider is just a new entry in API_SIGNATURES.

Each signature is a raw regex. `matched_snippet` stores the whole matched line;
for providers with known object tokens, we extract them into `symbols` so the
alert engine can cross-reference changelog entries (Phase B).

Security: Evidence text references environment variable NAMES only, never values.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Provider signatures (Phase A: 15 providers)
# Keep patterns conservative to limit false positives.
# Each pattern matches either imports, env-var references, or SDK usage.
# ---------------------------------------------------------------------------
API_SIGNATURES: dict[str, list[str]] = {
    # --- Payment ---
    "stripe": [
        r"import stripe",
        r"from stripe",
        r"require\(['\"]stripe['\"]\)",
        r"new Stripe\(",
        r"Stripe\(",
        r"stripe\.(Charge|Customer|PaymentIntent|SetupIntent|Subscription|Invoice|Refund|Payout|Source|Token|Card|Price|Product|Checkout|PaymentMethod)\b",
        r"STRIPE_SECRET_KEY",
        r"STRIPE_PUBLISHABLE_KEY",
        r"STRIPE_WEBHOOK_SECRET",
        r"STRIPE_API_KEY",
        r"api\.stripe\.com",
    ],
    "shopify": [
        r"import shopify",
        r"from shopify",
        r"require\(['\"]shopify-api-node['\"]\)",
        r"require\(['\"]@shopify/shopify-api['\"]\)",
        r"@shopify/shopify-api",
        r"@shopify/shopify-app-react-router",
        r"@shopify/app-bridge-react",
        r"shopify_api",
        r"SHOPIFY_API_KEY",
        r"SHOPIFY_API_SECRET",
        r"SHOPIFY_ACCESS_TOKEN",
        r"SHOPIFY_API_SECRET_KEY",
        r"myshopify\.com",
    ],
    "paypal": [
        r"require\(['\"]@paypal/checkout-server-sdk['\"]\)",
        r"require\(['\"]@paypal/react-paypal-js['\"]\)",
        r"require\(['\"]paypal-rest-sdk['\"]\)",
        r"@paypal/checkout-server-sdk",
        r"@paypal/react-paypal-js",
        r"paypal-rest-sdk",
        r"import paypal",
        r"from paypal",
        r"PAYPAL_CLIENT_ID",
        r"PAYPAL_CLIENT_SECRET",
        r"PAYPAL_MODE",
        r"api\.paypal\.com",
    ],

    # --- Communication ---
    "twilio": [
        r"from twilio",
        r"import twilio",
        r"require\(['\"]twilio['\"]\)",
        r"twilio\.rest",
        r"TWILIO_ACCOUNT_SID",
        r"TWILIO_AUTH_TOKEN",
        r"TWILIO_API_KEY",
        r"TWILIO_API_SECRET",
        r"api\.twilio\.com",
    ],
    "sendgrid": [
        r"import sendgrid",
        r"from sendgrid",
        r"require\(['\"]@sendgrid/mail['\"]\)",
        r"require\(['\"]@sendgrid/client['\"]\)",
        r"@sendgrid/mail",
        r"@sendgrid/client",
        r"SENDGRID_API_KEY",
        r"api\.sendgrid\.com",
    ],
    "resend": [
        r"import resend",
        r"from resend",
        r"require\(['\"]resend['\"]\)",
        r"new Resend\(",
        r"Resend\(",
        r"RESEND_API_KEY",
        r"api\.resend\.com",
    ],
    "slack": [
        r"@slack/bolt",
        r"@slack/web-api",
        r"require\(['\"]@slack/bolt['\"]\)",
        r"require\(['\"]@slack/web-api['\"]\)",
        r"import slack",
        r"from slack",
        r"SLACK_BOT_TOKEN",
        r"SLACK_SIGNING_SECRET",
        r"SLACK_WEBHOOK_URL",
        r"SLACK_APP_TOKEN",
        r"hooks\.slack\.com",
    ],

    # --- AI ---
    "openai": [
        r"import openai",
        r"from openai",
        r"require\(['\"]openai['\"]\)",
        r"new OpenAI\(",
        r"OpenAI\(",
        r"OPENAI_API_KEY",
        r"api\.openai\.com",
    ],
    "anthropic": [
        r"import anthropic",
        r"from anthropic",
        r"require\(['\"]@anthropic-ai/sdk['\"]\)",
        r"require\(['\"]anthropic['\"]\)",
        r"@anthropic-ai/sdk",
        r"new Anthropic\(",
        r"Anthropic\(",
        r"ANTHROPIC_API_KEY",
        r"api\.anthropic\.com",
    ],

    # --- DevTools ---
    "github": [
        r"from github import",
        r"import github",
        r"PyGithub",
        r"@octokit/rest",
        r"require\(['\"]@octokit/rest['\"]\)",
        r"@actions/github",
        r"require\(['\"]@actions/github['\"]\)",
        r"GITHUB_TOKEN",
        r"GH_TOKEN",
        r"GITHUB_APP_PRIVATE_KEY",
        r"GITHUB_APP_ID",
        r"api\.github\.com",
    ],

    # --- Database ---
    "supabase": [
        r"import supabase",
        r"from supabase",
        r"require\(['\"]@supabase/supabase-js['\"]\)",
        r"@supabase/supabase-js",
        r"SUPABASE_URL",
        r"SUPABASE_ANON_KEY",
        r"SUPABASE_SERVICE_ROLE_KEY",
        r"supabase\.co",
    ],

    # --- Cloud ---
    "firebase": [
        r"import firebase",
        r"from firebase",
        r"require\(['\"]firebase['\"]\)",
        r"require\(['\"]firebase-admin['\"]\)",
        r"firebase-admin",
        r"initializeApp\(",
        r"FIREBASE_API_KEY",
        r"FIREBASE_PROJECT_ID",
        r"FIREBASE_CLIENT_EMAIL",
        r"firebaseio\.com",
        r"firestore\.googleapis\.com",
    ],
    "aws": [
        r"import boto3",
        r"from boto3",
        r"require\(['\"]aws-sdk['\"]\)",
        r"@aws-sdk/",
        r"aws-sdk",
        r"boto3",
        r"AWS_ACCESS_KEY_ID",
        r"AWS_SECRET_ACCESS_KEY",
        r"AWS_SESSION_TOKEN",
        r"AWS_REGION",
        r"amazonaws\.com",
    ],
    "vercel": [
        r"require\(['\"]@vercel/client['\"]\)",
        r"@vercel/client",
        r"import vercel",
        r"from vercel",
        r"VERCEL_TOKEN",
        r"api\.vercel\.com",
    ],

    # --- Media ---
    "cloudinary": [
        r"import cloudinary",
        r"from cloudinary",
        r"require\(['\"]cloudinary['\"]\)",
        r"cloudinary\.v2",
        r"Cloudinary\(",
        r"CLOUDINARY_URL",
        r"CLOUDINARY_API_KEY",
        r"CLOUDINARY_API_SECRET",
        r"res\.cloudinary\.com",
    ],

    # -------------------------------------------------------------------------
    # Phase C: 15 additional detection-only providers
    # -------------------------------------------------------------------------
    # --- AI ---
    "googleai": [
        r"import google\.generativeai",
        r"from google\.generativeai",
        r"import google\.genai",
        r"from google\.genai",
        r"require\(['\"]@google/generative-ai['\"]\)",
        r"require\(['\"]@google/genai['\"]\)",
        r"@google/generative-ai",
        r"@google/genai",
        r"GenerativeModel\(",
        r"GOOGLE_API_KEY",
        r"GEMINI_API_KEY",
        r"generativelanguage\.googleapis\.com",
    ],
    "huggingface": [
        r"import huggingface",
        r"from huggingface",
        r"require\(['\"]@huggingface/inference['\"]\)",
        r"require\(['\"]@huggingface/hub['\"]\)",
        r"@huggingface/inference",
        r"@huggingface/hub",
        r"InferenceClient\(",
        r"HF_TOKEN",
        r"HUGGINGFACEHUB_API_TOKEN",
        r"huggingface\.co",
    ],
    "elevenlabs": [
        r"import elevenlabs",
        r"from elevenlabs",
        r"require\(['\"]elevenlabs['\"]\)",
        r"ElevenLabs\(",
        r"client\.text_to_speech",
        r"ELEVENLABS_API_KEY",
        r"api\.elevenlabs\.io",
    ],

    # --- Communication ---
    "postmark": [
        r"import postmark",
        r"from postmark",
        r"require\(['\"]postmark['\"]\)",
        r"postmark\.send",
        r"POSTMARK_SERVER_TOKEN",
        r"api\.postmarkapp\.com",
    ],
    "mailgun": [
        r"import mailgun",
        r"from mailgun",
        r"require\(['\"]mailgun\.js['\"]\)",
        r"require\(['\"]mailgun-js['\"]\)",
        r"mailgun\.js",
        r"mailgun-js",
        r"mailgun\.",
        r"MAILGUN_API_KEY",
        r"MAILGUN_DOMAIN",
        r"api\.mailgun\.net",
    ],

    # --- Cloud ---
    "digitalocean": [
        r"import do_wrapper",
        r"from do_wrapper",
        r"require\(['\"]do-wrapper['\"]\)",
        r"do-wrapper",
        r"DoWrapper\(",
        r"digitalocean",
        r"DIGITALOCEAN_ACCESS_TOKEN",
        r"api\.digitalocean\.com",
    ],

    # --- DevTools / Observability ---
    "sentry": [
        r"import sentry_sdk",
        r"from sentry_sdk",
        r"require\(['\"]@sentry/node['\"]\)",
        r"require\(['\"]@sentry/browser['\"]\)",
        r"@sentry/nextjs",
        r"@sentry/node",
        r"@sentry/browser",
        r"Sentry\.init",
        r"SENTRY_DSN",
        r"SENTRY_AUTH_TOKEN",
        r"o\d+\.ingest\.sentry\.io",
    ],
    "auth0": [
        r"import auth0",
        r"from auth0",
        r"require\(['\"]@auth0/auth0-react['\"]\)",
        r"require\(['\"]@auth0/nextjs-auth0['\"]\)",
        r"@auth0/auth0-react",
        r"@auth0/nextjs-auth0",
        r"@auth0/auth0-spa-js",
        r"Auth0Provider",
        r"AUTH0_CLIENT_ID",
        r"AUTH0_CLIENT_SECRET",
        r"AUTH0_SECRET",
        r"AUTH0_BASE_URL",
        r"auth0\.com",
    ],
    "clerk": [
        r"import clerk",
        r"from clerk",
        r"require\(['\"]@clerk/nextjs['\"]\)",
        r"require\(['\"]@clerk/clerk-react['\"]\)",
        r"@clerk/nextjs",
        r"@clerk/clerk-react",
        r"@clerk/clerk-sdk-node",
        r"<ClerkProvider",
        r"CLERK_SECRET_KEY",
        r"NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY",
        r"clerk\.com",
    ],
    "mapbox": [
        r"import mapboxgl",
        r"from mapboxgl",
        r"require\(['\"]mapbox-gl['\"]\)",
        r"require\(['\"]@mapbox/mapbox-gl-js['\"]\)",
        r"import mapbox",
        r"mapbox-gl",
        r"@mapbox/mapbox-gl-js",
        r"mapboxgl\.accessToken",
        r"MAPBOX_ACCESS_TOKEN",
        r"api\.mapbox\.com",
    ],
    "algolia": [
        r"import algoliasearch",
        r"from algoliasearch",
        r"require\(['\"]algoliasearch['\"]\)",
        r"algoliasearch\(",
        r"ALGOLIA_APP_ID",
        r"ALGOLIA_API_KEY",
        r"ALGOLIA_ADMIN_API_KEY",
        r"\.algolia\.net",
    ],

    # --- Analytics ---
    "posthog": [
        r"import posthog",
        r"from posthog",
        r"require\(['\"]posthog-js['\"]\)",
        r"require\(['\"]posthog-node['\"]\)",
        r"posthog-js",
        r"posthog-node",
        r"posthog\.init",
        r"POSTHOG_API_KEY",
        r"NEXT_PUBLIC_POSTHOG_KEY",
        r"posthog\.com",
    ],
    "mixpanel": [
        r"import mixpanel",
        r"from mixpanel",
        r"require\(['\"]mixpanel['\"]\)",
        r"require\(['\"]mixpanel-browser['\"]\)",
        r"mixpanel-browser",
        r"mixpanel\.init",
        r"MIXPANEL_TOKEN",
        r"MIXPANEL_PROJECT_TOKEN",
        r"api\.mixpanel\.com",
    ],
    "segment": [
        r"import analytics",
        r"from analytics",
        r"require\(['\"]@segment/analytics-node['\"]\)",
        r"require\(['\"]@segment/analytics-next['\"]\)",
        r"@segment/analytics-node",
        r"@segment/analytics-next",
        r"Analytics\(",
        r"SEGMENT_WRITE_KEY",
        r"api\.segment\.io",
    ],
    "intercom": [
        r"import intercom",
        r"from intercom",
        r"require\(['\"]intercom-client['\"]\)",
        r"require\(['\"]intercom-node['\"]\)",
        r"intercom-client",
        r"Intercom\(",
        r"INTERCOM_ACCESS_TOKEN",
        r"api\.intercom\.io",
    ],

    # -------------------------------------------------------------------------
    # Phase D: 14 additional detection-only providers
    # -------------------------------------------------------------------------
    # --- Communication / Messaging ---
    "discord": [
        r"import discord",
        r"from discord",
        r"require\(['\"]discord\.js['\"]\)",
        r"require\(['\"]discord\.js\/rest['\"]\)",
        r"discord\.js",
        r"DiscordAPIError",
        r"new Client\(\s*\{\s*intents",
        r"DISCORD_TOKEN",
        r"DISCORD_BOT_TOKEN",
        r"DISCORD_CLIENT_ID",
        r"DISCORD_CLIENT_SECRET",
        r"discord\.com\/api",
    ],
    "telegram": [
        r"import telegram",
        r"from telegram",
        r"from telegram\.ext",
        r"require\(['\"]node-telegram-bot-api['\"]\)",
        r"require\(['\"]telegraf['\"]\)",
        r"node-telegram-bot-api",
        r"Telegraf\(",
        r"TelegramBot\(",
        r"TELEGRAM_BOT_TOKEN",
        r"api\.telegram\.org",
    ],
    "whatsapp": [
        r"require\(['\"]@whatsapp/cloud-api['\"]\)",
        r"@whatsapp/cloud-api",
        r"whatsapp-cloud-api",
        r"WHATSAPP_ACCESS_TOKEN",
        r"WHATSAPP_FROM_PHONE",
        r"WHATSAPP_API_TOKEN",
        r"graph\.facebook\.com\/v\d+\.\d+\/\d+\/messages",
    ],
    "twitter": [
        r"require\(['\"]twitter-api-v2['\"]\)",
        r"require\(['\"]twitter['\"]\)",
        r"twitter-api-v2",
        r"import tweepy",
        r"from tweepy",
        r"import twitter",
        r"from twitter",
        r"Tweepy\(",
        r"twitter\.v2",
        r"TWITTER_API_KEY",
        r"TWITTER_API_SECRET",
        r"TWITTER_ACCESS_TOKEN",
        r"TWITTER_ACCESS_SECRET",
        r"TWITTER_BEARER_TOKEN",
        r"api\.twitter\.com",
    ],
    "zoom": [
        r"require\(['\"]@zoom/videosdk['\"]\)",
        r"require\(['\"]zoom-embedded['\"]\)",
        r"@zoom/videosdk",
        r"import zoom",
        r"from zoom",
        r"ZOOM_API_KEY",
        r"ZOOM_API_SECRET",
        r"ZOOM_JWT_TOKEN",
        r"api\.zoom\.us",
    ],
    "pusher": [
        r"import pusher",
        r"from pusher",
        r"require\(['\"]pusher['\"]\)",
        r"new Pusher\(",
        r"Pusher\(",
        r"PUSHER_APP_ID",
        r"PUSHER_KEY",
        r"PUSHER_SECRET",
        r"PUSHER_CLUSTER",
    ],

    # --- Media / Productivity ---
    "youtube": [
        r"import googleapiclient",
        r"from googleapiclient",
        r"require\(['\"]@googleapis\/youtube['\"]\)",
        r"@googleapis/youtube",
        r"youtube\.v3",
        r"YOUTUBE_API_KEY",
        r"YOUTUBE_CLIENT_ID",
        r"YOUTUBE_CLIENT_SECRET",
        r"www\.youtube\.com\/api",
    ],
    "notion": [
        r"import notion",
        r"from notion",
        r"import notion_client",
        r"from notion_client",
        r"require\(['\"]@notionhq\/client['\"]\)",
        r"@notionhq/client",
        r"notion_client",
        r"NotionClient",
        r"new Client\(\s*\{\s*auth:",
        r"NOTION_API_KEY",
        r"NOTION_SECRET",
        r"NOTION_TOKEN",
        r"api\.notion\.com",
    ],

    # --- Database ---
    "airtable": [
        r"import pyairtable",
        r"from pyairtable",
        r"require\(['\"]airtable['\"]\)",
        r"import airtable",
        r"from airtable",
        r"Airtable\(",
        r"AIRTABLE_API_KEY",
        r"AIRTABLE_BASE_ID",
        r"AIRTABLE_PAT",
        r"api\.airtable\.com",
    ],
    "mongodb": [
        r"import pymongo",
        r"from pymongo",
        r"require\(['\"]mongodb['\"]\)",
        r"require\(['\"]mongoose['\"]\)",
        r"MongoClient\(",
        r"mongoose\.connect",
        r"mongodb(?:\+srv)?:\/\/",
        r"MONGODB_URI",
        r"MONGODB_URL",
        r"MONGODB_CONNECTION_STRING",
        r"MONGO_URI",
    ],
    "redis": [
        r"import redis",
        r"from redis",
        r"from redis\.asyncio",
        r"require\(['\"]redis['\"]\)",
        r"require\(['\"]ioredis['\"]\)",
        r"ioredis",
        r"Redis\(url=",
        r"redis\.from_url",
        r"REDIS_URL",
        r"REDIS_HOST",
        r"REDIS_PASSWORD",
        r"REDIS_CONNECTION_STRING",
    ],

    # --- Banking / Other ---
    "plaid": [
        r"import plaid",
        r"from plaid",
        r"require\(['\"]plaid['\"]\)",
        r"PlaidApi",
        r"Configuration\(\s*\{\s*host\s*=?\s*plaid",
        r"PLAID_CLIENT_ID",
        r"PLAID_SECRET",
        r"PLAID_ENV",
        r"PLAID_PUBLIC_KEY",
    ],
    "openweather": [
        r"import pyowm",
        r"from pyowm",
        r"require\(['\"]openweather-apis['\"]\)",
        r"import openweather",
        r"from openweather",
        r"OPENWEATHER_API_KEY",
        r"OPENWEATHER_APPID",
        r"api\.openweathermap\.org",
    ],
    "serpapi": [
        r"import serpapi",
        r"from serpapi",
        r"from google_search_results",
        r"require\(['\"]serpapi['\"]\)",
        r"serpapi\.",
        r"SerpApiClient",
        r"SERPAPI_API_KEY",
        r"SERP_API_KEY",
        r"serpapi\.com",
    ],
}

# ---------------------------------------------------------------------------
# Monitoring status (Phase A: detection-only — no monitoring active)
# ---------------------------------------------------------------------------
# Phase B: the 12 providers with reliable official changelog sources are now
# "supported" (monitored). PayPal, AWS, Cloudinary remain "planned" (no
# reliable official source). Phase C/D providers are detection-only ("planned").
MONITORED_APIS: set[str] = {
    "stripe", "shopify", "twilio", "sendgrid", "github",
    "openai", "anthropic", "vercel", "supabase", "firebase",
    "slack", "resend",
}
PLANNED_APIS: set[str] = set(API_SIGNATURES.keys()) - MONITORED_APIS

# Providers that have a curated auto-fix rule set (Phase B+).
# Empty in Phase A — no auto-fix/PR generation.
FIXABLE_APIS: set[str] = set()

# ---------------------------------------------------------------------------
# Per-provider object/resource names for symbol extraction
# Used to tag detections + cross-reference changelog entries (Phase B).
# ---------------------------------------------------------------------------
STRIPE_OBJECTS: list[str] = [
    "PaymentIntent", "SetupIntent", "PaymentMethod", "Charge", "Customer",
    "Subscription", "SubscriptionSchedule", "SubscriptionItem", "Invoice",
    "InvoiceItem", "Source", "Card", "Token", "BankAccount", "Refund", "Payout",
    "Transfer", "Balance", "BalanceTransaction", "Coupon", "PromotionCode",
    "Plan", "Price", "Product", "Checkout", "Session", "Account", "Dispute",
    "Event", "WebhookEndpoint", "Mandate", "Quote", "CreditNote", "TaxRate",
    "TaxId", "Order", "SKU", "Review", "Radar",
]

SHOPIFY_OBJECTS: list[str] = [
    "Product", "ProductVariant", "Variant", "Collection", "CustomCollection",
    "SmartCollection", "Order", "DraftOrder", "Customer", "Fulfillment",
    "FulfillmentOrder", "FulfillmentService", "InventoryItem", "InventoryLevel",
    "Location", "Refund", "Transaction", "Checkout", "Cart", "Webhook",
    "Metafield", "PriceRule", "DiscountCode", "GiftCard", "Payout", "Dispute",
    "Shop", "Theme", "Asset", "ScriptTag", "RecurringApplicationCharge",
    "ApplicationCharge", "UsageCharge", "LineItem", "Image", "Collect",
    "Redirect", "Page", "Blog", "Article", "Comment",
]

TWILIO_OBJECTS: list[str] = [
    "Message", "Call", "Recording", "Transcription", "Conference", "Queue",
    "Participant", "Verification", "VerificationCheck", "Service", "PhoneNumber",
    "IncomingPhoneNumber", "OutgoingCallerId", "Account", "Application",
    "Notification", "Conversation", "Room", "Sync", "SyncList", "SyncMap",
    "Sim", "Fleet", "Fax", "Lookup", "Sender", "BrandRegistration",
    "MessagingService", "Studio", "Flow", "Execution", "Workspace", "Worker",
    "Task", "Activity",
]

SENDGRID_OBJECTS: list[str] = [
    "Mail", "Email", "Personalization", "Content", "Attachment",
    "Contact", "List", "Segment", "Sender", "Template",
    "Suppression", "Block", "Bounce", "SpamReport", "InvalidEmail",
    "UnsubscribeGroup", "ApiKey", "Subuser", "IpAccess", "IpPool",
    "IpWarmup", "DomainAuthentication", "LinkBranding", "ReverseDns",
]

GITHUB_OBJECTS: list[str] = [
    "Repository", "Issue", "PullRequest", "Commit", "Branch", "Tag",
    "Release", "Workflow", "WorkflowRun", "Job", "Step", "Action",
    "Secret", "Variable", "Environment", "Deployment", "DeployKey",
    "Webhook", "Milestone", "Label", "Project", "ProjectCard",
    "Team", "Organization", "User", "App", "Installation", "OAuthApp",
    "GitRef", "GitTree", "GitBlob", "GitCommit", "ContentFile",
]

OPENAI_OBJECTS: list[str] = [
    "ChatCompletion", "Completion", "Embedding", "Image", "Audio",
    "Moderation", "FineTune", "Model", "File", "Deployment",
]

ANTHROPIC_OBJECTS: list[str] = [
    "Message", "Completion", "Model", "ContentBlock", "Usage",
]

PAYPAL_OBJECTS: list[str] = [
    "Order", "Payment", "Capture", "Refund", "Payout", "Subscription",
    "Plan", "Agreement", "Webhook", "Client",
]

RESEND_OBJECTS: list[str] = [
    "Email", "Batch", "Domain", "Apikey",
]

SLACK_OBJECTS: list[str] = [
    "App", "Channel", "Message", "User", "Team", "Webhook",
]

SUPABASE_OBJECTS: list[str] = [
    "Client", "GoTrue", "Postgrest", "Storage", "Realtime",
]

FIREBASE_OBJECTS: list[str] = [
    "App", "Auth", "Firestore", "Database", "Storage", "Messaging",
    "Analytics", "RemoteConfig", "Functions",
]

AWS_OBJECTS: list[str] = [
    "S3", "SQS", "DynamoDB", "Lambda", "CloudWatch", "IAM",
    "EC2", "RDS", "SNS", "SES", "KMS", "SecretsManager",
]

VERCEL_OBJECTS: list[str] = [
    "Deployment", "Project", "Domain", "EnvironmentVariable",
]

CLOUDINARY_OBJECTS: list[str] = [
    "Upload", "Image", "Video", "Transform", "Archive",
]

# --- Phase C object lists ---
GOOGLEAI_OBJECTS: list[str] = [
    "GenerativeModel", "ChatSession", "Content", "Part", "GenerationConfig",
    "SafetySetting", "FunctionDeclaration", "Message", "Embedding",
]

HUGGINGFACE_OBJECTS: list[str] = [
    "InferenceClient", "Pipeline", "Model", "Dataset", "Space",
]

ELEVENLABS_OBJECTS: list[str] = [
    "Voice", "Audio", "TextToSpeech", "VoiceSettings", "History",
]

POSTMARK_OBJECTS: list[str] = [
    "Message", "Email", "Template", "Sender", "Webhook",
]

MAILGUN_OBJECTS: list[str] = [
    "Message", "Domain", "Route", "Webhook", "Suppression",
]

DIGITALOCEAN_OBJECTS: list[str] = [
    "Droplet", "Domain", "Volume", "Kernel", "Image", "Snapshot",
]

SENTRY_OBJECTS: list[str] = [
    "Event", "Issue", "Transaction", "Span", "Breadcrumb", "Exception",
]

AUTH0_OBJECTS: list[str] = [
    "User", "Client", "Connection", "Role", "Token", "Audience",
]

CLERK_OBJECTS: list[str] = [
    "User", "Session", "Organization", "Client", "Token", "Webhook",
]

MAPBOX_OBJECTS: list[str] = [
    "Map", "Marker", "Source", "Layer", "Geocoder", "Directions",
]

ALGOLIA_OBJECTS: list[str] = [
    "Index", "SearchResults", "Hit", "Facet", "Settings", "ApiKey",
]

POSTHOG_OBJECTS: list[str] = [
    "Event", "Capture", "Identify", "Page", "Group", "FeatureFlag",
]

MIXPANEL_OBJECTS: list[str] = [
    "Event", "Track", "Identify", "Alias", "Group", "Profile",
]

SEGMENT_OBJECTS: list[str] = [
    "Event", "Track", "Identify", "Page", "Group", "Alias",
]

INTERCOM_OBJECTS: list[str] = [
    "User", "Conversation", "Message", "Contact", "Company", "Webhook",
]

# --- Phase D object lists ---
DISCORD_OBJECTS: list[str] = [
    "Client", "Guild", "Channel", "Message", "User", "Role", "Embed",
    "Interaction", "SlashCommand", "Webhook", "Member", "VoiceChannel",
]
TELEGRAM_OBJECTS: list[str] = [
    "Message", "User", "Chat", "Update", "Bot", "InlineKeyboard", "CallbackQuery",
    "Sticker", "Document", "Photo",
]
WHATSAPP_OBJECTS: list[str] = [
    "Message", "Contact", "Text", "Media", "Template", "Webhook",
]
TWITTER_OBJECTS: list[str] = [
    "Tweet", "User", "List", "Media", "Poll", "Space", "Follow", "Retweet",
    "Like", "Mention",
]
ZOOM_OBJECTS: list[str] = [
    "Meeting", "User", "Recording", "Webinar", "Participant", "Webhook",
]
PUSHER_OBJECTS: list[str] = [
    "Channel", "Event", "Presence", "Trigger",
]
YOUTUBE_OBJECTS: list[str] = [
    "Video", "Channel", "Playlist", "Comment", "Thumbnail", "LiveBroadcast",
    "Subscription", "SearchResult",
]
NOTION_OBJECTS: list[str] = [
    "Page", "Database", "Block", "User", "Comment", "Property", "Parent",
]
AIRTABLE_OBJECTS: list[str] = [
    "Base", "Table", "Record", "View", "Field", "Attachment",
]
MONGODB_OBJECTS: list[str] = [
    "Collection", "Document", "Database", "ObjectId", "GridFS", "Index",
]
REDIS_OBJECTS: list[str] = [
    "Key", "Hash", "List", "Set", "SortedSet", "Stream", "PubSub",
]
PLAID_OBJECTS: list[str] = [
    "Account", "Transaction", "Item", "LinkToken", "Balance", "Identity",
    "Institution", "Loan",
]
OPENWEATHER_OBJECTS: list[str] = [
    "Current", "Forecast", "OneCall", "Weather", "Alert", "Minutely",
]
SERPAPI_OBJECTS: list[str] = [
    "Search", "Image", "News", "Video", "Maps", "Shopping", "LocalPack",
]

# ---------------------------------------------------------------------------
# Source files we bother scanning
# ---------------------------------------------------------------------------
SCANNABLE_EXTENSIONS: set[str] = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".rb", ".php", ".go",
    ".java", ".cs", ".env", ".example",
}

# File extension -> language name
EXTENSION_LANGUAGE: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".rb": "ruby",
    ".php": "php",
    ".go": "go",
    ".java": "java",
    ".cs": "csharp",
}

# Excluded file/folder patterns (security rules)
EXCLUDED_FILE_PATTERNS: tuple[str, ...] = (
    ".env", ".env.local", ".env.production", ".env.staging",
    ".pem", ".key", "credentials.json", "service-account.json",
    ".env.development", ".env.test",
)

SKIP_DIR_FRAGMENTS: tuple[str, ...] = (
    "node_modules/", "/venv/", "venv/", ".venv/", "/.git/", ".git/",
    "dist/", "build/", ".next/", "out/", "vendor/", "__pycache__/",
    "site-packages/", ".mypy_cache/", ".pytest_cache/", "coverage/",
    ".terraform/", ".serverless/", "functions/",
)


def language_for_path(path: str) -> str | None:
    """Map a file path to a language name, or None if not a known source type."""
    dot = path.rfind(".")
    if dot == -1:
        return None
    return EXTENSION_LANGUAGE.get(path[dot:].lower())


def is_excluded_file(path: str) -> bool:
    """Check if a file should be excluded from scanning (security rules)."""
    lower = path.lower()
    for pattern in EXCLUDED_FILE_PATTERNS:
        if lower.endswith(pattern) or f"/{pattern}" in lower:
            return True
    return False


# ---------------------------------------------------------------------------
# Precompile signatures
# ---------------------------------------------------------------------------
COMPILED_SIGNATURES: dict[str, list[re.Pattern[str]]] = {
    api: [re.compile(p) for p in patterns] for api, patterns in API_SIGNATURES.items()
}

# Per-provider object token lists
_OBJECT_LISTS: dict[str, list[str]] = {
    "stripe": STRIPE_OBJECTS,
    "shopify": SHOPIFY_OBJECTS,
    "twilio": TWILIO_OBJECTS,
    "sendgrid": SENDGRID_OBJECTS,
    "github": GITHUB_OBJECTS,
    "openai": OPENAI_OBJECTS,
    "anthropic": ANTHROPIC_OBJECTS,
    "paypal": PAYPAL_OBJECTS,
    "resend": RESEND_OBJECTS,
    "slack": SLACK_OBJECTS,
    "supabase": SUPABASE_OBJECTS,
    "firebase": FIREBASE_OBJECTS,
    "aws": AWS_OBJECTS,
    "vercel": VERCEL_OBJECTS,
    "cloudinary": CLOUDINARY_OBJECTS,
    # Phase C
    "googleai": GOOGLEAI_OBJECTS,
    "huggingface": HUGGINGFACE_OBJECTS,
    "elevenlabs": ELEVENLABS_OBJECTS,
    "postmark": POSTMARK_OBJECTS,
    "mailgun": MAILGUN_OBJECTS,
    "digitalocean": DIGITALOCEAN_OBJECTS,
    "sentry": SENTRY_OBJECTS,
    "auth0": AUTH0_OBJECTS,
    "clerk": CLERK_OBJECTS,
    "mapbox": MAPBOX_OBJECTS,
    "algolia": ALGOLIA_OBJECTS,
    "posthog": POSTHOG_OBJECTS,
    "mixpanel": MIXPANEL_OBJECTS,
    "segment": SEGMENT_OBJECTS,
    "intercom": INTERCOM_OBJECTS,
    # Phase D
    "discord": DISCORD_OBJECTS,
    "telegram": TELEGRAM_OBJECTS,
    "whatsapp": WHATSAPP_OBJECTS,
    "twitter": TWITTER_OBJECTS,
    "zoom": ZOOM_OBJECTS,
    "pusher": PUSHER_OBJECTS,
    "youtube": YOUTUBE_OBJECTS,
    "notion": NOTION_OBJECTS,
    "airtable": AIRTABLE_OBJECTS,
    "mongodb": MONGODB_OBJECTS,
    "redis": REDIS_OBJECTS,
    "plaid": PLAID_OBJECTS,
    "openweather": OPENWEATHER_OBJECTS,
    "serpapi": SERPAPI_OBJECTS,
}

# Longest-match-first alternation per provider (compiled once)
_OBJECT_RES: dict[str, re.Pattern[str]] = {
    api: re.compile(r"\b(" + "|".join(sorted(objs, key=len, reverse=True)) + r")\b")
    for api, objs in _OBJECT_LISTS.items()
}


def extract_symbols(api_name: str, text: str) -> list[str]:
    """Return lowercased, de-duplicated object tokens for `api_name` in `text`."""
    if not text:
        return []
    regex = _OBJECT_RES.get(api_name)
    if regex is None:
        return []
    found = {m.group(1).lower() for m in regex.finditer(text)}
    return sorted(found)


def extract_stripe_symbols(text: str) -> list[str]:
    """Backward-compatible Stripe-only wrapper around extract_symbols()."""
    return extract_symbols("stripe", text)


def status_for_api(api_name: str) -> str:
    """Return monitoring status for a provider (Phase A: all 'planned')."""
    if api_name in MONITORED_APIS:
        return "monitored"
    if api_name in PLANNED_APIS:
        return "planned"
    return "unsupported"


def get_provider_category(api_name: str) -> str:
    """Return the category for a provider."""
    _CATEGORIES = {
        "stripe": "payment", "shopify": "payment", "paypal": "payment",
        "twilio": "communication", "sendgrid": "communication",
        "resend": "communication", "slack": "communication",
        "openai": "ai", "anthropic": "ai",
        "github": "devtools",
        "supabase": "database",
        "firebase": "cloud", "aws": "cloud", "vercel": "cloud",
        "cloudinary": "media",
        # Phase C
        "googleai": "ai", "huggingface": "ai", "elevenlabs": "ai",
        "postmark": "communication", "mailgun": "communication",
        "digitalocean": "cloud",
        "sentry": "devtools", "auth0": "devtools", "clerk": "devtools",
        "mapbox": "other", "algolia": "devtools",
        "posthog": "analytics", "mixpanel": "analytics",
        "segment": "analytics", "intercom": "analytics",
        # Phase D
        "discord": "communication", "telegram": "communication",
        "whatsapp": "communication", "twitter": "communication",
        "zoom": "communication", "pusher": "communication",
        "youtube": "media",
        "notion": "productivity",
        "airtable": "database", "mongodb": "database", "redis": "database",
        "plaid": "payment",
        "openweather": "other", "serpapi": "other",
    }
    return _CATEGORIES.get(api_name, "other")
