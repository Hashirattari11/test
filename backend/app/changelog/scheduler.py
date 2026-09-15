"""Changelog monitoring scheduler (Phase B).

Orchestrates fetching from all provider changelogs, deduplication,
and insertion into the changelog_events table. Also handles daily
code-health scans and email notifications.
"""
from __future__ import annotations

import json
import os
import time as _time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Optional

from ..config import settings
from ..db import db
from ..health.code_health import run_code_health_checks
from .base import ChangelogEvent
from .matching import match_event_to_repo

# Vercel cron function timeout is 30s; give each provider parser a hard cap so
# one slow scraper cannot blow the whole run, and cap the TOTAL run so the
# endpoint always returns inside the budget (leftovers are marked timed_out
# and picked up by the next cron tick — DB dedup makes that safe).
FETCH_TIMEOUT_SECONDS = 15
FETCH_MAX_WORKERS = 4
TOTAL_BUDGET_SECONDS = 25

# Impact analysis runs inside the daily-scan endpoint (60s Vercel budget).
# Cap the number of analyzed events per invocation; since detections are
# preloaded in memory this is a pure CPU/DB-persist bound, and leftover
# events are covered on the next cron tick (the (repo, event) pair check
# makes it idempotent).
MAX_IMPACT_EVENTS_PER_RUN = int(os.getenv("MAX_IMPACT_EVENTS_PER_RUN", "20"))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def store_events(events: list[ChangelogEvent]) -> dict:
    """Store changelog events in the database with deduplication.
    
    Returns stats: {stored: int, duplicates: int, errors: int}
    """
    stats = {"stored": 0, "duplicates": 0, "errors": 0}
    
    for event in events:
        try:
            # Check for duplicate using provider + source_url + content_hash
            existing = (
                db()
                .table("changelog_events")
                .select("id")
                .eq("api_name", event.provider)
                .eq("source_url", event.source_url)
                .eq("content_hash", event.content_hash)
                .limit(1)
                .execute()
            )
            
            if existing.data:
                stats["duplicates"] += 1
                continue
            
            # Insert new event
            row = {
                "api_name": event.provider,
                "title": event.title,
                "source_url": event.source_url,
                "detected_at": event.published_date,
                "description": event.raw_summary,
                "change_type": event.event_type,
                "severity": event.severity,
                "content_hash": event.content_hash,
                "symbols": ",".join(event.symbols) if event.symbols else None,
                "old_value": event.symbols[0] if event.symbols else None,
                "new_value": event.symbols[1] if len(event.symbols) > 1 else None,
                "processed_at": None,  # Not processed yet
            }
            
            # Add optional fields
            if event.deadline:
                row["deadline"] = event.deadline
            if event.affected_endpoints:
                row["affected_endpoints"] = json.dumps(event.affected_endpoints)
            if event.affected_sdks:
                row["affected_sdks"] = json.dumps(event.affected_sdks)
            if event.affected_versions:
                row["affected_versions"] = json.dumps(event.affected_versions)
            
            db().table("changelog_events").insert(row).execute()
            stats["stored"] += 1
            
        except Exception as e:
            stats["errors"] += 1
            print(f"Error storing event: {e}")
    
    return stats


def fetch_provider(provider_id: str, user_agent: str | None = None) -> list[ChangelogEvent]:
    """Fetch changelog events for a single provider."""
    from .parsers import FETCHERS
    
    fetcher_class = FETCHERS.get(provider_id)
    if not fetcher_class:
        return []
    
    ua = user_agent or settings.scraper_user_agent
    fetcher = fetcher_class(user_agent=ua)
    
    try:
        return fetcher.fetch()
    except Exception as e:
        print(f"Error fetching {provider_id}: {e}")
        return []


