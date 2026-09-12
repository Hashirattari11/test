"""Slack integration (Phase 5, Section 2).

Mirrors alert/fix-created notifications into a customer's Slack workspace and
lets them approve fixes from Slack.

Design:
  * `slack_connections` table stores one optional connection per user (bot
    token + channel). The bot token is encrypted at rest like GitHub tokens.
  * OAuth install flow: user visits Slack's install URL, Slack redirects to our
    callback with a `code`; we exchange it for a bot token + the app's channel.
  * Alert engine and the fix-created notifier both call `post_alert_to_slack`
    / `post_fix_to_slack` when a connection exists — in addition to email.
  * Slack interactive button ("Approve Fix") posts back to us; we verify the
    signature, look up the fix, and reuse the same approve logic as the
    dashboard (`POST /repos/{repo_id}/fixes/{fix_id}/approve`).

All reads/writes go through the server-side service role (like the rest of the
backend) — no direct client access, so RLS is not a concern here.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time

import httpx

from .config import settings
from .crypto import get_cipher
from .db import db

SLACK_TOKEN_URL = "https://slack.com/api/oauth.v2.access"
SLACK_POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"
SLACK_CONVERSATIONS_LIST_URL = "https://slack.com/api/conversations.list"

_TIMEOUT = httpx.Timeout(15.0)


class SlackError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# storage
# ---------------------------------------------------------------------------
def get_connection(user_id: str) -> dict | None:
    res = (
        db().table("slack_connections").select("*").eq("user_id", user_id).limit(1).execute()
    )
    if not res.data:
        return None
    conn = res.data[0]
    # Decrypt the stored bot token for outbound calls.
    conn["_bot_token"] = get_cipher().decrypt(conn["access_token"])
    return conn


def _decrypt_token(conn: dict) -> str:
    return get_cipher().decrypt(conn["access_token"])


# ---------------------------------------------------------------------------
# OAuth install flow
# ---------------------------------------------------------------------------
def build_install_url(redirect_uri: str | None = None) -> str:
    if not settings.slack_client_id:
        raise SlackError("Slack is not configured on the server.")
    scope = settings.slack_bot_scopes
    url = (
        "https://slack.com/oauth/v2/authorize"
        f"?client_id={settings.slack_client_id}"
        f"&scope={scope}"
        "&user_scope=identity.basic"
    )
    if redirect_uri:
        url += f"&redirect_uri={redirect_uri}"
    return url


def get_install_url_absolute(tok_user_id: str | None = None, state: str = "") -> str:
    """Return the install URL. `state` can carry e.g. the session JWT so the
    callback knows who to associate the connection with."""
    url = build_install_url()
    if state:
        url += f"&state={state}"
    return url


def exchange_install_code(code: str, redirect_uri: str | None = None) -> dict:
    """Exchange the OAuth install code for a bot token + channel info."""
    if not settings.slack_client_id or not settings.slack_client_secret:
        raise SlackError("Slack is not configured on the server.")
    payload = {
        "client_id": settings.slack_client_id,
        "client_secret": settings.slack_client_secret,
        "code": code,
    }
    if redirect_uri:
        payload["redirect_uri"] = redirect_uri

    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.post(SLACK_TOKEN_URL, data=payload)
    if resp.status_code != 200:
        raise SlackError(f"Slack OAuth failed ({resp.status_code}): {resp.text}")

    data = resp.json()
    if not data.get("ok"):
        raise SlackError(f"Slack OAuth error: {data.get('error')}")
    if not data.get("access_token"):
        raise SlackError("Slack OAuth returned no bot token.")

    team = data.get("team") or {}
    channel = data.get("incoming_webhook") or {}
    return {
        "access_token": data["access_token"],
        "team_id": team.get("id") or data.get("team_id", ""),
        "team_name": team.get("name") or "",
        "channel_id": channel.get("channel_id") or data.get("channel_id", ""),
        "channel_name": channel.get("channel") or data.get("channel_name", ""),
    }


def save_connection(
    user_id: str,
    access_token: str,
    team_id: str,
    team_name: str,
    channel_id: str,
    channel_name: str,
) -> dict:
    """Upsert the user's Slack connection (one per user)."""
    row = {
        "user_id": user_id,
        "access_token": get_cipher().encrypt(access_token),
        "slack_team_id": team_id,
        "slack_team_name": team_name,
        "slack_channel_id": channel_id,
        "slack_channel_name": channel_name,
    }
    # Delete any existing so we never end up with multiple rows for a user.
    db().table("slack_connections").delete().eq("user_id", user_id).execute()
    res = (
        db().table("slack_connections").insert(row).execute()
    )
    if not res.data:
        raise SlackError("Failed to save Slack connection")
    return res.data[0]


