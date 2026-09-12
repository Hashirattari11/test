"""Health Engine — configurable scoring for API integrations.

Produces a 0-100 health score for each provider integration, with a
breakdown showing exactly what contributed to the score. Weights are
configurable per-provider via the provider_capabilities registry.

The engine does NOT fetch data — it consumes health check results and
produces scores. This separation keeps it testable and provider-agnostic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .provider_capabilities import Capability, ProviderProfile


# ---------------------------------------------------------------------------
# Health check result (input to scoring)
# ---------------------------------------------------------------------------
@dataclass
class HealthCheckResult:
    """A single health check result for an integration."""
    check_type: str      # provider_status, breaking_changes, deprecated_apis, code_health, sdk_version, quota, rate_limit, errors, auth, config, incidents
    status: str          # healthy | warning | critical | unavailable | unknown
    score: float         # 0-100 for this check
    severity: str        # info | low | medium | high | critical
    message: str
    evidence: str = ""
    recommendation: str = ""
    source: str = ""     # api | scan | config | dependency
    timestamp: str = ""
    data: dict = field(default_factory=dict)  # raw data (sanitized)


# ---------------------------------------------------------------------------
# Scoring weights (configurable)
# ---------------------------------------------------------------------------
DEFAULT_WEIGHTS: dict[str, float] = {
    "provider_status": 15,
    "breaking_changes": 15,
    "deprecated_apis": 10,
    "code_health": 15,
    "sdk_version": 10,
    "quota": 5,
    "rate_limit": 5,
    "errors": 10,
    "auth": 10,
    "config": 5,
    "incidents": 10,
}

PROVIDER_WEIGHTS: dict[str, dict[str, float]] = {
    "openai": {**DEFAULT_WEIGHTS, "quota": 10, "rate_limit": 10, "incidents": 5},
    "anthropic": {**DEFAULT_WEIGHTS, "quota": 10, "rate_limit": 10, "incidents": 5},
    "stripe": {**DEFAULT_WEIGHTS, "quota": 5, "rate_limit": 10, "incidents": 10},
}


# ---------------------------------------------------------------------------
# Health Score output
# ---------------------------------------------------------------------------
@dataclass
class HealthScore:
    """Computed health score with full breakdown."""
    overall: float           # 0-100
    status: str              # excellent | healthy | warning | at_risk | critical
    checks: list[HealthCheckResult]
    breakdown: dict[str, float]  # check_type -> weighted contribution
    timestamp: str
    provider: str
    repository: str | None = None

    def to_dict(self) -> dict:
        return {
            "overall": self.overall,
            "status": self.status,
            "provider": self.provider,
            "repository": self.repository,
            "breakdown": self.breakdown,
            "timestamp": self.timestamp,
            "checks": [
                {
                    "check_type": c.check_type,
                    "status": c.status,
                    "score": c.score,
                    "severity": c.severity,
                    "message": c.message,
                    "evidence": c.evidence,
                    "recommendation": c.recommendation,
                    "source": c.source,
                }
                for c in self.checks
            ],
        }


def _status_label(score: float) -> str:
    if score >= 90:
        return "excellent"
    if score >= 75:
        return "healthy"
    if score >= 50:
        return "warning"
    if score >= 25:
        return "at_risk"
    return "critical"


# ---------------------------------------------------------------------------
# Scoring engine
# ---------------------------------------------------------------------------
class HealthEngine:
    """Configurable health scoring engine.

    Usage:
        engine = HealthEngine(provider_profile)
        engine.add_check(check_result)
        score = engine.compute()
    """

    def __init__(
        self,
        provider: ProviderProfile,
        weights: dict[str, float] | None = None,
    ):
        self.provider = provider
        self.weights = weights or PROVIDER_WEIGHTS.get(
            provider.provider_id, DEFAULT_WEIGHTS
        )
        self._checks: list[HealthCheckResult] = []

    def add_check(self, check: HealthCheckResult) -> None:
        self._checks.append(check)

    def add_checks(self, checks: list[HealthCheckResult]) -> None:
        self._checks.extend(checks)

    def compute(self, repository: str | None = None) -> HealthScore:
        """Compute the health score from all added checks.

        The score is a weighted average where each check_type contributes
        up to its weight in points. Missing check types get a neutral
        score (70/100) to avoid penalizing providers that don't expose
        certain data.
        """
        # Group checks by type (keep latest per type)
        by_type: dict[str, HealthCheckResult] = {}
        for c in self._checks:
            existing = by_type.get(c.check_type)
            if existing is None or (c.timestamp > existing.timestamp):
                by_type[c.check_type] = c

        total_weight = 0.0
        weighted_sum = 0.0
        breakdown: dict[str, float] = {}

        for check_type, weight in self.weights.items():
            if check_type in by_type:
                check = by_type[check_type]
                contribution = (check.score / 100) * weight
                breakdown[check_type] = round(contribution, 2)
                weighted_sum += contribution
            else:
                # Neutral default — don't penalize for missing data
                breakdown[check_type] = round(0.7 * weight, 2)
                weighted_sum += 0.7 * weight
            total_weight += weight

        overall = round((weighted_sum / total_weight) * 100, 1) if total_weight else 70.0
        overall = max(0.0, min(100.0, overall))

        return HealthScore(
            overall=overall,
            status=_status_label(overall),
            checks=self._checks,
            breakdown=breakdown,
            timestamp=datetime.now(timezone.utc).isoformat(),
            provider=self.provider.provider_id,
            repository=repository,
        )


# ---------------------------------------------------------------------------
# Convenience: build checks from existing data
# ---------------------------------------------------------------------------
def check_from_alerts(alerts: list[dict]) -> HealthCheckResult:
    """Build a breaking_changes check from existing alerts."""
    if not alerts:
        return HealthCheckResult(
            check_type="breaking_changes",
            status="healthy",
            score=100,
            severity="info",
            message="No breaking changes detected",
        )
    critical = sum(1 for a in alerts if a.get("severity") in ("critical", "high"))
    if critical:
        return HealthCheckResult(
            check_type="breaking_changes",
            status="critical",
            score=max(0, 100 - critical * 30),
            severity="critical",
            message=f"{critical} critical/high breaking changes detected",
            evidence=f"Total alerts: {len(alerts)}",
            recommendation="Review and apply fixes for breaking changes",
        )
    return HealthCheckResult(
        check_type="breaking_changes",
        status="warning",
        score=max(0, 100 - len(alerts) * 10),
        severity="medium",
        message=f"{len(alerts)} breaking change alerts pending",
        recommendation="Review pending alerts",
    )


def check_from_findings(findings: list[dict]) -> HealthCheckResult:
    """Build a code_health check from scan findings."""
    if not findings:
        return HealthCheckResult(
            check_type="code_health",
            status="healthy",
            score=100,
            severity="info",
            message="No issues found in integration code",
        )
    by_sev = {}
    for f in findings:
        sev = f.get("severity", "info")
        by_sev[sev] = by_sev.get(sev, 0) + 1

    crit = by_sev.get("critical", 0)
    high = by_sev.get("high", 0)
    med = by_sev.get("medium", 0)

    score = 100 - (crit * 35 + high * 15 + med * 5)
    score = max(0, min(100, score))
    status = "critical" if crit else ("warning" if high or med else "healthy")
    sev = "critical" if crit else ("high" if high else "medium")

    return HealthCheckResult(
        check_type="code_health",
        status=status,
        score=score,
        severity=sev,
        message=f"{len(findings)} code issues detected ({crit} critical, {high} high, {med} medium)",
        evidence=f"Findings: {by_sev}",
        recommendation="Review and fix code-level issues" if findings else "",
    )


def check_from_quota(used: float, limit: float, provider: str) -> HealthCheckResult:
    """Build a quota check from usage data."""
    if limit <= 0:
        return HealthCheckResult(
            check_type="quota",
            status="unknown",
            score=70,
            severity="info",
            message="Quota data unavailable",
            source="provider_api",
        )
    pct = (used / limit) * 100
    if pct >= 90:
        return HealthCheckResult(
            check_type="quota",
            status="critical",
            score=max(0, 100 - int(pct)),
            severity="critical",
            message=f"Quota {pct:.0f}% used — near limit",
            recommendation="Upgrade plan or reduce usage",
            source="provider_api",
            data={"used": used, "limit": limit, "percentage": round(pct, 1)},
        )
    if pct >= 70:
        return HealthCheckResult(
            check_type="quota",
            status="warning",
            score=max(0, 100 - int(pct)),
            severity="medium",
            message=f"Quota {pct:.0f}% used",
            recommendation="Monitor usage trend",
            source="provider_api",
            data={"used": used, "limit": limit, "percentage": round(pct, 1)},
        )
    return HealthCheckResult(
        check_type="quota",
        status="healthy",
        score=100 - int(pct * 0.3),
        severity="info",
        message=f"Quota {pct:.0f}% used — healthy",
        source="provider_api",
        data={"used": used, "limit": limit, "percentage": round(pct, 1)},
    )


def check_from_rate_limit(
    remaining: int | None,
    limit: int | None,
    retry_after: int | None = None,
) -> HealthCheckResult:
    """Build a rate_limit check from API response headers."""
    if remaining is None and limit is None:
        return HealthCheckResult(
            check_type="rate_limit",
            status="unknown",
            score=70,
            severity="info",
            message="Rate limit data unavailable",
        )
    if retry_after and retry_after > 0:
        return HealthCheckResult(
            check_type="rate_limit",
            status="critical",
            score=20,
            severity="critical",
            message=f"Rate limited — retry after {retry_after}s",
            recommendation="Reduce request frequency or implement backoff",
            source="provider_api",
            data={"retry_after": retry_after},
        )
    if limit and remaining is not None:
        pct = ((limit - remaining) / limit) * 100
        if pct >= 90:
            return HealthCheckResult(
                check_type="rate_limit",
                status="warning",
                score=40,
                severity="medium",
                message=f"Rate limit {pct:.0f}% consumed",
                recommendation="Monitor request volume",
                source="provider_api",
                data={"remaining": remaining, "limit": limit},
            )
    return HealthCheckResult(
        check_type="rate_limit",
        status="healthy",
        score=90,
        severity="info",
        message="Rate limit healthy",
        source="provider_api",
        data={"remaining": remaining, "limit": limit},
    )


def check_from_incidents(incidents: list[dict]) -> HealthCheckResult:
    """Build an incidents check from provider status data."""
    active = [i for i in incidents if i.get("status") not in ("resolved", "operational")]
    if not active:
        return HealthCheckResult(
            check_type="incidents",
            status="healthy",
            score=100,
            severity="info",
            message="No active provider incidents",
        )
    return HealthCheckResult(
        check_type="incidents",
        status="critical",
        score=max(0, 100 - len(active) * 30),
        severity="critical",
        message=f"{len(active)} active provider incident(s)",
        evidence="\n".join(f"- {i.get('title', 'Unknown')}: {i.get('status')}" for i in active[:5]),
        recommendation="Monitor provider status page",
    )