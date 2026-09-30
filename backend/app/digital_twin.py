"""Breaklytix — API Digital Twin engine.

Answers ONE question better than a normal monitoring tool:
  "WHAT EXACTLY WILL BREAK IN MY CODE, AND WHAT DO I NEED TO CHANGE?"

Digital Twin = simulate the FUTURE provider state (real, already-detected
provider changelog events) against a SPECIFIC repository's REAL scanned API
usage (api_detections rows), and produce exact file / symbol / line evidence.

Feature boundaries (no duplication of existing systems):
  * Provider Monitoring (global): "What changed at the provider?"
  * Impact Engine (repo):         "What in this repository is affected?"
  * Fire Drill (repo):            "What could happen if this reaches us?"
  * Digital Twin (repo):          "Simulate the future provider state against
                                   THIS repository and show the exact impact."
  * Auto-Fix (repo):              "Prepare a reviewable GitHub PR."

Digital Twin REUSES the Impact Engine's analyzer (matching + severity +
confidence + verification) so all systems share the same normalized change
event and repository usage evidence.  It adds:
  * explicit STATIC impact status labels (SAFE / NO MATCH / POTENTIAL IMPACT /
    HIGH RISK / BREAKING RISK / UNKNOWN) — static analysis NEVER claims
    production is already failing;
  * per-usage analysis rows (file / symbol / line / snippet evidence);
  * a persisted, idempotent simulation run per repository;
  * alert creation via the EXISTING alerts pipeline only.

No-fabrication rules:
  * Only REAL changelog_events rows and REAL api_detections rows are used.
  * affected_file / affected_symbol / line_number are set ONLY from detection
    evidence; otherwise they stay None and the explanation says
    "Evidence not available".
  * source_url is copied from the provider event only; never invented
    ("Source URL not available." when absent).
  * Email is attempted only through email_service.send_alert_email; when
    Resend is not configured the result truthfully reports that delivery was
    not configured/verified.
  * Repositories without detections for the changed provider are skipped —
    no NO_MATCH rows, no alerts for non-users of the API.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .db import db
from .impact.analyzer import analyze_changelog_event
from .impact.severity import calculate_impact_severity
from .changelog.matching import match_event_to_detection

logger = logging.getLogger("autofix.digital_twin")

# Static analysis labels — NEVER "production is failing".
STATUS_NO_MATCH = "NO MATCH"
STATUS_SAFE = "SAFE"
STATUS_POTENTIAL = "POTENTIAL IMPACT"
STATUS_HIGH_RISK = "HIGH RISK"
STATUS_BREAKING_RISK = "BREAKING RISK"
STATUS_UNKNOWN = "UNKNOWN"

STATIC_STATUS_BY_SEVERITY = {
    "breaking": STATUS_BREAKING_RISK,
    "high": STATUS_HIGH_RISK,
    "medium": STATUS_POTENTIAL,
    "low": STATUS_POTENTIAL,
    "safe": STATUS_SAFE,
    "unknown": STATUS_UNKNOWN,
}

# Changelog event types the Digital Twin simulates.  Non-impact types
# (new features, bug fixes) are skipped — they cannot break repository code.
SIMULATED_CHANGE_TYPES = ("BREAKING_CHANGE", "DEPRECATION", "SECURITY_CHANGE")

MAX_EVENTS_PER_RUN = 10


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TwinUsageFinding:
    """One affected (or matched-but-evidence-poor) usage in the repository."""
    api_detection_id: str | None
    affected_file: str | None = None
    affected_symbol: str | None = None
    line_number: int | None = None
    usage_context: str | None = None
    explanation: str = ""
    recommended_change: str | None = None
    severity: str = "unknown"
    confidence: float = 0.0
    impact_status: str = STATUS_UNKNOWN
    matched_fields: list[str] = field(default_factory=list)


@dataclass
class TwinRunResult:
    """Result of one Digital Twin simulation run for one repository."""
    run_id: str | None = None
    repository_id: str = ""
    provider_filter: str | None = None
    events_considered: int = 0
    analyses_created: int = 0
    no_match_count: int = 0
    findings: list[TwinUsageFinding] = field(default_factory=list)
    alerts_created: int = 0
    email_status: str = "not_attempted"   # sent | failed | skipped_* | not_attempted
    email_detail: str | None = None
    last_simulated_at: str = ""
    triggered_by: str = "user"             # user | cron


# ---------------------------------------------------------------------------
# Evidence extraction helpers
# ---------------------------------------------------------------------------
def _symbol_from_detection(detection: dict) -> str | None:
    """Best-effort code symbol from a detection row.  Returns None when the
    scan recorded no symbols — never a guessed name."""
    symbols = detection.get("symbols")
    if not symbols:
        return None
    if isinstance(symbols, str):
        symbols = [s.strip() for s in symbols.split(",") if s.strip()]
    return symbols[0] if symbols else None


def _recommended_change(change_type: str, match_fields: list[str]) -> str | None:
    """Actionable guidance derived from the change type and what matched.
    Generic only when evidence is generic — exact evidence yields exact text."""
    ct = (change_type or "").upper()
    if "REMOVED" in ct or ct == "BREAKING_CHANGE":
        base = "Remove or replace the affected usage — the provider removed/broke it."
    elif ct == "DEPRECATION":
        base = "Migrate the affected usage to the supported replacement before the provider removes it."
    elif ct == "SECURITY_CHANGE":
        base = "Update authentication/secret handling for the affected usage per the provider's security guidance."
    elif ct in ("API_VERSION_CHANGE", "ENDPOINT_CHANGE", "REQUEST_SCHEMA_CHANGE", "RESPONSE_SCHEMA_CHANGE"):
        base = "Update the affected call to the new endpoint/version/shape documented by the provider."
    elif ct in ("SDK_CHANGE",):
        base = "Upgrade the affected SDK package to a version compatible with the provider change."
    elif ct in ("RATE_LIMIT_CHANGE", "BEHAVIOR_CHANGE"):
        base = "Review the affected usage against the provider's new limits/behavior."
    else:
        return None
    if "symbol" in match_fields:
        base += " The exact symbol using the changed API is identified in the evidence."
    if "endpoint" in match_fields:
        base += " The exact endpoint call is identified in the evidence."
    return base


def _analyze_event_usage(
    event: dict,
    detections: list[dict],
    repo_packages: list[str] | None,
) -> tuple[list[TwinUsageFinding], int]:
    """Match one real changelog event against real detections.

    Returns (findings, no_match_count).
    A detection with NO field match at all does not become a finding (that
    would be fabrication); only provider-level matches become findings, and
    weak matches carry POTENTIAL IMPACT / evidence-not-available text.
    """
    provider = event.get("api_name") or event.get("provider", "")
    change_type = event.get("change_type") or "unknown"
    findings: list[TwinUsageFinding] = []
    provider_only_matches = 0

    for detection in detections:
        # A detection of a DIFFERENT provider is never affected by this event —
        # never fabricate a cross-provider finding (defense in depth: the
        # caller already filters detections by the event's provider).
        det_api = (detection.get("api_name") or "").lower()
        if det_api and provider and det_api != provider.lower():
            continue
        result = match_event_to_detection(event, detection, repo_packages)
        if not result.matched_fields:
            continue  # no match — this usage is NOT affected (no fake rows)

        fields = list(result.matched_fields)
        # Severity/confidence for THIS usage via the shared engine.
        sev, conf = calculate_impact_severity(
            change_type=change_type,
            matched_count=1,
            matched_fields=fields,
            has_endpoint="endpoint" in fields,
            has_sdk=bool(repo_packages) and "package" in fields,
            has_old_value=bool(event.get("old_value")),
            has_new_value=bool(event.get("new_value")),
        )
        status = STATIC_STATUS_BY_SEVERITY.get(sev, STATUS_UNKNOWN)

        snippet = detection.get("matched_snippet") or None
        symbol = _symbol_from_detection(detection)
        evidence_parts: list[str] = []
        if detection.get("file_path"):
            evidence_parts.append(
                f"Detected usage: {detection['file_path']}"
                + (f":{detection['line_number']}" if detection.get("line_number") else "")
            )
        if snippet:
            evidence_parts.append(f"Code context recorded by the scanner.")
        if fields:
            evidence_parts.append(f"Matched on: {', '.join(fields)}")
        explanation = " ".join(evidence_parts) if evidence_parts else "Evidence not available."
        if not snippet:
            explanation += " Full code context not available from the last scan."
        if not symbol:
            explanation += " Exact function/symbol not identified in scan evidence."

        if fields == ["provider"]:
            provider_only_matches += 1
            explanation = (
                f"Repository uses the {provider} SDK/integration, but no specific "
                "endpoint/symbol match to this change was found in scan evidence. "
                "Evidence not available for an exact code location."
            )

        findings.append(TwinUsageFinding(
            api_detection_id=detection.get("id"),
            affected_file=detection.get("file_path") or None,
            affected_symbol=symbol,
            line_number=detection.get("line_number"),
            usage_context=snippet,
            explanation=explanation,
            recommended_change=_recommended_change(change_type, fields),
            severity=sev,
            confidence=round(float(conf), 2),
            impact_status=status,
            matched_fields=fields,
        ))
    return findings, provider_only_matches


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
def _persist_run(repo_id: str, result: TwinRunResult, status: str = "completed",
                 error_message: str | None = None) -> str | None:
    try:
        row = {
            "repository_id": repo_id,
            "triggered_by": getattr(result, "triggered_by", "user") or "user",
            "status": status,
            "events_considered": result.events_considered,
            "analyses_created": result.analyses_created,
            "no_match_count": result.no_match_count,
            "error_message": error_message[:500] if error_message else None,
            "created_at": _now_iso(),
        }
        res = db().table("digital_twin_runs").insert(row).execute()
        return (res.data or [{}])[0].get("id")
    except Exception as e:  # noqa: BLE001 — run logging is best-effort
        logger.warning("digital_twin run insert failed: %s", e)
        return None


def _persist_analyses(repo_id: str, event: dict, findings: list[TwinUsageFinding],
                      run_id: str | None) -> int:
    """Insert (repo, event, usage) rows idempotently.  Returns rows written."""
    if not findings:
        return 0
    source_url = event.get("source_url") or None  # never invent a URL
    rows = []
    for f in findings:
        rows.append({
            "repository_id": repo_id,
            "provider_id": event.get("api_name") or event.get("provider", ""),
            "change_event_id": event.get("id"),
            "impact_status": f.impact_status,
            "severity": f.severity,
            "confidence": f.confidence,
            "affected_file": f.affected_file,
            "affected_symbol": f.affected_symbol,
            "line_number": f.line_number,
            "usage_context": (f.usage_context or "")[:1000] or None,
            "explanation": f.explanation[:2000],
            "recommended_change": (f.recommended_change or "")[:1000] or None,
            "source_url": source_url,
            "api_detection_id": f.api_detection_id,
            "run_id": run_id,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        })
    try:
        res = db().table("digital_twin_analyses").upsert(
            rows,
            on_conflict="repository_id,change_event_id,api_detection_id",
            ignore_duplicates=True,
        ).execute()
        return len(res.data or [])
    except Exception as e:  # noqa: BLE001
        logger.warning("digital_twin analyses upsert failed: %s", e)
        # Fallback: insert one-by-one, tolerating duplicate-key races.
        written = 0
        for r in rows:
            try:
                res = db().table("digital_twin_analyses").insert(r).execute()
                if res.data:
                    written += 1
            except Exception:
                pass
        return written


# ---------------------------------------------------------------------------
# Alert via the EXISTING pipeline (alerts table + email_service only)
# ---------------------------------------------------------------------------
def _persist_alert(repo_id: str, event: dict, findings: list[TwinUsageFinding]) -> tuple[str | None, bool]:
    """Create ONE in-app alert row for this (event, repo) from real evidence.
    Reuses the alerts table so Notification Center / dedup stay unified.
    Dedup: one alert per (changelog_event_id, api_detection_id) — the same
    constraint the alerts pipeline already enforces.
    Returns (alert_id, created) — created is False when deduped/failed."""
    top = max(findings, key=lambda f: f.confidence)
    try:
        existing = (
            db().table("alerts")
            .select("id")
            .eq("changelog_event_id", event["id"])
            .eq("repo_id", repo_id)
            .limit(1)
            .execute()
        ).data or []
        if existing:
            return existing[0].get("id"), False  # already alerted for this event — dedup
        res = db().table("alerts").insert({
            "repo_id": repo_id,
            "changelog_event_id": event["id"],
            "api_detection_id": top.api_detection_id,
            "email_sent": False,
            "severity": top.severity if top.severity in ("breaking", "high", "medium", "low") else "medium",
            "severity_reason": f"Digital Twin: {top.impact_status}",
            "confidence": ("high" if top.confidence >= 0.75
                           else "medium" if top.confidence >= 0.45 else "low"),
            "status": "pending",
            "is_test": False,
        }).execute()
        return (res.data or [{}])[0].get("id"), True
    except Exception as e:  # noqa: BLE001
        logger.warning("digital_twin alert insert failed: %s", e)
        return None, False


def _send_twin_email(repo_id: str, event: dict, findings: list[TwinUsageFinding],
                     alert_id: str | None, repo_name: str) -> tuple[str, str | None]:
    """Email via the existing email_service (Resend) — respects preferences,
    dedup, caps.  Truthful when Resend is not configured."""
    try:
        from .email_service import send_alert_email, resolve_user_email, sender_problem

        # Log the delivery attempt even when the recipient/config is missing —
        # "nothing arrived in the inbox" must be diagnosable from the DB.
        def _log_email_attempt(status: str, error_category: str | None) -> None:
            try:
                db().table("email_deliveries").insert({
                    "user_id": user_id,
                    "alert_id": alert_id,
                    "alert_type": "digital_twin",
                    "recipient": recipient or "",
                    "subject": subject,
                    "status": status,
                    "provider": "resend",
                    "error_category": error_category,
                }).execute()
            except Exception:  # noqa: BLE001 — delivery logging never breaks the run
                pass

        repo = (db().table("repos").select("user_id").eq("id", repo_id).limit(1).execute()).data or []
        if not repo:
            return "skipped_no_user", None
        user_id = repo[0].get("user_id")

        recipient = resolve_user_email(user_id)
        problem = sender_problem()
        if not recipient or problem:
            detail = (
                "Email delivery not configured/verified." if problem
                else "No recipient email on file for the repository owner."
            )
            _log_email_attempt("skipped", "sender_config" if problem else "no_recipient")
            return ("skipped_email_not_configured", detail)

        top = max(findings, key=lambda f: f.confidence)
        files = "\n".join(
            f"• {f.affected_file}" + (f" — line {f.line_number}" if f.line_number else "")
            + (f" — {f.affected_symbol}()" if f.affected_symbol else "")
            for f in findings[:6] if f.affected_file
        ) or "Evidence not available"
        src = event.get("source_url") or "Source URL not available."
        conf_pct = int(round(top.confidence * 100))
        change_type = (event.get("change_type") or "change").replace("_", " ").title()
        sev_label = {"breaking": "BREAKING RISK", "high": "HIGH RISK"}.get(top.severity, top.impact_status)

        subject = f"Breaklytix Digital Twin: {sev_label} — {repo_name}"
        html = f"""<div style="font-family:sans-serif;max-width:640px">
  <h2 style="margin:0 0 4px">🔴 API Change Impact Detected</h2>
  <p style="color:#555;margin:0 0 16px">Simulated against <b>{repo_name}</b> before the provider change reaches production.</p>
  <p><b>Provider:</b> {event.get("provider_display") or event.get("api_name", "")}</p>
  <p><b>What changed:</b> {change_type} — {(event.get("title") or event.get("description") or "")[:300]}</p>
  <p><b>Affected files:</b></p><pre style="white-space:pre-wrap">{files}</pre>
  <p><b>Why:</b> {top.explanation[:400]}</p>
  <p><b>What to change:</b> {top.recommended_change or "See the official source for migration guidance."}</p>
  <p><b>Severity:</b> {sev_label} &nbsp; <b>Confidence:</b> {conf_pct}%</p>
  <p><b>Official source:</b> <a href="{src}">{src}</a></p>
  <p style="color:#888;font-size:13px">Static simulation — not a claim that production is failing.</p>
