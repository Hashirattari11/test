"""Notification preferences + test-email endpoints (authenticated).

* GET  /notifications/preferences   — all categories with effective state
* PUT  /notifications/preferences   — enable/disable categories (upsert)
* POST /notifications/test-email    — send a REAL test email to the user's own
                                       address via Resend; never fakes success
* PATCH /notifications/daily-status — toggle daily status email (notify_daily_status)
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..db import db
from ..deps import get_current_user_id
from ..email_service import (
    NOTIFICATION_CATEGORIES,
    preferences_map,
    resolve_user_email,
    send_alert_email,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


class PreferencesUpdate(BaseModel):
    preferences: dict[str, bool] = Field(..., description="category -> enabled")


class PreferencesResponse(BaseModel):
    categories: dict[str, bool]


class DailyStatusUpdate(BaseModel):
    notify_daily_status: bool = Field(..., description="Enable daily status email")


class DailyStatusResponse(BaseModel):
    notify_daily_status: bool


class TestEmailResponse(BaseModel):
    ok: bool
    status: str
    provider_message_id: str | None = None
    error_category: str | None = None
    detail: str | None = None
    sender_warning: str | None = None


@router.get("/preferences", response_model=PreferencesResponse)
def get_preferences(user_id: str = Depends(get_current_user_id)) -> PreferencesResponse:
    return PreferencesResponse(categories=preferences_map(user_id))


@router.put("/preferences", response_model=PreferencesResponse)
def put_preferences(
    body: PreferencesUpdate,
    user_id: str = Depends(get_current_user_id),
) -> PreferencesResponse:
    invalid = [c for c in body.preferences if c not in NOTIFICATION_CATEGORIES]
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown categories: {', '.join(sorted(invalid))}",
        )
    for cat, enabled in body.preferences.items():
        try:
            db().table("notification_preferences").upsert(
                {
                    "user_id": user_id,
                    "category": cat,
                    "email_enabled": bool(enabled),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                on_conflict="user_id,category",
            ).execute()
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to save preferences")
    return PreferencesResponse(categories=preferences_map(user_id))


@router.post("/test-email", response_model=TestEmailResponse)
def send_test_email(user_id: str = Depends(get_current_user_id)) -> TestEmailResponse:
    to_email = resolve_user_email(user_id)
    if not to_email:
        raise HTTPException(status_code=400, detail="No email address on file for this user")

    subject = "AutoFix API — test email"
    html = (
        '<div style="font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;'
        'max-width:560px;margin:0 auto;color:#1a1a2e;">'
        "<h2 style=\"margin:0 0 8px;\">&#9989; AutoFix API test email</h2>"
        "<p style=\"color:#555;\">This is a test message to verify your email "
        "alert delivery. If you received this, the pipeline works.</p>"
        "</div>"
    )
    text = "AutoFix API test email — if you received this, the pipeline works."

    result = send_alert_email(
        user_id=user_id,
        recipient=to_email,
        alert_type="test",
        subject=subject,
        html=html,
        text=text,
    )
    return TestEmailResponse(
        ok=result.get("ok", False),
        status=result.get("status", "failed"),
        provider_message_id=result.get("provider_message_id"),
        error_category=result.get("error_category"),
        detail=result.get("detail"),
        sender_warning=result.get("sender_warning"),
    )


@router.patch("/daily-status", response_model=DailyStatusResponse)
def update_daily_status(
    body: DailyStatusUpdate,
    user_id: str = Depends(get_current_user_id),
) -> DailyStatusResponse:
    """Toggle daily status email for the user."""
    try:
        db().table("users").update(
            {"notify_daily_status": body.notify_daily_status}
        ).eq("id", user_id).execute()
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to update daily status preference")
    
    # Fetch updated value
    user = db().table("users").select("notify_daily_status").eq("id", user_id).execute()
    if user.data:
        return DailyStatusResponse(notify_daily_status=user.data[0].get("notify_daily_status", False))
    return DailyStatusResponse(notify_daily_status=body.notify_daily_status)