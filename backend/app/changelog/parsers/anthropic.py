"""Anthropic changelog fetcher.

Source: https://docs.anthropic.com/en/docs/about-claude/changelog (HTML scraping)
"""
from __future__ import annotations

from ..base import BaseFetcher, ChangelogEvent


class AnthropicFetcher(BaseFetcher):
    provider_id = "anthropic"
    changelog_url = "https://docs.anthropic.com/en/docs/about-claude/changelog"
    
    SELECTORS = [
        "article",
        "[class*=changelog]",
        "div[class*=entry]",
        "section[class*=entry]",
        "h2",
        "h3",
    ]
    
    def fetch(self) -> list[ChangelogEvent]:
        return self.fetch_html(self.changelog_url, self.SELECTORS)
