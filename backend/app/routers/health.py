"""Health Intelligence API endpoints.

Provides health scores, reliability issues, usage snapshots, and provider
status for every connected repository. All data is real — no fake numbers.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from ..crypto import get_cipher
from ..db import db, fetch_one
from ..deps import get_current_user_id
from ..health.collectors import rate_limit_status
from ..health.issues import ReliabilityIssue
from ..health.key_validation import SUPPORTED as KEY_VALIDATED_PROVIDERS
from ..health.risk import RiskEngine
from ..health.usage_graph import build_usage_graph
from ..schemas import FindingOut

router = APIRouter(prefix="/health", tags=["health"])

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _owned_repo(user_id: str, repo_id: str) -> dict:
    repo = fetch_one("repos", {"id": repo_id})
    if not repo or repo["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Repo not found")
    return repo


# ---------------------------------------------------------------------------
# API usage graph (Repository -> Provider -> SDK method -> file -> line -> env)
# ---------------------------------------------------------------------------
@router.get("/repo/{repo_id}/usage-graph")
def repo_usage_graph(
    repo_id: str,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Real usage graph from the repo's persisted detections.

    Every entry is backed by an actual scan hit: provider, SDK method chain,
    source file, line, and environment-variable NAME references (values are
    never extracted or returned).
    """
    _owned_repo(user_id, repo_id)
    res = (
        db()
        .table("api_detections")
        .select("api_name, file_path, line_number, matched_snippet")
        .eq("repo_id", repo_id)
        .execute()
    )
    return {"repo_id": repo_id, "integrations": build_usage_graph(res.data or [])}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _user_repos(user_id: str) -> list[dict]:
    res = db().table("repos").select("id, full_name, default_branch, agency_client_id").eq("user_id", user_id).execute()
    return res.data or []


# Providers whose outages directly cost money / availability.
_FINTECH_PROVIDERS = {"stripe", "twilio", "sendgrid", "openai", "anthropic"}


def _repo_production(repo: dict) -> bool:
    """Production exposure heuristic: agency-managed repos or main/master default
    branch are treated as production. Deterministic and documented."""
    if repo.get("agency_client_id"):
        return True
    return (repo.get("default_branch") or "main") in ("main", "master")


def _provider_criticality(provider: str) -> float:
    return 0.75 if provider in _FINTECH_PROVIDERS else 0.5


def _attach_risk(issues: list[dict], repo_map: dict[str, dict]) -> list[dict]:
    """Attach explainable risk scores (production-aware) and sort by risk desc."""
    engine = RiskEngine()
    for issue in issues:
        try:
            model = ReliabilityIssue.from_row(issue)
        except Exception:  # defensive: never crash listing on a bad row
            continue
        repo = repo_map.get(issue.get("repo_id") or "") or {}
        rs = engine.compute(
            model,
            is_production=_repo_production(repo),
            provider_criticality=_provider_criticality(issue.get("provider") or ""),
        )
        issue["risk_score"] = rs.score
        issue["risk_level"] = rs.level
        issue["risk_factors"] = [f.label for f in rs.factors]
    return sorted(issues, key=lambda i: i.get("risk_score", 0) or 0, reverse=True)


# ---------------------------------------------------------------------------
# GET /health/overview — overall health across all repos
# ---------------------------------------------------------------------------
@router.get("/overview")
def health_overview(user_id: str = Depends(get_current_user_id)) -> dict:
    repos = _user_repos(user_id)
    if not repos:
        return {"score": 0, "status": "no_repos", "repos": 0, "integrations": 0, "issues": {}}

    repo_ids = [r["id"] for r in repos]

    # Latest health score per provider across all repos
    scores = (
        db().table("health_scores")
        .select("provider, overall, status")
        .in_("repo_id", repo_ids)
        .order("computed_at", desc=True)
        .execute()
    ).data or []

    # Dedupe: keep latest per provider
    latest_by_provider: dict[str, dict] = {}
    for s in scores:
        p = s["provider"]
        if p not in latest_by_provider:
            latest_by_provider[p] = s

    # Issues
    issues = (
        db().table("reliability_issues")
        .select("severity, status, category")
        .in_("repo_id", repo_ids)
        .eq("status", "open")
        .execute()
    ).data or []

    issue_summary = {}
    for i in issues:
        sev = i.get("severity", "medium")
        issue_summary[sev] = issue_summary.get(sev, 0) + 1

    # Overall score (weighted average of provider scores)
    if latest_by_provider:
        avg_score = sum(s["overall"] for s in latest_by_provider.values()) / len(latest_by_provider)
    else:
        avg_score = 0

    return {
        "score": round(avg_score, 1),
        "status": "healthy" if avg_score >= 75 else ("warning" if avg_score >= 50 else "critical"),
        "repos": len(repos),
        "integrations": len(latest_by_provider),
        "providers": [
            {"provider": p, "score": s["overall"], "status": s["status"]}
            for p, s in sorted(latest_by_provider.items(), key=lambda x: x[1]["overall"])
        ],
        "issues": issue_summary,
    }


