"""Changelog scrapers (requests + BeautifulSoup) for multiple providers.

Kept PURE (fetch + parse only) so it's unit-testable and so the DB dedupe logic
lives in the router. On each daily cron run we fetch once, parse candidate
entries, and hand them up; the caller inserts only genuinely-new ones (dedupe by
content_hash).

Politeness: one request per run, descriptive User-Agent, sane timeout. The
"at most once per day" guarantee comes from the cron schedule, not from here.

NOTE ON MARKUP: Provider changelog markup changes over time. This parser is
deliberately *heuristic and resilient*: it first tries structured entry
containers, then falls back to keyword-filtered text blocks. If a provider
ships new markup, tune the selectors — no other code needs to change.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup

from .config import settings
from .signatures import extract_stripe_symbols, extract_symbols

# Elements that (historically) wrap an individual changelog entry. Tried in order.
STRUCTURED_SELECTORS: list[str] = [
    "article",
    "[class*=Changelog]",
    "[class*=changelog]",
    "section[class*=entry]",
    "li[class*=entry]",
]

# Only text blocks mentioning these are treated as (potentially breaking) entries
# in the generic fallback path.
BREAKING_KEYWORDS = re.compile(
    r"\b(deprecat|remov|renam|no longer|replaced|breaking|is now|will be removed|"
    r"sunset|discontinu|migrat)\w*",
    re.IGNORECASE,
)

_CODE_TOKEN = re.compile(r"`([^`]+)`")
_WS = re.compile(r"\s+")


@dataclass
class ParsedEntry:
    description: str
    change_type: str
    old_value: str | None
    new_value: str | None
    content_hash: str
    symbols: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# fetch
# ---------------------------------------------------------------------------
def fetch_changelog_html(url: str | None = None) -> str:
    url = url or settings.stripe_changelog_url
    resp = requests.get(
        url,
        headers={
            "User-Agent": settings.scraper_user_agent,
            "Accept": "text/html,application/xhtml+xml",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.text


# ---------------------------------------------------------------------------
# classify + extract
# ---------------------------------------------------------------------------
def _normalize(text: str) -> str:
    return _WS.sub(" ", text).strip()


def _hash(text: str) -> str:
    return hashlib.sha256(_normalize(text).lower().encode("utf-8")).hexdigest()


def classify_change_type(text: str) -> str:
    t = text.lower()
    # Order matters: removal/deprecation win over rename when both could match
    # (e.g. "X is now deprecated" is a deprecation, not a rename).
    if "deprecat" in t:
        return "endpoint_deprecated"
    if "remov" in t or "no longer" in t or "sunset" in t or "discontinu" in t:
        return "field_removed"
    if (
        "renam" in t
        or "is now called" in t
        or "renamed to" in t
        or "replaced" in t
        or re.search(r"`[^`]+`\s+is now\s+`", text)
    ):
        return "field_renamed"
    return "other"


def extract_old_new(text: str) -> tuple[str | None, str | None]:
    """Best-effort old/new value extraction from an entry's text."""
    # `X` is now `Y`  /  renamed `X` to `Y`  /  replaced `X` with `Y`
    m = re.search(r"`([^`]+)`\s+is now\s+`([^`]+)`", text)
    if m:
        return m.group(1), m.group(2)
    m = re.search(r"renamed\s+`([^`]+)`\s+to\s+`([^`]+)`", text, re.IGNORECASE)
    if m:
        return m.group(1), m.group(2)
    m = re.search(r"replaced?\s+`([^`]+)`\s+with\s+`([^`]+)`", text, re.IGNORECASE)
    if m:
        return m.group(1), m.group(2)
    m = re.search(r"`([^`]+)`\s+.*\b(?:renamed|changed)\b.*\bto\s+`([^`]+)`", text, re.IGNORECASE)
    if m:
        return m.group(1), m.group(2)

    # Deprecation/removal: capture the first backticked token as the old value.
    codes = _CODE_TOKEN.findall(text)
    if codes and re.search(r"deprecat|remov|no longer|sunset", text, re.IGNORECASE):
        return codes[0], None
    return None, None


