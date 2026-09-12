"""Runtime provider data collectors (post API-Intelligence removal, Session-10).

Only runtime monitoring collectors remain:
- ``collect_github_rate_limit`` / ``record_github_rate_limit`` — real GitHub
  core rate-limit snapshot taken during repository scans (Runtime "Rate Limit
  Events"). Provider-level usage/quota/rate-limit collectors were removed with
  the API Intelligence feature; provider incidents now live in ``incidents.py``.
"""
from __future__ import annotations

import datetime as _dt
from typing import Any

from .incidents import CollectorError, ProviderPermissionError, TIMEOUT, _get_json


# ---------------------------------------------------------------------------
# GitHub rate limit (real, uses the repo's GitHub token)
# ---------------------------------------------------------------------------
def collect_github_rate_limit(token: str) -> dict[str, Any]:
    """Real GitHub core rate-limit snapshot (proven HTTP 200)."""
    data = _get_json("https://api.github.com/rate_limit", token)
    core = (data.get("resources") or {}).get("core") or {}
    reset_ts = int(core.get("reset") or 0)
    return {
        "limit_value": int(core.get("limit") or 0),
        "remaining": int(core.get("remaining") or 0),
        "reset_at": (
            _dt.datetime.fromtimestamp(reset_ts, tz=_dt.timezone.utc).isoformat()
            if reset_ts
            else None
        ),
        "raw_data": data,
    }


def record_github_rate_limit(
    repo_id: str | None, token: str, user_id: str | None = None
) -> dict[str, Any]:
    """Collect + persist a real GitHub rate-limit snapshot.

    ``repo_id`` is optional: provider-level snapshots (repo_id None) are scoped
    by ``user_id`` so they never leak across users.
    """
    snap = collect_github_rate_limit(token)
    payload = {**snap, "provider": "github"}
    if repo_id:
        payload["repo_id"] = repo_id
    if user_id:
        payload["user_id"] = user_id
    from ..db import db

    db().table("rate_limit_snapshots").insert(payload).execute()
    return snap


# ---------------------------------------------------------------------------
# Rate-limit status aggregate (pure, deterministic — no network/DB)
# ---------------------------------------------------------------------------
def rate_limit_status(rows: list[dict]) -> dict | None:
    """Aggregate rate-limit snapshots into a status verdict.

    Uses the newest snapshot (by ``recorded_at``); missing values yield
    ``level == "unknown"``. Levels: ``ok`` (<70% used), ``warning`` (70-89%),
    ``critical`` (>=90%). No fabricated numbers, ever.
    """
    if not rows:
        return None
    newest = max(rows, key=lambda r: r.get("recorded_at") or "")
    remaining = newest.get("remaining")
    limit_value = newest.get("limit_value")
    recorded_at = newest.get("recorded_at")
    if remaining is None or limit_value is None or limit_value <= 0:
        return {
            "level": "unknown",
            "message": "Rate limit status unknown",
            "remaining": remaining,
            "used": None,
            "pct_used": None,
            "recorded_at": recorded_at,
        }
    used = max(0, limit_value - remaining)
    pct_used = round(used / limit_value * 100, 1)
    if pct_used >= 90:
        level = "critical"
    elif pct_used >= 70:
        level = "warning"
    else:
        level = "ok"
    return {
        "level": level,
        "message": f"{pct_used}% used",
        "remaining": remaining,
        "used": used,
        "pct_used": pct_used,
        "recorded_at": recorded_at,
    }