# ---------------------------------------------------------------------------
# GET /health/repo/{repo_id} — health for a specific repo
# ---------------------------------------------------------------------------
@router.get("/repo/{repo_id}")
def repo_health_detail(
    repo_id: str,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    repo = _owned_repo(user_id, repo_id)

    # Latest health scores per provider
    scores = (
        db().table("health_scores")
        .select("*")
        .eq("repo_id", repo_id)
        .order("computed_at", desc=True)
        .execute()
    ).data or []

    latest_by_provider: dict[str, dict] = {}
    for s in scores:
        p = s["provider"]
        if p not in latest_by_provider:
            latest_by_provider[p] = s

    # Open issues
    issues = (
        db().table("reliability_issues")
        .select("*")
        .eq("repo_id", repo_id)
        .eq("status", "open")
        .limit(200)
        .execute()
    ).data or []

    return {
        "repo": {
            "id": repo["id"],
            "full_name": repo["full_name"],
            "default_branch": repo.get("default_branch", "main"),
            "is_production": _repo_production(repo),
        },
        "providers": [
            {
                "provider": p,
                "score": s["overall"],
                "status": s["status"],
                "breakdown": s.get("breakdown", {}),
                "checks": s.get("checks", []),
                "computed_at": s.get("computed_at"),
            }
            for p, s in latest_by_provider.items()
        ],
        "issues": _attach_risk(issues, {repo["id"]: repo}),
    }

@router.get("/issues")
def list_issues(
    severity: str | None = Query(None),
    category: str | None = Query(None),
    provider: str | None = Query(None),
    status: str = Query("open"),
    limit: int = Query(100, ge=1, le=500),
    user_id: str = Depends(get_current_user_id),
) -> list[dict]:
    repos = _user_repos(user_id)
    repo_ids = [r["id"] for r in repos]
    if not repo_ids:
        return []

    repo_map = {r["id"]: r for r in repos}

    query = (
        db().table("reliability_issues")
        .select("*")
        .in_("repo_id", repo_ids)
        .eq("status", status)
        .limit(1000)
    )
    if severity:
        query = query.eq("severity", severity)
    if category:
        query = query.eq("category", category)
    if provider:
        query = query.eq("provider", provider)

    rows = (query.execute()).data or []
    return _attach_risk(rows, repo_map)[:limit]


def _all_open_issues(user_id: str) -> tuple[list[dict], dict[str, dict]]:
    """Fetch all open reliability issues for the user's repos, risk-attached.

    Returns (rows, repo_map) using the same plumbing as /health/issues so the
    Runtime Intelligence views share one source of truth.
    """
    repos = _user_repos(user_id)
    repo_ids = [r["id"] for r in repos]
    if not repo_ids:
        return [], {}
    repo_map = {r["id"]: r for r in repos}
    rows = (
        db().table("reliability_issues")
        .select("*")
        .in_("repo_id", repo_ids)
        .eq("status", "open")
        .limit(1000)
        .execute()
    ).data or []
    return _attach_risk(rows, repo_map), repo_map


def _with_repo(row: dict, repo_map: dict[str, dict]) -> dict:
    out = dict(row)
    repo = repo_map.get(row.get("repo_id") or "") or {}
    out["repo_full_name"] = repo.get("full_name") or ""
    return out


# Providers that support the API-key connection flow (real key validation).
# OAuth-based providers (GitHub repo connection, Slack install) use their own
# dedicated flows and are reported as connectable only via those.
_OAUTH_PROVIDERS = {"github", "slack"}
# Providers with no provider-specific connection/validation path at all.
_NO_CONNECT_FLOW = {"vercel", "supabase", "firebase", "resend", "shopify"}

# Human-facing description per provider category (never leaks internals/secrets).
_CATEGORY_DESC = {
    "payment": "Payments & billing APIs",
    "ai": "AI / large-language-model APIs",
    "communication": "SMS / messaging / collaboration APIs",
    "email": "Email sending and delivery APIs",
    "cloud": "Cloud platform & DevOps APIs",
    "database": "Database platform APIs",
    "ecommerce": "Commerce & storefront APIs",
}



@router.get("/errors")
def list_errors(
    limit: int = Query(200, ge=1, le=500),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """API errors: issues with critical/high severity, excluding provider incidents."""
    rows, repo_map = _all_open_issues(user_id)
    errors = [
        _with_repo(r, repo_map)
        for r in rows
        if r.get("severity") in ("critical", "high") and (r.get("category") or "") != "provider_incident"
    ]
    critical = sum(1 for e in errors if e.get("severity") == "critical")
    return {
        "total": len(errors),
        "critical": critical,
        "high": len(errors) - critical,
        "errors": errors[:limit],
    }


# ---------------------------------------------------------------------------
# GET /health/failures — Runtime Intelligence: code-side failures + incidents
# ---------------------------------------------------------------------------
@router.get("/failures")
def list_failures(
    limit: int = Query(200, ge=1, le=500),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Failures: code-side errors (customer_code) and provider incidents."""
    rows, repo_map = _all_open_issues(user_id)
    failures = [
        _with_repo(r, repo_map)
        for r in rows
        if r.get("category") in ("customer_code", "provider_incident")
    ]
    customer_code = sum(1 for f in failures if f.get("category") == "customer_code")
    provider_incident = sum(1 for f in failures if f.get("category") == "provider_incident")
    return {
        "total": len(failures),
        "customer_code": customer_code,
        "provider_incident": provider_incident,
        "failures": failures[:limit],
    }


# ---------------------------------------------------------------------------
# GET /health/incidents — Runtime Intelligence: live provider incidents feed
# (global real incident records refreshed during scans; no per-provider detail
# dependency — replaces the removed API-Intelligence aggregation)
# ---------------------------------------------------------------------------
@router.get("/incidents")
def list_provider_incidents(
    limit: int = Query(100, ge=1, le=200),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Recent real provider incidents (provider status pages / Stripe feed)."""
    rows = (
        db().table("provider_incidents")
        .select("*")
        .order("started_at", desc=True)
        .limit(limit)
        .execute()
    ).data or []
    incidents = [
        {
            "id": r.get("id"),
            "provider": r.get("provider"),
            "title": r.get("title"),
            "status": r.get("status"),
            "impact": r.get("impact"),
            "started_at": r.get("started_at"),
            "source_url": r.get("source_url"),
        }
        for r in rows
    ]
    return {"total": len(incidents), "incidents": incidents}


# ---------------------------------------------------------------------------
# GET /health/anomalies — Runtime Intelligence: high/critical-risk findings
# ---------------------------------------------------------------------------
@router.get("/anomalies")
def list_anomalies(
    limit: int = Query(200, ge=1, le=500),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Anomalies: findings whose computed risk level is high or critical."""
    rows, repo_map = _all_open_issues(user_id)
    anomalies = [
        _with_repo(r, repo_map)
        for r in rows
        if r.get("risk_level") in ("high", "critical")
    ]
    critical = sum(1 for a in anomalies if a.get("risk_level") == "critical")
    return {
        "total": len(anomalies),
        "critical": critical,
        "high": len(anomalies) - critical,
        "anomalies": anomalies[:limit],
    }


# ---------------------------------------------------------------------------
# GET /health/issues/{issue_id} — single issue detail
# ---------------------------------------------------------------------------
@router.get("/issues/{issue_id}")
def issue_detail(
    issue_id: str,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    issue = fetch_one("reliability_issues", {"id": issue_id})
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    repo = fetch_one("repos", {"id": issue.get("repo_id")})
    if not repo or repo["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Issue not found")

    return {"issue": issue, "repo": {"id": repo["id"], "full_name": repo["full_name"]}}


# ---------------------------------------------------------------------------
# PATCH /health/issues/{issue_id} — update issue status
# ---------------------------------------------------------------------------
@router.patch("/issues/{issue_id}")
def update_issue(
    issue_id: str,
    body: dict,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    issue = fetch_one("reliability_issues", {"id": issue_id})
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    # Verify user owns the repo
    repo = fetch_one("repos", {"id": issue.get("repo_id")})
    if not repo or repo["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Issue not found")

    updates = {}
    if "status" in body:
        updates["status"] = body["status"]
    if body.get("status") == "resolved":
        updates["resolved_at"] = datetime.now(timezone.utc).isoformat()

    if updates:
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        db().table("reliability_issues").update(updates).eq("id", issue_id).execute()

    return fetch_one("reliability_issues", {"id": issue_id})


# ---------------------------------------------------------------------------
# GET /health/history/{repo_id} — trend data
# ---------------------------------------------------------------------------
@router.get("/history/{repo_id}")
def health_history(
    repo_id: str,
    provider: str | None = Query(None),
    days: int = Query(30, ge=1, le=365),
    user_id: str = Depends(get_current_user_id),
) -> list[dict]:
    _owned_repo(user_id, repo_id)

    query = (
        db().table("health_history")
        .select("*")
        .eq("repo_id", repo_id)
    )
    if provider:
        query = query.eq("provider", provider)

    return (query.order("recorded_at", desc=True).limit(500).execute()).data or []

@router.get("/rate-limit/{repo_id}")
def rate_limit_history(
    repo_id: str,
    provider: str | None = Query(None),
    limit: int = Query(60, ge=1, le=500),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    _owned_repo(user_id, repo_id)

    query = (
        db().table("rate_limit_snapshots")
        .select("*")
        .eq("repo_id", repo_id)
    )
    if provider:
        query = query.eq("provider", provider)

    rows = (query.order("recorded_at", desc=True).limit(limit).execute()).data or []

    by_provider: dict[str, list[dict]] = {}
    for r in rows:
        by_provider.setdefault(r["provider"], []).append(r)

    return {
        "snapshots": rows,
        "status": {p: rate_limit_status(rows_for_p) for p, rows_for_p in by_provider.items()},
    }


# ---------------------------------------------------------------------------
# POST /health/issues/{issue_id}/fix — queue a deterministic auto-fix (Phase J)
# ---------------------------------------------------------------------------
@router.post("/issues/{issue_id}/fix")
def fix_reliability_issue(
    issue_id: str,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Create a needs_review fix for a reliability issue using the existing
    deterministic rule pipeline. NEVER applied automatically — the user
    approves it in the Fixes tab (existing approval flow)."""
    issue = fetch_one("reliability_issues", {"id": issue_id})
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    repo = fetch_one("repos", {"id": issue.get("repo_id")})
    if not repo or repo["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Issue not found")

    from ..health.bridge import create_fix_for_issue

    fix = create_fix_for_issue(issue, repo)
    if fix is None:
        raise HTTPException(
            status_code=409,
            detail="No deterministic auto-fix is available for this issue (review manually).",
        )
    return {
        "fix_id": fix["id"],
        "status": fix["status"],
        "file_path": fix["file_path"],
        "message": "Fix queued for review. Approve it in the Fixes tab to open the GitHub PR.",
    }


# ---------------------------------------------------------------------------
# GET /health/agency/overview — per-client health for agency owners (Phase K)
# ---------------------------------------------------------------------------
@router.get("/agency/overview")
def agency_health_overview(user_id: str = Depends(get_current_user_id)) -> dict:
    from .agency import _verify_agency_owner

    _verify_agency_owner(user_id)

    clients = (
        db().table("agency_clients")
        .select("id, client_display_name, status")
        .eq("agency_owner_id", user_id)
        .execute()
    ).data or []

    result: list[dict] = []
    for client in clients:
        if client.get("status") != "authorized":
            continue
        cid = client["id"]
        repos = (
            db().table("repos")
            .select("id")
            .eq("agency_client_id", cid)
            .execute()
        ).data or []
        repo_ids = [r["id"] for r in repos]
        if not repo_ids:
            result.append({
                "client_id": cid,
                "client_name": client.get("client_display_name") or "Client",
                "health": None,
                "repos": 0,
                "issues": {},
            })
            continue

        scores = (
            db().table("health_scores")
            .select("overall")
            .in_("repo_id", repo_ids)
            .order("computed_at", desc=True)
            .execute()
        ).data or []
        latest: dict[str, float] = {}
        for s in scores:
            if s["repo_id"] not in latest:
                latest[s["repo_id"]] = s["overall"]
        avg = round(sum(latest.values()) / len(latest), 1) if latest else None

        issues = (
            db().table("reliability_issues")
            .select("severity")
            .in_("repo_id", repo_ids)
            .eq("status", "open")
            .execute()
        ).data or []
        summary: dict[str, int] = {}
        for i in issues:
            sev = i.get("severity", "medium")
            summary[sev] = summary.get(sev, 0) + 1

        result.append({
            "client_id": cid,
            "client_name": client.get("client_display_name") or "Client",
            "health": avg,
            "repos": len(repo_ids),
            "issues": summary,
        })

    return {"clients": result}


# ---------------------------------------------------------------------------
# Provider connections (capability-gated real usage collectors)
#
# Key handling: the API key is encrypted at rest with the same Fernet cipher
# used for GitHub tokens and is NEVER returned by any endpoint. Only the
# existence + last error are exposed.
# ---------------------------------------------------------------------------
@router.get("/provider-connections")
def list_provider_connections(user_id: str = Depends(get_current_user_id)) -> dict:
    rows = (
        db().table("provider_connections")
        .select("provider, connected_at, last_error")
        .eq("user_id", user_id)
        .execute()
    ).data or []
    return {
        "connections": [
            {
                "provider": r["provider"],
                "connected_at": r.get("connected_at"),
                "has_key": True,
                "last_error": r.get("last_error"),
            }
            for r in rows
        ]
    }


@router.post("/provider-connections")
def create_provider_connection(
    body: dict,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    provider = (body.get("provider") or "").strip().lower()
    api_key = (body.get("api_key") or "").strip()
    if provider not in KEY_VALIDATED_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported provider '{provider}' — no real key-validation endpoint exists for it.",
        )
    if not api_key or len(api_key) < 8 or " " in api_key:
        raise HTTPException(status_code=400, detail="A valid API key is required")

    # Real validation: probe the provider with this key BEFORE storing. A bad
    # key is never persisted (and never echoed in any response/log).
    from ..health.key_validation import validate_provider_key
    valid, message = validate_provider_key(provider, api_key)
    if not valid:
        raise HTTPException(status_code=400, detail=f"Connection failed: {message}")

    encrypted = get_cipher().encrypt(api_key)
    existing = fetch_one("provider_connections", {"user_id": user_id, "provider": provider})
    if existing:
        db().table("provider_connections").update(
            {"encrypted_key": encrypted, "last_error": None}
        ).eq("id", existing["id"]).execute()
    else:
        db().table("provider_connections").insert(
            {"user_id": user_id, "provider": provider, "encrypted_key": encrypted}
        ).execute()
    return {"provider": provider, "connected": True, "validated": True, "message": message}


@router.post("/provider-connections/{provider}/test")
def test_provider_connection(
    provider: str,
    body: dict,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Test an API key against the provider's real API WITHOUT storing it."""
    api_key = (body.get("api_key") or "").strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="An API key is required to test the connection")
    from ..health.key_validation import validate_provider_key
    valid, message = validate_provider_key(provider, api_key)
    return {"provider": provider, "valid": valid, "message": message}


@router.delete("/provider-connections/{provider}")
def delete_provider_connection(
    provider: str,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    db().table("provider_connections").delete().eq("user_id", user_id).eq(
        "provider", provider
    ).execute()
    return {"provider": provider, "connected": False}

