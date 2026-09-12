"""Rule-based severity scoring for alerts (Phase 5, Section 1).

Scores a changelog-event match against a repo's code so the dashboard can tell a
customer what to fix first. Deterministic (no AI) — pure rules over the change
type and the set of file paths a detection matched in.

Severity ∈ {critical, high, medium, low}.

Rules (per spec):
  * critical : change_type is field_removed or endpoint_deprecated AND matched
               in 5+ files, OR matched in any file path containing payment /
               checkout / billing / webhook.
  * high     : change_type is field_removed or endpoint_deprecated, matched in
               1-4 files.
  * medium   : change_type is field_renamed, any file count.
  * low      : change_type is other (unparsed entry, needs manual review).

We always return a short human `reason` the dashboard can display next to the
badge (e.g. "Affects 3 files including a webhook handler").
"""
from __future__ import annotations

from collections import Counter

# Change types that, by themselves, are high-impact removals/deprecations.
_HIGH_IMPACT_TYPES = {"field_removed", "endpoint_deprecated"}
# Renames are medium by default.
_MEDIUM_TYPES = {"field_renamed"}
# Anything else (unparsed changelog entry) is low.
_LOW_TYPES = {"other"}

# Path fragments that flag a file as payment/billing critical.
_CRITICAL_PATH_FRAGMENTS = ("payment", "checkout", "billing", "webhook")


def _critical_path(file_paths: list[str]) -> str | None:
    for p in file_paths:
        low = p.lower()
        for frag in _CRITICAL_PATH_FRAGMENTS:
            if frag in low:
                return p
    return None


def score_severity(change_type: str, file_paths: list[str]) -> tuple[str, str]:
    """Return (severity, reason) for a change type + the file paths it matched."""
    change_type = (change_type or "other").lower()
    file_paths = [p for p in file_paths if p]
    count = len(set(file_paths))

    critical_path = _critical_path(file_paths)
    if change_type in _HIGH_IMPACT_TYPES and count >= 5:
        return "critical", f"Deprecation affects {count} files"
    if critical_path:
        return (
            "critical",
            f"Affects {count} file(s) including {critical_path}",
        )
    if change_type in _HIGH_IMPACT_TYPES:
        return "high", f"Deprecation affects {count} file(s)"
    if change_type in _MEDIUM_TYPES:
        return "medium", f"Renamed field affects {count} file(s)"
    # fallthrough: 'other' / anything unlisted → low
    return "low", "Unparsed changelog entry — review manually"


# ---------------------------------------------------------------------------
# severity ordering helpers (dashboard sort/filter)
# ---------------------------------------------------------------------------
SEVERITY_ORDER: dict[str, int] = {"critical": 0, "high": 1, "medium": 2, "low": 3}

SEVERITY_LABELS: dict[str, str] = {
    "critical": "Critical",
    "high": "High",
    "medium": "Medium",
    "low": "Low",
}

# Badge color classes used by the dashboard (tailwind).
SEVERITY_BADGE: dict[str, str] = {
    "critical": "bg-red-100 text-red-700 border-red-200",
    "high": "bg-orange-100 text-orange-700 border-orange-200",
    "medium": "bg-yellow-100 text-yellow-700 border-yellow-200",
    "low": "bg-gray-100 text-gray-600 border-gray-200",
}


def severity_sort_key(alert: dict) -> tuple[int, str]:
    """Sort key so critical-first ordering works across N alerts."""
    sev = (alert.get("severity") or "medium").lower()
    # Secondary sort by detected_at desc (most recent first within a severity).
    return (SEVERITY_ORDER.get(sev, 2), alert.get("detected_at") or "",)
