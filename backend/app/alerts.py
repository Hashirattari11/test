"""Alert engine: cross-reference new changelog events against detected
code, create alert rows, and email affected users via Resend.

Matching (deterministic, no AI):
  * Each changelog event carries `symbols` (e.g. "charge,source") plus tokens
    pulled from its old/new values.
  * A detection matches if any of those tokens appears in the detection's
    stored `symbols` or `matched_snippet` (case-insensitive substring).
  * If an event has no extractable tokens, we alert every repo using that API
    only when ALERT_ON_UNMATCHED is enabled (default off, to avoid noise).

Idempotency: alerts are unique on (changelog_event_id, api_detection_id), and an
event is marked `processed_at` once handled so the cron never re-processes it.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone

from .config import settings
from .db import db
from .email_service import category_enabled, send_alert_email
from .severity import SEVERITY_LABELS, score_severity
from .changelog.matching import match_event_to_detection

# Phase B: events of these types are never alerted on by default.
NON_ALERT_EVENT_TYPES = {"new_feature", "bug_fix"}

# Vercel functions cap at 60s (maxDuration). Each event costs several DB
# round-trips, so a large backlog can exceed the budget. We cap the number of
# events handled per invocation; leftovers are picked up by the next cron tick
# (the cron runs again 15 minutes later, and the processed_at marker makes
# partial/batched runs idempotent).
MAX_EVENTS_PER_RUN = int(os.getenv("MAX_EVENTS_PER_RUN", "120"))

# Imported lazily to avoid a circular import with slack router wiring.
def _try_slack_alert(repo: dict, event: dict, severity: str) -> None:
    """Phase 5 §2: mirror an alert to the repo owner's Slack, best-effort."""
    try:
        from .slack_integration import get_connection, post_alert_to_slack
        conn = get_connection(repo["user_id"])
        if not conn:
            return
        post_alert_to_slack(
            conn,
            api_name=event.get("api_name", "API"),
            repo_name=repo["full_name"],
            change_type=event.get("change_type", "other"),
            description=event.get("description") or "",
            source_url=event.get("source_url"),
            severity=severity,
        )
    except Exception:
        # Best-effort mirroring; never let Slack break the email path.
        pass

_WORD = re.compile(r"[A-Za-z_]{3,}")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def event_tokens(event: dict) -> set[str]:
    """Lowercased tokens an event refers to, used to find affected code."""
    tokens: set[str] = set()
    if event.get("symbols"):
        tokens |= {t.strip().lower() for t in event["symbols"].split(",") if t.strip()}
    for key in ("old_value", "new_value"):
        val = event.get(key)
        if val:
            tokens |= {w.lower() for w in _WORD.findall(val)}
    # Drop generic noise words that would over-match.
    return tokens - {"the", "and", "for", "api", "value", "field", "object", "property"}


def detection_matches(detection: dict, tokens: set[str]) -> bool:
    haystack = f"{detection.get('symbols') or ''} {detection.get('matched_snippet') or ''}".lower()
    return any(tok in haystack for tok in tokens)


