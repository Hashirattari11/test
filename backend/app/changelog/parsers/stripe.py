"""Stripe changelog fetcher.

Source: https://docs.stripe.com/changelog (HTML scraping with structured selectors)
Stripe has a well-structured changelog page with versioned entries.
"""
from __future__ import annotations

from ..base import BaseFetcher, ChangelogEvent


class StripeFetcher(BaseFetcher):
    provider_id = "stripe"
    changelog_url = "https://docs.stripe.com/changelog"
    
    SELECTORS = [
        "article",
        "[class*=changelog]",
        "[class*=Changelog]",
        "section[class*=entry]",
        "h3",
        "h4",
    ]
    
    def fetch(self) -> list[ChangelogEvent]:
        return self.fetch_html(self.changelog_url, self.SELECTORS)
