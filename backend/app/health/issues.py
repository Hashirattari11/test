"""Unified Issue Model — the single source of truth for all reliability issues.

Every problem (provider changes, code bugs, quota risks, incidents) is
represented as a ReliabilityIssue. Deduplication via content_hash prevents
duplicate findings across scans. States track lifecycle from detection to
resolution.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class IssueStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    IGNORED = "ignored"


class IssueCategory(str, Enum):
    """The four fundamental problem types (must be distinguishable on dashboard)."""
    PROVIDER_PROBLEM = "provider_problem"       # Provider removed/changed API
    CUSTOMER_CODE = "customer_code"             # Customer code uses outdated pattern
    CUSTOMER_USAGE = "customer_usage"           # Quota/rate limit exceeded
    PROVIDER_INCIDENT = "provider_incident"     # Provider outage
    DEPENDENCY = "dependency"                   # SDK/package version issue
    CONFIGURATION = "configuration"             # Auth/config problem
    UNKNOWN = "unknown"


class IssueSource(str, Enum):
    SCAN = "scan"               # GitHub code scan
    CHANGELOG = "changelog"     # Provider changelog monitor
    PROVIDER_API = "provider_api"  # Direct provider API call
    STATUS_PAGE = "status_page" # Provider status page
    DEPENDENCY = "dependency"   # Package/dependency check
    MANUAL = "manual"           # User-reported


class IssueSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class ReliabilityIssue:
    """A unified reliability issue."""
    id: str | None = None
    provider: str = ""
    repository: str | None = None
    repo_id: str | None = None
    category: IssueCategory = IssueCategory.UNKNOWN
    severity: IssueSeverity = IssueSeverity.MEDIUM
    status: IssueStatus = IssueStatus.OPEN
    confidence: float = 0.5
    title: str = ""
    description: str = ""
    evidence: str = ""
    file: str | None = None
    line: int | None = None
    source: IssueSource = IssueSource.SCAN
    recommended_action: str = ""
    auto_fix_available: bool = False
    auto_fix_rule_id: str | None = None
    content_hash: str = ""
    created_at: str = ""
    updated_at: str = ""
    resolved_at: str | None = None

    def compute_hash(self) -> str:
        """Deterministic hash for deduplication."""
        text = f"{self.provider}:{self.repository}:{self.category.value}:{self.title}:{self.file}:{self.line}"
        return hashlib.sha256(text.lower().encode()).hexdigest()[:32]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "provider": self.provider,
            "repository": self.repository,
            "repo_id": self.repo_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "status": self.status.value,
            "confidence": self.confidence,
            "title": self.title,
            "description": self.description,
            "evidence": self.evidence,
            "file": self.file,
            "line": self.line,
            "source": self.source.value,
            "recommended_action": self.recommended_action,
            "auto_fix_available": self.auto_fix_available,
            "auto_fix_rule_id": self.auto_fix_rule_id,
            "content_hash": self.content_hash or self.compute_hash(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "resolved_at": self.resolved_at,
        }

    def to_client_friendly(self) -> dict:
        """Human-readable version for the dashboard (no technical jargon)."""
        friendly = self.to_dict()
        friendly["what_happened"] = _plain_language(self.description)
        friendly["why_it_matters"] = _impact_explanation(self.category, self.severity)
        friendly["what_to_do"] = _action_text(self.recommended_action, self.auto_fix_available)
        return friendly

    @classmethod
    def from_row(cls, row: dict) -> "ReliabilityIssue":
        """Build an issue from a reliability_issues DB row (tolerant parsing)."""
        def enum_of(enum, value, default):
            if value is None:
                return default
            try:
                return enum(value)
            except (ValueError, TypeError):
                return default

        return cls(
            id=row.get("id"),
            provider=row.get("provider") or "",
            repository=row.get("repository") or row.get("repo_full_name"),
            repo_id=row.get("repo_id"),
            category=enum_of(IssueCategory, row.get("category"), IssueCategory.UNKNOWN),
            severity=enum_of(IssueSeverity, row.get("severity"), IssueSeverity.MEDIUM),
            status=enum_of(IssueStatus, row.get("status"), IssueStatus.OPEN),
            confidence=row.get("confidence") or 0.5,
            title=row.get("title") or "",
            description=row.get("description") or "",
            evidence=row.get("evidence") or "",
            file=row.get("file"),
            line=row.get("line"),
            source=enum_of(IssueSource, row.get("source"), IssueSource.SCAN),
            recommended_action=row.get("recommended_action") or "",
            auto_fix_available=bool(row.get("auto_fix_available")),
            auto_fix_rule_id=row.get("auto_fix_rule_id"),
            content_hash=row.get("content_hash") or "",
            created_at=row.get("created_at") or "",
            updated_at=row.get("updated_at") or "",
            resolved_at=row.get("resolved_at"),
        )


def _plain_language(text: str) -> str:
    """Remove technical jargon for client-facing display."""
    replacements = {
        "AST resolver": "Code analysis",
        "call graph parameter mapping": "API call structure",
        "deprecated": "no longer supported",
        "breaking change": "change that may cause failures",
        "incompatible": "not matching",
    }
    result = text
    for old, new in replacements.items():
        result = result.replace(old, new)
    return result


def _impact_explanation(category: IssueCategory, severity: IssueSeverity) -> str:
    if category == IssueCategory.PROVIDER_PROBLEM:
        return "The API provider has changed something that affects your integration."
    if category == IssueCategory.CUSTOMER_CODE:
        return "Your code may be using an outdated API pattern that could fail."
    if category == IssueCategory.CUSTOMER_USAGE:
        return "Your usage may exceed limits, causing requests to fail."
    if category == IssueCategory.PROVIDER_INCIDENT:
        return "The API provider is experiencing an outage or degradation."
    if category == IssueCategory.DEPENDENCY:
        return "Your SDK or package version may be incompatible."
    if category == IssueCategory.CONFIGURATION:
        return "Your integration configuration may be incorrect."
    return "An issue was detected with your API integration."


def _action_text(recommended: str, auto_fix: bool) -> str:
    parts = [recommended] if recommended else ["Review this issue"]
    if auto_fix:
        parts.append("An automatic fix is available — you can create a PR from the dashboard.")
    return " ".join(parts)