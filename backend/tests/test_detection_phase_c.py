"""Unit tests for Phase C detection (15 additional detection-only providers).

Pure detection engine tests — no network/DB needed. Mirrors the Phase A
test_detection.py pattern. Security: only environment variable NAMES and
mock descriptors are used; no secret VALUES ever appear.
"""
from app.detection import scan_file

# Provider ID -> representative code snippet that should trigger detection.
PHASE_C_CASES: dict[str, str] = {
    "googleai": (
        "import google.generativeai as genai\n"
        "model = genai.GenerativeModel('gemini-pro')\n"
        "GOOGLE_API_KEY = 'placeholder'\n"
    ),
    "huggingface": (
        "from huggingface_hub import InferenceClient\n"
        "client = InferenceClient(token=HF_TOKEN)\n"
    ),
    "elevenlabs": (
        "import elevenlabs\n"
        "ELEVENLABS_API_KEY = 'placeholder'\n"
        "audio = elevenlabs.generate(text='hi')\n"
    ),
    "postmark": (
        "import postmark\n"
        "client = postmark.Client(POSTMARK_SERVER_TOKEN)\n"
    ),
    "mailgun": (
        "const mg = require('mailgun-js')({ apiKey: MAILGUN_API_KEY, domain: MAILGUN_DOMAIN });\n"
    ),
    "digitalocean": (
        "const DigitalOcean = require('do-wrapper');\n"
        "const api = new DigitalOcean(DIGITALOCEAN_ACCESS_TOKEN);\n"
    ),
    "sentry": (
        "import * as Sentry from '@sentry/nextjs';\n"
        "Sentry.init({ dsn: SENTRY_DSN });\n"
    ),
    "auth0": (
        "import { Auth0Provider } from '@auth0/auth0-react';\n"
        "AUTH0_CLIENT_ID = 'placeholder'\n"
        "AUTH0_DOMAIN = 'example.auth0.com'\n"
    ),
    "clerk": (
        "import { ClerkProvider } from '@clerk/nextjs';\n"
        "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY = 'placeholder'\n"
    ),
    "mapbox": (
        "import mapboxgl from 'mapbox-gl';\n"
        "mapboxgl.accessToken = MAPBOX_ACCESS_TOKEN;\n"
    ),
    "algolia": (
        "import algoliasearch from 'algoliasearch';\n"
        "const client = algoliasearch(ALGOLIA_APP_ID, ALGOLIA_API_KEY);\n"
    ),
    "posthog": (
        "import posthog from 'posthog-js';\n"
        "posthog.init(NEXT_PUBLIC_POSTHOG_KEY);\n"
    ),
    "mixpanel": (
        "import mixpanel from 'mixpanel-browser';\n"
        "mixpanel.init(MIXPANEL_PROJECT_TOKEN);\n"
    ),
    "segment": (
        "const Analytics = require('@segment/analytics-node');\n"
        "const a = new Analytics({ writeKey: SEGMENT_WRITE_KEY });\n"
    ),
    "intercom": (
        "const intercom = require('intercom-client');\n"
        "const c = new intercom.Client({ token: INTERCOM_ACCESS_TOKEN });\n"
    ),
}


def test_all_phase_c_providers_detected():
    """Each Phase C provider must be detected from its representative snippet."""
    for api_name, code in PHASE_C_CASES.items():
        dets = scan_file("app/example.js", code)
        apis = {d.api_name for d in dets}
        assert api_name in apis, f"{api_name} was not detected:\n{code}"


def test_phase_c_env_var_only_detection():
    """Environment-variable NAME references alone still detect the provider."""
    code = "process.env.SEGMENT_WRITE_KEY\nprocess.env.MIXPANEL_TOKEN\n"
    dets = scan_file("config.js", code)
    apis = {d.api_name for d in dets}
    assert "segment" in apis and "mixpanel" in apis


def test_phase_c_no_false_positive_on_plain_text():
    code = "def compute_threshold(score):\n    return score * 2\n"
    assert scan_file("math.py", code) == []
