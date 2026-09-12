"""GitHub changelog fetcher.

Source: GitHub Releases API (JSON) - most reliable for API changes
Also scrapes https://github.blog/changelog/ as fallback.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from ..base import BaseFetcher, ChangelogEvent, normalize_text, compute_content_hash, classify_event_type, score_severity, extract_symbols


class GitHubFetcher(BaseFetcher):
    provider_id = "github"
    changelog_url = "https://github.blog/changelog/"
    api_releases_url = "https://api.github.com/repos/github/rest-api-description/releases"
    
    def fetch(self) -> list[ChangelogEvent]:
        events = []
        
        # Try GitHub Releases API first (most reliable for API changes)
        try:
            events.extend(self._fetch_releases())
        except Exception:
            pass
        
        # Fallback to HTML scraping
        if not events:
            try:
                events.extend(self.fetch_html(self.changelog_url, [
                    "article",
                    "[class*=changelog]",
                    "div[class*=post]",
                    "li[class*=post]",
                    ".post-item",
                ]))
            except Exception:
                pass
        
        return events
    
    def _fetch_releases(self) -> list[ChangelogEvent]:
        """Fetch from GitHub REST API releases."""
        resp = self.session.get(self.api_releases_url, timeout=30)
        resp.raise_for_status()
        
        releases = resp.json()[:20]  # Last 20 releases
        events = []
        
        for release in releases:
            name = release.get("name", "")
            body = release.get("body", "")
            html_url = release.get("html_url", "")
            published = release.get("published_at", "")
            
            if not name and not body:
                continue
            
            text = f"{name} {body}"
            event_type = classify_event_type(text)
            severity = score_severity(text, event_type)
            symbols = extract_symbols(text)
            
            event = ChangelogEvent(
                provider=self.provider_id,
                title=name[:500],
                source_url=html_url,
                published_date=published or datetime.now(timezone.utc).isoformat(),
                raw_summary=normalize_text(body)[:2000],
                event_type=event_type,
                severity=severity,
                content_hash=compute_content_hash(f"github:{name}:{body}"),
                symbols=symbols,
            )
            events.append(event)
        
        return events
