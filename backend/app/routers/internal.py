"""Internal endpoints, triggered by the GitHub Actions cron.

All are guarded by the shared X-Internal-Secret header (see deps.require_internal_secret).
"""
from __future__ import annotations

import requests
from fastapi import APIRouter, Depends, HTTPException

from ..alerts import process_new_events, send_approved_alerts
from ..config import settings
from ..db import db
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
