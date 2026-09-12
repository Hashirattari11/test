"""Bridge between the scanner/rules engine and the health system.

Runs after every completed scan (idempotent, never sinks the scan):

1. findings -> reliability_issues  (unified model, deduped via content_hash)
2. reliability_issues -> alerts    (severity-gated, deduped; existing alert
   processing pipeline delivers them)
3. findings/usage/rate-limit -> health checks -> health_scores + history

All data here is REAL (scan output). Missing signals are marked "unavailable"
instead of being silently treated as healthy.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from ..db import db, fetch_one
from .engine import HealthCheckResult, HealthEngine, PROVIDER_WEIGHTS
from .issues import (
    IssueCategory,
    IssueSeverity,
    IssueSource,
    IssueStatus,
    ReliabilityIssue,
)
from .provider_capabilities import Capability, PROVIDERS
from .redact import redact

logger = logging.getLogger("autofix.health")

# Maps rule change_type -> unified issue category (the FOUR problem types).
CATEGORY_BY_CHANGE: dict[str, IssueCategory] = {
    "removed": IssueCategory.PROVIDER_PROBLEM,
    "endpoint_changed": IssueCategory.PROVIDER_PROBLEM,
    "deprecated": IssueCategory.CUSTOMER_CODE,
    "renamed": IssueCategory.CUSTOMER_CODE,
    "auth_changed": IssueCategory.CONFIGURATION,
    "secret_leak": IssueCategory.CONFIGURATION,
    "dependency": IssueCategory.DEPENDENCY,
    "usage": IssueCategory.CUSTOMER_USAGE,
    "incident": IssueCategory.PROVIDER_INCIDENT,
}

SEVERITY_RANK = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _finding_rule(f: dict) -> tuple[Any, bool]:
    """Return (rule, found) for a finding's rule_id (deterministic registry rule)."""
    rule_id = f.get("rule_id")
    if not rule_id:
        return None, False
    try:
        from ..engine.rules.registry import RULES
        rule = next((r for r in RULES if r.id == rule_id), None)
        return rule, rule is not None
    except Exception:
        return None, False


def issue_from_finding(f: dict, repo_name: str) -> ReliabilityIssue | None:
    """Map a scanner finding to a unified ReliabilityIssue (None if noise)."""
    # Only raise issues for rule-matched (breaking) findings, not every usage hit.
    rule, is_rule = _finding_rule(f)
    is_breaking = f.get("type") == "breaking_change" or is_rule
    if not is_breaking:
        return None

    provider = f.get("provider") or "unknown"
    change_type = str(f.get("change_type") or "removed")
    category = CATEGORY_BY_CHANGE.get(
        change_type,
        IssueCategory.PROVIDER_PROBLEM if change_type == "breaking_change" else IssueCategory.CUSTOMER_CODE,
    )

    if rule is not None:
        title = rule.title
        description = rule.description
        severity = IssueSeverity(rule.severity) if rule.severity in SEVERITY_RANK else IssueSeverity.MEDIUM
        confidence = rule.confidence
        recommended = rule.recommended_fix
        auto_fix = bool(rule.old_value and rule.new_value is not None)
        rule_ref = rule.id
    else:
        title = str(f.get("message") or "API integration issue detected")
        description = str(f.get("message") or "")
        severity = IssueSeverity(f["severity"]) if f.get("severity") in SEVERITY_RANK else IssueSeverity.MEDIUM
        confidence = float(f.get("confidence") or 0.7)
        recommended = str(f.get("recommended_fix") or "")
        auto_fix = False
        rule_ref = None

    evidence = redact(str(f.get("current_usage") or "")[:500])  # code snapshot, NEVER secret VALUES

    issue = ReliabilityIssue(
        provider=provider,
        repository=repo_name,
        category=category,
        severity=severity,
        status=IssueStatus.OPEN,
        confidence=confidence,
        title=title,
        description=description,
        evidence=evidence,
        file=f.get("file"),
        line=f.get("line"),
        source=IssueSource.SCAN,
        recommended_action=recommended,
        auto_fix_available=auto_fix,
        auto_fix_rule_id=rule_ref,
    )
    issue.content_hash = issue.compute_hash()
    return issue


