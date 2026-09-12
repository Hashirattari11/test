"""Twilio changelog fetcher.

Source: https://www.twilio.com/en-us/changelog (HTML scraping)
"""
from __future__ import annotations

from ..base import BaseFetcher, ChangelogEvent


class TwilioFetcher(BaseFetcher):
    provider_id = "twilio"
    changelog_url = "https://www.twilio.com/en-us/changelog"
    
    SELECTORS = [
        "article",
        "[class*=changelog]",
        "div[class*=post]",
        "li[class*=entry]",
        "h2",
        "h3",
    ]
    
    def fetch(self) -> list[ChangelogEvent]:
        return self.fetch_html(self.changelog_url, self.SELECTORS)