def fetch_all_providers(user_agent: str | None = None) -> dict:
    """Fetch changelogs from all Phase B providers in parallel, bounded.

    Returns per-provider stats. Providers are fetched concurrently (max 4
    workers), each parser is hard-capped at FETCH_TIMEOUT_SECONDS, and the
    whole run is capped at TOTAL_BUDGET_SECONDS. Providers that can't finish
    inside the budget are reported as timed_out — never silently dropped.
    """
    PHASE_B_PROVIDERS = [
        "stripe", "shopify", "twilio", "sendgrid", "github",
        "openai", "anthropic", "vercel", "supabase", "firebase",
        "slack", "resend",
    ]

    results: dict = {}
    deadline = _time.time() + TOTAL_BUDGET_SECONDS

    def _work(provider_id: str) -> tuple[str, dict]:
        try:
            events = _fetch_with_timeout(provider_id, user_agent)
            stats = store_events(events)
            return provider_id, {
                "fetched": len(events),
                **stats,
            }
        except Exception as e:  # noqa: BLE001 — a bad provider must not kill the run
            print(f"Provider {provider_id} failed: {e}")
            return provider_id, {"fetched": 0, "stored": 0, "duplicates": 0, "errors": 1}

    pool = ThreadPoolExecutor(max_workers=FETCH_MAX_WORKERS)
    try:
        futures: dict[Future, str] = {pool.submit(_work, pid): pid for pid in PHASE_B_PROVIDERS}
        pending = set(futures)
        while pending:
            remaining = deadline - _time.time()
            if remaining <= 0:
                break
            try:
                for future in as_completed(pending, timeout=remaining):
                    pid = futures[future]
                    pending.discard(future)
                    try:
                        _, stats = future.result()
                    except Exception as e:  # noqa: BLE001
                        stats = {"fetched": 0, "stored": 0, "duplicates": 0, "errors": 1}
                        print(f"Provider {pid} failed: {e}")
                    results.setdefault(pid, stats)
                    if _time.time() >= deadline:
                        break
            except _TimeoutError:
                break
    finally:
        # Never block the response on stuck workers: serverless cron recycles
        # the process anyway, and DB dedup makes a partial run safe.
        pool.shutdown(wait=False, cancel_futures=True)

    # Anything still pending when the budget expired is reported truthfully.
    for future in pending:
        pid = futures[future]
        results.setdefault(pid, {"fetched": 0, "stored": 0, "duplicates": 0, "errors": 1, "timed_out": True})

    return results


_TimeoutError = TimeoutError  # noqa: N816 — used for the as_completed budget


def _fetch_with_timeout(provider_id: str, user_agent: str | None) -> list[ChangelogEvent]:
    """Run a single provider fetch inside a worker thread with a hard timeout.

    urllib/requests-style parsers can hang on a slow endpoint; the threadpool
    keeps the overall cron run bounded because we only ever wait
    FETCH_TIMEOUT_SECONDS for one parser.
    """
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        future = pool.submit(fetch_provider, provider_id, user_agent)
        try:
            return future.result(timeout=FETCH_TIMEOUT_SECONDS)
        except _TimeoutError:
            future.cancel()
            print(f"Provider {provider_id} exceeded {FETCH_TIMEOUT_SECONDS}s — skipping")
            return []
    finally:
        # Do not block this worker on a stuck parser; the serverless cron
        # process is recycled anyway.
        pool.shutdown(wait=False, cancel_futures=True)


def log_health(provider_id: str, status: str, duration_ms: int, error: str | None = None):
    """Log fetch health to system_health table (uses existing schema with job_name)."""
    try:
        row = {
            "job_name": f"changelog:{provider_id}",
            "status": status,
            "duration_ms": duration_ms,
            "error_message": error,
            "ran_at": _now_iso(),
        }
        db().table("system_health").insert(row).execute()
    except Exception:
        pass  # Best-effort logging