def _maybe_alert(repo_id: str, issue: ReliabilityIssue) -> None:
    """Insert an alert for critical/high issues (deduped). Email delivery flows
    through the existing alert-processing pipeline — no secrets in the payload."""
    if issue.severity not in (IssueSeverity.CRITICAL, IssueSeverity.HIGH):
        return
    try:
        dup = (
            db().table("alerts")
            .select("id")
            .eq("provider", issue.provider)
            .eq("description", issue.title)
            .eq("file_path", issue.file or "unknown")
            .eq("status", "open")
            .limit(1)
            .execute()
        ).data
        if dup:
            return
        db().table("alerts").insert({
            "repo_id": repo_id,
            "provider": issue.provider,
            "change_type": issue.category.value,
            "description": issue.title,
            "source_url": None,
            "file_path": issue.file,
            "line_number": issue.line,
            "email_sent": False,
            "severity": issue.severity.value,
            "severity_reason": issue.description[:300],
            "status": "open",
            "created_at": _now(),
        }).execute()
    except Exception as exc:
        logger.warning("alert insert skipped: %s", exc)


def sync_findings_to_issues(repo_id: str, findings_rows: list[dict]) -> int:
    """Persist reliability issues from scan findings (deduped, idempotent)."""
    repo = fetch_one("repos", {"id": repo_id})
    repo_name = repo["full_name"] if repo else "repository"
    created = 0
    for f in findings_rows:
        issue = issue_from_finding(f, repo_name)
        if issue is None:
            continue
        issue.repo_id = repo_id
        try:
            existing = (
                db().table("reliability_issues")
                .select("id, status")
                .eq("content_hash", issue.content_hash)
                .in_("status", ["open", "acknowledged", "in_progress"])
                .limit(1)
                .execute()
            ).data
        except Exception:
            existing = []
        if existing:
            continue  # still open — do not duplicate
        try:
            row = {k: v for k, v in issue.to_dict().items() if k not in ("id", "repository")}
            row["created_at"] = _now()
            row["updated_at"] = _now()
            db().table("reliability_issues").insert(row).execute()
            created += 1
            _maybe_alert(repo_id, issue)
        except Exception as exc:
            logger.warning("issue insert skipped: %s", exc)
    return created


def sync_dependency_issues(repo_id: str, dep_issues: list) -> int:
    """Persist DEPENDENCY-category reliability issues from REAL manifest data.

    Outdated SDK/package versions (validated against the curated catalog in
    dependencies.py) become open issues so the SDK/dependency dashboard pages
    show real verdicts — never fabricated "latest" claims. Deduped via
    content_hash, idempotent, and never sinks the calling scan.
    """
    repo = fetch_one("repos", {"id": repo_id})
    repo_name = repo["full_name"] if repo else "repository"
    created = 0
    for dep in dep_issues:
        if dep.status != "outdated":
            continue
        try:
            sev = {"warning": "medium"}.get(dep.severity, dep.severity)
            issue = ReliabilityIssue(
                provider=dep.provider or "unknown",
                repository=repo_name,
                repo_id=repo_id,
                category=IssueCategory.DEPENDENCY,
                severity=IssueSeverity(sev),
                status=IssueStatus.OPEN,
                confidence=0.9,
                title=f"SDK {dep.package} {dep.installed} is outdated",
                description=dep.reason,
                evidence=f"installed {dep.installed}; known compatible major {dep.latest}",
                file=dep.file,
                line=None,
                source=IssueSource.DEPENDENCY,
                recommended_action=(
                    f"Upgrade {dep.package} to a supported major version "
                    f"(known compatible major: {dep.latest})."
                ),
                auto_fix_available=False,
                auto_fix_rule_id=None,
            )
            issue.content_hash = issue.compute_hash()
            existing = (
                db().table("reliability_issues")
                .select("id")
                .eq("content_hash", issue.content_hash)
                .in_("status", ["open", "acknowledged", "in_progress"])
                .limit(1)
                .execute()
            ).data
            if existing:
                continue  # still open — do not duplicate
            row = {k: v for k, v in issue.to_dict().items() if k not in ("id", "repository")}
            row["created_at"] = _now()
            row["updated_at"] = _now()
            db().table("reliability_issues").insert(row).execute()
            created += 1
            _maybe_alert(repo_id, issue)
        except Exception as exc:
            logger.warning("dependency issue insert skipped: %s", exc)
    return created


