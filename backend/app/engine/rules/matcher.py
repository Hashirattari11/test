"""Rules matcher: enrich a scan's usage findings with breaking-change findings."""
from __future__ import annotations

from .registry import RULES, BreakingRule


def enrich_findings(findings_rows: list[dict], tree_paths: list[str] | None = None) -> list[dict]:
    """Return the original findings plus any matched breaking-change findings.

    Each input row is a usage finding dict with keys: severity, type, provider,
    file, line, message, current_usage, recommended_fix, confidence, ...
    (matching the `findings` table schema). Matching is done against the
    snippet/current_usage and, for file-name rules, the repo's file list.
    """
    out = list(findings_rows)
    existing_keys = {(r["file"], r.get("line"), r["message"]) for r in out}
    tree_low = {p.lower() for p in (tree_paths or [])}

    for row in findings_rows:
        provider = row.get("provider")
        snippet = row.get("current_usage") or row.get("message") or ""
        file_low = (row.get("file") or "").lower()

        for rule in RULES:
            if rule.provider is not None and provider != rule.provider:
                # A provider rule may also match via content even if the detection
                # didn't tag the provider (e.g. `new Mail` without a sendgrid hit).
                if not rule.matches(snippet):
                    continue
            if rule.provider is None and not rule.matches(snippet):
                # File-scoped universal rules can also match on path keywords.
                if not any(kw in file_low for kw in ("secret", "config", "env", "credentials")):
                    continue

            message = f"{rule.title}: {rule.description}"
            if rule.change_type != "secret_leak":
                message = f"Potential: {message}"
            key = (row.get("file"), row.get("line"), message)
            if key in existing_keys:
                continue
            existing_keys.add(key)

            out.append({
                "scan_id": row.get("scan_id"),
                "repo_id": row.get("repo_id"),
                "severity": rule.severity,
                "type": rule.change_type,
                "provider": row.get("provider"),
                "file": row.get("file"),
                "line": row.get("line"),
                "message": message,
                "current_usage": snippet,
                "recommended_fix": rule.recommended_fix,
                "confidence": rule.confidence,
                "status": "open",
                "verification_status": "potential",
                "tech": row.get("tech"),
                "rule_id": rule.id,
            })
    return out