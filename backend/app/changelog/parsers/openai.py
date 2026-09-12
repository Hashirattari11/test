"""OpenAI changelog fetcher.

Source: https://platform.openai.com/docs/changelog (HTML scraping)
OpenAI has a structured changelog with versioned API changes.
"""
from __future__ import annotations

from ..base import BaseFetcher, ChangelogEvent


class OpenAIFetcher(BaseFetcher):
    provider_id = "openai"
    changelog_url = "https://platform.openai.com/docs/changelog"
    
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