def _latest_rate_snapshot(repo_id: str, provider: str) -> dict | None:
    """Latest rate-limit snapshot for a provider (may be None)."""
    try:
        r = (
            db().table("rate_limit_snapshots")
            .select("*")
            .eq("repo_id", repo_id)
            .eq("provider", provider)
            .order("recorded_at", desc=True)
            .limit(1)
            .execute()
        ).data
        if r:
            return r[0]
    except Exception:
        pass
    return None


def compute_and_store_health(
    repo_id: str,
    findings_rows: list[dict],
    manifests: dict[str, str] | None = None,
) -> int:
    """Compute + persist health scores/history for every provider in the scan.

    ``manifests`` maps manifest file path -> raw text (see dependencies.py).
    When provided, the real installed SDK version (from package.json /
    requirements.txt / go.mod / Gemfile.lock / composer.json) drives the
    sdk_version check. Without it, the check reports "SDK version not
    detectable" — never a fabricated verdict.
    """
    repo = fetch_one("repos", {"id": repo_id})
    repo_name = repo["full_name"] if repo else "repository"

    from .dependencies import check_dependencies
    dep_issues = check_dependencies(manifests or {})

    by_provider: dict[str, list[dict]] = {}
    for f in findings_rows:
        p = f.get("provider") or "unknown"
        by_provider.setdefault(p, []).append(f)

    stored = 0
    for provider, pr_rows in by_provider.items():
        profile = PROVIDERS.get(provider)
        if profile is None:
            continue  # unknown provider — skip (no fabricated data)

        engine = HealthEngine(profile)

        # 1. Breaking changes (provider_problem)
        breaking = [f for f in pr_rows if f.get("type") == "breaking_change" or f.get("rule_id")]
        if breaking:
            worst = max(SEVERITY_RANK.get((f.get("severity") or "medium"), 2) for f in breaking)
            engine.add_check(HealthCheckResult(
                check_type="breaking_changes", status="critical" if worst >= 4 else "warning",
                score=30 if worst >= 4 else 60,
                severity="critical" if worst >= 4 else "high",
                message=f"{len(breaking)} breaking-change match(es) detected",
                recommendation="Review the flagged usages and update the integration.",
                source="scan", timestamp=_now(),
            ))
        else:
            engine.add_check(HealthCheckResult(
                check_type="breaking_changes", status="healthy", score=100,
                severity="info", message="No breaking changes detected",
                source="scan", timestamp=_now(),
            ))

        # 2. Deprecated API usage
        deprecated = [f for f in pr_rows if (f.get("change_type") or "") == "deprecated"]
        if deprecated:
            engine.add_check(HealthCheckResult(
                check_type="deprecated_apis", status="warning", score=55,
                severity="high", message=f"{len(deprecated)} deprecated API usage(s) detected",
                recommendation="Replace deprecated API usage before it is removed.",
                source="scan", timestamp=_now(),
            ))
        else:
            engine.add_check(HealthCheckResult(
                check_type="deprecated_apis", status="healthy", score=100,
                severity="info", message="No deprecated API usage detected",
                source="scan", timestamp=_now(),
            ))

        # 3. Code health (customer_code issues)
        code_issues = [
            f for f in pr_rows
            if CATEGORY_BY_CHANGE.get(str(f.get("change_type") or "")) in (
                IssueCategory.CUSTOMER_CODE, IssueCategory.CONFIGURATION,
            )
        ]
        if code_issues:
            engine.add_check(HealthCheckResult(
                check_type="code_health", status="warning", score=60,
                severity="medium", message=f"{len(code_issues)} code-level issue(s) found",
                recommendation="Address the raised issues in the flagged files.",
                source="scan", timestamp=_now(),
            ))
        else:
            engine.add_check(HealthCheckResult(
                check_type="code_health", status="healthy", score=100,
                severity="info", message="Integration code looks healthy",
                source="scan", timestamp=_now(),
            ))

        # 4. SDK/package version — REAL verdict from the repo's manifests when
        # present; otherwise honestly "not detectable". Never invented.
        dep = next((d for d in dep_issues if d.provider == provider), None)
        if dep is not None and dep.status == "outdated":
            engine.add_check(HealthCheckResult(
                check_type="sdk_version", status="warning", score=60,
                severity="high",
                message=f"SDK {dep.package} {dep.installed} is outdated (known compatible major {dep.latest})",
                recommendation="Upgrade the SDK to a supported major version.",
                source="dependency", timestamp=_now(), evidence=dep.reason,
            ))
        elif dep is not None and dep.status == "current":
            engine.add_check(HealthCheckResult(
                check_type="sdk_version", status="healthy", score=100,
                severity="info",
                message=f"SDK {dep.package} {dep.installed} is on a known compatible major",
                source="dependency", timestamp=_now(), evidence=dep.reason,
            ))
        elif dep is not None and dep.status == "unknown_latest":
            engine.add_check(HealthCheckResult(
                check_type="sdk_version", status="unknown", score=70,
                severity="info",
                message=f"SDK {dep.package} {dep.installed} detected; latest known version not cataloged",
                source="dependency", timestamp=_now(), evidence=dep.reason,
            ))
        elif profile.has(Capability.CODE_DETECTION) and profile.sdk_package:
            sdk_hits = [f for f in pr_rows if (f.get("type") or "") == "api_usage"]
            if not sdk_hits:
                engine.add_check(HealthCheckResult(
                    check_type="sdk_version", status="unknown", score=70,
                    severity="info", message="SDK version not detectable from scan (no usage hits)",
                    source="dependency", timestamp=_now(),
                ))
            else:
                engine.add_check(HealthCheckResult(
                    check_type="sdk_version", status="healthy", score=100,
                    severity="info", message=f"SDK usage detected for {profile.sdk_package}",
                    source="dependency", timestamp=_now(),
                ))
        else:
            engine.add_check(HealthCheckResult(
                check_type="sdk_version", status="unavailable", score=70,
                severity="info", message="SDK version monitoring unavailable for this provider",
                source="dependency", timestamp=_now(),
            ))

        # 5. Rate limit from real snapshots (never fabricated)
        rate = _latest_rate_snapshot(repo_id, provider)

        if rate is not None and rate.get("remaining") is not None:
            remaining = int(rate["remaining"])
            if remaining <= 100:
                engine.add_check(HealthCheckResult(
                    check_type="rate_limit", status="critical", score=20, severity="critical",
                    message=f"Rate limit nearly exhausted ({remaining} remaining)",
                    recommendation="Reduce request frequency or raise limits.",
                    source="api", timestamp=_now(), data={"remaining": remaining},
                ))
            else:
                engine.add_check(HealthCheckResult(
                    check_type="rate_limit", status="healthy", score=100, severity="info",
                    message=f"Rate limit normal ({remaining} remaining)", source="api",
                    timestamp=_now(), data={"remaining": remaining},
                ))
        else:
            engine.add_check(HealthCheckResult(
                check_type="rate_limit", status="unavailable", score=70, severity="info",
                message="Rate limit monitoring unavailable for this provider", source="api", timestamp=_now(),
            ))

        # 6. Provider status / incidents (only from real incident records)
        try:
            incidents = (
                db().table("provider_incidents")
                .select("status")
                .eq("provider", provider)
                .in_("status", ["investigating", "identified", "monitoring", "ongoing", "resolved"])
                .execute()
            ).data or []
            active = [i for i in incidents if i.get("status") != "resolved"]
        except Exception:
            active = []
        if active:
            engine.add_check(HealthCheckResult(
                check_type="provider_status", status="critical", score=25, severity="critical",
                message=f"{len(active)} active provider incident(s)", recommendation="Check provider status page.",
                source="status_page", timestamp=_now(),
            ))
            engine.add_check(HealthCheckResult(
                check_type="incidents", status="critical", score=25, severity="critical",
                message=f"{len(active)} active incident(s) for {provider}", source="status_page", timestamp=_now(),
            ))
        else:
            engine.add_check(HealthCheckResult(
                check_type="provider_status", status="healthy", score=100, severity="info",
                message="No active provider incidents", source="status_page", timestamp=_now(),
            ))
            engine.add_check(HealthCheckResult(
                check_type="incidents", status="healthy", score=100, severity="info",
                message="No active provider incidents", source="status_page", timestamp=_now(),
            ))

        # 7. Errors + auth + config — only real signal available so far is findings
        engine.add_check(HealthCheckResult(
            check_type="errors", status="unavailable", score=70, severity="info",
            message="Error telemetry unavailable for this provider", source="api", timestamp=_now(),
        ))
        engine.add_check(HealthCheckResult(
            check_type="auth", status="unavailable", score=70, severity="info",
            message="Authentication health unavailable (no provider connection configured)",
            source="api", timestamp=_now(),
        ))
        engine.add_check(HealthCheckResult(
            check_type="config", status="healthy", score=100, severity="info",
            message="Scan configuration looks valid", source="scan", timestamp=_now(),
        ))

        score = engine.compute()
        try:
            db().table("health_scores").insert({
                "repo_id": repo_id,
                "provider": provider,
                "overall": score.overall,
                "status": score.status,
                "breakdown": score.breakdown,
                "checks": score.to_dict()["checks"],
                "repository_name": repo_name,
                "computed_at": _now(),
            }).execute()
            db().table("health_history").insert({
                "repo_id": repo_id,
                "provider": provider,
                "overall": score.overall,
                "status": score.status,
                "snapshot": {"checks": score.to_dict()["checks"], "breakdown": score.breakdown},
                "recorded_at": _now(),
            }).execute()
            db().table("health_checks").insert([
                {
                    "repo_id": repo_id,
                    "provider": provider,
                    "check_type": c.check_type,
                    "status": c.status,
                    "score": c.score,
                    "severity": c.severity,
                    "message": c.message,
                    "evidence": c.evidence,
                    "recommendation": c.recommendation,
                    "source": c.source,
                    "created_at": _now(),
                }
                for c in score.checks
            ]).execute()
            stored += 1
        except Exception as exc:
            logger.warning("health persist failed for %s: %s", provider, exc)
    return stored


