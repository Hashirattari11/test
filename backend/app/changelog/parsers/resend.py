"""Resend changelog fetcher.

Source: https://resend.com/changelog (HTML scraping)
Resend has a clean changelog page.
"""
from __future__ import annotations

from ..base import BaseFetcher, ChangelogEvent


class ResendFetcher(BaseFetcher):
    provider_id = "resend"
    changelog_url = "https://resend.com/changelog"
    
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