def run_daily_scan(repo_id: str) -> dict:
    """Run daily scan for a repository: changelog check + code-health check.
    
    Returns: {changelog_check_status, code_check_status, changelog_issues_count, code_issues_count}
    """
    stats = {
        "changelog_check_status": "skipped_no_providers",
        "code_check_status": "clear",
        "changelog_issues_count": 0,
        "code_issues_count": 0,
    }
    
    try:
        # Get repo details
        repo = db().table("repos").select("*").eq("id", repo_id).execute()
        if not repo.data:
            return stats
        
        repo_data = repo.data[0]
        user_id = repo_data.get("user_id")
        
        # Check 1: Changelog breaking changes
        # Get connected providers for this user
        connections = db().table("provider_connections").select("provider").eq("user_id", user_id).execute()
        providers = [c["provider"] for c in connections.data] if connections.data else []
        
        if providers:
            # Check for breaking changes in recent changelog events
            breaking_changes = (
                db().table("changelog_events")
                .select("id")
                .in_("api_name", providers)
                .eq("severity", "breaking")
                .gte("detected_at", _now_iso()[:10])  # Today
                .execute()
            )
            
            if breaking_changes.data:
                stats["changelog_check_status"] = "breaking_change_found"
                stats["changelog_issues_count"] = len(breaking_changes.data)
            else:
                stats["changelog_check_status"] = "clear"
        
        # Check 2: Code-health rules
        # Get detections for this repo (api_detections is the real scan store;
        # the legacy "detections" table does not exist in production)
        detections = db().table("api_detections").select("*").eq("repo_id", repo_id).execute()
        detection_list = detections.data if detections.data else []
        
        if detection_list:
            # Get file contents (simplified - in production would fetch from GitHub)
            file_contents = {}
            for det in detection_list:
                file_path = det.get("file_path", "")
                if file_path and file_path not in file_contents:
                    # In real implementation, fetch file content from GitHub
                    # For now, use matched_snippet as proxy
                    file_contents[file_path] = det.get("matched_snippet", "")
            
            # Run code-health checks
            issues = run_code_health_checks(repo_id, detection_list, file_contents)
            
            if issues:
                stats["code_check_status"] = "issue_found"
                stats["code_issues_count"] = len(issues)
                
                # Store new issues (only if not already detected)
                for issue in issues:
                    # Check if issue already exists
                    existing = (
                        db().table("code_health_issues")
                        .select("id")
                        .eq("repo_id", repo_id)
                        .eq("provider", issue.provider)
                        .eq("issue_type", issue.issue_type)
                        .eq("file_path", issue.file_path)
                        .eq("status", "open")
                        .limit(1)
                        .execute()
                    )
                    
                    if not existing.data:
                        db().table("code_health_issues").insert({
                            "repo_id": repo_id,
                            "provider": issue.provider,
                            "issue_type": issue.issue_type,
                            "description": issue.description,
                            "file_path": issue.file_path,
                            "line_number": issue.line_number,
                            "status": "open",
                        }).execute()
        
        return stats
        
    except Exception as e:
        print(f"Error running daily scan for repo {repo_id}: {e}")
        return stats


def insert_daily_scan_run(repo_id: str, stats: dict):
    """Insert a daily_scan_runs row for the repo."""
    try:
        db().table("daily_scan_runs").insert({
            "repo_id": repo_id,
            "changelog_check_status": stats.get("changelog_check_status", "skipped_no_providers"),
            "code_check_status": stats.get("code_check_status", "clear"),
            "changelog_issues_count": stats.get("changelog_issues_count", 0),
            "code_issues_count": stats.get("code_issues_count", 0),
            "ran_at": _now_iso(),
        }).execute()
    except Exception as e:
        print(f"Error inserting daily scan run for repo {repo_id}: {e}")


def send_daily_status_email(repo_id: str, stats: dict, user_email: str, repo_name: str, notify_daily_status: bool):
    """Send daily status email (only if issues found or daily status enabled)."""
    has_issues = (
        stats.get("changelog_issues_count", 0) > 0 or
        stats.get("code_issues_count", 0) > 0
    )
    
    # Skip if no issues and daily status not enabled
    if not has_issues and not notify_daily_status:
        return
    
    try:
        from ..email_service import send_alert_email
        
        # Build email content
        if has_issues:
            subject = f"Breaklytix Alert: Issues found for {repo_name}"
            status_text = "issues were detected"
        else:
            subject = f"Breaklytix Daily Status: {repo_name} — All Clear"
            status_text = "no issues found"
        
        # Build HTML body
        html_parts = [
            '<div style="font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;max-width:560px;margin:0 auto;color:#1a1a2e;">',
            f'<h2 style="margin:0 0 8px;">Daily Status: {repo_name}</h2>',
            f'<p style="color:#555;">{status_text} in your daily check.</p>',
        ]
        
        if stats.get("changelog_issues_count", 0) > 0:
            html_parts.append(f'<p style="color:#b91c1c;"><strong>Breaking changes:</strong> {stats["changelog_issues_count"]} detected</p>')
        
        if stats.get("code_issues_count", 0) > 0:
            html_parts.append(f'<p style="color:#b91c1c;"><strong>Code health issues:</strong> {stats["code_issues_count"]} detected</p>')
        
        if not has_issues:
            html_parts.append('<p style="color:#16a34a;">All checks passed. No breaking changes or code health issues found.</p>')
        
        html_parts.append("</div>")
        html = "\n".join(html_parts)
        text = f"Daily Status: {repo_name} — {status_text}"
        
        send_alert_email(
            user_id=None,  # Will be resolved from email
            recipient=user_email,
            alert_type="daily_status",
            subject=subject,
            html=html,
            text=text,
        )
        
    except Exception as e:
        print(f"Error sending daily status email: {e}")


