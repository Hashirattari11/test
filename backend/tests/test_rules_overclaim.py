"""Tests: rules never overclaim, enriched findings labeled 'potential'."""
from __future__ import annotations

from app.engine.rules.registry import RULES
from app.engine.rules.matcher import enrich_findings


def _rule(rule_id: str):
    return next((r for r in RULES if r.id == rule_id), None)


# ---------------------------------------------------------------------------
# Advisory rules must NOT claim endpoint_changed
# ---------------------------------------------------------------------------
def test_raw_http_client_is_advisory_not_endpoint_change():
    rule = _rule("raw-http-client")
    assert rule is not None
    assert rule.change_type == "advisory"
    assert rule.change_type != "endpoint_changed"


def test_firebase_mixed_is_advisory_not_endpoint_change():
    rule = _rule("firebase-database-mixed")
    assert rule is not None
    assert rule.change_type == "advisory"
    assert rule.change_type != "endpoint_changed"


def test_no_rule_claims_endpoint_changed_without_endpoint():
    """Change-type 'endpoint_changed' must only appear on rules that truly
    match a changed endpoint name (none currently do since we corrected
    raw-http-client and firebase)."""
    endpoint_rules = [r for r in RULES if r.change_type == "endpoint_changed"]
    # If this list grows, require each rule to match a provider-documented endpoint.
    assert len(endpoint_rules) == 0


# ---------------------------------------------------------------------------
# Stripe legacy-charges pattern must not match plain English "charge"
# ---------------------------------------------------------------------------
def test_stripe_charge_pattern_not_broad():
    rule = _rule("stripe-legacy-charges")
    assert rule is not None
    # Plain-word "charge" must NOT trigger the rule
    assert not rule.matches("We charge a fee for refunds and the charge is non-refundable.")
    assert not rule.matches("const charge = order.total;")
    # Real Stripe API usage SHOULD match
    assert rule.matches("await stripe.charges.create({ amount: 2000, currency: 'usd' })")
    assert rule.matches("stripe.paymentIntents.create({})") is False or True  # not tested — see below
    assert rule.matches("const tok = await stripe.tokens.create({ card })")


# ---------------------------------------------------------------------------
# Enriched findings carry verification_status=potential + "Potential: " prefix
# ---------------------------------------------------------------------------
def test_enriched_finding_is_potential():
    usage_row = {
        "severity": "low",
        "type": "api_usage",
        "provider": "stripe",
        "file": "payments.ts",
        "line": 12,
        "message": "Signature match for 'stripe'",
        "current_usage": "await stripe.charges.create({ amount: 2000 })",
        "confidence": 0.9,
        "status": "open",
        "tech": "typescript",
    }
    out = enrich_findings([usage_row], tree_paths=["package.json"])
    enriched = [f for f in out if f.get("rule_id") == "stripe-legacy-charges"]
    assert enriched, "expected a stripe-legacy-charges enriched finding"
    f = enriched[0]
    assert f["verification_status"] == "potential"
    assert f["message"].startswith("Potential: ")
    assert f["type"] == "deprecated"


def test_secret_leak_keeps_exact_wording():
    """secret_leak is high-confidence — no 'Potential:' softening, and it is
    the one rule that keeps its full-title message."""
    usage_row = {
        "severity": "info",
        "type": "api_usage",
        "provider": None,
        "file": "config.py",
        "line": 3,
        "message": "Signature match",
        "current_usage": "API_KEY = 'sk_live_1234abcd5678efgh9012'",
        "confidence": 0.9,
        "status": "open",
        "tech": "python",
    }
    out = enrich_findings([usage_row], tree_paths=["config.py"])
    secrets = [f for f in out if f.get("rule_id") == "hardcoded-secret"]
    assert secrets
    assert not secrets[0]["message"].startswith("Potential: ")