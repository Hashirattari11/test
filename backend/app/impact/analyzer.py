"""Impact Engine: Analyzes provider changes against repository code.

Core flow:
1. Detect changed API/endpoint/SDK from changelog event
2. Match against connected GitHub repository
3. Identify exact affected files/functions/API calls
4. Calculate impact + severity + confidence
5. Explain WHY it is affected
6. Generate possible fix
7. Run tests/typecheck/lint
8. Show verified result
9. Optionally create GitHub PR
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from ..db import db
from ..changelog.matching import ENDPOINT_PATTERNS, SDK_PATTERNS, match_event_to_detection

logger = logging.getLogger("autofix.impact")


@dataclass
class AffectedCode:
    """Represents a specific code location affected by a provider change."""
    file_path: str
    line_number: int | None = None
    function_name: str | None = None
    class_name: str | None = None
    snippet: str = ""
    api_endpoint: str | None = None
    sdk_package: str | None = None
    sdk_version: str | None = None
    workflow: str | None = None  # e.g., "Checkout workflow"
    reason: str = ""  # Why this code is affected


@dataclass
class ImpactAnalysis:
    """Complete impact analysis result for a provider change."""
    id: str | None = None
    repo_id: str | None = None
    changelog_event_id: str | None = None
    provider: str = ""
    api_endpoint: str | None = None
    change_type: str = ""
    change_description: str | None = None
    source_url: str | None = None
    detected_at: str = ""
    
    # Affected code
    affected_files: list[AffectedCode] = field(default_factory=list)
    affected_sdks: list[dict] = field(default_factory=list)
    
    # Impact assessment
    severity: str = "unknown"  # safe | low | medium | high | breaking | unknown
    confidence: float = 0.5
    impact_reason: str | None = None
    expected_behavior: str | None = None
    potential_failure: str | None = None
    
    # Fix details
    recommended_fix: str | None = None
    fix_diff: str | None = None
    fix_status: str = "not_generated"
    
    # Verification
    verification_status: str = "not_verified"
    verification_details: dict = field(default_factory=dict)
    
    # Metadata
    scan_id: str | None = None
    created_at: str = ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def analyze_changelog_event(
    event: dict,
    repo_id: str,
    detections: list[dict],
    repo_packages: list[str] | None = None,
) -> ImpactAnalysis:
    """Analyze a changelog event against a repository's detections.
    
    Args:
        event: Changelog event from database
        repo_id: Repository ID to analyze against
        detections: List of detection dicts from api_detections table
        repo_packages: Optional list of package names from repo
    
    Returns:
        ImpactAnalysis with affected code and severity assessment
    """
    provider = event.get("api_name") or event.get("provider", "")
    change_type = event.get("change_type", "unknown")
    source_url = event.get("source_url")
    description = event.get("description", "")
    
    # Find matching detections
    matching_detections = []
    for detection in detections:
        result = match_event_to_detection(event, detection, repo_packages)
        if len(result.matched_fields) >= 1:
            matching_detections.append((detection, result))
    
    # Build affected code list
    affected_files: list[AffectedCode] = []
    affected_sdks: list[dict] = []
    
    for detection, match_result in matching_detections:
        affected = AffectedCode(
            file_path=detection.get("file_path", ""),
            line_number=detection.get("line_number"),
            snippet=detection.get("matched_snippet", ""),
            reason=f"Matched on: {', '.join(match_result.matched_fields)}",
        )
        
        # Extract endpoint if matched
        if "endpoint" in match_result.matched_fields:
            affected.api_endpoint = next(
                (e for e in match_result.evidence if e.startswith("Endpoint:")),
                None
            )
        
        affected_files.append(affected)
    
    # Extract SDK info from packages
    if repo_packages:
        sdk_patterns = SDK_PATTERNS.get(provider, [])
        for pkg in repo_packages:
            for pattern in sdk_patterns:
                if pattern.lower() in pkg.lower():
                    affected_sdks.append({
                        "package": pkg,
                        "provider": provider,
                        "pattern": pattern,
                    })
                    break
    
    # Calculate severity and confidence
    from .severity import calculate_impact_severity
    severity, confidence = calculate_impact_severity(
        change_type=change_type,
        matched_count=len(matching_detections),
        matched_fields=[f for _, r in matching_detections for f in r.matched_fields],
        has_endpoint=any("endpoint" in r.matched_fields for _, r in matching_detections),
        has_sdk=bool(affected_sdks),
    )
    
    # Build analysis
    analysis = ImpactAnalysis(
        repo_id=repo_id,
        changelog_event_id=event.get("id"),
        provider=provider,
        api_endpoint=event.get("old_value"),
        change_type=change_type,
        change_description=description,
        source_url=source_url,
        detected_at=_now_iso(),
        affected_files=affected_files,
        affected_sdks=affected_sdks,
        severity=severity,
        confidence=confidence,
        impact_reason=_build_impact_reason(provider, change_type, len(matching_detections)),
        expected_behavior=_build_expected_behavior(change_type),
        potential_failure=_build_potential_failure(change_type, severity),
        created_at=_now_iso(),
    )
    
    return analysis


def analyze_repo_for_provider(
    repo_id: str,
    provider: str,
    detections: list[dict],
) -> ImpactAnalysis:
    """Analyze a repository for potential impact from a specific provider.
    
    Used for Fire Drill analysis.
    """
    # Get recent changelog events for this provider
    events = (
        db()
        .table("changelog_events")
        .select("*")
        .eq("api_name", provider)
        .order("detected_at", desc=True)
        .limit(10)
        .execute()
    ).data or []
    
    if not events:
        # No changelog events - create safe analysis
        return ImpactAnalysis(
            repo_id=repo_id,
            provider=provider,
            change_type="none",
            severity="safe",
            confidence=0.9,
            impact_reason="No known provider changes detected",
            detected_at=_now_iso(),
            created_at=_now_iso(),
        )
    
    # Analyze against most recent event
    return analyze_changelog_event(
        event=events[0],
        repo_id=repo_id,
        detections=detections,
    )


def persist_impact_analysis(analysis: ImpactAnalysis) -> str:
    """Persist an impact analysis to the database.
    
    Returns the analysis ID.
    """
    row = {
        "repo_id": analysis.repo_id,
        "changelog_event_id": analysis.changelog_event_id,
        "provider": analysis.provider,
        "api_endpoint": analysis.api_endpoint,
        "change_type": analysis.change_type,
        "change_description": analysis.change_description,
        "source_url": analysis.source_url,
        "detected_at": analysis.detected_at,
        "affected_files": json.dumps([{
            "file_path": f.file_path,
            "line_number": f.line_number,
            "function_name": f.function_name,
            "class_name": f.class_name,
            "snippet": f.snippet,
            "api_endpoint": f.api_endpoint,
            "sdk_package": f.sdk_package,
            "sdk_version": f.sdk_version,
            "workflow": f.workflow,
            "reason": f.reason,
        } for f in analysis.affected_files]),
        "affected_sdks": json.dumps(analysis.affected_sdks),
        "severity": analysis.severity,
        "confidence": analysis.confidence,
        "impact_reason": analysis.impact_reason,
        "expected_behavior": analysis.expected_behavior,
        "potential_failure": analysis.potential_failure,
        "recommended_fix": analysis.recommended_fix,
        "fix_diff": analysis.fix_diff,
        "fix_status": analysis.fix_status,
        "verification_status": analysis.verification_status,
        "verification_details": json.dumps(analysis.verification_details),
        "scan_id": analysis.scan_id,
        "created_at": analysis.created_at,
        "updated_at": _now_iso(),
    }
    
    result = db().table("impact_analyses").insert(row).execute()
    return result.data[0]["id"]


def get_impact_analysis(analysis_id: str) -> ImpactAnalysis | None:
    """Retrieve an impact analysis from the database."""
    result = (
        db()
        .table("impact_analyses")
        .select("*")
        .eq("id", analysis_id)
        .limit(1)
        .execute()
    )
    
    if not result.data:
        return None
    
    return _row_to_analysis(result.data[0])


def get_repo_impact_analyses(
    repo_id: str,
    limit: int = 50,
    offset: int = 0,
    severity: str | None = None,
) -> list[ImpactAnalysis]:
    """Get all impact analyses for a repository."""
    query = (
        db()
        .table("impact_analyses")
        .select("*")
        .eq("repo_id", repo_id)
        .order("detected_at", desc=True)
        .range(offset, offset + limit - 1)
    )
    
    if severity:
        query = query.eq("severity", severity)
    
    result = query.execute()
    return [_row_to_analysis(row) for row in (result.data or [])]


def _row_to_analysis(row: dict) -> ImpactAnalysis:
    """Convert a database row to an ImpactAnalysis."""
    affected_files_data = row.get("affected_files") or []
    if isinstance(affected_files_data, str):
        affected_files_data = json.loads(affected_files_data)
    
    affected_files = [
        AffectedCode(
            file_path=f.get("file_path", ""),
            line_number=f.get("line_number"),
            function_name=f.get("function_name"),
            class_name=f.get("class_name"),
            snippet=f.get("snippet", ""),
            api_endpoint=f.get("api_endpoint"),
            sdk_package=f.get("sdk_package"),
            sdk_version=f.get("sdk_version"),
            workflow=f.get("workflow"),
            reason=f.get("reason", ""),
        )
        for f in affected_files_data
    ]
    
    affected_sdks = row.get("affected_sdks") or []
    if isinstance(affected_sdks, str):
        affected_sdks = json.loads(affected_sdks)
    
    verification_details = row.get("verification_details") or {}
    if isinstance(verification_details, str):
        verification_details = json.loads(verification_details)
    
    return ImpactAnalysis(
        id=row.get("id"),
        repo_id=row.get("repo_id"),
        changelog_event_id=row.get("changelog_event_id"),
        provider=row.get("provider", ""),
        api_endpoint=row.get("api_endpoint"),
        change_type=row.get("change_type", ""),
        change_description=row.get("change_description"),
        source_url=row.get("source_url"),
        detected_at=row.get("detected_at", ""),
        affected_files=affected_files,
        affected_sdks=affected_sdks,
        severity=row.get("severity", "unknown"),
        confidence=float(row.get("confidence", 0.5)),
        impact_reason=row.get("impact_reason"),
        expected_behavior=row.get("expected_behavior"),
        potential_failure=row.get("potential_failure"),
        recommended_fix=row.get("recommended_fix"),
        fix_diff=row.get("fix_diff"),
        fix_status=row.get("fix_status", "not_generated"),
        verification_status=row.get("verification_status", "not_verified"),
        verification_details=verification_details,
        scan_id=row.get("scan_id"),
        created_at=row.get("created_at", ""),
    )


def _build_impact_reason(provider: str, change_type: str, match_count: int) -> str:
    """Build human-readable impact reason.

    User-spec phrasing: matched usage -> "Potential impact detected";
    no usage -> "No matching repository usage detected". Never implies the
    user's code is broken (that judgment belongs to the user).
    """
    if match_count == 0:
        return f"No matching repository usage detected"
    
    if change_type == "removed":
        return f"Potential impact detected: repository uses {provider} API that has been removed"
    elif change_type == "deprecated":
        return f"Potential impact detected: repository uses {provider} API that is deprecated"
    elif change_type == "renamed":
        return f"Potential impact detected: repository uses {provider} API that has been renamed"
    elif change_type == "endpoint_changed":
        return f"Potential impact detected: repository uses {provider} endpoint that has changed"
    elif change_type == "auth_changed":
        return f"Potential impact detected: repository uses {provider} authentication that has changed"
    else:
        return f"Potential impact detected: repository uses {provider} API affected by change"


def _build_expected_behavior(change_type: str) -> str:
    """Build expected behavior description."""
    behaviors = {
        "removed": "Requests to removed endpoints will fail with 404 or similar error",
        "deprecated": "Deprecated features may stop working at any time",
        "renamed": "Old function/method names will no longer work",
        "endpoint_changed": "Requests to old endpoints may fail or return unexpected results",
        "auth_changed": "Authentication with old credentials may fail",
    }
    return behaviors.get(change_type, "Behavior may change unexpectedly")


def _build_potential_failure(change_type: str, severity: str) -> str:
    """Build potential failure description (evidence-based, non-alarmist)."""
    if severity == "breaking":
        return "Potential impact detected: affected requests may fail or return unexpected results"
    elif severity == "high":
        return "Potential impact detected: critical functionality may be disrupted"
    elif severity == "medium":
        return "Potential impact detected: some features may be affected"
    elif severity == "low":
        return "Minor impact expected"
    else:
        return "No significant impact expected"
