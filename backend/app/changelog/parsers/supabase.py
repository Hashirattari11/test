"""Supabase changelog fetcher.

Source: https://supabase.com/changelog (HTML scraping)
Supabase has a clean changelog with product-specific entries.
"""
from __future__ import annotations

from ..base import BaseFetcher, ChangelogEvent


class SupabaseFetcher(BaseFetcher):
    provider_id = "supabase"
    changelog_url = "https://supabase.com/changelog"
    
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