# ---------------------------------------------------------------------------
# email rendering
# ---------------------------------------------------------------------------
def render_alert_email(repo_name: str, event: dict, detections: list[dict], severity: str = "medium", confidence: str = "medium", brand_name: str | None = None, brand_logo: str | None = None) -> tuple[str, str, str]:
    api_name = event.get("api_name", "API").capitalize()
    label = SEVERITY_LABELS.get((severity or "medium").lower(), "Medium")
    prefix = f"[{label}] " if severity in ("critical", "high") else ""
    subject = f"{prefix}⚠️ {api_name} API change may affect {repo_name}"
    source_url = event.get("source_url") or settings.changelog_sources.get(event.get("api_name", ""), "")
    description = event.get("description") or f"A {api_name} API change was detected."
    change_type = (event.get("change_type") or "other").replace("_", " ")
    
    # Confidence-based messaging
    confidence = (confidence or "medium").lower()
    if confidence == "high":
        confidence_label = "Action required"
        confidence_color = "#dc3545"
        confidence_bg = "#fff5f5"
        confidence_message = "This change is likely to affect your integration."
    elif confidence == "medium":
        confidence_label = "Review recommended"
        confidence_color = "#f5b301"
        confidence_bg = "#fff8e1"
        confidence_message = "This official provider change may affect your integration."
    else:
        confidence_label = "Potential notice"
        confidence_color = "#6c757d"
        confidence_bg = "#f8f9fa"
        confidence_message = "Review if you use this provider."

    locations = "\n".join(
        f"  - {d['file_path']}" + (f":{d['line_number']}" if d.get("line_number") else "")
        for d in detections
    )
    loc_html = "".join(
        f"<li><code>{d['file_path']}"
        + (f":{d['line_number']}" if d.get("line_number") else "")
        + "</code></li>"
        for d in detections
    )
    dash_url = (
        f"{settings.frontend_base_url}/dashboard/changelog/{event.get('id')}"
        if event.get("id") else settings.frontend_base_url
    )

    text = f"""Heads-up: a {api_name} API change may affect your repo "{repo_name}".

What changed ({change_type}):
{description}

Likely affected in your code:
{locations}

{api_name}'s official changelog:
{source_url}

This is a heads-up only - no code was changed. Review and update manually.

— {brand_name or "Breaklytix"}
"""

    logo_html = f'<img src="{brand_logo}" alt="{brand_name or "Breaklytix"}" style="height:32px;margin-bottom:12px;" />' if brand_logo else ""
    sender = brand_name or "Breaklytix"

    html = f"""\
<div style="font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;max-width:560px;margin:0 auto;color:#1a1a2e;">
  {logo_html}
  <h2 style="margin:0 0 4px;">&#9888;&#65039; {api_name} API change may affect <span style="color:#635bff;">{repo_name}</span></h2>
  <p style="color:#555;margin:0 0 8px;font-size:13px;text-transform:capitalize;">Change type: {change_type}</p>
  <p style="margin:0 0 16px;font-size:13px;">
    <span style="background:{confidence_color};color:white;padding:2px 8px;border-radius:4px;font-weight:600;">{confidence_label}</span>
    <span style="margin-left:8px;color:#555;">{confidence_message}</span>
  </p>
  <div style="background:#f6f6fb;border-radius:8px;padding:14px 16px;margin-bottom:16px;">
    <strong>What changed</strong>
    <p style="margin:6px 0 0;line-height:1.5;">{description}</p>
  </div>
  <div style="margin-bottom:16px;">
    <strong>Likely affected in your code</strong>
    <ul style="margin:6px 0 0;padding-left:18px;line-height:1.7;">{loc_html}</ul>
  </div>
  <p style="margin:0 0 16px;">
    <a href="{source_url}" style="color:#635bff;">View {api_name}'s official changelog &rarr;</a>
  </p>
  <p style="margin:0 0 16px;">
    <a href="{dash_url}" style="display:inline-block;background:#635bff;color:#fff;padding:10px 16px;border-radius:6px;text-decoration:none;font-weight:600;">View Issue in dashboard &rarr;</a>
  </p>
  <p style="background:{confidence_bg};border-left:3px solid {confidence_color};padding:10px 12px;border-radius:4px;font-size:13px;color:#333;margin:0;">
    {confidence_message}<br/>
    Breaklytix did not read or store your secret values and did not modify your code.
  </p>
  <p style="color:#999;font-size:12px;margin-top:20px;">&mdash; {brand_name or "Breaklytix"}</p>
</div>"""
    return subject, html, text


# ---------------------------------------------------------------------------
# processing
# ---------------------------------------------------------------------------
def _compute_confidence(event: dict, detection: dict):
    """Compute a confidence label (high/medium/low) for a detection vs an event."""
    try:
        result = match_event_to_detection(event, detection)
        return (result.confidence or "low").lower()
    except Exception:
        return "low"


def _annotate_detections(event: dict, detections: list[dict]) -> list[tuple[dict, str]]:
    """Return (detection, confidence) pairs computed via the matching engine."""
    return [(d, _compute_confidence(event, d)) for d in detections]


