"""Offline tests for the API Reliability & Health Intelligence system.

Run with:  python -m pytest tests/test_health_intelligence.py -q
No network, no database, no real credentials — pure logic with mocks.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.health.provider_capabilities import PROVIDERS, Capability  # noqa: E402
from app.health.engine import HealthCheckResult, HealthEngine, DEFAULT_WEIGHTS  # noqa: E402
from app.health.issues import (  # noqa: E402
    IssueCategory,
    IssueSeverity,
    IssueSource,
    IssueStatus,
    ReliabilityIssue,
)
from app.health.risk import RiskEngine  # noqa: E402
from app.health.redact import contains_secret_like, redact  # noqa: E402
from app.health.bridge import issue_from_finding  # noqa: E402
from app.health.collectors import rate_limit_status  # noqa: E402


# ---------------------------------------------------------------------------
# 1. Provider capability matrix
# ---------------------------------------------------------------------------
def test_provider_registry_major_providers():
    for name in ("stripe", "openai", "anthropic", "github", "twilio", "sendgrid", "vercel", "supabase"):
        assert name in PROVIDERS, f"missing provider {name}"
        assert PROVIDERS[name].provider_id == name


def test_no_fake_usage_data_for_unsupported_providers():
    # Supabase only offers dashboard-based usage — quota/usage monitoring must
    # be explicitly unsupported (never fabricate numbers).
    assert not PROVIDERS["supabase"].has(Capability.USAGE_MONITORING)
    assert not PROVIDERS["supabase"].has(Capability.QUOTA_MONITORING)
    assert PROVIDERS["supabase"].has(Capability.CHANGELOG_MONITORING)


def test_stripe_capabilities():
    p = PROVIDERS["stripe"]
    for cap in (Capability.CHANGELOG_MONITORING, Capability.CODE_DETECTION,
                Capability.USAGE_MONITORING, Capability.RATE_LIMIT_MONITORING,
                Capability.INCIDENT_MONITORING, Capability.AUTO_FIX):
        assert p.has(cap), f"stripe should support {cap.value}"


# ---------------------------------------------------------------------------
# 2. Health engine scoring
# ---------------------------------------------------------------------------
def test_engine_all_healthy_is_100():
    engine = HealthEngine(PROVIDERS["stripe"])
    for ct in DEFAULT_WEIGHTS:
        engine.add_check(HealthCheckResult(
            check_type=ct, status="healthy", score=100, severity="info",
            message="ok", source="test", timestamp="",
        ))
    score = engine.compute()
    assert score.overall >= 99
    assert score.status == "excellent"


def test_engine_critical_breaking_change_drops_score():
    engine = HealthEngine(PROVIDERS["stripe"])
    # Breaking changes must be added first (engine keeps first check per type).
    engine.add_check(HealthCheckResult(
        check_type="breaking_changes", status="critical", score=30, severity="critical",
        message="breaking", source="scan", timestamp="",
    ))
    for ct in DEFAULT_WEIGHTS:
        if ct == "breaking_changes":
            continue
        engine.add_check(HealthCheckResult(
            check_type=ct, status="healthy", score=100, severity="info",
            message="ok", source="test", timestamp="",
        ))
    score = engine.compute()
    assert score.overall < 95  # critical breaking change must dent the score
    assert score.breakdown.get("breaking_changes", 0) < 15  # weighted contribution reduced


def test_missing_check_is_neutral_not_penalized():
    # A provider with only SOME checks should not be punished for missing data.
    engine = HealthEngine(PROVIDERS["vercel"])
    engine.add_check(HealthCheckResult(
        check_type="breaking_changes", status="healthy", score=100, severity="info",
        message="none", source="scan", timestamp="",
    ))
    score = engine.compute()
    assert 0 < score.overall <= 100


# ---------------------------------------------------------------------------
# 3. Unified issue model + dedup
# ---------------------------------------------------------------------------
def test_issue_hash_is_deterministic_and_distinct():
    a = ReliabilityIssue(provider="stripe", repository="r", category=IssueCategory.PROVIDER_PROBLEM,
                         title="T", file="f.py", line=1)
    b = ReliabilityIssue(provider="stripe", repository="r", category=IssueCategory.PROVIDER_PROBLEM,
                         title="T", file="f.py", line=1)
    c = ReliabilityIssue(provider="stripe", repository="r", category=IssueCategory.PROVIDER_PROBLEM,
                         title="T", file="f.py", line=2)
    assert a.compute_hash() == b.compute_hash()
    assert a.compute_hash() != c.compute_hash()


def test_client_friendly_language():
    issue = ReliabilityIssue(
        provider="openai", category=IssueCategory.CUSTOMER_CODE, severity=IssueSeverity.HIGH,
        title="OpenAI issue", description="AST resolver detected deprecated method call",
        recommended_action="Update the integration", auto_fix_available=True,
    )
    friendly = issue.to_client_friendly()
    # Technical jargon replaced with plain language; fix hint present.
    assert "deprecated" not in friendly["what_happened"] or "no longer supported" in friendly["what_happened"]
    assert "automatic fix" in friendly["what_to_do"]


# ---------------------------------------------------------------------------
# 4. Risk engine
# ---------------------------------------------------------------------------
def test_risk_critical_greater_than_medium():
    eng = RiskEngine()
    low = eng.compute(ReliabilityIssue(
        provider="stripe", category=IssueCategory.PROVIDER_PROBLEM,
        severity=IssueSeverity.MEDIUM, title="t", description="d",
    ))
    high = eng.compute(ReliabilityIssue(
        provider="stripe", category=IssueCategory.PROVIDER_PROBLEM,
        severity=IssueSeverity.CRITICAL, title="t", description="d",
    ))
    assert high.level != low.level
    assert high.score > low.score


# ---------------------------------------------------------------------------
# 5. Redaction
# ---------------------------------------------------------------------------
def test_redact_common_secret_formats():
    samples = [
        "key=STRIPE_TEST_KEY",
        "Authorization: Bearer abcdefghijklmnopqrstuvwxyz123456",
        "openai sk-TEST_PLACEHOLDER",
        "github_pat_TEST_PLACEHOLDER",
        "AIzaSyA1234567890abcdefghijklmnop",
        "xoxb-123456789012-123456789012-ABCDefghijkl",
        "AKIA_TEST_PLACEHOLDER",
    ]
    for s in samples:
        out = redact(s)
        assert not contains_secret_like(out), f"still leaked: {out}"
        assert out != s


def test_redact_env_var_assignment():
    out = redact("STRIPE_SECRET_KEY=STRIPE_TEST_KEY")
    assert "sk_live_" not in out
    assert "STRIPE_SECRET_KEY=…REDACTED…" in out


def test_redact_leaves_plain_text_alone():
    out = redact("The integration uses STRIPE_SECRET_KEY as an env var name.")
    assert "STRIPE_SECRET_KEY" in out  # NAMES are fine — VALUES are not


def test_redact_empty_and_none():
    assert redact(None) == ""
    assert redact("") == ""


# ---------------------------------------------------------------------------
# 6. Bridge: finding -> issue mapping
# ---------------------------------------------------------------------------
def test_baseline_usage_finding_is_not_an_issue():
    f = {"provider": "stripe", "type": "api_usage", "file": "a.py", "line": 5,
         "message": "Detected usage", "severity": "low"}
    assert issue_from_finding(f, "repo") is None  # noise filtered


def test_rule_matched_finding_becomes_issue_with_autofix():
    f = {"provider": "openai", "type": "breaking_change", "rule_id": "openai-legacy-completions",
         "file": "svc.py", "line": 84, "severity": "critical", "confidence": 0.95,
         "message": "legacy completions", "current_usage": "openai.Completion.create("}
    issue = issue_from_finding(f, "repo")
    assert issue is not None
    assert issue.category in (IssueCategory.PROVIDER_PROBLEM, IssueCategory.CUSTOMER_CODE)
    assert issue.auto_fix_available is True
    assert issue.auto_fix_rule_id == "openai-legacy-completions"
    assert issue.file == "svc.py"


def test_secret_leak_finding_maps_to_configuration():
    f = {"provider": "github", "type": "breaking_change", "change_type": "secret_leak",
         "file": "x.py", "line": 1, "severity": "critical", "confidence": 0.9,
         "message": "secret", "current_usage": "STRIPE_SECRET_KEY=STRIPE_TEST_KEY"}
    issue = issue_from_finding(f, "repo")
    assert issue is not None
    assert issue.category == IssueCategory.CONFIGURATION
    # Evidence is redacted before display.
    assert "sk_live_" not in issue.to_client_friendly()["evidence"]


# ---------------------------------------------------------------------------
# 7. Quota forecasting (deterministic, never fabricated)
# ---------------------------------------------------------------------------
# 7. Rate-limit status aggregate (runtime; forecast/quota removed in Session-10)
# ---------------------------------------------------------------------------
def _snap(day: int, used: float, limit: float = 1000.0) -> dict:
    return {
        "used": used,
        "limit_value": limit,
        "recorded_at": f"2026-08-{day:02d}T00:00:00+00:00",
    }


def test_rate_limit_status_uses_newest():
    rows = [
        {"limit_value": 500, "remaining": 100, "recorded_at": "2026-08-01T00:00:00+00:00"},
        {"limit_value": 500, "remaining": 200, "recorded_at": "2026-08-02T00:00:00+00:00"},
    ]
    st = rate_limit_status(rows)
    assert st is not None
    assert st["remaining"] == 200
    assert st["used"] == 300
    assert st["pct_used"] == 60.0
    assert st["level"] == "ok"
    assert "60.0% used" in st["message"]


def test_rate_limit_status_level_thresholds():
    # >= 70 => warning, >= 90 => critical, missing numbers => unknown
    warn = rate_limit_status([{"limit_value": 100, "remaining": 20, "recorded_at": "2026-08-01T00:00:00+00:00"}])
    crit = rate_limit_status([{"limit_value": 100, "remaining": 5, "recorded_at": "2026-08-01T00:00:00+00:00"}])
    unknown = rate_limit_status([{"limit_value": None, "remaining": None, "recorded_at": "2026-08-01T00:00:00+00:00"}])
    assert warn is not None and warn["level"] == "warning"
    assert crit is not None and crit["level"] == "critical"
    assert unknown is not None and unknown["level"] == "unknown"


# ---------------------------------------------------------------------------
# 8. Production-aware risk (wiring used by the API)
# ---------------------------------------------------------------------------
def test_risk_production_aware_priority():
    eng = RiskEngine()
    base = dict(provider="stripe", category=IssueCategory.PROVIDER_PROBLEM,
                severity=IssueSeverity.HIGH, title="t", description="d")
    prod = eng.compute(ReliabilityIssue(**base, repository="r"), is_production=True)
    dev = eng.compute(ReliabilityIssue(**base, repository="r"), is_production=False)
    assert prod.score >= dev.score
    assert prod.level in ("critical", "high")


def test_from_row_tolerates_bad_enum_values():
    row = {"provider": "stripe", "category": "not-a-category", "severity": None,
           "title": "x", "description": "y"}
    issue = ReliabilityIssue.from_row(row)
    assert issue.category == IssueCategory.UNKNOWN
    assert issue.severity == IssueSeverity.MEDIUM
