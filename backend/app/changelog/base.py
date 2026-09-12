"""Base changelog fetcher with RSS/Atom parsing and HTML fallback.

All provider-specific fetchers inherit from BaseFetcher. The base handles:
- RSS/Atom feed parsing (preferred)
- HTML scraping fallback (BeautifulSoup)
- Content hashing for deduplication
- Normalization to changelog_events schema
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import requests
from bs4 import BeautifulSoup

# Breaking change keywords for classification
BREAKING_KEYWORDS = re.compile(
    r"\b(deprecat|remov|renam|no longer|replaced|breaking|is now|will be removed|"
    r"sunset|discontinu|migrat|retired|end.of.life|eol|shutdown|deprecated|removed)\w*",
    re.IGNORECASE,
)

SECURITY_KEYWORDS = re.compile(
    r"\b(security|vulnerability|cve|exploit|breach|patch|urgent|critical)\w*",
    re.IGNORECASE,
)

CODE_TOKEN = re.compile(r"`([^`]+)`")
WS = re.compile(r"\s+")


@dataclass
class ChangelogEvent:
    """Normalized changelog event ready for DB insertion."""
    provider: str
    title: str
    source_url: str
    published_date: str  # ISO format
    raw_summary: str
    event_type: str  # breaking_change | deprecation | security | new_feature | bug_fix | unknown
    severity: str  # critical | high | medium | low
    deadline: Optional[str] = None
    affected_endpoints: Optional[list[str]] = None
    affected_sdks: Optional[list[str]] = None
    affected_versions: Optional[list[str]] = None
    content_hash: str = ""
    symbols: list[str] = field(default_factory=list)


def normalize_text(text: str) -> str:
    """Normalize whitespace in text."""
    return WS.sub(" ", text).strip()


def compute_content_hash(text: str) -> str:
    """SHA256 hash of normalized lowercase text for deduplication."""
    return hashlib.sha256(normalize_text(text).lower().encode("utf-8")).hexdigest()


def classify_event_type(text: str) -> str:
    """Classify a changelog entry into an event type."""
    lower = text.lower()
    if SECURITY_KEYWORDS.search(lower):
        return "security"
    if "deprecat" in lower:
        return "deprecation"
    if BREAKING_KEYWORDS.search(lower):
        return "breaking_change"
    if any(w in lower for w in ["new feature", "added", "introducing", "now supports"]):
        return "new_feature"
    if any(w in lower for w in ["bug fix", "fixed", "resolved", "patch"]):
        return "bug_fix"
    return "unknown"


def extract_old_new(text: str) -> tuple[str | None, str | None]:
    """Best-effort old/new value extraction from backticked tokens."""
    m = re.search(r"`([^`]+)`\s+is now\s+`([^`]+)`", text)
    if m:
        return m.group(1), m.group(2)
    m = re.search(r"renamed\s+`([^`]+)`\s+to\s+`([^`]+)`", text, re.IGNORECASE)
    if m:
        return m.group(1), m.group(2)
    m = re.search(r"replaced?\s+`([^`]+)`\s+with\s+`([^`]+)`", text, re.IGNORECASE)
    if m:
        return m.group(1), m.group(2)
    codes = CODE_TOKEN.findall(text)
    if codes and re.search(r"deprecat|remov|no longer|sunset", text, re.IGNORECASE):
        return codes[0], None
    return None, None


def extract_symbols(text: str) -> list[str]:
    """Extract code symbols (backticked tokens) from text."""
    return CODE_TOKEN.findall(text)


def score_severity(text: str, event_type: str) -> str:
    """Score severity based on event type and content."""
    lower = text.lower()
    if event_type == "security":
        return "critical"
    if event_type in ("breaking_change", "deprecation"):
        if any(w in lower for w in ["immediately", "urgent", "critical", "shutdown"]):
            return "critical"
        if any(w in lower for w in ["soon", "next release", "30 days", "60 days"]):
            return "high"
        return "medium"
    return "low"


class BaseFetcher:
    """Base class for provider changelog fetchers.
    
    Subclasses must implement:
    - provider_id: str
    - fetch() -> list[ChangelogEvent]
    """
    
    provider_id: str = ""
    changelog_url: str = ""
    rss_url: Optional[str] = None
    
    def __init__(self, user_agent: str = "AutoFixAPI-ChangelogMonitor/1.0"):
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
    
    def fetch(self) -> list[ChangelogEvent]:
        """Fetch and parse changelog entries. Override in subclasses."""
        raise NotImplementedError
    
    def fetch_rss(self, url: str | None = None) -> list[ChangelogEvent]:
        """Parse an RSS/Atom feed into ChangelogEvents."""
        url = url or self.rss_url
        if not url:
            return []
        
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.content, "html.parser")
        events = []
        
        # Handle RSS 2.0
        for item in soup.find_all("item"):
            title = item.find("title")
            link = item.find("link")
            pub_date = item.find("pubdate") or item.find("date")
            desc = item.find("description")
            
            if not title or not link:
                continue
            
            title_text = normalize_text(title.get_text())
            link_text = normalize_text(link.get_text()) or link.get("href", "")
            desc_text = normalize_text(desc.get_text()) if desc else ""
            pub_text = normalize_text(pub_date.get_text()) if pub_date else ""
            
            event = self._make_event(title_text, link_text, pub_text, desc_text)
            if event:
                events.append(event)
        
        # Handle Atom
        for entry in soup.find_all("entry"):
            title = entry.find("title")
            link = entry.find("link")
            updated = entry.find("updated") or entry.find("published")
            summary = entry.find("summary") or entry.find("content")
            
            if not title or not link:
                continue
            
            title_text = normalize_text(title.get_text())
            link_text = link.get("href", "")
            updated_text = normalize_text(updated.get_text()) if updated else ""
            summary_text = normalize_text(summary.get_text()) if summary else ""
            
            event = self._make_event(title_text, link_text, updated_text, summary_text)
            if event:
                events.append(event)
        
        return events
    
    def fetch_html(self, url: str | None = None, selectors: list[str] | None = None) -> list[ChangelogEvent]:
        """Scrape HTML changelog page using CSS selectors."""
        url = url or self.changelog_url
        selectors = selectors or ["article", "[class*=changelog]", "li", "p", "h2", "h3"]
        
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, "html.parser")
        events = []
        seen = set()
        
        for selector in selectors:
            for el in soup.select(selector):
                text = normalize_text(el.get_text(" ", strip=True))
                if len(text) < 20:
                    continue
                
                content_hash = compute_content_hash(text)
                if content_hash in seen:
                    continue
                seen.add(content_hash)
                
                # Find nearest link
                link = el.find("a", href=True)
                link_url = link["href"] if link else url
                if link_url and not link_url.startswith("http"):
                    link_url = url.rstrip("/") + "/" + link_url.lstrip("/")
                
                event = self._make_event(text[:200], link_url, "", text)
                if event:
                    events.append(event)
            
            if events:
                break
        
        return events
    
    def _make_event(self, title: str, url: str, published: str, summary: str) -> ChangelogEvent | None:
        """Create a ChangelogEvent from raw data."""
        text = f"{title} {summary}"
        if len(normalize_text(text)) < 15:
            return None
        
        event_type = classify_event_type(text)
        severity = score_severity(text, event_type)
        symbols = extract_symbols(text)
        old_val, new_val = extract_old_new(text)
        
        if old_val:
            symbols.append(old_val)
        if new_val:
            symbols.append(new_val)
        
        # Parse published date to ISO format
        if published:
            try:
                # Try common formats
                for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
                    try:
                        dt = datetime.strptime(published, fmt)
                        published = dt.isoformat()
                        break
                    except ValueError:
                        continue
            except Exception:
                published = datetime.now(timezone.utc).isoformat()
        else:
            published = datetime.now(timezone.utc).isoformat()
        
        return ChangelogEvent(
            provider=self.provider_id,
            title=title[:500],
            source_url=url,
            published_date=published,
            raw_summary=normalize_text(summary)[:2000],
            event_type=event_type,
            severity=severity,
            content_hash=compute_content_hash(f"{self.provider_id}:{title}:{summary}"),
            symbols=symbols,
        )
