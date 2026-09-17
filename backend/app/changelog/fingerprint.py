"""Stable change fingerprints for deduplication.

Primary key: provider_id + external_id (official entry id / release id / URL).
When an external_id is missing the entry cannot be stored (no-fabrication
invariant), so the DB-level secondary key (content hash) is only a safety net
for legacy rows.

Dedup semantics on a re-fetch of the SAME official entry:
  * external_id is unchanged -> do NOT insert a new row; bump last_seen_at so
    monitoring can show the entry is still current.
"""
from __future__ import annotations

import hashlib

from .base import RawEntry, normalize_text


def fingerprint_for_external(provider_id: str, external_id: str) -> str:
    """Stable fingerprint: provider + official external id."""
    raw = f"{provider_id}:{external_id}".strip().lower()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def content_fingerprint(provider_id: str, title: str, summary: str) -> str:
    """Content-based fingerprint (safety net; not used for storage decisions)."""
    raw = f"{provider_id}:{normalize_text(title)}:{normalize_text(summary)}"
    return hashlib.sha256(raw.lower().encode("utf-8")).hexdigest()


def entry_fingerprint(provider_id: str, entry: RawEntry) -> str:
    """Primary fingerprint used for dedup — based on the official external_id."""
    return fingerprint_for_external(provider_id, entry.external_id)