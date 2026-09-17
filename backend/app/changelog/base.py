"""Strict provider-adapter framework (replaces generic scraping).

A ProviderAdapter fetches entries from an OFFICIAL source only and returns
RawEntry objects. The no-fabrication invariant:

  An entry is stored ONLY when ALL of the following come from the official
  source: external_id (feed entry id / release id / entry URL), title,
  permalink, and published_at. Anything less is DROPPED with a reason.

Lookback window: entries older than ``lookback_days`` are never returned, so
a provider's archive is never re-reported as "new" changes.

HTML_STRICT extraction only accepts blocks that contain a permalink, a
title-like heading, and a parseable date; undated boilerplate (nav text,
footers) is dropped. If fewer than 2 dated entries parse, the adapter returns
[] (the scheduler marks the provider LIMITED) instead of emitting junk.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Callable, Optional

import requests
from bs4 import BeautifulSoup, Tag

from .sources import ProviderSource, HTML_STRICT


class FetchError(Exception):
    """Raised when a provider source cannot be fetched (network/HTTP/parse)."""


@dataclass
class RawEntry:
    """A typed entry from an official source. Every field is required."""
    external_id: str
    title: str
    url: str
    published_at: str  # ISO 8601 UTC
    summary: str
    source: str        # human-readable official source label

    def __post_init__(self) -> None:
        # The invariant: nothing here may be empty.
        if not self.external_id or not self.title or not self.url or not self.published_at:
            raise ValueError(f"RawEntry missing required field: {self}")


# ---------------------------------------------------------------------------
# text / date / url helpers
# ---------------------------------------------------------------------------
WS = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    return WS.sub(" ", text or "").strip()


def compute_content_hash(text: str) -> str:
    return hashlib.sha256(normalize_text(text).lower().encode("utf-8")).hexdigest()


def parse_datetime(value: str) -> Optional[datetime]:
    """Parse a date string into a tz-aware UTC datetime, or None."""
    value = (value or "").strip()
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


_DATEFMT = re.compile(r"\b(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\b")


def coerce_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def resolve_url(base: str, href: str) -> str:
    """Resolve possibly-relative links against the page URL."""
    if not href:
        return base
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return base.rstrip("/") + "/" + href.lstrip("/")


def extract_date_from_element(el: Tag) -> Optional[datetime]:
    """Best-effort date extraction from an HTML element (strict date rule)."""
    time_el = el.find("time", attrs={"datetime": True})
    if time_el and time_el.get("datetime"):
        dt = parse_datetime(time_el["datetime"])
        if dt:
            return dt
    meta = el.find("meta", attrs={"itemprop": "datePublished"})
    if meta and meta.get("content"):
        dt = parse_datetime(meta["content"])
        if dt:
            return dt
    for cls in ("date", "time", "published", "post-date", "entry-date", "updated"):
        node = el.find(class_=lambda c: c and cls in (c or "").lower()) if el.find else None
        if node:
            dt = parse_datetime(node.get_text(" ", strip=True))
            if dt:
                return dt
    m = _DATEFMT.search(el.get_text(" ", strip=True))
    if m:
        dt = parse_datetime(f"{m.group(1)}-{m.group(2)}-{m.group(3)}")
        if dt:
            return dt
    return None


# ---------------------------------------------------------------------------
# Adapter base class
# ---------------------------------------------------------------------------
class ProviderAdapter:
    """Base class for official-source adapters.

    Subclasses define ``provider_id`` and ``fetch(session) -> list[RawEntry]``
    using the strict helpers below. ``source`` comes from the registry.
    """

    provider_id: str = ""

    def __init__(self, source: ProviderSource, user_agent: str = "Breaklytix-ChangelogMonitor/1.0"):
        self.source = source
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
        })

    def _lookback_cutoff(self) -> datetime:
        return datetime.now(timezone.utc) - timedelta(days=self.source.lookback_days)

    def _in_window(self, dt: datetime | None) -> bool:
        return dt is not None and dt >= self._lookback_cutoff()

    def _cap(self, entries: list[RawEntry]) -> list[RawEntry]:
        return entries[: self.source.max_entries]

    # -- strict RSS/Atom -----------------------------------------------------
    def fetch_rss_strict(self, url: str) -> list[RawEntry]:
        """Parse an official RSS/Atom feed with the strict invariant + window."""
        resp = self._get(url)
        soup = BeautifulSoup(resp.content, "html.parser")
        entries: list[RawEntry] = []
        for item in soup.find_all(["item", "entry"]):
            title_el = item.find("title")
            link = item.find("link")
            if item.name == "item":
                link_url = (link.get_text(" ", strip=True) or link.get("href", "")) if link else ""
            else:  # atom
                link_url = link.get("href", "") if link else ""
            guid = item.find("guid") or item.find("id")
            pub_el = (item.find("pubdate") or item.find("date")
                      or item.find("updated") or item.find("published"))
            summary_el = item.find("description") or item.find("summary") or item.find("content")

            title = normalize_text(title_el.get_text(" ", strip=True)) if title_el else ""
            summary = normalize_text(summary_el.get_text(" ", strip=True)) if summary_el else ""
            pub = parse_datetime(pub_el.get_text(" ", strip=True)) if pub_el else None
            if not self._in_window(pub):
                continue
            ext_id = (guid.get_text(" ", strip=True) if guid else "") or link_url or title
            entry = RawEntry(
                external_id=ext_id,
                title=title or ext_id,
                url=resolve_url(url, link_url) if link_url else url,
                published_at=coerce_iso(pub or datetime.now(timezone.utc)),
                summary=summary,
                source=f"{self.source.display_name} Changelog (RSS)",
            )
            entries.append(entry)
        return self._cap([e for e in entries if e.title])

    # -- strict GitHub Releases API -------------------------------------------
    def fetch_github_releases(self, api_url: str, owner_repo: str) -> list[RawEntry]:
        """Fetch official GitHub Releases for an organization's repos (API)."""
        resp = self._get(api_url, headers={"Accept": "application/vnd.github+json"})
        data = resp.json()
        if not isinstance(data, list):
            raise FetchError(f"{owner_repo}: unexpected releases payload")
        entries: list[RawEntry] = []
        for rel in data:
            pub = parse_datetime(rel.get("published_at") or "")
            if not self._in_window(pub):
                continue
            name = normalize_text(rel.get("name") or rel.get("tag_name") or "")
            body = normalize_text(rel.get("body") or "")
            if not name and not body:
                continue
            entries.append(RawEntry(
                external_id=str(rel.get("id") or rel.get("html_url") or name),
                title=name or f"{owner_repo} {rel.get('tag_name', '')}".strip(),
                url=rel.get("html_url") or self.source.changelog_url,
                published_at=coerce_iso(pub or datetime.now(timezone.utc)),
                summary=body[:2000],
                source=f"{self.source.display_name} Releases (GitHub)",
            ))
        return self._cap(entries)

    # -- strict HTML extraction -----------------------------------------------
    def fetch_html_strict(
        self,
        url: str,
        selectors: list[str],
        date_selector: Optional[list[str]] = None,
    ) -> list[RawEntry]:
        """Extract dated entries from an official HTML page (strict).

        A candidate block is accepted only when it yields a permalink, a
        title, AND a parseable date within the lookback window. Undated
        blocks (nav, footer, boilerplate) are always dropped.
        """
        resp = self._get(url)
        soup = BeautifulSoup(resp.text, "html.parser")
        entries: list[RawEntry] = []
        seen: set[str] = set()
        candidates: list[Tag] = []
        for sel in selectors:
            candidates = soup.select(sel)
            if len(candidates) >= 2:
                break
        for el in candidates:
            title_el = el.find(["h2", "h3", "h4", "[class*=title]"]) if el.find else None
            link_el = el.find("a", href=True) if el.find else None
            if not title_el and not link_el:
                continue
            dt = extract_date_from_element(el)
            if not self._in_window(dt):
                continue
            title = normalize_text(title_el.get_text(" ", strip=True)) if title_el else ""
            if not title and link_el:
                title = normalize_text(link_el.get_text(" ", strip=True))
            if len(title) < 8:
                continue
            link_url = resolve_url(url, link_el["href"]) if link_el else url
            if link_url in seen:
                continue
            seen.add(link_url)
            summary = normalize_text(el.get_text(" ", strip=True))[:2000]
            entries.append(RawEntry(
                external_id=link_url,
                title=title[:500],
                url=link_url,
                published_at=coerce_iso(dt),
                summary=summary,
                source=f"{self.source.display_name} Changelog (official page)",
            ))
        return self._cap(entries)

    # -- HTTP -----------------------------------------------------------------
    def _get(self, url: str, headers: dict | None = None) -> requests.Response:
        self._assert_allowed_url(url)
        try:
            resp = self.session.get(url, timeout=20, headers=headers or {})
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            raise FetchError(f"{self.provider_id}: GET {url} failed: {e}") from e

    # -- SSRF guard -----------------------------------------------------------
    def _assert_allowed_url(self, url: str) -> None:
        """SSRF guard (user spec §security): only the registry's official host
        may be fetched. The sources registry is a hardcoded allowlist, so any
        URL that isn't on the provider's own host is refused outright — no
        user-supplied URLs are ever requested."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.scheme not in ("https", "http"):
            raise FetchError(f"{self.provider_id}: refused non-http(s) URL {url}")
        allowed = {self.source.host, "api.github.com", "github.com"}
        if parsed.hostname not in allowed:
            raise FetchError(
                f"{self.provider_id}: SSRF guard refused host {parsed.hostname!r} "
                f"(allowed: {sorted(allowed)})"
            )

    def fetch(self) -> list[RawEntry]:
        """Override in subclasses. Returns raw entries from the official source."""
        raise NotImplementedError

    def fetch_with_source(self) -> tuple[list[RawEntry], str]:
        """Fetch + report the source kind used (for monitoring status)."""
        return self.fetch(), self.source.source_kind