def process_new_events() -> dict[str, int]:
    """Handle every unprocessed changelog event for all monitored APIs.

    Phase B behavior:
      * Events of type new_feature/bug_fix are never alerted on — just marked
        processed.
      * Real events create alert rows (dashboard visibility) immediately, and
        the email channel is attempted for high/medium-confidence matches via
        the central email service (respecting notification preferences, dedup
        and daily caps). The old admin-approval email gate is removed.
      * Low-confidence matches are dashboard-only (no email).
    """
    counts = {"events_processed": 0, "alerts_created": 0, "emails_sent": 0, "emails_failed": 0, "remaining": 0}

    monitored_apis = list(settings.changelog_sources.keys())
    total_pending = 0

    for api_name in monitored_apis:
        if counts["events_processed"] >= MAX_EVENTS_PER_RUN:
            break

        events = (
            db()
            .table("changelog_events")
            .select("*")
            .eq("api_name", api_name)
            .is_("processed_at", "null")
            .order("detected_at")
            .execute()
        ).data or []

        if not events:
            continue
        total_pending += len(events)

        # All detections for this API.
        api_detections = (
            db().table("api_detections").select("*").eq("api_name", api_name).execute()
        ).data or []

        # Slice to the remaining budget so a large backlog can never blow the
        # function timeout; leftovers are retried on the next cron tick.
        remaining_budget = MAX_EVENTS_PER_RUN - counts["events_processed"]
        events = events[:remaining_budget]

        # Bulk-mark non-alert event types in ONE round-trip instead of one
        # update per event (new_feature/bug_fix are never alerted on).
        non_alert_ids: list[str] = []
        for event in events:
            change_type = (event.get("change_type") or "other").lower()
            if change_type in NON_ALERT_EVENT_TYPES:
                non_alert_ids.append(event["id"])

        if non_alert_ids:
            db().table("changelog_events").update({"processed_at": _now_iso()}).in_(
                "id", non_alert_ids
            ).execute()
            counts["events_processed"] += len(non_alert_ids)

        for event in events:
            if counts["events_processed"] >= MAX_EVENTS_PER_RUN:
                break
            if event["id"] in non_alert_ids:
                continue
            counts["events_processed"] += 1

            tokens = event_tokens(event)

            if tokens:
                matched = [d for d in api_detections if detection_matches(d, tokens)]
            else:
                matched = api_detections if settings.alert_on_unmatched else []

            # Group matched detections by repo.
            by_repo: dict[str, list[dict]] = {}
            for d in matched:
                by_repo.setdefault(d["repo_id"], []).append(d)

            for repo_id, dets in by_repo.items():
                # Create alert rows + (possibly) email — honor admin gate.
                _handle_repo_alerts(event, repo_id, dets, counts)

            # Always mark the event processed; emailing for approved events is
            # handled (immediately here if already approved, else deferred).
            db().table("changelog_events").update({"processed_at": _now_iso()}).eq(
                "id", event["id"]
            ).execute()

    counts["remaining"] = max(0, total_pending - counts["events_processed"])
    return counts


def send_approved_alerts() -> dict[str, int]:
    """Flush emails for admin-approved changelog events with unsent alerts.

    Retained for the admin queue: approving an event (re)attempts emails for
    its high/medium-confidence alerts that have not been sent yet (e.g. ones
    that failed during processing). Low-confidence matches stay dashboard-only.
    The email itself is no longer gated on approval — this endpoint only
    retries/backfills.
    """
    counts = {"events_with_pending": 0, "repos_emailed": 0, "emails_sent": 0, "emails_failed": 0}

    # All admin-approved events that still have unsent alerts.
    events = (
        db()
        .table("changelog_events")
        .select("*")
        .eq("admin_approved", True)
        .order("detected_at", desc=True)
        .execute()
    ).data or []

    for event in events:
        # Unsent alerts for this event.
        pending = (
            db()
            .table("alerts")
            .select("*")
            .eq("changelog_event_id", event["id"])
            .eq("email_sent", False)
            .execute()
        ).data or []
        if not pending:
            continue
        counts["events_with_pending"] += 1

        # Group high/medium-confidence alerts by repo.
        by_repo: dict[str, dict] = {}  # repo_id -> {"repo": dict, "dets": [detection,...]}
        for alert in pending:
            repo_id = alert["repo_id"]
            confidence = (alert.get("confidence") or "low").lower()
            if confidence == "low":
                continue  # dashboard-only
            if repo_id not in by_repo:
                repo = (db().table("repos").select("*").eq("id", repo_id).limit(1).execute()).data
                if not repo:
                    continue
                by_repo[repo_id] = {"repo": repo[0], "dets": []}
            det = (
                db().table("api_detections").select("*")
                .eq("id", alert["api_detection_id"]).limit(1).execute()
            ).data
            if det:
                by_repo[repo_id]["dets"].append(det[0])

        for repo_id, group in by_repo.items():
            ok = _email_repo_alert_group(event, group["repo"], group["dets"], counts)
            if ok:
                counts["repos_emailed"] += 1

    return counts


