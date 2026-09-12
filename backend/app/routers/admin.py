"""Internal Admin Panel - admin-only endpoints under /admin/*.

Every route in this module is guarded server-side by ``require_admin`` which
verifies ``users.is_admin = true`` in the database. Non-admins receive 403.
The UI hiding of admin links is purely cosmetic; this layer is the authoritative
gate and must never be bypassed.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..alerts import render_alert_email
from ..db import db, fetch_one
from ..deps import require_admin
from ..email_service import send_alert_email
from ..config import settings
from ..signatures import MONITORED_APIS, PLANNED_APIS

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _count(table: str) -> int:
    """Row count without loading full rows (uses PostgREST exact count)."""
    try:
        res = db().table(table).select("id", count="exact").execute()
        return res.count if res.count is not None else len(res.data or [])
    except Exception:
        try:
            return len(db().table(table).select("id").execute().data or [])
        except Exception:
            return 0


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------
@router.get("/overview")
def admin_overview() -> dict:
    repo_count = _count("repos")
    alerts_sent = 0
    alerts_pending = 0
    alerts_dismissed = 0
    test_alerts_sent = 0
    for row in (db().table("alerts").select("status", "is_test").execute().data or []):
        if row.get("status") == "sent":
            if row.get("is_test"):
                test_alerts_sent += 1
            else:
                alerts_sent += 1
        elif row.get("status") == "pending":
            alerts_pending += 1
        elif row.get("status") == "dismissed":
            alerts_dismissed += 1

    return {
        "total_users": _count("users"),
        "total_repos": repo_count,
        "alerts_sent": alerts_sent,
        "alerts_pending": alerts_pending,
        "alerts_dismissed": alerts_dismissed,
        "test_alerts_sent": test_alerts_sent,
        "providers_monitored": len(MONITORED_APIS),
        "providers_planned": len(PLANNED_APIS),
    }


# ---------------------------------------------------------------------------
# Pending alert approval queue (real, non-test alerts awaiting approval)
# ---------------------------------------------------------------------------
@router.get("/alerts/pending")
def pending_alerts(limit: int = 100) -> dict:
    rows = (
        db()
        .table("alerts")
        .select("*, changelog_events(*), api_detections(*), repos(*)")
        .eq("status", "pending")
        .neq("is_test", True)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    alerts = []
    for a in rows.data or []:
        event = a.get("changelog_events") or {}
        detections = a.get("api_detections") or {}
        repo = a.get("repos") or {}
        # Resolve the owning user email (repo.user_id -> users.email)
        customer_email = None
        owner_id = repo.get("user_id")
        if owner_id:
            u = fetch_one("users", {"id": owner_id})
            customer_email = (u or {}).get("email")

        alert_id = a.get("id")
        subject = None
        preview = None
        ev = dict(event) if event else {}
        # Re-render the email preview using the stored event/detection data.
        try:
            if ev and repo.get("full_name"):
                dets = [dict(detections)] if detections else []
                subject, _html, text = render_alert_email(
                    repo.get("full_name", "repo"),
                    ev,
                    dets,
                    severity=a.get("severity", "medium"),
                    confidence=a.get("confidence", "medium"),
                )
                preview = (text or "")[:300]
        except Exception:
            pass

        alerts.append({
            "id": alert_id,
            "repo_id": repo.get("id"),
            "repo_name": repo.get("full_name"),
            "provider": event.get("api_name") or a.get("provider"),
            "api_name": event.get("api_name"),
            "customer_email": customer_email,
            "confidence": a.get("confidence"),
            "severity": a.get("severity"),
            "severity_reason": a.get("severity_reason"),
            "evidence": detections.get("matched_snippet") or detections.get("file_path"),
            "subject": subject,
            "preview": preview,
            "created_at": a.get("created_at"),
        })
    return {"alerts": alerts}


# ---------------------------------------------------------------------------
# Approve / Reject
# ---------------------------------------------------------------------------
def _load_alert(alert_id: str) -> dict:
    res = (
        db()
        .table("alerts")
        .select("*, changelog_events(*), api_detections(*), repos(*)")
        .eq("id", alert_id)
        .limit(1)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Alert not found")
    return res.data[0]


@router.post("/alerts/{alert_id}/approve")
def approve_alert(alert_id: str) -> dict:
    a = _load_alert(alert_id)
    event = a.get("changelog_events") or {}
    repo = a.get("repos") or {}
    dets = [dict(a.get("api_detections") or {})] if a.get("api_detections") else []

    email_sent = False
    owner_id = repo.get("user_id")
    if owner_id:
        u = fetch_one("users", {"id": owner_id})
        owner_email = (u or {}).get("email")
        if owner_email and repo.get("full_name"):
            try:
                subject, html, text = render_alert_email(
                    repo["full_name"], dict(event), dets,
                    severity=a.get("severity", "medium"),
                    confidence=a.get("confidence", "medium"),
                )
                # Through the central email service: respects preferences,
                # dedups and logs to email_deliveries.
                result = send_alert_email(
                    user_id=owner_id,
                    recipient=owner_email,
                    alert_type="breaking_changes",
                    subject=subject,
                    html=html,
                    text=text,
                    alert_id=alert_id,
                    fingerprint=f"approve:{alert_id}",
                    context={"event_id": event.get("id")},
                )
                email_sent = bool(result.get("ok"))
            except Exception:
                email_sent = False

    now = _now_iso()
    upd: dict[str, Any] = {"status": "sent", "email_sent": True, "sent_at": now}
    if email_sent is False:
        # Still mark as sent (approved) but record that email delivery failed.
        upd["status"] = "sent"
        upd["email_sent"] = False
    db().table("alerts").update(upd).eq("id", alert_id).execute()
    return {"ok": True, "email_sent": email_sent, "alert_id": alert_id}


@router.post("/alerts/{alert_id}/reject")
def reject_alert(alert_id: str) -> dict:
    a = _load_alert(alert_id)
    db().table("alerts").update({"status": "dismissed"}).eq("id", a["id"]).execute()
    return {"ok": True, "alert_id": a["id"], "status": "dismissed"}


# ---------------------------------------------------------------------------
# System health
# ---------------------------------------------------------------------------
@router.get("/health")
def system_health() -> dict:
    rows = (
        db()
        .table("system_health")
        .select("*")
        .order("ran_at", desc=True)
        .limit(100)
        .execute()
    )
    return {"rows": rows.data or []}


# ---------------------------------------------------------------------------
# Users (read-only)
# ---------------------------------------------------------------------------
@router.get("/users")
def admin_users(limit: int = 200) -> dict:
    rows = (
        db()
        .table("users")
        .select("id,email,github_login,plan,is_admin,is_agency,created_at")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return {"users": rows.data or []}
