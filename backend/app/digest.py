"""Weekly digest email for Breaklytix users.

Sent every Monday summarizing the past week's activity:
- APIs monitored
- Alerts received
- Fixes pending review
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .config import settings
from .db import db
from .email_service import category_enabled, send_alert_email

_WORD = __import__("re").compile(r"[A-Za-z_]{3,}")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _week_ago() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()


def send_weekly_digest() -> dict[str, int]:
    """Send weekly digest to all users with connected repos. Returns counts."""
    counts = {"users_emailed": 0, "emails_failed": 0, "users_skipped": 0}

    # Get all users with at least one repo
    users = (
        db()
        .table("users")
        .select("id, email")
        .execute()
    ).data or []

    for user in users:
        user_id = user["id"]
        email = user.get("email")
        if not email:
            counts["users_skipped"] += 1
            continue

        # Respect the user's digest preference (defaults to ON).
        if not category_enabled(user_id, "digest"):
            counts["users_skipped"] += 1
            continue

        # Get user's repos
        repos = (
            db()
            .table("repos")
            .select("id, full_name")
            .eq("user_id", user_id)
            .execute()
        ).data or []

        if not repos:
            counts["users_skipped"] += 1
            continue

        repo_ids = [r["id"] for r in repos]

        # Stats for the past week
        week_start = _week_ago()

        # APIs monitored (unique APIs across all user's repos)
        detections = (
            db()
            .table("api_detections")
            .select("api_name")
            .in_("repo_id", repo_ids)
            .execute()
        ).data or []
        apis_monitored = sorted({d["api_name"] for d in detections})

        # Alerts this week
        alerts = (
            db()
            .table("alerts")
            .select("id, created_at, changelog_events(api_name, change_type, description)")
            .in_("repo_id", repo_ids)
            .gte("created_at", week_start)
            .execute()
        ).data or []

        alerts_by_api: dict[str, int] = {}
        for a in alerts:
            ev = a.get("changelog_events") or {}
            api = ev.get("api_name", "unknown")
            alerts_by_api[api] = alerts_by_api.get(api, 0) + 1

        # Fixes needing review
        fixes = (
            db()
            .table("fixes")
            .select("id, status, file_path, fix_rules(title)")
            .in_("repo_id", repo_ids)
            .in_("status", ["needs_review", "pending"])
            .execute()
        ).data or []

        fixes_by_status: dict[str, int] = {}
        for f in fixes:
            fixes_by_status[f["status"]] = fixes_by_status.get(f["status"], 0) + 1

        # Only send if there's something to report (or always send per spec)
        subject, html, text = render_digest_email(
            user_email=email,
            repos=repos,
            apis_monitored=apis_monitored,
            alerts_by_api=alerts_by_api,
            fixes_by_status=fixes_by_status,
            total_alerts=len(alerts),
            total_fixes=len(fixes),
        )

        result = send_alert_email(
            user_id=user_id,
            recipient=email,
            alert_type="digest",
            subject=subject,
            html=html,
            text=text,
            fingerprint=f"digest:{user_id}:{_week_ago()[:10]}",
            context={"user_id": user_id},
        )
        if result.get("ok"):
            counts["users_emailed"] += 1
        else:
            counts["emails_failed"] += 1

    return counts


def render_digest_email(
    user_email: str,
    repos: list[dict],
    apis_monitored: list[str],
    alerts_by_api: dict[str, int],
    fixes_by_status: dict[str, int],
    total_alerts: int,
    total_fixes: int,
) -> tuple[str, str, str]:
    """Render the weekly digest email."""
    repo_names = ", ".join(r["full_name"] for r in repos[:5])
    if len(repos) > 5:
        repo_names += f" and {len(repos) - 5} more"

    subject = f"📊 Your Breaklytix Weekly Digest — {len(repos)} repo(s), {total_alerts} alert(s)"

    # Build API list
    api_list = ", ".join(apis_monitored) if apis_monitored else "None yet"

    # Build alerts summary
    if alerts_by_api:
        alerts_summary = "\n".join(f"  • {api}: {count}" for api, count in alerts_by_api.items())
    else:
        alerts_summary = "  No alerts this week. 🎉"

    # Build fixes summary
    if fixes_by_status:
        fixes_summary = "\n".join(f"  • {status.replace('_', ' ').title()}: {count}" for status, count in fixes_by_status.items())
    else:
        fixes_summary = "  No fixes pending review."

    text = f"""Hi there,

Here's your Breaklytix weekly summary for the past 7 days.

📦 Repositories: {repo_names}
🔍 APIs Monitored: {api_list}

🔔 Alerts This Week ({total_alerts} total):
{alerts_summary}

🔧 Fixes Pending Review ({total_fixes} total):
{fixes_summary}

---

View your dashboard: {settings.frontend_origins.split(",")[0].strip()}/dashboard

- Breaklytix
"""

    # HTML version
    alerts_html = "".join(
        f"<li><strong>{api}:</strong> {count} alert(s)</li>" for api, count in alerts_by_api.items()
    ) or "<li>No alerts this week. 🎉</li>"

    fixes_html = "".join(
        f"<li><strong>{status.replace('_', ' ').title()}:</strong> {count}</li>"
        for status, count in fixes_by_status.items()
    ) or "<li>No fixes pending review.</li>"

    html = f"""\
<div style="font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;max-width:560px;margin:0 auto;color:#1a1a2e;">
  <h2 style="margin:0 0 4px;">📊 Your Breaklytix Weekly Digest</h2>
  <p style="color:#555;margin:0 0 16px;font-size:13px;">
    Summary for the past 7 days across {len(repos)} repository(ies)
  </p>

  <div style="background:#f6f6fb;border-radius:8px;padding:14px 16px;margin-bottom:16px;">
    <strong>Repositories:</strong> {repo_names}<br>
    <strong>APIs Monitored:</strong> {api_list}
  </div>

  <div style="margin-bottom:16px;">
    <strong>🔔 Alerts This Week ({total_alerts} total)</strong>
    <ul style="margin:6px 0 0;padding-left:18px;line-height:1.7;">{alerts_html}</ul>
  </div>

  <div style="margin-bottom:16px;">
    <strong>🔧 Fixes Pending Review ({total_fixes} total)</strong>
    <ul style="margin:6px 0 0;padding-left:18px;line-height:1.7;">{fixes_html}</ul>
  </div>

  <p style="margin:0 0 16px;">
    <a href="{settings.frontend_origins.split(",")[0].strip()}/dashboard" style="color:#635bff;">View your dashboard &rarr;</a>
  </p>

  <p style="color:#999;font-size:12px;margin-top:20px;">&mdash; Breaklytix</p>
</div>"""

    return subject, html, text