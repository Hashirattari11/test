"""Risk Engine — explainable risk scoring for reliability issues.

Risk scores are NOT arbitrary — every point has a clear reason. The engine
considers severity, confidence, production exposure, provider criticality,
frequency, and mitigation availability.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .issues import IssueCategory, IssueSeverity, ReliabilityIssue


@dataclass
class RiskFactor:
    """A single contributing factor to the risk score."""
    label: str
    points: int  # positive = increases risk, negative = decreases
    explanation: str


@dataclass
class RiskScore:
    """Computed risk score with explainable factors."""
    score: int  # 0-100
    level: str  # low | medium | high | critical
    factors: list[RiskFactor]
    reasons: list[str]  # human-readable

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "level": self.level,
            "factors": [
                {"label": f.label, "points": f.points, "explanation": f.explanation}
                for f in self.factors
            ],
            "reasons": self.reasons,
        }


def _level(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


class RiskEngine:
    """Compute explainable risk scores for reliability issues.

    Scoring is transparent — every point has a labeled reason. The engine
    is extensible: new factors can be added without changing the API.
    """

    # Severity base points
    SEVERITY_POINTS = {
        IssueSeverity.CRITICAL: 40,
        IssueSeverity.HIGH: 25,
        IssueSeverity.MEDIUM: 15,
        IssueSeverity.LOW: 5,
        IssueSeverity.INFO: 1,
    }

    # Category modifiers
    CATEGORY_POINTS = {
        IssueCategory.PROVIDER_PROBLEM: 10,
        IssueCategory.CUSTOMER_CODE: 8,
        IssueCategory.CUSTOMER_USAGE: 5,
        IssueCategory.PROVIDER_INCIDENT: 12,
        IssueCategory.DEPENDENCY: 6,
        IssueCategory.CONFIGURATION: 4,
        IssueCategory.UNKNOWN: 2,
    }

    def compute(self, issue: ReliabilityIssue, *, is_production: bool = False,
                provider_criticality: float = 0.5) -> RiskScore:
        """Compute risk score with explainable factors.

        Args:
            issue: The reliability issue to score
            is_production: Whether this affects a production repo
            provider_criticality: 0-1 how critical this provider is (0.5 = default)
        """
        factors: list[RiskFactor] = []
        reasons: list[str] = []
        total = 0

        # 1. Severity
        sev_pts = self.SEVERITY_POINTS.get(issue.severity, 1)
        factors.append(RiskFactor(
            label="Severity",
            points=sev_pts,
            explanation=f"Issue severity is {issue.severity.value}",
        ))
        total += sev_pts

        # 2. Confidence
        conf_pts = int(issue.confidence * 15)
        factors.append(RiskFactor(
            label="Confidence",
            points=conf_pts,
            explanation=f"Detection confidence: {issue.confidence * 100:.0f}%",
        ))
        total += conf_pts

        # 3. Category
        cat_pts = self.CATEGORY_POINTS.get(issue.category, 2)
        factors.append(RiskFactor(
            label="Category",
            points=cat_pts,
            explanation=f"Category: {issue.category.value.replace('_', ' ')}",
        ))
        total += cat_pts

        # 4. Production exposure
        if is_production:
            prod_pts = 15
            factors.append(RiskFactor(
                label="Production",
                points=prod_pts,
                explanation="Affects a production repository",
            ))
            total += prod_pts
            reasons.append("Affects production")

        # 5. Provider criticality
        crit_pts = int(provider_criticality * 12)
        if crit_pts > 0:
            factors.append(RiskFactor(
                label="Provider criticality",
                points=crit_pts,
                explanation=f"Provider importance score: {provider_criticality:.0%}",
            ))
            total += crit_pts

        # 6. Mitigation available (reduces risk)
        if issue.auto_fix_available:
            mitig_pts = -10
            factors.append(RiskFactor(
                label="Mitigation",
                points=mitig_pts,
                explanation="Automatic fix available",
            ))
            total += mitig_pts
            reasons.append("Mitigation available")

        # 7. Multi-file impact
        if issue.file and "/" in issue.file:
            # Single file = lower risk; multi-file would be higher
            pass  # TODO: when multi-file issues are supported

        # Cap and label
        total = max(0, min(100, total))
        level = _level(total)

        if total >= 80:
            reasons.insert(0, "Critical risk — immediate attention needed")
        elif total >= 60:
            reasons.insert(0, "High risk — should be addressed soon")
        elif total >= 40:
            reasons.insert(0, "Medium risk — monitor and plan")
        else:
            reasons.insert(0, "Low risk — no immediate action needed")

        return RiskScore(score=total, level=level, factors=factors, reasons=reasons)