def _make_entry(text: str) -> ParsedEntry | None:
    norm = _normalize(text)
    if len(norm) < 12:
        return None
    old, new = extract_old_new(norm)
    return ParsedEntry(
        description=norm[:2000],
        change_type=classify_change_type(norm),
        old_value=old,
        new_value=new,
        content_hash=_hash(norm),
        symbols=extract_stripe_symbols(norm),
    )


# ---------------------------------------------------------------------------
# parse
# ---------------------------------------------------------------------------
def parse_entries(html: str, breaking_only: bool = True, max_entries: int = 200) -> list[ParsedEntry]:
    """Extract candidate changelog entries from raw HTML.

    breaking_only=True keeps only entries that look like breaking changes
    (deprecation/removal/rename), which is what we alert on.
    """
    soup = BeautifulSoup(html, "html.parser")
    seen_hashes: set[str] = set()
    entries: list[ParsedEntry] = []

    def consider(text: str) -> None:
        if not text:
            return
        if breaking_only and not BREAKING_KEYWORDS.search(text):
            return
        entry = _make_entry(text)
        if entry and entry.content_hash not in seen_hashes:
            seen_hashes.add(entry.content_hash)
            entries.append(entry)

    # 1) structured containers
    for selector in STRUCTURED_SELECTORS:
        for el in soup.select(selector):
            consider(el.get_text(" ", strip=True))
        if entries:
            break

    # 2) generic fallback: individual list items / paragraphs / headings
    if not entries:
        for el in soup.select("li, p, h2, h3, h4"):
            consider(el.get_text(" ", strip=True))

    return entries[:max_entries]


def scrape(url: str | None = None, breaking_only: bool = True) -> tuple[list[ParsedEntry], str]:
    """Fetch + parse. Returns (entries, source_url)."""
    url = url or settings.stripe_changelog_url
    html = fetch_changelog_html(url)
    return parse_entries(html, breaking_only=breaking_only), url


# ---------------------------------------------------------------------------
# SendGrid Changelog Scraper
# ---------------------------------------------------------------------------
# SendGrid's changelog at docs.sendgrid.com/for-developers/changelog uses a
# different structure. We'll use a generic parser with SendGrid-specific selectors.

SENDGRID_SELECTORS: list[str] = [
    "article",
    "[class*=changelog]",
    "[class*=Changelog]",
    "section[class*=post]",
    "div[class*=post]",
    "li[class*=entry]",
]

SENDGRID_BREAKING_KEYWORDS = re.compile(
    r"\b(deprecat|remov|renam|no longer|replaced|breaking|is now|will be removed|"
    r"sunset|discontinu|migrat|retired|end.of.life|eol)\w*",
    re.IGNORECASE,
)


def _make_sendgrid_entry(text: str) -> ParsedEntry | None:
    norm = _normalize(text)
    if len(norm) < 12:
        return None
    old, new = extract_old_new(norm)
    return ParsedEntry(
        description=norm[:2000],
        change_type=classify_change_type(norm),
        old_value=old,
        new_value=new,
        content_hash=_hash(norm),
        symbols=extract_symbols("sendgrid", norm),
    )


def parse_sendgrid_entries(html: str, breaking_only: bool = True, max_entries: int = 200) -> list[ParsedEntry]:
    soup = BeautifulSoup(html, "html.parser")
    seen_hashes: set[str] = set()
    entries: list[ParsedEntry] = []

    def consider(text: str) -> None:
        if not text:
            return
        if breaking_only and not SENDGRID_BREAKING_KEYWORDS.search(text):
            return
        entry = _make_sendgrid_entry(text)
        if entry and entry.content_hash not in seen_hashes:
            seen_hashes.add(entry.content_hash)
            entries.append(entry)

    # 1) structured containers
    for selector in SENDGRID_SELECTORS:
        for el in soup.select(selector):
            consider(el.get_text(" ", strip=True))
        if entries:
            break

    # 2) generic fallback
    if not entries:
        for el in soup.select("li, p, h2, h3, h4, article, .post, .entry"):
            consider(el.get_text(" ", strip=True))

    return entries[:max_entries]


