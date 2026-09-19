"""Secret redaction for persisted scan output.

Any line of source code can contain a real credential (a hardcoded API key,
token, or secret). Detections/findings persist the whole matched line in
``matched_snippet`` / ``current_usage`` — that would leak the raw secret into
the database. Every persisted snippet passes through :func:`redact_snippet`
before insert.

Only secret VALUES are replaced. Environment-variable NAMES (e.g.
``STRIPE_SECRET_KEY``) are references, not secrets, and are left intact.
"""
from __future__ import annotations

import re
from typing import Any

_PLACEHOLDER = "\u2022\u2022\u2022\u2022\u2022\u2022"  # •••••• (6 bullets)

# Order matters: longest/most specific tokens first. Each pattern must capture
# the FULL token so the raw secret never survives in any substring.
_REDACT_PATTERNS: list[re.Pattern] = [
    # Stripe live/restricted keys
    re.compile(r"sk_live_[A-Za-z0-9]{16,}"),
    re.compile(r"rk_live_[A-Za-z0-9]{16,}"),
    # OpenAI / generic sk- bearer keys (letters, digits, hyphens, underscores)
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    # SendGrid
    re.compile(r"SG\.[A-Za-z0-9_\-\.]{16,}"),
    # Slack tokens (xoxb / xoxa / xoxp / xoxr / xoxs)
    re.compile(r"xox[baprs]-[A-Za-z0-9\-]{10,}"),
    # Google API keys
    re.compile(r"AIza[0-9A-Za-z\-_]{35}"),
    # Twilio account SIDs
    re.compile(r"\bAC[0-9a-f]{32}\b"),
    # AWS access key IDs
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    # GitHub PATs (ghp_, gho_, ghu_, ghs_, ghr_, github_pat_)
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    # GitHub fine-grained PAT
    re.compile(r"gho_[A-Za-z0-9]{36}"),
    # Generic bearer tokens in code (Authorization headers) — keep the
    # "Bearer" label, redact only the token value.
    re.compile(r"(?i)(Bearer\s+)[A-Za-z0-9\-._~+/]+=*"),
    # Shopify admin access tokens (shpat_, shpca_, shppa_, shpss_)
    re.compile(r"sh[pca]+_[A-Za-z0-9]{20,}"),
    # Heroku / other UUID-ish secrets only when clearly assigned (avoid over-redact risk of sha hashes): skip.
]


def redact_snippet(text: str | None) -> str | None:
    """Replace known secret tokens in ``text`` with a bullet placeholder.

    Safe on ``None`` and empty strings. Env-var NAMES are untouched because
    none of the patterns match a bare ``NAME_LIKE`` token without a value
    prefix/suffix shape (e.g. ``sk_live_`` requires 16+ alnum chars after it).
    """
    if not text:
        return text
    out = text
    for pattern in _REDACT_PATTERNS:
        use_group = "(?i)(Bearer\\s+)" in pattern.pattern
        if use_group:
            out = pattern.sub(r"\1" + _PLACEHOLDER, out)
        else:
            out = pattern.sub(_PLACEHOLDER, out)
    return out


def redact_object(obj: Any) -> Any:
    """Deep-redact every string inside dicts/lists/JSON strings.

    Used before persisting any scan artifact.
    """
    if isinstance(obj, str):
        return redact_snippet(obj)
    if isinstance(obj, dict):
        return {k: redact_object(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact_object(v) for v in obj]
    return obj