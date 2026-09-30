"""Internal endpoints, triggered by the GitHub Actions cron.

All are guarded by the shared X-Internal-Secret header (see deps.require_internal_secret).
"""
from __future__ import annotations

import requests
from fastapi import APIRouter, Depends, HTTPException

from ..alerts import process_new_events, send_approved_alerts
from ..config import settings
from ..db import db, fetch_one
from ..deps import require_internal_secret
from ..digest import send_weekly_digest
from ..scraper import scrape, scrape_sendgrid, scrape_github, scrape_shopify, scrape_twilio
from ..schemas import ProcessResultOut, ScrapeResultOut

router = APIRouter(prefix="/internal", tags=["internal"], dependencies=[Depends(require_internal_secret)])


@router.post("/changelog/scan-stripe", response_model=ScrapeResultOut)
def scan_stripe() -> ScrapeResultOut:
    """Scrape Stripe's changelog and insert only genuinely-new entries."""
    try:
        entries, source_url = scrape()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch Stripe changelog: {exc}")

    existing = (
        db().table("changelog_events").select("content_hash").eq("api_name", "stripe").execute()
    ).data or []
    existing_hashes = {r["content_hash"] for r in existing}

    new_rows = [
        {
            "api_name": "stripe",
            "change_type": e.change_type,
            "old_value": e.old_value,
            "new_value": e.new_value,
            "description": e.description,
            "source_url": source_url,
            "content_hash": e.content_hash,
            "symbols": ",".join(e.symbols) if e.symbols else None,
        }
        for e in entries
        if e.content_hash not in existing_hashes
    ]

    if new_rows:
        db().table("changelog_events").upsert(
            new_rows, on_conflict="api_name,content_hash", ignore_duplicates=True
        ).execute()

    return ScrapeResultOut(
        fetched_entries=len(entries), new_events=len(new_rows), source_url=source_url
    )


@router.post("/changelog/scan-sendgrid", response_model=ScrapeResultOut)
def scan_sendgrid_endpoint() -> ScrapeResultOut:
    """Scrape SendGrid's changelog and insert only genuinely-new entries."""
    try:
        entries, source_url = scrape_sendgrid()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch SendGrid changelog: {exc}")

    existing = (
        db().table("changelog_events").select("content_hash").eq("api_name", "sendgrid").execute()
    ).data or []
    existing_hashes = {r["content_hash"] for r in existing}

    new_rows = [
        {
            "api_name": "sendgrid",
            "change_type": e.change_type,
            "old_value": e.old_value,
            "new_value": e.new_value,
            "description": e.description,
            "source_url": source_url,
            "content_hash": e.content_hash,
            "symbols": ",".join(e.symbols) if e.symbols else None,
        }
        for e in entries
        if e.content_hash not in existing_hashes
    ]

    if new_rows:
        db().table("changelog_events").upsert(
            new_rows, on_conflict="api_name,content_hash", ignore_duplicates=True
        ).execute()

    return ScrapeResultOut(
        fetched_entries=len(entries), new_events=len(new_rows), source_url=source_url
    )


@router.post("/changelog/scan-github", response_model=ScrapeResultOut)
def scan_github_endpoint() -> ScrapeResultOut:
    """Scrape GitHub's changelog and insert only genuinely-new entries."""
    try:
        entries, source_url = scrape_github()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch GitHub changelog: {exc}")

    existing = (
        db().table("changelog_events").select("content_hash").eq("api_name", "github").execute()
    ).data or []
    existing_hashes = {r["content_hash"] for r in existing}

    new_rows = [
        {
            "api_name": "github",
            "change_type": e.change_type,
            "old_value": e.old_value,
            "new_value": e.new_value,
            "description": e.description,
            "source_url": source_url,
            "content_hash": e.content_hash,
            "symbols": ",".join(e.symbols) if e.symbols else None,
        }
        for e in entries
        if e.content_hash not in existing_hashes
    ]

    if new_rows:
        db().table("changelog_events").upsert(
            new_rows, on_conflict="api_name,content_hash", ignore_duplicates=True
        ).execute()

    return ScrapeResultOut(
        fetched_entries=len(entries), new_events=len(new_rows), source_url=source_url
    )


@router.post("/changelog/scan-shopify", response_model=ScrapeResultOut)
def scan_shopify_endpoint() -> ScrapeResultOut:
    """Scrape Shopify's changelog and insert only genuinely-new entries."""
    try:
        entries, source_url = scrape_shopify()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch Shopify changelog: {exc}")

    existing = (
        db().table("changelog_events").select("content_hash").eq("api_name", "shopify").execute()
    ).data or []
    existing_hashes = {r["content_hash"] for r in existing}

    new_rows = [
        {
            "api_name": "shopify",
            "change_type": e.change_type,
            "old_value": e.old_value,
            "new_value": e.new_value,
            "description": e.description,
            "source_url": source_url,
            "content_hash": e.content_hash,
            "symbols": ",".join(e.symbols) if e.symbols else None,
        }
        for e in entries
        if e.content_hash not in existing_hashes
    ]

    if new_rows:
        db().table("changelog_events").upsert(
            new_rows, on_conflict="api_name,content_hash", ignore_duplicates=True
        ).execute()

    return ScrapeResultOut(
        fetched_entries=len(entries), new_events=len(new_rows), source_url=source_url
    )


