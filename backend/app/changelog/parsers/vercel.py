"""Vercel changelog fetcher.

Source: https://vercel.com/changelog (HTML scraping)
Vercel has a clean changelog page with product-specific entries.
"""
from __future__ import annotations

from ..base import BaseFetcher, ChangelogEvent


class VercelFetcher(BaseFetcher):
    provider_id = "vercel"
    changelog_url = "https://vercel.com/changelog"
    
    SELECTORS = [
        "article",
        "[class*=changelog]",
        "[class*=Changelog]",
        "div[class*=entry]",
        "li[class*=entry]",
        "h2",
        "h3",
    ]
    
    def fetch(self) -> list[ChangelogEvent]:
        return self.fetch_html(self.changelog_url, self.SELECTORS)
