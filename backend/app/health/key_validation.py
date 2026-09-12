"""Real per-provider API-key validation.

Every probe calls the provider's REAL endpoint with the provided key
(8s timeout, no secrets logged — never echo the key). 2xx => valid;
401/403 => invalid key; any other outcome => honest reason.

Used by:
  1. POST /health/provider-connections  — a bad key is NEVER stored.
  2. POST /health/provider-connections/{provider}/test  — "Test Connection".
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable

_TIMEOUT = 8
_PROBES: dict[str, Callable[[str], tuple[bool, str]]] = {}


def _probe(provider: str):
    def deco(fn: Callable[[str], tuple[bool, str]]) -> Callable[[str], tuple[bool, str]]:
        _PROBES[provider] = fn
        return fn
    return deco


def _check(url: str, headers: dict[str, str], provider: str) -> tuple[bool, str]:
    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return True, f"{provider} accepted the key (HTTP {resp.status})"
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            return False, f"{provider} rejected the key (HTTP {exc.code} {exc.reason})"
        return False, f"{provider} returned HTTP {exc.code} {exc.reason}"
    except urllib.error.URLError as exc:
        return False, f"{provider} unreachable ({exc.reason})"
    except TimeoutError:
        return False, f"{provider} timed out after {_TIMEOUT}s"
    except Exception as exc:  # pragma: no cover - defensive
        return False, f"{provider} validation error ({type(exc).__name__})"


@_probe("openai")
def _openai(key: str) -> tuple[bool, str]:
    return _check(
        "https://api.openai.com/v1/models",
        {"Authorization": f"Bearer {key}"},
        "openai",
    )


@_probe("github")
def _github(key: str) -> tuple[bool, str]:
    return _check(
        "https://api.github.com/user",
        {
            "Authorization": f"Bearer {key}",
            "User-Agent": "autofix-health",
            "Accept": "application/vnd.github+json",
        },
        "github",
    )


@_probe("anthropic")
def _anthropic(key: str) -> tuple[bool, str]:
    return _check(
        "https://api.anthropic.com/v1/models",
        {"x-api-key": key, "anthropic-version": "2023-06-01"},
        "anthropic",
    )


@_probe("stripe")
def _stripe(key: str) -> tuple[bool, str]:
    return _check(
        "https://api.stripe.com/v1/balance",
        {"Authorization": f"Bearer {key}"},
        "stripe",
    )


@_probe("sendgrid")
def _sendgrid(key: str) -> tuple[bool, str]:
    return _check(
        "https://api.sendgrid.com/v3/scopes",
        {"Authorization": f"Bearer {key}"},
        "sendgrid",
    )


@_probe("twilio")
def _twilio(key: str) -> tuple[bool, str]:
    if ":" not in key:
        return False, "twilio requires an Account SID and Auth Token as sid:auth_token"
    sid, tok = key.split(":", 1)
    if not sid or not tok:
        return False, "twilio requires a non-empty Account SID and Auth Token"
    basic = base64.b64encode(f"{sid}:{tok}".encode()).decode()
    return _check(
        "https://api.twilio.com/2010-04-01/Accounts.json",
        {"Authorization": f"Basic {basic}"},
        "twilio",
    )


def _post_json(url: str, headers: dict[str, str], body: str, provider: str,
               ok_codes: tuple[int, ...] = (200,)) -> tuple[bool, str]:
    """POST a form/JSON body and treat 2xx (or explicit ok_codes) as valid."""
    try:
        req = urllib.request.Request(url, data=body.encode(), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return True, f"{provider} accepted the credential (HTTP {resp.status})"
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            return False, f"{provider} rejected the credential (HTTP {exc.code} {exc.reason})"
        if exc.code in ok_codes:
            return True, f"{provider} accepted the credential (HTTP {exc.code})"
        return False, f"{provider} returned HTTP {exc.code} {exc.reason}"
    except urllib.error.URLError as exc:
        return False, f"{provider} unreachable ({exc.reason})"
    except TimeoutError:
        return False, f"{provider} timed out after {_TIMEOUT}s"
    except Exception as exc:  # pragma: no cover - defensive
        return False, f"{provider} validation error ({type(exc).__name__})"


def _oauth_cc(token_url: str, key: str, provider: str) -> tuple[bool, str]:
    """OAuth2 client-credentials validation (client_id:client_secret)."""
    if ":" not in key:
        return False, f"{provider} requires client_id:client_secret"
    cid, sec = key.split(":", 1)
    if not cid or not sec:
        return False, f"{provider} requires a non-empty client_id and client_secret"
    basic = base64.b64encode(f"{cid}:{sec}".encode()).decode()
    return _post_json(
        token_url,
        {"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"},
        "grant_type=client_credentials",
        provider,
    )


@_probe("stripe")
def _stripe(key: str) -> tuple[bool, str]:
    return _check(
        "https://api.stripe.com/v1/balance",
        {"Authorization": f"Bearer {key}"},
        "stripe",
    )


@_probe("paypal")
def _paypal(key: str) -> tuple[bool, str]:
    return _oauth_cc("https://api-m.paypal.com/v1/oauth2/token", key, "paypal")


@_probe("zoom")
def _zoom(key: str) -> tuple[bool, str]:
    return _oauth_cc("https://zoom.us/oauth/token", key, "zoom")


@_probe("twitter")
def _twitter(key: str) -> tuple[bool, str]:
    return _oauth_cc("https://api.x.com/oauth2/token", key, "twitter")


@_probe("auth0")
def _auth0(key: str) -> tuple[bool, str]:
    parts = key.split(":", 2)
    if len(parts) < 3 or not parts[0]:
        return False, "auth0 requires domain:client_id:client_secret"
    dom, cid, sec = parts[0], parts[1], parts[2]
    basic = base64.b64encode(f"{cid}:{sec}".encode()).decode()
    body = f"grant_type=client_credentials&audience={urllib.parse.quote_plus(f'https://{dom}/api/v2/')}"
    return _post_json(
        f"https://{dom}/oauth/token",
        {"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"},
        body,
        "auth0",
    )


@_probe("plaid")
def _plaid(key: str) -> tuple[bool, str]:
    if ":" not in key:
        return False, "plaid requires client_id:secret (sandbox credentials)"
    cid, sec = key.split(":", 1)
    body = json.dumps({
        "client_id": cid, "secret": sec, "client_name": "AutoFix Provider Health",
        "user": {"client_user_id": "autofix-provider-health"},
        "products": ["auth"], "country_codes": ["US"], "language": "en",
    })
    return _post_json(
        "https://sandbox.plaid.com/link/token/create",
        {"Content-Type": "application/json"},
        body,
        "plaid",
    )


@_probe("cloudinary")
def _cloudinary(key: str) -> tuple[bool, str]:
    parts = key.split(":")
    if len(parts) < 3:
        return False, "cloudinary requires cloud_name:api_key:api_secret"
    cloud, ck, cs = parts[0], parts[1], parts[2]
    basic = base64.b64encode(f"{ck}:{cs}".encode()).decode()
    return _check(
        f"https://api.cloudinary.com/v1_1/{cloud}/usage",
        {"Authorization": f"Basic {basic}"},
        "cloudinary",
    )


@_probe("mailgun")
def _mailgun(key: str) -> tuple[bool, str]:
    parts = key.split(":")
    if len(parts) < 2:
        return False, "mailgun requires api_key:sending_domain"
    apikey = parts[0]
    basic = base64.b64encode(f"api:{apikey}".encode()).decode()
    return _check(
        "https://api.mailgun.net/v3/domains",
        {"Authorization": f"Basic {basic}"},
        "mailgun",
    )


@_probe("postmark")
def _postmark(key: str) -> tuple[bool, str]:
    st = key.split(":", 1)[0]
    if not st:
        return False, "postmark requires a server token (or server_token:account_token)"
    return _check(
        "https://api.postmarkapp.com/server",
        {"X-Postmark-Server-Token": st},
        "postmark",
    )


@_probe("digitalocean")
def _digitalocean(key: str) -> tuple[bool, str]:
    return _check(
        "https://api.digitalocean.com/v2/account",
        {"Authorization": f"Bearer {key}"},
        "digitalocean",
    )


@_probe("huggingface")
def _huggingface(key: str) -> tuple[bool, str]:
    return _check(
        "https://huggingface.co/api/whoami-v2",
        {"Authorization": f"Bearer {key}"},
        "huggingface",
    )


@_probe("elevenlabs")
def _elevenlabs(key: str) -> tuple[bool, str]:
    return _check(
        "https://api.elevenlabs.io/v1/user",
        {"Authorization": f"Bearer {key}"},
        "elevenlabs",
    )


@_probe("sentry")
def _sentry(key: str) -> tuple[bool, str]:
    return _check(
        "https://sentry.io/api/0/organizations/",
        {"Authorization": f"Bearer {key}"},
        "sentry",
    )


@_probe("clerk")
def _clerk(key: str) -> tuple[bool, str]:
    return _check(
        "https://api.clerk.com/v1/instance",
        {"Authorization": f"Bearer {key}"},
        "clerk",
    )


@_probe("intercom")
def _intercom(key: str) -> tuple[bool, str]:
    return _check(
        "https://api.intercom.io/admins",
        {"Authorization": f"Bearer {key}"},
        "intercom",
    )


@_probe("discord")
def _discord(key: str) -> tuple[bool, str]:
    return _check(
        "https://discord.com/api/v10/applications/@me",
        {"Authorization": f"Bearer {key}"},
        "discord",
    )


@_probe("notion")
def _notion(key: str) -> tuple[bool, str]:
    return _check(
        "https://api.notion.com/v1/users/me",
        {"Authorization": f"Bearer {key}", "Notion-Version": "2022-06-28"},
        "notion",
    )


@_probe("airtable")
def _airtable(key: str) -> tuple[bool, str]:
    return _check(
        "https://api.airtable.com/v0/meta/whoami",
        {"Authorization": f"Bearer {key}"},
        "airtable",
    )


@_probe("whatsapp")
def _whatsapp(key: str) -> tuple[bool, str]:
    return _check(
        "https://graph.facebook.com/v19.0/me",
        {"Authorization": f"Bearer {key}"},
        "whatsapp",
    )


@_probe("mapbox")
def _mapbox(key: str) -> tuple[bool, str]:
    return _check(
        f"https://api.mapbox.com/account/whoami?access_token={key}",
        {},
        "mapbox",
    )


@_probe("google_ai")
def _google_ai(key: str) -> tuple[bool, str]:
    return _check(
        f"https://generativelanguage.googleapis.com/v1beta/models?key={key}",
        {},
        "google_ai",
    )


@_probe("youtube")
def _youtube(key: str) -> tuple[bool, str]:
    return _check(
        f"https://www.googleapis.com/youtube/v3/videos?part=id&chart=mostPopular&maxResults=1&key={key}",
        {},
        "youtube",
    )


@_probe("openweather")
def _openweather(key: str) -> tuple[bool, str]:
    return _check(
        f"https://api.openweathermap.org/data/2.5/weather?lat=0&lon=0&appid={key}",
        {},
        "openweather",
    )


@_probe("serpapi")
def _serpapi(key: str) -> tuple[bool, str]:
    return _check(
        f"https://serpapi.com/account?api_key={key}",
        {},
        "serpapi",
    )


@_probe("algolia")
def _algolia(key: str) -> tuple[bool, str]:
    if ":" not in key:
        return False, "algolia requires application_id:api_key"
    app, k = key.split(":", 1)
    # A 404 for a nonexistent index still proves the key authenticated.
    return _post_json(
        f"https://{app}-dsn.algolia.net/1/indexes/__autofix_probe__/query",
        {
            "X-Algolia-Application-Id": app,
            "X-Algolia-API-Key": k,
            "Content-Type": "application/json",
        },
        json.dumps({"query": ""}),
        "algolia",
        ok_codes=(200, 404, 400),
    )


@_probe("posthog")
def _posthog(key: str) -> tuple[bool, str]:
    return _check(
        "https://us.i.posthog.com/api/projects/@current/",
        {"Authorization": f"Bearer {key}"},
        "posthog",
    )


@_probe("mixpanel")
def _mixpanel(key: str) -> tuple[bool, str]:
    basic = base64.b64encode(key.encode()).decode()
    return _check(
        "https://mixpanel.com/api/2.0/annotations",
        {"Authorization": f"Basic {basic}"},
        "mixpanel",
    )


@_probe("telegram")
def _telegram(key: str) -> tuple[bool, str]:
    try:
        req = urllib.request.Request(f"https://api.telegram.org/bot{key}/getMe", method="GET")
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            body = json.loads(resp.read().decode())
            if body.get("ok"):
                return True, f"telegram accepted the bot token (user @{body.get('result', {}).get('username', '?')})"
            return False, f"telegram rejected the bot token ({body.get('description', 'unknown')})"
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            return False, f"telegram rejected the bot token (HTTP {exc.code} {exc.reason})"
        return False, f"telegram returned HTTP {exc.code} {exc.reason}"
    except urllib.error.URLError as exc:
        return False, f"telegram unreachable ({exc.reason})"
    except TimeoutError:
        return False, f"telegram timed out after {_TIMEOUT}s"
    except Exception as exc:  # pragma: no cover - defensive
        return False, f"telegram validation error ({type(exc).__name__})"


@_probe("pusher")
def _pusher(key: str) -> tuple[bool, str]:
    parts = key.split(":")
    if len(parts) < 3:
        return False, "pusher requires app_id:key:secret(:cluster, default mt1)"
    app_id, pkey, secret = parts[0], parts[1], parts[2]
    cluster = parts[3] if len(parts) > 3 else "mt1"
    params = {
        "auth_key": pkey,
        "auth_timestamp": str(int(time.time())),
        "auth_version": "1.0",
    }
    qs = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    path = f"/apps/{app_id}/channels"
    sig = hmac.new(secret.encode(), f"GET\n{path}\n{qs}".encode(), hashlib.sha256).hexdigest()
    return _check(
        f"https://api-{cluster}.pusher.com{path}?{qs}&auth_signature={sig}",
        {},
        "pusher",
    )


@_probe("mongodb")
def _mongodb(key: str) -> tuple[bool, str]:
    """MongoDB Atlas uses HTTP DIGEST auth (not Basic) — use requests."""
    if ":" not in key:
        return False, "mongodb requires Atlas public_key:private_key"
    pub, priv = key.split(":", 1)
    import requests  # local import — requests is a project dependency
    try:
        resp = requests.get(
            "https://cloud.mongodb.com/api/atlas/v1.0/groups",
            auth=requests.auth.HTTPDigestAuth(pub, priv),
            timeout=_TIMEOUT,
        )
        if resp.status_code in (200, 201):
            return True, f"mongodb accepted the Atlas API key (HTTP {resp.status_code})"
        if resp.status_code in (401, 403):
            return False, f"mongodb rejected the Atlas API key (HTTP {resp.status_code})"
        return False, f"mongodb returned HTTP {resp.status_code}"
    except requests.exceptions.Timeout:
        return False, f"mongodb timed out after {_TIMEOUT}s"
    except requests.exceptions.RequestException as exc:
        return False, f"mongodb unreachable ({exc})"
    except Exception as exc:  # pragma: no cover - defensive
        return False, f"mongodb validation error ({type(exc).__name__})"


SUPPORTED: frozenset[str] = frozenset(_PROBES)


def validate_provider_key(provider: str, api_key: str) -> tuple[bool, str]:
    """Validate an API key against the provider's real API. Never logs the key."""
    fn = _PROBES.get((provider or "").strip().lower())
    if fn is None:
        return False, f"Unsupported provider '{provider}'"
    return fn(api_key)