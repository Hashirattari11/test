"""Shopify changelog fetcher.

Source: https://shopify.dev/changelog (HTML scraping)
Shopify's changelog is well-structured with API versioning info.
"""
from __future__ import annotations

from ..base import BaseFetcher, ChangelogEvent


class ShopifyFetcher(BaseFetcher):
    provider_id = "shopify"
    changelog_url = "https://shopify.dev/changelog"
    
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
