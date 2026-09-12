"""Unit tests for Phase D detection (14 additional detection-only providers).

Pure detection engine tests — no network/DB needed. Mirrors the Phase A/C
test_detection.py and test_detection_phase_c.py patterns. Security: only
environment variable NAMES and mock descriptors are used; no secret VALUES
ever appear.
"""
from app.detection import scan_file

# Provider ID -> representative code snippet that should trigger detection.
# Snippets align with the backend signatures in app/signatures.py.
PHASE_D_CASES: dict[str, str] = {
    "discord": (
        "const { Client, GatewayIntentBits } = require('discord.js');\n"
        "const client = new Client({ intents: [GatewayIntentBits.Guilds] });\n"
        "client.login(DISCORD_BOT_TOKEN);\n"
    ),
    "telegram": (
        "const TelegramBot = require('node-telegram-bot-api');\n"
        "const bot = new TelegramBot(TELEGRAM_BOT_TOKEN);\n"
    ),
    "whatsapp": (
        "import WhatsAppCloud from '@whatsapp/cloud-api';\n"
        "WHATSAPP_ACCESS_TOKEN = 'placeholder'\n"
    ),
    "twitter": (
        "import tweepy\n"
        "client = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN)\n"
    ),
    "zoom": (
        "import zoom\n"
        "ZOOM_API_KEY = 'placeholder'\n"
        "ZOOM_API_SECRET = 'placeholder'\n"
    ),
    "pusher": (
        "const Pusher = require('pusher');\n"
        "const p = new Pusher({ appId: PUSHER_APP_ID, key: PUSHER_KEY, secret: PUSHER_SECRET });\n"
    ),
    "youtube": (
        "const { google } = require('@googleapis/youtube');\n"
        "YOUTUBE_API_KEY = 'placeholder'\n"
    ),
    "notion": (
        "const { Client } = require('@notionhq/client');\n"
        "const notion = new Client({ auth: NOTION_API_KEY });\n"
    ),
    "airtable": (
        "import airtable\n"
        "base = airtable.Airtable(AIRTABLE_BASE_ID, AIRTABLE_API_KEY)\n"
    ),
    "mongodb": (
        "import pymongo\n"
        "client = pymongo.MongoClient(MONGODB_URI)\n"
    ),
    "redis": (
        "import redis\n"
        "r = redis.Redis.from_url(REDIS_URL)\n"
    ),
    "plaid": (
        "import plaid\n"
        "PLAID_CLIENT_ID = 'placeholder'\n"
        "PLAID_SECRET = 'placeholder'\n"
    ),
    "openweather": (
        "import pyowm\n"
        "owm = pyowm.OWM(OPENWEATHER_API_KEY)\n"
    ),
    "serpapi": (
        "from serpapi import GoogleSearch\n"
        "results = GoogleSearch({'q': 'pizza', 'api_key': SERPAPI_API_KEY})\n"
    ),
}


def test_all_phase_d_providers_detected():
    """Each Phase D provider must be detected from its representative snippet."""
    for api_name, code in PHASE_D_CASES.items():
        dets = scan_file("app/example.js", code)
        apis = {d.api_name for d in dets}
        assert api_name in apis, f"{api_name} was not detected:\n{code}"


def test_phase_d_env_var_only_detection():
    """Environment-variable NAME references alone still detect the provider."""
    code = (
        "process.env.MONGODB_URI\n"
        "process.env.REDIS_URL\n"
        "process.env.NOTION_API_KEY\n"
        "process.env.SERPAPI_API_KEY\n"
    )
    dets = scan_file("config.js", code)
    apis = {d.api_name for d in dets}
    assert "mongodb" in apis and "redis" in apis
    assert "notion" in apis and "serpapi" in apis


def test_phase_d_no_false_positive_on_plain_text():
    code = "def compute_threshold(score):\n    return score * 2\n"
    assert scan_file("math.py", code) == []
