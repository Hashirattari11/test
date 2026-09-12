"""SendGrid changelog fetcher.

Source: https://docs.sendgrid.com/for-developers/changelog (HTML scraping)
"""
from __future__ import annotations

from ..base import BaseFetcher, ChangelogEvent


class SendGridFetcher(BaseFetcher):
    provider_id = "sendgrid"
    changelog_url = "https://docs.sendgrid.com/for-developers/changelog"
    
    SELECTORS = [
        "article",
        "[class*=changelog]",
        "section[class*=post]",
        "div[class*=post]",
        "li[class*=entry]",
        "h2",
        "h3",
    ]
    
    def fetch(self) -> list[ChangelogEvent]:
        return self.fetch_html(self.changelog_url, self.SELECTORS)