def scrape_sendgrid(url: str | None = None, breaking_only: bool = True) -> tuple[list[ParsedEntry], str]:
    url = url or settings.sendgrid_changelog_url
    html = fetch_changelog_html(url)
    return parse_sendgrid_entries(html, breaking_only=breaking_only), url


# ---------------------------------------------------------------------------
# GitHub Changelog Scraper
# ---------------------------------------------------------------------------
# GitHub's changelog at github.blog/changelog/ uses a blog-style layout.

GITHUB_SELECTORS: list[str] = [
    "article",
    "[class*=changelog]",
    "[class*=Changelog]",
    "div[class*=post]",
    "li[class*=post]",
    ".post-item",
]

GITHUB_BREAKING_KEYWORDS = re.compile(
    r"\b(deprecat|remov|renam|no longer|replaced|breaking|is now|will be removed|"
    r"sunset|discontinu|migrat|retired|end.of.life|eol|deprecated|removed)\w*",
    re.IGNORECASE,
)


def _make_github_entry(text: str) -> ParsedEntry | None:
    norm = _normalize(text)
    if len(norm) < 12:
        return None
    old, new = extract_old_new(norm)
    return ParsedEntry(
        description=norm[:2000],
        change_type=classify_change_type(norm),
        old_value=old,
        new_value=new,
        content_hash=_hash(norm),
        symbols=extract_symbols("github", norm),
    )


def parse_github_entries(html: str, breaking_only: bool = True, max_entries: int = 200) -> list[ParsedEntry]:
    soup = BeautifulSoup(html, "html.parser")
    seen_hashes: set[str] = set()
    entries: list[ParsedEntry] = []

    def consider(text: str) -> None:
        if not text:
            return
        if breaking_only and not GITHUB_BREAKING_KEYWORDS.search(text):
            return
        entry = _make_github_entry(text)
        if entry and entry.content_hash not in seen_hashes:
            seen_hashes.add(entry.content_hash)
            entries.append(entry)

    # 1) structured containers
    for selector in GITHUB_SELECTORS:
        for el in soup.select(selector):
            consider(el.get_text(" ", strip=True))
        if entries:
            break

    # 2) generic fallback
    if not entries:
        for el in soup.select("li, p, h2, h3, h4, article, .post-item, .changelog-entry"):
            consider(el.get_text(" ", strip=True))

    return entries[:max_entries]


def scrape_github(url: str | None = None, breaking_only: bool = True) -> tuple[list[ParsedEntry], str]:
    url = url or settings.github_changelog_url
    html = fetch_changelog_html(url)
    return parse_github_entries(html, breaking_only=breaking_only), url


# ---------------------------------------------------------------------------
# Shopify Changelog Scraper
# ---------------------------------------------------------------------------
# Shopify's changelog at shopify.dev/changelog uses a blog-style layout.

SHOPIFY_SELECTORS: list[str] = [
    "article",
    "[class*=changelog]",
    "[class*=Changelog]",
    "div[class*=post]",
    "li[class*=post]",
    ".post-item",
]

SHOPIFY_BREAKING_KEYWORDS = re.compile(
    r"\b(deprecat|remov|renam|no longer|replaced|breaking|is now|will be removed|"
    r"sunset|discontinu|migrat|retired|end.of.life|eol|deprecated|removed)\w*",
    re.IGNORECASE,
)


