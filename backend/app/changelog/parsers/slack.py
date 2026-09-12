"""Slack changelog fetcher.

Source: https://api.slack.com/changelog (HTML scraping)
Slack has a well-structured changelog with API versioning.
"""
from __future__ import annotations

from ..base import BaseFetcher, ChangelogEvent


class SlackFetcher(BaseFetcher):
    provider_id = "slack"
    changelog_url = "https://api.slack.com/changelog"
    
    SELECTORS = [
        "article",
        "[class*=changelog]",
        "[class*=Changelog]",
        "div[class*=entry]",
        "section[class*=entry]",
        "h2",
        "h3",
    ]
    
    def fetch(self) -> list[ChangelogEvent]:
        return self.fetch_html(self.changelog_url, self.SELECTORS)
