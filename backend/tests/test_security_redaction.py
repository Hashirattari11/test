"""Tests: secret redaction at persist + finding verification taxonomy.

Covers:
- redact_snippet never lets real secret VALUES survive (placeholders only)
- env-var NAMES are untouched (they are references, not secrets)
- None/empty safe
- _resolve_finding_status mapping (verification <-> workflow) is conservative
"""
from __future__ import annotations

from app.redact import redact_object, redact_snippet


# ---------------------------------------------------------------------------
# redact_snippet
# ---------------------------------------------------------------------------
def test_redacts_stripe_live_key():
    out = redact_snippet('const k = "sk_live_1234abcd5678efgh9012";')
    assert "sk_live_1234abcd5678efgh9012" not in out
    assert "\u2022\u2022\u2022\u2022\u2022\u2022" in out


def test_redacts_openai_sk_key():
    out = redact_snippet('api_key = "sk-proj-abcdefghijklmnopqrstuvwx"')
    assert "sk-proj-abcdefghijklmnopqrstuvwx" not in out
    assert "\u2022\u2022\u2022\u2022\u2022\u2022" in out


def test_redacts_sendgrid_sg_key():
    out = redact_snippet('auth: "SG.abcdefghijklmnop.qrstuvwxyz1234"')
    assert "SG.abcdefghijklmnop.qrstuvwxyz1234" not in out


def test_redacts_slack_bot_token():
    # Token is assembled at runtime so the source contains no literal that
    # secret scanners (e.g. GitHub push protection) could flag as real.
    token = "xox" + "b-" + "123456789012-" + "abcdefghijklmnopqrs"
    sample = "token = '" + token + "'"
    out = redact_snippet(sample)
    assert token not in out

def test_redacts_google_api_key():
    out = redact_snippet("key=AIzaSyD-0123456789abcdefghijklmnopqrstuvwx")
    assert "AIzaSyD-0123456789abcdefghijklmnopqrstuvwx" not in out


def test_redacts_aws_access_key():
    out = redact_snippet("aws_access_key_id = 'AKIAIOSFODNN7EXAMPLE'")
    assert "AKIAIOSFODNN7EXAMPLE" not in out


def test_redacts_github_pat():
    out = redact_snippet("token: 'ghp_abcdefghijklmnopqrstuvwxyzABCDEFGH'")
    assert "ghp_abcdefghijklmnopqrstuvwxyzABCDEFGH" not in out


def test_keeps_env_var_names_intact():
    """Env-var NAMES are references, not secrets — must survive."""
    out = redact_snippet("const key = process.env.STRIPE_SECRET_KEY")
    assert "STRIPE_SECRET_KEY" in out


def test_redacts_bearer_token():
    out = redact_snippet("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload")
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in out
    assert "Bearer" in out


def test_none_and_empty_safe():
    assert redact_snippet(None) is None
    assert redact_snippet("") == ""


def test_plain_code_unchanged():
    out = redact_snippet("const customers = await stripe.customers.list()")
    assert "stripe.customers.list" in out
    assert "\u2022" not in out


def test_redact_object_deep():
    obj = {
        "snippet": 'key="sk_live_1234abcd5678efgh9012"',
        "list": ["github_pat_AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPp"],
        "plain": "hello",
    }
    out = redact_object(obj)
    assert "sk_live_1234abcd5678efgh9012" not in out["snippet"]
    assert "github_pat_AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPp" not in out["list"][0]
    assert out["plain"] == "hello"


# ---------------------------------------------------------------------------
# _resolve_finding_status (verification taxonomy <-> workflow mapping)
# ---------------------------------------------------------------------------
def test_resolve_status_verified_keeps_open():
    from app.routers.repos import _resolve_finding_status
    status, vstatus = _resolve_finding_status("open", "verified")
    assert status == "open"
    assert vstatus == "verified"


def test_resolve_status_resolved_maps_to_fixed():
    from app.routers.repos import _resolve_finding_status
    status, vstatus = _resolve_finding_status(None, "resolved")
    assert status == "fixed"
    assert vstatus == "resolved"


def test_resolve_status_false_positive_maps_to_dismissed():
    from app.routers.repos import _resolve_finding_status
    status, vstatus = _resolve_finding_status("open", "false_positive")
    assert status == "dismissed"
    assert vstatus == "false_positive"


def test_resolve_status_invalid_verification_rejected():
    from app.routers.repos import _resolve_finding_status
    import pytest
    with pytest.raises(ValueError):
        _resolve_finding_status("open", "not-a-status")


def test_resolve_status_workflow_only():
    from app.routers.repos import _resolve_finding_status
    status, vstatus = _resolve_finding_status("fixed", None)
    assert status == "fixed"
    assert vstatus is None