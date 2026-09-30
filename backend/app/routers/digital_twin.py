"""API Digital Twin endpoints (repository-scoped, IDOR-safe).

Digital Twin = simulate real provider changelog events against ONE
repository's real scanned usage (api_detections) and show exact file /
symbol / line evidence with a recommended change.

Every endpoint first verifies the caller owns the repository (same
_owned_repo pattern as the impact router) — a 404 for any repository the
caller does not own, never another user's data.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..db import db, fetch_one
from ..deps import get_current_user_id
from ..digital_twin import (
    get_repo_twin_analyses,
    get_repo_twin_summary,
    get_twin_analysis,
    run_digital_twin,
)

router = APIRouter(prefix="/digital-twin", tags=["digital-twin"])


class SimulateRequest(BaseModel):
    provider: str | None = None          # optional: simulate one provider only
    changelog_event_id: str | None = None  # optional: simulate one specific real event


def _owned_repo(user_id: str, repo_id: str) -> dict:
    """Verify repo ownership and return the repo row (404 otherwise)."""
    repo = fetch_one("repos", {"id": repo_id, "user_id": user_id})
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


@router.post("/{repo_id}/simulate")
def simulate(
    repo_id: str,
    body: SimulateRequest,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Run the Digital Twin simulation for one owned repository.

    Uses ONLY real changelog_events and real api_detections rows. The run is
    persisted idempotently; high-risk findings create alerts through the
    EXISTING alerts pipeline and (for user-triggered runs) one email via the
    EXISTING email_service.
    """
    repo = _owned_repo(user_id, repo_id)
    result = run_digital_twin(
        repo_id=repo_id,
        repo_name=repo.get("full_name") or "",
        provider=body.provider,
        changelog_event_id=body.changelog_event_id,
        triggered_by="user",
    )
    return {
        "run_id": result.run_id,
        "repository_id": result.repository_id,
        "provider_filter": result.provider_filter,
        "events_considered": result.events_considered,
        "analyses_created": result.analyses_created,
        "no_match_count": result.no_match_count,
        "alerts_created": result.alerts_created,
        "email_status": result.email_status,
        "email_detail": result.email_detail,
        "last_simulated_at": result.last_simulated_at,
        "findings": [
            {
                "api_detection_id": f.api_detection_id,
                "affected_file": f.affected_file,
                "affected_symbol": f.affected_symbol,
                "line_number": f.line_number,
                "usage_context": f.usage_context,
                "explanation": f.explanation,
                "recommended_change": f.recommended_change,
                "severity": f.severity,
                "confidence": f.confidence,
                "impact_status": f.impact_status,
                "matched_fields": f.matched_fields,
            }
            for f in result.findings
        ],
    }


@router.get("/{repo_id}/summary")
def summary(repo_id: str, user_id: str = Depends(get_current_user_id)) -> dict:
    """Aggregates for the flagship Digital Twin card — always repo-scoped."""
    _owned_repo(user_id, repo_id)
    return get_repo_twin_summary(repo_id)


@router.get("/{repo_id}/analyses")
def analyses(
    repo_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    provider: str | None = Query(default=None),
    status: str | None = Query(default=None),
    user_id: str = Depends(get_current_user_id),
) -> list[dict]:
    """Analysis rows for one owned repository — ALWAYS filtered by repo_id."""
    _owned_repo(user_id, repo_id)
    return get_repo_twin_analyses(repo_id, limit=limit, offset=offset,
                                  provider=provider, status=status)


@router.get("/{repo_id}/analyses/{analysis_id}")
def analysis_detail(
    repo_id: str,
    analysis_id: str,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """One analysis — must belong to the owned repository (isolation guard)."""
    _owned_repo(user_id, repo_id)
    row = get_twin_analysis(analysis_id, repo_id)
    if not row:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return row
