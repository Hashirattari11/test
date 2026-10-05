"""Thin Supabase (PostgREST) client wrapper.

The backend is the *only* client that talks to Supabase, and it uses the
service-role key, so it can read/write freely. We keep a single cached client.

We deliberately keep this tiny: callers use `db().table("...")` directly with
the supabase-py fluent API. Helpers here just centralize construction and a few
common patterns (single-row fetch).
"""
from __future__ import annotations

import re
import time
from functools import lru_cache
from typing import Any

import httpx
import supabase._sync.client as supabase_sync_client
from supabase import Client, create_client

from .config import settings


def _add_transient_retry(client: Client, attempts: int = 3) -> None:
    """Retry idempotent PostgREST calls on transient transport failures.

    A dashboard page load fires a burst of Supabase calls from cold serverless
    instances, and Supabase occasionally drops mid-flight connections
    (httpx.RemoteProtocolError "Server disconnected" / ConnectError /
    ReadTimeout). Unhandled, those surfaced as random 500s on exactly the
    pages users hit first (/repos, /admin/users, health routes).

    Retry idempotent methods (GET/PATCH/DELETE) with a short backoff; POST is
    never retried — a disconnected POST may already have been applied and a
    retry could duplicate rows.
    """
    session = client.postgrest.session
    if getattr(session, "_autofix_retry_patched", False):
        return
    real_request = session.request

    def request_with_retry(method: str, url, **kwargs):
        last_exc: Exception | None = None
        for attempt in range(attempts):
            try:
                return real_request(method, url, **kwargs)
            except (
                httpx.RemoteProtocolError,
                httpx.ConnectError,
                httpx.ConnectTimeout,
                httpx.ReadTimeout,
                httpx.ReadError,
                httpx.PoolTimeout,
            ) as exc:
                last_exc = exc
                if str(method).upper() in ("GET", "PATCH", "DELETE") and attempt < attempts - 1:
                    time.sleep(0.15 * (2**attempt))
                    continue
                raise
        raise last_exc  # pragma: no cover — loop always returns or raises

    session.request = request_with_retry  # type: ignore[method-assign]
    session._autofix_retry_patched = True  # type: ignore[attr-defined]


def _patched() -> None:
    """Widen supabase-py's API-key validation to accept `sb_secret_...` keys.

    Supabase now issues service-role / publishable keys in the `sb_secret_...`
    format. The supabase-py client (v2.x) only accepts the legacy JWT format and
    rejects anything else by raising "Invalid API key" from a strict regex in
    `SyncClient.__init__`:
        re.match(r"^[A-Za-z0-9-_=]+\\.[A-Za-z0-9-_=]+\\.?[A-Za-z0-9-_.+/=]*$", key)

    The `sb_secret_...` keys are valid PostgREST credentials (the REST API
    accepts them), so we relax the module's `re` to also accept that format. We
    swap out the `re` module the `supabase._sync.client` module sees for a tiny
    stand-in whose `match` is lenient for the key validation pattern. The real
    `re` module is untouched.
    """
    if getattr(supabase_sync_client, "_autofix_patched", False):
        return

    real_match = re.match

    def lenient_match(pattern: str, string, flags=0):
        # Only relax the exact key-validation check; pass through everything else.
        if pattern.startswith(r"^[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?"):
            if isinstance(string, str) and string.startswith("sb_secret_"):
                return re.compile(r"^sb_secret_[A-Za-z0-9_-]+$").match(string)
        return real_match(pattern, string, flags)

    class _LenientRe:
        match = staticmethod(lenient_match)

        def __getattr__(self, name):
            return getattr(re, name)

    # Replace the module-level `re` binding that `supabase._sync.client` uses.
    supabase_sync_client.re = _LenientRe()
    supabase_sync_client._autofix_patched = True


@lru_cache
def db() -> Client:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set to talk to the database."
        )
    _patched()
    client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    _add_transient_retry(client)
    return client


def fetch_one(table: str, match: dict[str, Any]) -> dict[str, Any] | None:
    """Return the first row matching `match`, or None."""
    query = db().table(table).select("*")
    for col, val in match.items():
        query = query.eq(col, val)
    res = query.limit(1).execute()
    rows = res.data or []
    return rows[0] if rows else None