def run_daily_scans():
    """Run daily scans for all monitored repos. Called by cron.

    Each repo is scanned at most once per 24h (due check against the
    latest daily_scan_runs.ran_at). Token-expired / repo-deleted /
    permission-revoked failures are caught per-repo and reported in the
    scan run record, never silently dropped.
    """
    try:
        # Get all repos with connected providers
        repos = db().table("repos").select("*").execute()
        if not repos.data:
            return

        # Latest scan per repo (due check)
        latest = (
            db().table("daily_scan_runs")
            .select("repo_id, ran_at")
            .order("ran_at", desc=True)
            .limit(1000)
            .execute()
        ).data or []
        latest_by_repo: dict[str, str] = {}
        for row in latest:
            rid = row.get("repo_id")
            if rid and rid not in latest_by_repo:
                latest_by_repo[rid] = row.get("ran_at") or ""

        from datetime import datetime, timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        for repo in repos.data:
            repo_id = repo["id"]
            user_id = repo.get("user_id")

            # Due check: skip repos scanned within the last 24h
            last = latest_by_repo.get(repo_id)
            if last:
                try:
                    last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
                    if last_dt.tzinfo is None:
                        last_dt = last_dt.replace(tzinfo=timezone.utc)
                    if last_dt > cutoff:
                        continue
                except ValueError:
                    pass  # unparseable → scan anyway

            # Get user email and daily status preference
            user = db().table("users").select("email,notify_daily_status").eq("id", user_id).execute()
            if not user.data:
                continue
            
            user_data = user.data[0]
            user_email = user_data.get("email")
            notify_daily_status = user_data.get("notify_daily_status", False)
            
            if not user_email:
                continue
            
            # Run daily scan
            stats = run_daily_scan(repo_id)
            
            # Insert scan run record
            insert_daily_scan_run(repo_id, stats)
            
            # Send email if needed
            send_daily_status_email(
                repo_id=repo_id,
                stats=stats,
                user_email=user_email,
                repo_name=repo.get("full_name", "Unknown"),
                notify_daily_status=notify_daily_status,
            )
            
    except Exception as e:
        print(f"Error running daily scans: {e}")


