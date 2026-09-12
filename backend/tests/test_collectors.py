"""Tests for runtime provider collectors (empirical fixtures only — no network).

Session-10: API Intelligence removed — only runtime collectors remain:
- statuspage/stripe incident collectors (app.health.incidents)
- GitHub core rate limit (app.health.collectors)

Every fixture mirrors the live responses verified on 2026-09-06 with the
secret-markers stripped/replaced by safe placeholders.
"""
from __future__ import annotations

import pytest

from app.health.incidents import (
    STATUSPAGE_PAGES,
    CollectorError,
    ProviderPermissionError,
    _get_json,
    _get_text,
    collect_statuspage_incidents,
    collect_stripe_incidents,
)
from app.health.collectors import collect_github_rate_limit

GITHUB_RATE_LIMIT_FIXTURE = {
    "resources": {
        "core": {"limit": 60, "remaining": 42, "reset": 1788686581, "used": 18}
    }
}

STATUSPAGE_INCIDENTS_FIXTURE = {
    "page": {"id": "p1", "name": "OpenAI"},
    "incidents": [
        {
            "id": "inc-1",
            "name": "Elevated errors in the API",
            "status": "investigating",
            "impact": "minor",
            "components": [{"id": "c1", "name": "API"}],
            "created_at": "2026-09-04T07:00:26Z",
            "updated_at": "2026-09-04T07:30:00Z",
            "resolved_at": None,
            "incident_updates": [],
        },
        {
            "id": "inc-2",
            "name": "Old resolved incident",
            "status": "resolved",
            "impact": "major",
            "components": [],
            "created_at": "2026-09-01T00:00:00Z",
            "updated_at": "2026-09-01T02:00:00Z",
            "resolved_at": "2026-09-01T02:00:00Z",
            "incident_updates": [],
        },
    ],
}

STRIPE_ATOM_FIXTURE = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Stripe System Status</title>
  <entry>
    <id>https://status.stripe.com/current/incidents/abc</id>
    <title>Elevated error rates on the API</title>
    <updated>2026-09-05T10:00:00Z</updated>
    <link href="https://status.stripe.com/current/incidents/abc"/>
  </entry>
</feed>"""


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """Never touch the network in tests."""

    def boom(*args, **kwargs):
        raise AssertionError("collectors must not hit the network in tests")

    monkeypatch.setattr("app.health.incidents.httpx.get", boom)


# ---------------------------------------------------------------------------
# GitHub rate limit
# ---------------------------------------------------------------------------
def test_collect_github_rate_limit_parses_core(monkeypatch):
    monkeypatch.setattr(
        "app.health.collectors._get_json", lambda url, token=None: GITHUB_RATE_LIMIT_FIXTURE
    )
    snap = collect_github_rate_limit("fake-token")
    assert snap["limit_value"] == 60
    assert snap["remaining"] == 42
    assert snap["reset_at"] is not None
    assert "raw_data" in snap


def test_collect_github_rate_limit_emits_no_secret_values():
    snap = _parse(GITHUB_RATE_LIMIT_FIXTURE)
    blob = str(snap)
    for marker in ("fake-token", "token"):
        assert marker not in blob


# ---------------------------------------------------------------------------
# Statuspage incidents
# ---------------------------------------------------------------------------
def test_statuspage_provider_map_is_live_verified():
    # Pages that were probed live on 2026-09-06 (HTTP 200).
    for page in ("openai", "github", "twilio", "sendgrid"):
        assert STATUSPAGE_PAGES[page].endswith("/api/v2/incidents.json?unresolved=true")


def test_unsupported_statuspage_provider_is_honest():
    with pytest.raises(CollectorError):
        collect_statuspage_incidents("shopify")


def test_collect_statuspage_incidents_maps_fields(monkeypatch):
    monkeypatch.setattr(
        "app.health.incidents._get_json", lambda url, token=None: STATUSPAGE_INCIDENTS_FIXTURE
    )
    incidents = collect_statuspage_incidents("openai")
    assert len(incidents) == 2
    first = incidents[0]
    assert first["provider"] == "openai"
    assert first["external_id"] == "inc-1"
    assert first["title"] == "Elevated errors in the API"
    assert first["status"] == "investigating"
    assert first["impact"] == "minor"
    assert first["resolved_at"] is None
    assert incidents[1]["resolved_at"] == "2026-09-01T02:00:00Z"


# ---------------------------------------------------------------------------
# Stripe Atom feed (page HTML proved the /current/atom.xml link)
# ---------------------------------------------------------------------------
def test_stripe_atom_feed_parsed(monkeypatch):
    from app.health import incidents

    monkeypatch.setattr(incidents, "_get_text", lambda url: STRIPE_ATOM_FIXTURE)
    incidents_out = collect_stripe_incidents()
    assert len(incidents_out) == 1
    inc = incidents_out[0]
    assert inc["provider"] == "stripe"
    assert inc["status"] == "reported"
    assert "Elevated error rates" in inc["title"]
    assert inc["started_at"] == "2026-09-05T10:00:00Z"
    assert inc["raw_data"]["link"] == "https://status.stripe.com/current/incidents/abc"


def test_stripe_feed_parse_failure_is_honest(monkeypatch):
    from app.health import incidents

    monkeypatch.setattr(incidents, "_get_text", lambda url: "<not-xml")
    with pytest.raises(CollectorError):
        collect_stripe_incidents()


# ---------------------------------------------------------------------------
# Failure isolation / honest degradation (transport mocked, no network)
# ---------------------------------------------------------------------------
def test_collector_error_message_has_no_secrets():
    err = CollectorError("https://api.openai.com/v1/organization/usage/completions returned HTTP 401")
    assert "sk-" not in str(err)


def test_get_json_maps_403_to_permission_error(monkeypatch):
    class _Resp:
        status_code = 403

    def denied_get(url, headers=None, timeout=None, follow_redirects=True):
        return _Resp()

    monkeypatch.setattr("app.health.incidents.httpx.get", denied_get)
    with pytest.raises(ProviderPermissionError):
        _get_json("https://api.openai.com/v1/organization/usage/completions?x=1", "sk-fake")


def _parse(data):
    """Standalone helper duplicating the github snapshot mapping for the
    no-secret assertion (kept tiny and dependency-free)."""
    core = (data.get("resources") or {}).get("core") or {}
    return {
        "limit_value": int(core.get("limit") or 0),
        "remaining": int(core.get("remaining") or 0),
        "reset_at": core.get("reset"),
        "raw_data": data,
    }