@router.post("/changelog/scan-twilio", response_model=ScrapeResultOut)
def scan_twilio_endpoint() -> ScrapeResultOut:
    """Scrape Twilio's changelog and insert only genuinely-new entries."""
    try:
        entries, source_url = scrape_twilio()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch Twilio changelog: {exc}")

    existing = (
        db().table("changelog_events").select("content_hash").eq("api_name", "twilio").execute()
    ).data or []
    existing_hashes = {r["content_hash"] for r in existing}

    new_rows = [
        {
            "api_name": "twilio",
            "change_type": e.change_type,
            "old_value": e.old_value,
            "new_value": e.new_value,
            "description": e.description,
            "source_url": source_url,
            "content_hash": e.content_hash,
            "symbols": ",".join(e.symbols) if e.symbols else None,
        }
        for e in entries
        if e.content_hash not in existing_hashes
    ]

    if new_rows:
        db().table("changelog_events").upsert(
            new_rows, on_conflict="api_name,content_hash", ignore_duplicates=True
        ).execute()

    return ScrapeResultOut(
        fetched_entries=len(entries), new_events=len(new_rows), source_url=source_url
    )


@router.post("/alerts/process", response_model=ProcessResultOut)
def process_alerts() -> ProcessResultOut:
    """Cross-reference new changelog events with detections and email users."""
    counts = process_new_events()
    send_approved_alerts()  # flush emails for admin-approved events
    return ProcessResultOut(**counts)


@router.post("/digest/send-weekly")
def send_weekly_digest_endpoint() -> dict:
    """Send weekly digest emails to all users with repos."""
    counts = send_weekly_digest()
    return {"status": "sent", **counts}


@router.get("/diagnostics/pipeline")
def pipeline_diagnostics() -> dict:
    """Why-are-alerts-not-arriving diagnostics (counts only — NO secrets, NO PII).

    Answers the email/alert "silence" question with real numbers from the
    production database: how many impact-type changelog events exist and are
    unprocessed, whether they carry matchable tokens, how many detections the
    repos have, and what the email pipeline has actually logged in
    email_deliveries (its insert path logs even skipped attempts).
    """
    def _count(table: str, **filters) -> int:
        try:
            q = db().table(table).select("id", count="exact")
            for col, val in filters.items():
                if val is None:
                    q = q.is_(col, "null")
                else:
                    q = q.eq(col, val)
            res = q.execute()
            return int(getattr(res, "count", None) or len(res.data or []))
        except Exception as e:  # noqa: BLE001 — diagnostics must never 500
            return -1

    impact_types = ["BREAKING_CHANGE", "DEPRECATION", "SECURITY_CHANGE",
                    "ENDPOINT_CHANGE", "API_VERSION_CHANGE",
                    "REQUEST_SCHEMA_CHANGE", "RESPONSE_SCHEMA_CHANGE",
                    "AUTH_CHANGE", "RATE_LIMIT_CHANGE"]

    out: dict = {
        "impact_type_events": {t: _count("changelog_events", change_type=t) for t in impact_types},
        "all_events": _count("changelog_events"),
        "unprocessed_events": _count("changelog_events", processed_at=None),
        "unprocessed_impact_events": _count(
            "changelog_events", processed_at=None, change_type="BREAKING_CHANGE"
        ) + sum(
            _count("changelog_events", processed_at=None, change_type=t)
            for t in impact_types[1:]
        ),
        "repos": _count("repos"),
        "api_detections": _count("api_detections"),
        "alerts": _count("alerts"),
        "email_deliveries": _count("email_deliveries"),
        "email_sent": _count("email_deliveries", status="sent"),
        "email_failed": _count("email_deliveries", status="failed"),
        "email_failed_sender_config": _count("email_deliveries", error_category="sender_config"),
        "email_failed_no_recipient": _count("email_deliveries", error_category="no_recipient"),
        "email_failed_rate_limit": _count("email_deliveries", error_category="rate_limit"),
        "digital_twin_runs": _count("digital_twin_runs"),
        "digital_twin_analyses": _count("digital_twin_analyses"),
    }
    return out