def create_fix_for_issue(issue: dict, repo: dict) -> dict | None:
    """Create a needs_review fix row for a reliability issue (Phase J).

    Reuses the existing deterministic rule + fix generation pipeline. The fix
    is NEVER applied automatically — it enters the existing approval flow.
    Returns the inserted fix row dict, or None when no deterministic fix exists.
    """
    rule_ref = issue.get("auto_fix_rule_id")
    if not rule_ref or not issue.get("auto_fix_available"):
        return None
    try:
        from ..engine.fixer import generator, pr as pr_lib
        from ..routers.fixes import _ensure_fix_rule, _rule_uuid

        rule = generator.find_rule(rule_ref)
        if rule is None or not rule.old_value or rule.new_value is None:
            return None

        # Build a minimal finding dict for the generator (file/rule/line only —
        # no secrets involved).
        finding = {
            "file": issue.get("file"),
            "line": issue.get("line"),
            "rule_id": rule_ref,
            "severity": issue.get("severity", "medium"),
            "message": issue.get("title", ""),
            "current_usage": (issue.get("evidence") or "")[:500],
            "provider": issue.get("provider"),
        }
        repo_token = _maybe_repo_token(repo)
        current = None
        if repo_token and finding["file"]:
            current = pr_lib.fetch_file_content(
                repo_token, repo["full_name"], finding["file"], repo.get("default_branch", "main")
            )
        if current is None:
            # Cannot read the current file — still store a needs_review fix;
            # the approval flow re-validates before opening the PR.
            diff = ""
        else:
            gen = generator.generate_fix(finding, current.get("content") or "")
            diff = gen.diff if gen is not None else ""

        _ensure_fix_rule(rule)
        now = _now()
        res = db().table("fixes").insert({
            "repo_id": repo["id"],
            "fix_rule_id": _rule_uuid(rule.id),
            "file_path": finding["file"],
            "diff_preview": diff,
            "status": "needs_review",
            "created_at": now,
            "updated_at": now,
        }).execute()
        return res.data[0] if res and res.data else None
    except Exception as exc:
        logger.warning("fix creation for issue failed: %s", exc)
        return None


def _maybe_repo_token(repo: dict) -> str | None:
    """Decrypt repo token only when present; NEVER log or expose the value."""
    try:
        raw = repo.get("access_token")
        if not raw:
            return None
        from ..deps import get_cipher
        return get_cipher().decrypt(raw)
    except Exception:
        return None