def disconnect(user_id: str) -> None:
    db().table("slack_connections").delete().eq("user_id", user_id).execute()


# ---------------------------------------------------------------------------
# posting
# ---------------------------------------------------------------------------
def _post(token: str, channel_id: str, text: str, blocks: list | None = None) -> None:
    payload: dict = {"channel": channel_id, "text": text}
    if blocks:
        payload["blocks"] = blocks
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.post(
            SLACK_POST_MESSAGE_URL,
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
    if resp.status_code != 200:
        raise SlackError(f"Slack post failed ({resp.status_code}): {resp.text}")
    data = resp.json()
    if not data.get("ok"):
        raise SlackError(f"Slack post error: {data.get('error')}")


def post_alert_to_slack(
    conn: dict,
    *,
    api_name: str,
    repo_name: str,
    change_type: str,
    description: str,
    source_url: str | None,
    severity: str = "medium",
) -> None:
    token = _decrypt_token(conn)
    label = severity.capitalize()
    text = (
        f"`[{label}]` {api_name.capitalize()} API change may affect *{repo_name}* "
        f"({change_type.replace('_', ' ')}).\n{description}"
    )
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": text}},
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Severity: *{label}* · {source_url or 'No link'}",
                }
            ],
        },
    ]
    _post(token, conn["slack_channel_id"], text, blocks)


def post_fix_to_slack(
    conn: dict,
    *,
    repo_name: str,
    rule_title: str,
    file_path: str,
    fix_id: str,
    repo_id: str,
    pr_url: str | None = None,
) -> None:
    token = _decrypt_token(conn)
    text = (
        f"A fix for *{repo_name}* is ready: *{rule_title}*\n"
        f"`{file_path}`"
        + (f"\nPR: {pr_url}" if pr_url else "\nReview it to open a PR.")
    )
    blocks: list[dict] = [
        {"type": "section", "text": {"type": "mrkdwn", "text": text}},
    ]
    if not pr_url:
        # Include an interactive Approve button (payload routed to interactions).
        blocks.append(
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Approve Fix"},
                        "action_id": "approve_fix",
                        "value": f"{repo_id}:{fix_id}",
                    }
                ],
            }
        )
    _post(token, conn["slack_channel_id"], text, blocks)


# ---------------------------------------------------------------------------
# interactions (verify + parse the interactive button payload)
# ---------------------------------------------------------------------------
def verify_slack_signature(headers: dict, raw_body: bytes) -> bool:
    """Verify the X-Slack-Signature (HMAC-SHA256) of an interaction payload."""
    secret = settings.slack_signing_secret
    if not secret:
        return False
    timestamp = headers.get("x-slack-request-timestamp", headers.get("X-Slack-Request-Timestamp", ""))
    signature = headers.get("x-slack-signature", headers.get("X-Slack-Signature", ""))
    # Reject if the timestamp is older than 5 minutes (replay protection).
    if not timestamp.isdigit() or abs(int(time.time()) - int(timestamp)) > 300:
        return False
    base = f"v0:{timestamp}:{raw_body.decode('utf-8', 'replace')}"
    expected = "v0=" + hmac.new(
        secret.encode(), base.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def parse_interaction(raw_body_bytes: bytes) -> dict:
    """Parse a Slack interactive payload. Returns the JSON payload dict."""
    text = raw_body_bytes.decode("utf-8", "replace")
    # Interactions come URL-encoded: payload=<json>
    if text.startswith("payload="):
        import urllib.parse
        text = urllib.parse.unquote(text[len("payload="):])
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise SlackError(f"Invalid interaction payload: {exc}")