</div>"""
        text = (
            f"API Change Impact Detected — {repo_name}\n"
            f"Provider: {event.get('api_name','')}\nWhat changed: {change_type}\n"
            f"Affected files:\n{files}\nWhy: {top.explanation[:400]}\n"
            f"What to change: {top.recommended_change or ''}\n"
            f"Severity: {sev_label}  Confidence: {conf_pct}%\nSource: {src}"
        )
        result = send_alert_email(
            user_id=user_id,
            recipient=recipient,
            alert_type="digital_twin",
            subject=subject,
            html=html,
            text=text,
            alert_id=alert_id,
            context={"kind": "digital_twin", "repo_id": repo_id, "event_id": event.get("id")},
        )
        if result.get("ok"):
            return "sent", result.get("provider_message_id")
        if result.get("skipped_duplicate"):
            return "skipped_duplicate", "Already sent for this event."
        return ("failed", result.get("detail") or result.get("error_category") or "Email delivery not verified.")
    except Exception as e:  # noqa: BLE001
        logger.warning("digital_twin email failed: %s", e)
        return ("failed", "Email delivery not configured/verified.")


# ---------------------------------------------------------------------------
# Main entry: run the simulation for ONE repository (repository-scoped ALWAYS)
# ---------------------------------------------------------------------------
def run_digital_twin(
    repo_id: str,
    repo_name: str,
    provider: str | None = None,
    changelog_event_id: str | None = None,
    triggered_by: str = "user",
) -> TwinRunResult:
    """Simulate real provider changes against one repository's real usage.

    repository_id is REQUIRED — there is no global mode.  Detections are
    filtered by repo_id at the query; events are global provider facts.
    """
    result = TwinRunResult(repository_id=repo_id, provider_filter=provider)
    result.triggered_by = triggered_by  # recorded by _persist_run

    # 1) This repository's REAL scanned usage (repo-scoped query).
    det_query = (
        db().table("api_detections")
        .select("id, repo_id, api_name, file_path, line_number, matched_snippet, symbols")
        .eq("repo_id", repo_id)
    )
    if provider:
        det_query = det_query.eq("api_name", provider)
    detections = (det_query.execute()).data or []

    # 2) Real provider events to simulate (global provider facts).
    ev_query = (
        db().table("changelog_events")
        .select("*")
        .in_("change_type", list(SIMULATED_CHANGE_TYPES))
        .order("detected_at", desc=True)
        .limit(MAX_EVENTS_PER_RUN if not changelog_event_id else 1)
    )
    if changelog_event_id:
        ev_query = ev_query.eq("id", changelog_event_id)
    elif provider:
        ev_query = ev_query.eq("api_name", provider)
    events = (ev_query.execute()).data or []
    result.events_considered = len(events)

    # Repo packages for SDK matching (from latest scan summary, if any).
    repo_packages: list[str] = []
    try:
        scans = (
            db().table("scans")
            .select("summary")
            .eq("repo_id", repo_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        ).data or []
        summary = scans[0].get("summary") if scans else None
        if isinstance(summary, str):
            summary = json.loads(summary) if summary else None
        pkgs = (summary or {}).get("packages")
        if isinstance(pkgs, list):
            repo_packages = [p for p in pkgs if isinstance(p, str)]
    except Exception:  # noqa: BLE001 — packages are optional evidence
        repo_packages = []

    if not detections:
        # This repository uses none of the monitored APIs (for this provider):
        # truthfully a NO MATCH — no findings, no analyses, no alerts.
        result.no_match_count = len(events)
        result.last_simulated_at = _now_iso()
        result.run_id = _persist_run(repo_id, result)
        return result
    # Persist the run FIRST so analysis rows can reference run_id.
    result.run_id = _persist_run(repo_id, result, status="running")

    seen_pairs: set[tuple] = set()
    email_done = False
    for event in events:
        provider_name = event.get("api_name") or event.get("provider", "")
        event_detections = [
            d for d in detections if (d.get("api_name") or "").lower() == provider_name.lower()
        ]
        if not event_detections:
            result.no_match_count += 1
            continue

        findings, provider_only = _analyze_event_usage(event, event_detections, repo_packages or None)
        if not findings:
            result.no_match_count += 1
            continue

        written = _persist_analyses(repo_id, event, findings, result.run_id)
        result.analyses_created += written
        result.findings.extend(findings)    # Alert + ONE email per run (not per event) via existing pipelines.
    meaningful = [f for f in findings if f.impact_status in
                  (STATUS_BREAKING_RISK, STATUS_HIGH_RISK, STATUS_POTENTIAL)]
    if meaningful:
        alert_id, created = _persist_alert(repo_id, event, meaningful)
        if created:
            result.alerts_created += 1
        if not email_done and triggered_by == "user":
            status, detail = _send_twin_email(repo_id, event, meaningful, alert_id, repo_name)
            result.email_status, result.email_detail = status, detail
            email_done = True

    result.last_simulated_at = _now_iso()
    # Finalize the run row persisted earlier with status="running".
    if result.run_id:
        try:
            db().table("digital_twin_runs").update({
                "status": "completed",
                "events_considered": result.events_considered,
                "analyses_created": result.analyses_created,
                "no_match_count": result.no_match_count,
            }).eq("id", result.run_id).execute()
        except Exception as e:  # noqa: BLE001 — run logging is best-effort
            logger.warning("digital_twin run update failed: %s", e)
    return result



# ---------------------------------------------------------------------------
# Read APIs (repository-scoped, used by the router after ownership check)
# ---------------------------------------------------------------------------
def get_repo_twin_summary(repo_id: str) -> dict:
    """Aggregates for the flagship card — every query filtered by repo_id."""
    rows = (
        db().table("digital_twin_analyses")
        .select("impact_status, severity, confidence, provider_id, change_event_id, created_at")
        .eq("repository_id", repo_id)
        .order("created_at", desc=True)
        .limit(500)
        .execute()
    ).data or []
    by_status: dict[str, int] = {}
    providers: set[str] = set()
    events: set[str] = set()
    high_risk = breaking = safe = potential = 0
    for r in rows:
        st = r.get("impact_status") or STATUS_UNKNOWN
        by_status[st] = by_status.get(st, 0) + 1
        providers.add(r.get("provider_id") or "")
        if r.get("change_event_id"):
            events.add(r["change_event_id"])
        if st == STATUS_BREAKING_RISK:
            breaking += 1
        elif st == STATUS_HIGH_RISK:
            high_risk += 1
        elif st == STATUS_POTENTIAL:
            potential += 1
        elif st == STATUS_SAFE:
            safe += 1
    runs = (
        db().table("digital_twin_runs")
        .select("created_at, events_considered, analyses_created, no_match_count, status")
        .eq("repository_id", repo_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    ).data or []
    last_run = runs[0] if runs else None
    return {
        "repository_id": repo_id,
        "provider_changes": len(events),
        "affected_usages": len(rows),
        "potential_breaks": potential + high_risk + breaking,
        "high_risk": high_risk,
        "breaking_risk": breaking,
        "safe": safe,
        "by_status": by_status,
        "providers": sorted(p for p in providers if p),
        "last_simulation": (last_run or {}).get("created_at"),
        "last_run": last_run,
    }


def get_repo_twin_analyses(
    repo_id: str,
    limit: int = 100,
    offset: int = 0,
    provider: str | None = None,
    status: str | None = None,
) -> list[dict]:
    """Analysis rows for one repository — ALWAYS repo-scoped."""
    query = (
        db().table("digital_twin_analyses")
        .select("*")
        .eq("repository_id", repo_id)
        .order("created_at", desc=True)
        .range(offset, offset + max(1, min(limit, 500)) - 1)
    )
    if provider:
        query = query.eq("provider_id", provider)
    if status:
        query = query.eq("impact_status", status)
    return (query.execute()).data or []


def get_twin_analysis(analysis_id: str, repository_id: str) -> dict | None:
    """One analysis — must belong to repository_id (isolation guard)."""
    rows = (
        db().table("digital_twin_analyses")
        .select("*")
        .eq("id", analysis_id)
        .eq("repository_id", repository_id)
        .limit(1)
        .execute()
    ).data or []
    return rows[0] if rows else None
