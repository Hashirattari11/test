"""Secret redaction — defensive sanitation for any text that leaves the system.

The scanner only ever stores environment-variable NAMES, never values. This
utility is a second layer: before any evidence/description/alert/PR text is
persisted or displayed, runs through redact() so accidental raw secrets can
never reach logs, emails, the dashboard, or PR bodies.
"""
from __future__ import annotations

import re

# Covers common provider secret formats WITHOUT hardcoding any real value.
_PATTERNS: list[tuple[str, str]] = [
    (r"sk_live_[A-Za-z0-9]{16,}", "sk_live_…REDACTED…"),
    (r"sk_test_[A-Za-z0-9]{16,}", "sk_test_…REDACTED…"),
    (r"sk-[A-Za-z0-9_-]{20,}", "sk-…REDACTED…"),
    (r"AIza[0-9A-Za-z_-]{20,}", "AIza…REDACTED…"),
    (r"xox[baprs]-[0-9A-Za-z-]{10,}", "xox…REDACTED…"),
    (r"ghp_[0-9A-Za-z]{30,}", "ghp_…REDACTED…"),
    (r"github_pat_[0-9A-Za-z_]{20,}", "github_pat_…REDACTED…"),
    (r"AKIA[0-9A-Z]{16}", "AKIA…REDACTED…"),
    (r"Bearer\s+[A-Za-z0-9._-]{16,}", "Bearer …REDACTED…"),
    (r"Basic\s+[A-Za-z0-9+/=]{16,}", "Basic …REDACTED…"),
    (r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}", "JWT…REDACTED…"),
    (r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----", "-----BEGIN PRIVATE KEY-----…REDACTED…"),
    # Generic secret assignment: NAME=value / NAME: value  (env-var style)
    (r"\b([A-Z][A-Z0-9_]{2,}(?:_KEY|_SECRET|_TOKEN|_PASSWORD|_API_KEY))\s*[=:]\s*\S+", r"\1=…REDACTED…"),
    (r"\b(api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password)\b\s*[=:]\s*\S+", r"\1=…REDACTED…"),
]

_COMPILED: list[tuple[re.Pattern, str]] = [
    (re.compile(pat, re.IGNORECASE), repl) for pat, repl in _PATTERNS
]


def redact(text: str | None, placeholder: str = "…REDACTED…") -> str:
    """Return a safe copy of text with secret-like values replaced."""
    if not text:
        return text or ""
    out = text
    for pattern, repl in _COMPILED:
        out = pattern.sub(repl, out)
    return out


def contains_secret_like(text: str | None) -> bool:
    """True when text still contains something that looks like a secret."""
    if not text:
        return False
    return any(p.search(text) for p, _ in _COMPILED)