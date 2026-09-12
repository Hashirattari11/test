"""Real provider incident collectors (Runtime Intelligence).

Relocated from the removed API-Intelligence collector set (Session-10):
status-page incidents are runtime monitoring data and remain in the product.

Collectors NEVER return secret values. Each collector is isolated: a failure
raises :class:`CollectorError` and the caller decides how to degrade, so one
broken provider never breaks a scan.
"""
from __future__ import annotations

import datetime as _dt
import xml.etree.ElementTree as ET
from typing import Any

import httpx

from ..db import db

TIMEOUT = httpx.Timeout(10.0, connect=5.0)


class CollectorError(RuntimeError):
    """A single collector failed. Message is user-safe (no secrets)."""


class ProviderPermissionError(CollectorError):
    """The connected credential lacks permission for this metric (e.g. an
    admin/organization-level key is required). Shown honestly in the UI —
    never converted to zero or fabricated data."""


# Statuspage v2 API pages (verified live 2026-09-06).
STATUSPAGE_PAGES: dict[str, str] = {
    "openai": "https://status.openai.com/api/v2/incidents.json?unresolved=true",
    "github": "https://www.githubstatus.com/api/v2/incidents.json?unresolved=true",
    "twilio": "https://status.twilio.com/api/v2/incidents.json?unresolved=true",
    "sendgrid": "https://status.sendgrid.com/api/v2/incidents.json?unresolved=true",
}

# Stripe does not expose the statuspage v2 API; its page links this Atom feed.
STRIPE_RSS_URL = "https://status.stripe.com/current/atom.xml"

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


def _get_json(url: str, token: str | None = None) -> dict[str, Any]:
    headers = {"User-Agent": "AutoFixAPI/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        # follow_redirects is REQUIRED: status.stripe.com 301s to
        # www.stripestatus.com and status.sendgrid.com 302s to Twilio's page
        # (verified live 2026-09-06). Without it both return empty bodies.
        resp = httpx.get(url, headers=headers, timeout=TIMEOUT, follow_redirects=True)
    except httpx.HTTPError as exc:
        raise CollectorError(f"Request failed for {url}: {exc.__class__.__name__}") from exc
    if resp.status_code >= 400:
        if resp.status_code == 403:
            raise ProviderPermissionError(
                f"{url} requires additional provider permissions (HTTP 403)"
            )
        raise CollectorError(f"{url} returned HTTP {resp.status_code}")
    return resp.json()


def _get_text(url: str) -> str:
    try:
        resp = httpx.get(
            url,
            headers={"User-Agent": "AutoFixAPI/1.0"},
            timeout=TIMEOUT,
            follow_redirects=True,
        )
    except httpx.HTTPError as exc:
        raise CollectorError(f"Request failed for {url}: {exc.__class__.__name__}") from exc
    if resp.status_code >= 400:
        raise CollectorError(f"{url} returned HTTP {resp.status_code}")
    return resp.text


# ---------------------------------------------------------------------------
# Statuspage v2 incidents (public, no key needed)
# ---------------------------------------------------------------------------
def collect_statuspage_incidents(provider: str) -> list[dict[str, Any]]:
    url = STATUSPAGE_PAGES.get(provider)
    if not url:
        raise CollectorError(f"No status-page adapter for provider '{provider}'")
    data = _get_json(url)
    incidents: list[dict[str, Any]] = []
    for inc in data.get("incidents") or []:
        incidents.append(
            {
                "provider": provider,
                "external_id": inc.get("id"),
                "title": (inc.get("name") or "Untitled incident")[:500],
                "status": inc.get("status") or "investigating",
                "impact": inc.get("impact"),
                "components": inc.get("components") or [],
                "started_at": inc.get("created_at"),
                "resolved_at": inc.get("resolved_at"),
                "raw_data": inc,
            }
        )
    return incidents


# ---------------------------------------------------------------------------
# Stripe incidents via the page's own Atom feed
# ---------------------------------------------------------------------------
def collect_stripe_incidents() -> list[dict[str, Any]]:
    text = _get_text(STRIPE_RSS_URL)
    incidents: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise CollectorError("Stripe status feed could not be parsed") from exc
    for entry in root.findall("atom:entry", ATOM_NS):
        title_el = entry.find("atom:title", ATOM_NS)
        updated_el = entry.find("atom:updated", ATOM_NS)
        link_el = entry.find("atom:link", ATOM_NS)
        title = (title_el.text if title_el is not None and title_el.text else "Untitled")[:500]
        updated = updated_el.text if updated_el is not None and updated_el.text else None
        incidents.append(
            {
                "provider": "stripe",
                "external_id": updated or title,
                "title": title,
                "status": "reported",
                "impact": None,
                "components": [],
                "started_at": updated,
                "resolved_at": None,
                "raw_data": {
                    "link": link_el.get("href") if link_el is not None else None,
                    "title": title,
                    "updated": updated,
                },
            }
        )
    return incidents


# ---------------------------------------------------------------------------
# Persistence helper (isolated, best-effort)
# ---------------------------------------------------------------------------
def refresh_provider_incidents(provider: str) -> int:
    """Fetch current incidents and upsert into provider_incidents.

    Returns the number of NEW incidents recorded. Raises CollectorError on
    fetch/parse failure; DB write failures are swallowed (caller degrades).
    """
    if provider == "stripe":
        incidents = collect_stripe_incidents()
    else:
        incidents = collect_statuspage_incidents(provider)

    existing = (
        db()
        .table("provider_incidents")
        .select("external_id, id, status, resolved_at")
        .eq("provider", provider)
        .execute()
    ).data or []
    by_ext = {row["external_id"]: row for row in existing if row.get("external_id")}

    new_count = 0
    for inc in incidents:
        ext_id = inc["external_id"]
        row = by_ext.get(ext_id)
        if row is None:
            db().table("provider_incidents").insert(inc).execute()
            new_count += 1
        else:
            changed = (
                row.get("status") != inc["status"]
                or row.get("resolved_at") != inc["resolved_at"]
            )
            if changed:
                db().table("provider_incidents").update(
                    {
                        "status": inc["status"],
                        "resolved_at": inc["resolved_at"],
                        "raw_data": inc["raw_data"],
                    }
                ).eq("id", row["id"]).execute()
    return new_count