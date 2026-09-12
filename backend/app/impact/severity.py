"""Severity and confidence calculation for Impact Engine.

Calculates:
- Impact severity: safe | low | medium | high | breaking | unknown
- Confidence score: 0.0 - 1.0
- Static vs Verified status
"""
from __future__ import annotations


# Severity levels with their numeric weights for comparison
SEVERITY_WEIGHTS = {
    "safe": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "breaking": 4,
    "unknown": -1,
}


def calculate_impact_severity(
    change_type: str,
    matched_count: int,
    matched_fields: list[str],
    has_endpoint: bool = False,
    has_sdk: bool = False,
    has_old_value: bool = False,
    has_new_value: bool = False,
) -> tuple[str, float]:
    """Calculate impact severity and confidence.
    
    Args:
        change_type: Type of change (removed, deprecated, renamed, etc.)
        matched_count: Number of matching detections
        matched_fields: List of matched field types
        has_endpoint: Whether endpoint was matched
        has_sdk: Whether SDK/package was matched
        has_old_value: Whether old value was matched
        has_new_value: Whether new value was matched
    
    Returns:
        Tuple of (severity, confidence)
    """
    # Base severity from change type
    base_severity = _severity_from_change_type(change_type)
    
    # Adjust based on match quality
    severity = _adjust_severity(
        base_severity=base_severity,
        matched_count=matched_count,
        has_endpoint=has_endpoint,
        has_sdk=has_sdk,
        has_old_value=has_old_value,
        has_new_value=has_new_value,
    )
    
    # Calculate confidence
    confidence = _calculate_confidence(
        matched_count=matched_count,
        matched_fields=matched_fields,
        has_endpoint=has_endpoint,
        has_sdk=has_sdk,
        has_old_value=has_old_value,
        has_new_value=has_new_value,
    )
    
    return severity, confidence


def _severity_from_change_type(change_type: str) -> str:
    """Get base severity from change type."""
    severity_map = {
        "removed": "breaking",
        "deprecated": "high",
        "renamed": "medium",
        "endpoint_changed": "medium",
        "auth_changed": "high",
        "secret_leak": "critical",
        "breaking": "breaking",
        "none": "safe",
    }
    return severity_map.get(change_type, "unknown")


def _adjust_severity(
    base_severity: str,
    matched_count: int,
    has_endpoint: bool,
    has_sdk: bool,
    has_old_value: bool,
    has_new_value: bool,
) -> str:
    """Adjust severity based on match quality."""
    if base_severity == "safe":
        return "safe"
    
    if base_severity == "unknown":
        return "unknown"
    
    # Start with base severity weight
    weight = SEVERITY_WEIGHTS.get(base_severity, 2)
    
    # Increase weight for strong matches
    if has_endpoint and (has_old_value or has_new_value):
        weight += 1  # Very strong match
    elif has_endpoint or has_sdk:
        weight += 0.5  # Good match
    
    # Decrease weight for weak matches
    if matched_count == 0:
        weight -= 1
    elif matched_count == 1 and not has_endpoint and not has_sdk:
        weight -= 0.5
    
    # Clamp to valid range
    weight = max(0, min(4, weight))
    
    # Convert back to severity
    for sev, w in SEVERITY_WEIGHTS.items():
        if w == int(weight):
            return sev
    
    return base_severity


def _calculate_confidence(
    matched_count: int,
    matched_fields: list[str],
    has_endpoint: bool,
    has_sdk: bool,
    has_old_value: bool,
    has_new_value: bool,
) -> float:
    """Calculate confidence score (0.0 - 1.0)."""
    if matched_count == 0:
        return 0.1  # Very low confidence
    
    # Start with base confidence
    confidence = 0.5
    
    # Increase confidence for strong matches
    if has_endpoint:
        confidence += 0.2
    if has_sdk:
        confidence += 0.15
    if has_old_value:
        confidence += 0.1
    if has_new_value:
        confidence += 0.1
    
    # Increase confidence for multiple matches
    if matched_count > 1:
        confidence += 0.05 * min(matched_count - 1, 5)
    
    # Decrease confidence for weak matches
    if matched_count == 1 and not has_endpoint and not has_sdk:
        confidence -= 0.1
    
    # Clamp to valid range
    confidence = max(0.1, min(0.99, confidence))
    
    return round(confidence, 2)


def get_verification_status(
    fix_status: str,
    has_tests: bool = False,
    tests_passed: bool = False,
    has_typecheck: bool = False,
    typecheck_passed: bool = False,
    has_lint: bool = False,
    lint_passed: bool = False,
) -> str:
    """Determine verification status based on available checks.
    
    Returns:
        Verification status: not_verified | static_analysis | verified | verification_failed
    """
    if fix_status == "not_generated":
        return "not_verified"
    
    if fix_status == "generated":
        return "static_analysis"
    
    if fix_status in ("applied", "verified"):
        # Check if any verification was performed
        if has_tests or has_typecheck or has_lint:
            if tests_passed and (not has_typecheck or typecheck_passed) and (not has_lint or lint_passed):
                return "verified"
            else:
                return "verification_failed"
        else:
            return "static_analysis"
    
    return "not_verified"


def format_confidence(confidence: float) -> str:
    """Format confidence as percentage string."""
    return f"{int(confidence * 100)}%"


def severity_color(severity: str) -> str:
    """Get color for severity level (for UI)."""
    colors = {
        "safe": "#22c55e",  # green
        "low": "#84cc16",   # lime
        "medium": "#f59e0b", # amber
        "high": "#f97316",  # orange
        "breaking": "#ef4444", # red
        "unknown": "#6b7280", # gray
    }
    return colors.get(severity, "#6b7280")


def severity_icon(severity: str) -> str:
    """Get icon for severity level (for UI)."""
    icons = {
        "safe": "check-circle",
        "low": "alert-circle",
        "medium": "alert-triangle",
        "high": "alert-octagon",
        "breaking": "x-circle",
        "unknown": "help-circle",
    }
    return icons.get(severity, "help-circle")
