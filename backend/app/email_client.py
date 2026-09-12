"""Email transport via the Resend REST API (no SDK, free tier: 100/day).

Kept to a single responsibility: send an email, report success/failure.
"""
from __future__ import annotations

import requests

from .config import settings

RESEND_ENDPOINT = "https://api.resend.com/emails"


def send_email(to: str, subject: str, html: str, text: str) -> tuple[bool, str]:
    """Send one email. Returns (ok, detail)."""
    if not settings.resend_api_key:
        return False, "RESEND_API_KEY not configured"
    try:
        resp = requests.post(
            RESEND_ENDPOINT,
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": settings.resend_from_email,
                "to": [to],
                "subject": subject,
                "html": html,
                "text": text,
            },
            timeout=20,
        )
    except requests.RequestException as exc:
        return False, f"request error: {exc}"
    if resp.status_code in (200, 201):
        return True, resp.json().get("id", "sent")
    return False, f"{resp.status_code}: {resp.text[:300]}"
