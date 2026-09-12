"""Cron endpoint for changelog monitoring (Phase B).

Called by Vercel Cron to fetch changelogs from all providers,
store new events, and process alerts. Also handles daily
code-health scans and email notifications.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from ..config import settings
from ..cronlog import run_cron
from ..db import db
from ..alerts import process_new_events, send_approved_alerts
from ..deps import get_current_user_id, require_internal_secret
from .scheduler import fetch_all_providers, log_health, run_daily_scans, run_impact_analysis_for_recent_events
from .admin import get_pending_alerts, approve_alert, disable_alert, is_admin

router = APIRouter()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("/internal/changelog/fetch")
async def fetch_changelogs(
    _guard: None = Depends(require_internal_secret),
) -> dict:
    """Fetch changelogs from all Phase B providers.
    
    Called by Vercel Cron or manually. Requires internal secret.
    """
    start = time.time()

    def _run() -> dict:
        results = fetch_all_providers(settings.scraper_user_agent)
        total_fetched = sum(r["fetched"] for r in results.values())
        total_stored = sum(r["stored"] for r in results.values())
        total_errors = sum(r["errors"] for r in results.values())
        return {
            "status": "ok",
            "providers": results,
            "summary": {
                "total_fetched": total_fetched,
                "total_stored": total_stored,
                "total_errors": total_errors,
            },
        }

    return run_cron("changelog_fetch", _run)


@router.post("/internal/changelog/process")
async def process_alerts(
    _guard: None = Depends(require_internal_secret),
) -> dict:
    """Process changelog events and create alerts.
    
    Called by Vercel Cron after fetch_changelogs.
    """
    def _run() -> dict:
        counts = process_new_events()
        flush = send_approved_alerts()
        return {"status": "ok", "counts": counts, "approved_flush": flush}

    return run_cron("changelog_process", _run)


@router.post("/internal/daily-scan")
async def daily_scan(
    _guard: None = Depends(require_internal_secret),
) -> dict:
    """Run daily scans for all monitored repos.
    
    Checks for breaking changelog changes and code-health issues.
    Sends exactly one email per repo/day.
    Called by Vercel Cron daily. Requires internal secret.
    """
    def _run() -> dict:
        run_daily_scans()
        run_impact_analysis_for_recent_events()
        return {"status": "ok", "message": "Daily scans + impact analysis completed"}

    return run_cron("daily_scan", _run)


@router.get("/internal/changelog/health")
async def health_check(_guard: None = Depends(require_internal_secret)) -> dict:
    """Health check for changelog monitoring. Requires internal secret.

    Safely reports DB connectivity without leaking exception internals.
    """
    try:
        db().table("changelog_events").select("id").limit(1).execute()
        return {"status": "ok", "database": "connected"}
    except Exception:
        # Log server-side only; never echo the exception to the client.
        import logging
        logging.getLogger("changelog").exception("changelog health check failed")
        return {"status": "error", "database": "unavailable"}


# ---------------------------------------------------------------------------
# Admin approval queue (beta safety net — owner-only)
# ---------------------------------------------------------------------------
@router.get("/internal/changelog/admin/pending")
async def admin_pending(user_id: str = Depends(get_current_user_id)) -> dict:
    """List changelog events pending admin approval (owner-only)."""
    if not is_admin(user_id):
        raise HTTPException(status_code=403, detail="Not authorized")
    return {"events": get_pending_alerts()}


@router.post("/internal/changelog/admin/approve/{event_id}")
async def admin_approve(event_id: str, user_id: str = Depends(get_current_user_id)) -> dict:
    """Approve an event for email sending, then flush approved emails (owner-only)."""
    if not is_admin(user_id):
        raise HTTPException(status_code=403, detail="Not authorized")
    ok = approve_alert(event_id, user_id)
    flush = send_approved_alerts() if ok else {}
    return {"approved": ok, "flush": flush}


@router.post("/internal/changelog/admin/disable/{event_id}")
async def admin_disable(
    event_id: str,
    reason: str | None = None,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Disable an event (won't send emails). Owner-only."""
    if not is_admin(user_id):
        raise HTTPException(status_code=403, detail="Not authorized")
    ok = disable_alert(event_id, user_id, reason)
    return {"disabled": ok}


@router.get("/internal/changelog/notices")
async def changelog_notices(user_id: str = Depends(get_current_user_id)) -> dict:
    """Dashboard view: notices surfaced for repos owned by the user."""
    repos = (
        db().table("repos").select("id").eq("user_id", user_id).execute()
    ).data or []
    repo_ids = [r["id"] for r in repos]
    if not repo_ids:
        return {"notices": []}

    notices = (
        db().table("alerts")
        .select("*, changelog_events(*)")
        .in_("repo_id", repo_ids)
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    ).data or []
    return {"notices": notices}