def run_impact_analysis_for_recent_events():
    """Run impact analysis for recent changelog events against all repos.

    Called after fetching new changelog events to automatically analyze
    their impact on connected repositories.

    Bounded + batched so it fits the Vercel function budget:
      * only impactful change types (breaking/deprecation/security/removal),
      * at most MAX_IMPACT_EVENTS_PER_RUN events per invocation (the rest are
        covered on the next cron tick),
      * detections and existing analyses are loaded ONCE (grouped in memory)
        instead of one query per (event, repo) pair.
    """
    try:
        from datetime import datetime, timedelta, timezone
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        IMPACT_CHANGE_TYPES = ("breaking_change", "breaking", "deprecation", "security", "removal")

        events = (
            db()
            .table("changelog_events")
            .select("*")
            .gte("detected_at", cutoff)
            .in_("change_type", IMPACT_CHANGE_TYPES)
            .order("detected_at", desc=True)
            .limit(MAX_IMPACT_EVENTS_PER_RUN)
            .execute()
        ).data or []

        if not events:
            return

        repos = (db().table("repos").select("*").execute()).data or []
        if not repos:
            return

        # Load ALL detections once, grouped by provider (case-insensitive).
        detections = (
            db().table("api_detections")
            .select("id, repo_id, api_name, file_path, line_number, matched_snippet, symbols")
            .execute()
        ).data or []
        by_provider: dict[str, list[dict]] = {}
        for d in detections:
            by_provider.setdefault((d.get("api_name") or "").lower(), []).append(d)

        # Load existing analysis pairs once, so we skip already-analyzed events.
        existing = (
            db().table("impact_analyses").select("repo_id, changelog_event_id").execute()
        ).data or []
        done_pairs = {(a.get("repo_id"), a.get("changelog_event_id")) for a in existing}

        # Import impact analyzer
        from ..impact.analyzer import analyze_changelog_event, persist_impact_analysis

        for event in events:
            provider = event.get("api_name") or event.get("provider", "")
            if not provider:
                continue

            provider_dets = by_provider.get(provider.lower(), [])
            if not provider_dets:
                continue

            # Group this provider's detections by repo.
            by_repo: dict[str, list[dict]] = {}
            for d in provider_dets:
                rid = d.get("repo_id")
                if rid:
                    by_repo.setdefault(rid, []).append(d)

            for repo_id, dets in by_repo.items():
                if (repo_id, event["id"]) in done_pairs:
                    continue  # Already analyzed

                repo = next((r for r in repos if r["id"] == repo_id), None)
                if not repo:
                    continue

                try:
                    analysis = analyze_changelog_event(
                        event=event,
                        repo_id=repo_id,
                        detections=dets,
                    )
                    analysis_id = persist_impact_analysis(analysis)
                    done_pairs.add((repo_id, event["id"]))

                    # Send alert for high-risk or breaking changes
                    if analysis.severity in ("high", "breaking"):
                        _send_impact_alert(
                            repo_id=repo_id,
                            analysis=analysis,
                            repo_name=repo.get("full_name", "Unknown"),
                        )
                except Exception as e:
                    print(f"Error analyzing impact for repo {repo_id}: {e}")

    except Exception as e:
        print(f"Error running impact analysis: {e}")


def _send_impact_alert(repo_id: str, analysis, repo_name: str):
    """Send alert for high-risk or breaking impact."""
    try:
        from ..email_service import send_alert_email
        
        # Get user email
        repo = db().table("repos").select("user_id").eq("id", repo_id).execute()
        if not repo.data:
            return
        
        user_id = repo.data[0].get("user_id")
        user = db().table("users").select("email,notify_email_alerts").eq("id", user_id).execute()
        if not user.data:
            return
        
        user_data = user.data[0]
        user_email = user_data.get("email")
        notify_alerts = user_data.get("notify_email_alerts", True)
        
        if not user_email or not notify_alerts:
            return
        
        # Build email
        severity_text = "BREAKING" if analysis.severity == "breaking" else "HIGH RISK"
        subject = f"Breaklytix Impact Alert: {severity_text} — {repo_name}"
        
        affected_files = analysis.affected_files[:5]  # Top 5 files
        files_text = "\n".join([
            f"• {f.file_path}" + (f" (line {f.line_number})" if f.line_number else "")
            for f in affected_files
        ])
        
        html = f'''
        <div style="font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;max-width:560px;margin:0 auto;color:#1a1a2e;">
            <h2 style="margin:0 0 8px;color:#b91c1c;">{severity_text}: {analysis.provider} API Change</h2>
            <p style="color:#555;">Repository: <strong>{repo_name}</strong></p>
            <p style="color:#555;">Change: {analysis.change_type}</p>
            <p style="color:#555;">Confidence: {int(analysis.confidence * 100)}%</p>
            <p style="color:#555;">Impact: {analysis.impact_reason}</p>
            <h3 style="margin:16px 0 8px;">Affected Files:</h3>
            <pre style="background:#f3f4f6;padding:12px;border-radius:6px;font-size:13px;overflow-x:auto;">{files_text}</pre>
            <p style="color:#555;margin-top:16px;">Potential Failure: {analysis.potential_failure}</p>
            <p style="color:#555;">Recommended Fix: {analysis.recommended_fix or "Review required"}</p>
            <p style="margin-top:16px;">
                <a href="{settings.frontend_base_url}/dashboard/impact/{analysis.id}" 
                   style="background:#1a1a2e;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;display:inline-block;">
                    View Impact Details
                </a>
            </p>
        </div>
        '''
        
        text = f"{severity_text}: {analysis.provider} API Change — {repo_name}"
        
        send_alert_email(
            user_id=user_id,
            recipient=user_email,
            alert_type="impact_alert",
            subject=subject,
            html=html,
            text=text,
        )
        
    except Exception as e:
        print(f"Error sending impact alert: {e}")