def _make_shopify_entry(text: str) -> ParsedEntry | None:
    norm = _normalize(text)
    if len(norm) < 12:
        return None
    old, new = extract_old_new(norm)
    return ParsedEntry(
        description=norm[:2000],
        change_type=classify_change_type(norm),
        old_value=old,
        new_value=new,
        content_hash=_hash(norm),
        symbols=extract_symbols("shopify", norm),
    )


def parse_shopify_entries(html: str, breaking_only: bool = True, max_entries: int = 200) -> list[ParsedEntry]:
    soup = BeautifulSoup(html, "html.parser")
    seen_hashes: set[str] = set()
    entries: list[ParsedEntry] = []

    def consider(text: str) -> None:
        if not text:
            return
        if breaking_only and not SHOPIFY_BREAKING_KEYWORDS.search(text):
            return
        entry = _make_shopify_entry(text)
        if entry and entry.content_hash not in seen_hashes:
            seen_hashes.add(entry.content_hash)
            entries.append(entry)

    # 1) structured containers
    for selector in SHOPIFY_SELECTORS:
        for el in soup.select(selector):
            consider(el.get_text(" ", strip=True))
        if entries:
            break

    # 2) generic fallback
    if not entries:
        for el in soup.select("li, p, h2, h3, h4, article, .post-item, .changelog-entry"):
            consider(el.get_text(" ", strip=True))

    return entries[:max_entries]


def scrape_shopify(url: str | None = None, breaking_only: bool = True) -> tuple[list[ParsedEntry], str]:
    url = url or settings.shopify_changelog_url
    html = fetch_changelog_html(url)
    return parse_shopify_entries(html, breaking_only=breaking_only), url


# ---------------------------------------------------------------------------
# Twilio Changelog Scraper
# ---------------------------------------------------------------------------
# Twilio's changelog at twilio.com/en-us/changelog uses a blog-style layout.

TWILIO_SELECTORS: list[str] = [
    "article",
    "[class*=changelog]",
    "[class*=Changelog]",
    "div[class*=post]",
    "li[class*=post]",
    ".post-item",
]

TWILIO_BREAKING_KEYWORDS = re.compile(
    r"\b(deprecat|remov|renam|no longer|replaced|breaking|is now|will be removed|"
    r"sunset|discontinu|migrat|retired|end.of.life|eol|deprecated|removed)\w*",
    re.IGNORECASE,
)


def _make_twilio_entry(text: str) -> ParsedEntry | None:
    norm = _normalize(text)
    if len(norm) < 12:
        return None
    old, new = extract_old_new(norm)
    return ParsedEntry(
        description=norm[:2000],
        change_type=classify_change_type(norm),
        old_value=old,
        new_value=new,
        content_hash=_hash(norm),
        symbols=extract_symbols("twilio", norm),
    )


def parse_twilio_entries(html: str, breaking_only: bool = True, max_entries: int = 200) -> list[ParsedEntry]:
    soup = BeautifulSoup(html, "html.parser")
    seen_hashes: set[str] = set()
    entries: list[ParsedEntry] = []

    def consider(text: str) -> None:
        if not text:
            return
        if breaking_only and not TWILIO_BREAKING_KEYWORDS.search(text):
            return
        entry = _make_twilio_entry(text)
        if entry and entry.content_hash not in seen_hashes:
            seen_hashes.add(entry.content_hash)
            entries.append(entry)

    # 1) structured containers
    for selector in TWILIO_SELECTORS:
        for el in soup.select(selector):
            consider(el.get_text(" ", strip=True))
        if entries:
            break

    # 2) generic fallback
    if not entries:
        for el in soup.select("li, p, h2, h3, h4, article, .post-item, .changelog-entry"):
            consider(el.get_text(" ", strip=True))

    return entries[:max_entries]


def scrape_twilio(url: str | None = None, breaking_only: bool = True) -> tuple[list[ParsedEntry], str]:
    url = url or settings.twilio_changelog_url
    html = fetch_changelog_html(url)
    return parse_twilio_entries(html, breaking_only=breaking_only), url
