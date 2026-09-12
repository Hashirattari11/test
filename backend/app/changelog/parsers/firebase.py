"""Firebase changelog fetcher.

Source: https://firebase.google.com/support/releases (HTML scraping)
Firebase has release notes for each product.
"""
from __future__ import annotations

from ..base import BaseFetcher, ChangelogEvent


class FirebaseFetcher(BaseFetcher):
    provider_id = "firebase"
    changelog_url = "https://firebase.google.com/support/releases"
    
    SELECTORS = [
        "article",
        "[class*=release]",
        "[class*=changelog]",
        "div[class*=entry]",
        "li[class*=entry]",
        "h2",
        "h3",
    ]
    
    def fetch(self) -> list[ChangelogEvent]:
        return self.fetch_html(self.changelog_url, self.SELECTORS)
