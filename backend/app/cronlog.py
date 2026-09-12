"""cron_run_log helper (M8 observability).

Records every internal cron invocation: job name, start/finish times,
duration, status, summary counts, and errors. Stores NO secrets — only
aggregate counts and a short error string.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from .db import db


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def start_run(job_name: str) -> str:
    """Insert a 'running' row and return its id.

    Failures to log are non-fatal: the cron job itself must continue.
    """
    try:
        res = (
            db()
            .table("cron_run_log")
            .insert({"job_name": job_name, "status": "running", "started_at": _now_iso()})
            .execute()
        )
        return (res.data or [{}])[0].get("id")
    except Exception:
        return ""


def finish_run(run_id: str, status: str, duration_ms: int, summary: Optional[dict] = None, error: Optional[str] = None) -> None:
    """Mark a run finished (ok | error) with duration and optional summary.

    'error' is a short sanitized message (first ~200 chars); never dump
    exception internals, tokens, or message content.
    """
    if not run_id:
        return
    try:
        patch: dict[str, Any] = {
            "status": status,
            "finished_at": _now_iso(),
            "duration_ms": int(duration_ms),
        }
        if summary is not None:
            patch["summary"] = summary
        if error:
            patch["error"] = error[:200]
        db().table("cron_run_log").update(patch).eq("id", run_id).execute()
    except Exception:
        pass


def run_cron(job_name: str, fn: Callable[[], dict]) -> dict:
    """Run a cron job function with automatic logging.

    Returns the job's own result dict, augmented with run_id/status/
    duration_ms. Any exception is caught, logged as error, and re-raised
    so Vercel sees a failure.
    """
    run_id = start_run(job_name)
    start = time.time()
    try:
        result = fn()
        duration_ms = int((time.time() - start) * 1000)
        finish_run(run_id, "ok", duration_ms, result.get("summary") or result)
        result.setdefault("cron_run_id", run_id)
        result.setdefault("status", "ok")
        result["duration_ms"] = result.get("duration_ms", duration_ms)
        return result
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        finish_run(run_id, "error", duration_ms, error=str(e))
        raise