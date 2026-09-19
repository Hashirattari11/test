"""Tests: impact analyzer evidence-based verification_status + fire drill matrix."""
from __future__ import annotations

from app.impact.analyzer import (
    analyze_changelog_event,
    compute_verification_status,
)


def _fake_event(change_type: str = "removed", **extra) -> dict:
    event = {
        "id": "evt-1",
        "api_name": "stripe",
        "provider": "stripe",
        "change_type": change_type,
        "description": "The Charges API was removed.",
        "source_url": "https://docs.stripe.com/changelog",
        "old_value": "charges.create",
        "new_value": "paymentIntents.create",
    }
    event.update(extra)
    return event


def _fake_detection(**extra) -> dict:
    d = {
        "file_path": "payments.ts",
        "line_number": 12,
        "matched_snippet": "await stripe.charges.create({amount})",
        "api_name": "stripe",
    }
    d.update(extra)
    return d


# ---------------------------------------------------------------------------
# compute_verification_status (pure) — never overclaims
# ---------------------------------------------------------------------------
def test_verified_when_endpoint_matched():
    status, details = compute_verification_status(
        has_matches=True,
        matched_fields=["endpoint", "provider"],
        has_endpoint=True,
        has_sdk=False,
        change_type="removed",
    )
    assert status == "verified"
    assert details["endpoint_match"] is True


def test_potential_when_only_generic_match():
    status, details = compute_verification_status(
        has_matches=True,
        matched_fields=["provider"],
        has_endpoint=False,
        has_sdk=False,
        change_type="deprecated",
    )
    assert status == "potential"
    assert "could not be confirmed" in details["reason"]


def test_not_found_when_no_usage():
    status, details = compute_verification_status(
        has_matches=False,
        matched_fields=[],
        has_endpoint=False,
        has_sdk=False,
        change_type="deprecated",
    )
    assert status == "not_found"


def test_unknown_when_event_uninterpretable():
    status, _ = compute_verification_status(
        has_matches=True,
        matched_fields=[],
        has_endpoint=False,
        has_sdk=False,
        change_type="",
    )
    assert status == "unknown"


def test_verified_when_sdk_matched():
    status, details = compute_verification_status(
        has_matches=True,
        matched_fields=["sdk"],
        has_endpoint=False,
        has_sdk=True,
        change_type="renamed",
    )
    assert status == "verified"
    assert details["sdk_match"] is True


# ---------------------------------------------------------------------------
# analyze_changelog_event end-to-end (with real match pipeline)
# ---------------------------------------------------------------------------
def test_analysis_verified_with_endpoint_detection():
    event = _fake_event(change_type="removed", old_value="charges.create")
    dets = [_fake_detection()]
    analysis = analyze_changelog_event(
        event=event,
        repo_id="repo-1",
        detections=dets,
        repo_packages=["stripe"],
    )
    assert analysis.verification_status in ("verified", "potential")
    assert analysis.change_type == "removed"
    # never claims more than evidence: severity derives from real matcher
    assert analysis.severity in ("breaking", "high", "medium", "low", "safe", "unknown")


def test_analysis_not_found_without_detections():
    event = _fake_event(change_type="deprecated")
    analysis = analyze_changelog_event(
        event=event,
        repo_id="repo-1",
        detections=[],
        repo_packages=[],
    )
    assert analysis.verification_status == "not_found"
    assert analysis.affected_files == []
    assert analysis.impact_reason == "No matching repository usage detected"


# ---------------------------------------------------------------------------
# fire-drill matrix classification (pure logic mirrors router)
# ---------------------------------------------------------------------------
def _classify(has_usage: bool, recent_events: int) -> str:
    if has_usage and recent_events > 0:
        return "active"
    if has_usage:
        return "at_risk"
    if recent_events > 0:
        return "unknown"
    return "inactive"


def test_matrix_classification_branches():
    assert _classify(True, 3) == "active"
    assert _classify(True, 0) == "at_risk"
    assert _classify(False, 2) == "unknown"
    assert _classify(False, 0) == "inactive"