def _email_repo_alert_group(event: dict, repo: dict, detections: list[dict], counts: dict) -> bool:
    """Send the alert email for one (event, repo) group. Returns True on success."""
    severity, _sr = score_severity(
        event.get("change_type") or "other",
        [d.get("file_path") or "" for d in detections],
    )
    # Phase 5 §2: mirror to Slack (best-effort) before/independent of email.
    _try_slack_alert(repo, event, severity)

    owner = (db().table("users").select("email").eq("id", repo["user_id"]).limit(1).execute()).data
    if not owner or not owner[0].get("email"):
        counts["emails_failed"] += 1
        return False
    to_email = owner[0]["email"]

    # Phase 5 §6: check agency branding for this repo owner.
    # agency_clients has NO client_user_id column — match by the owner's email
    # (client rows store client_email), and never let a branding miss break the
    # alert email flow.
    brand_name, brand_logo = None, None
    try:
        agency_row = (
            db().table("agency_clients")
            .select("client_display_name, logo_url")
            .eq("client_email", to_email)
            .limit(1)
            .execute()
        )
        if agency_row.data:
            brand_name = agency_row.data[0].get("client_display_name")
            brand_logo = agency_row.data[0].get("logo_url")
    except Exception:
        pass  # branding is best-effort; never fail the alert over it

    subject, html, text = render_alert_email(
        repo["full_name"], event, detections, severity=severity,
        confidence=event.get("confidence", "medium"),
        brand_name=brand_name, brand_logo=brand_logo,
    )

    # Central email service: respects notification preferences + dedups by
    # (event, repo) fingerprint within a 1h window, logs to email_deliveries.
    if not category_enabled(repo["user_id"], "breaking_changes"):
        counts["emails_failed"] += 0  # suppressed by user preference, not a failure
        return True

    result = send_alert_email(
        user_id=repo["user_id"],
        recipient=to_email,
        alert_type="breaking_changes",
        subject=subject,
        html=html,
        text=text,
        alert_id=detections[0].get("id"),
        fingerprint=f"alert:{event.get('id')}:{repo.get('id')}",
        context={"event_id": event.get("id"), "repo_id": repo.get("id")},
    )

    if result.get("ok"):
        sent_at = _now_iso()
        (db().table("alerts").update({"email_sent": True, "sent_at": sent_at})
            .eq("changelog_event_id", event["id"])
            .eq("repo_id", repo["id"])
            .execute())
        counts["emails_sent"] += 1
        return True
    counts["emails_failed"] += 1
    return False


def _handle_repo_alerts(event: dict, repo_id: str, detections: list[dict], counts: dict) -> None:
    """Create alert rows (with confidence) for a (event, repo) group.

    Alert rows are created for dashboard/queue visibility, and — unless the
    "breaking_changes" notification category is disabled by the owner — the
    email channel is attempted immediately for high/medium-confidence matches
    (the central email service applies dedup + daily caps). Low-confidence
    matches stay dashboard-only. `admin_approved`/`is_test` no longer gate the
    email: alerts are created WITH an attempted channel per spec.
    """
    existing = (
        db()
        .table("alerts")
        .select("*")
        .eq("changelog_event_id", event["id"])
        .eq("repo_id", repo_id)
        .execute()
    ).data or []
    existing_by_det = {a["api_detection_id"]: a for a in existing}

    severity, severity_reason = score_severity(
        event.get("change_type") or "other",
        [d.get("file_path") or "" for d in detections],
    )

    # Annotate each detection with confidence via the matching engine.
    annotated = _annotate_detections(event, detections)

    # Insert missing alert rows.
    to_insert = [
        {
            "repo_id": repo_id,
            "changelog_event_id": event["id"],
            "api_detection_id": d["id"],
            "email_sent": False,
            "severity": severity,
            "severity_reason": severity_reason,
            "confidence": conf,
            "status": "sent" if (event.get("admin_approved") or event.get("is_test")) else "pending",
            "is_test": False,
        }
        for d, conf in annotated
        if d["id"] not in existing_by_det
    ]
    inserted = []
    if to_insert:
        res = (
            db()
            .table("alerts")
            .upsert(to_insert, on_conflict="changelog_event_id,api_detection_id", ignore_duplicates=True)
            .execute()
        )
        inserted = res.data or []
        counts["alerts_created"] += len(to_insert)

    # Stamp confidence on pre-existing alert rows if missing.
    for a in existing:
        if not a.get("confidence") and a["api_detection_id"] in {d["id"] for d, _c in annotated}:
            conf = dict(annotated).get(a["api_detection_id"], "low")
            db().table("alerts").update({"confidence": conf}).eq("id", a["id"]).execute()

    all_alerts = existing + inserted
    unsent = [a for a in all_alerts if not a.get("email_sent")]
    if not unsent:
        return

    # Attempt the email channel for high/medium-confidence matches (prefs +
    # dedup + caps handled by the central email service). The admin-approval
    # safety net is removed per spec: alerts are created WITH an attempted
    # channel, not silently deferred.
    repo = (db().table("repos").select("*").eq("id", repo_id).limit(1).execute()).data
    if not repo:
        return
    repo = repo[0]

    high_med = [d for d, conf in annotated if conf != "low"]
    if not high_med:
        return  # low-confidence matches are dashboard-only

    _email_repo_alert_group(event, repo, high_med, counts)