@router.post("/migrate-digital-twin")
def migrate_digital_twin() -> dict:
    """Apply the additive Digital Twin migration (idempotent, IF NOT EXISTS).

    Mirrors migrate-phase-b: runs each statement via the exec_sql RPC and
    reports per-statement ok/skipped honestly. If the exec_sql RPC is not
    available, every statement reports skipped with the error so the SQL can
    be applied manually in the Supabase dashboard.
    """
    from pathlib import Path

    sql_path = Path(__file__).resolve().parents[3] / "db" / "migration_digital_twin.sql"
    statements: list[str] = []
    if sql_path.exists():
        raw = sql_path.read_text(encoding="utf-8")
        # Split on semicolons at end of statement; strip comment-only chunks.
        for chunk in raw.split(";"):
            lines = [l for l in chunk.splitlines() if not l.strip().startswith("--")]
            stmt = "\n".join(lines).strip()
            if stmt:
                statements.append(stmt)
    else:
        return {"status": "error", "detail": f"migration file not found: {sql_path}"}

    results = []
    for sql in statements:
        try:
            db().postgrest.rpc("exec_sql", {"query": sql}).execute()
            results.append({"sql": sql[:60].replace("\n", " "), "status": "ok"})
        except Exception as e:  # noqa: BLE001 — report honestly, never 500
            results.append({"sql": sql[:60].replace("\n", " "), "status": "skipped", "error": str(e)[:150]})
    ok = sum(1 for r in results if r["status"] == "ok")
    return {
        "status": "migration_complete" if ok == len(results) and ok > 0 else "partial_or_skipped",
        "statements_ok": ok,
        "statements_total": len(results),
        "results": results,
    }


@router.post("/digital-twin/run/{repo_id}")
def run_digital_twin_internal(repo_id: str) -> dict:
    """Cron-triggered Digital Twin run for ONE repository (repository-scoped).

    Same engine as the user-facing endpoint; emails are NOT sent for cron
    runs (the user-triggered flow owns email). Used for scheduled simulations
    and for verifying the pipeline with real production data.
    """
    repo = fetch_one("repos", {"id": repo_id})
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    from ..digital_twin import run_digital_twin

    result = run_digital_twin(
        repo_id=repo_id,
        repo_name=repo.get("full_name") or "",
        triggered_by="cron",
    )
    return {
        "run_id": result.run_id,
        "repository_id": result.repository_id,
        "events_considered": result.events_considered,
        "analyses_created": result.analyses_created,
        "no_match_count": result.no_match_count,
        "alerts_created": result.alerts_created,
        "email_status": result.email_status,
        "findings": [
            {
                "affected_file": f.affected_file,
                "affected_symbol": f.affected_symbol,
                "line_number": f.line_number,
                "impact_status": f.impact_status,
                "severity": f.severity,
                "confidence": f.confidence,
            }
            for f in result.findings
        ],
    }


@router.get("/digital-twin/repo-ids")
def list_twin_repo_ids() -> dict:
    """Repository ids + names for cron-driven Digital Twin runs (no secrets)."""
    try:
        rows = (
            db().table("repos")
            .select("id, full_name")
            .order("connected_at", desc=True)
            .limit(50)
            .execute()
        ).data or []
    except Exception as e:  # noqa: BLE001
        return {"repos": [], "error": str(e)[:150]}
    return {"repos": rows}


@router.post("/migrate-phase-b")
def migrate_phase_b() -> dict:
    """Run Phase B database migration. Safe to call multiple times (uses IF NOT EXISTS)."""
    results = []
    
    # SQL statements to run
    migrations = [
        "ALTER TABLE changelog_events ADD COLUMN IF NOT EXISTS content_hash TEXT",
        "ALTER TABLE changelog_events ADD COLUMN IF NOT EXISTS admin_approved BOOLEAN DEFAULT FALSE",
        "ALTER TABLE changelog_events ADD COLUMN IF NOT EXISTS approved_by UUID",
        "ALTER TABLE changelog_events ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ",
        "ALTER TABLE changelog_events ADD COLUMN IF NOT EXISTS disabled BOOLEAN DEFAULT FALSE",
        "ALTER TABLE changelog_events ADD COLUMN IF NOT EXISTS disabled_by UUID",
        "ALTER TABLE changelog_events ADD COLUMN IF NOT EXISTS disabled_at TIMESTAMPTZ",
        "ALTER TABLE changelog_events ADD COLUMN IF NOT EXISTS disabled_reason TEXT",
        "ALTER TABLE changelog_events ADD COLUMN IF NOT EXISTS affected_endpoints JSONB",
        "ALTER TABLE changelog_events ADD COLUMN IF NOT EXISTS affected_sdks JSONB",
        "ALTER TABLE changelog_events ADD COLUMN IF NOT EXISTS affected_versions JSONB",
        "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS confidence TEXT DEFAULT 'medium'",
    ]
    
    for sql in migrations:
        try:
            db().postgrest.rpc("exec_sql", {"query": sql}).execute()
            results.append({"sql": sql[:60], "status": "ok"})
        except Exception as e:
            results.append({"sql": sql[:60], "status": "skipped", "error": str(e)[:100]})
    
    return {"status": "migration_complete", "results": results}
