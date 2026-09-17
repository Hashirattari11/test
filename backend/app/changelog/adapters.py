"""Provider adapters — generated from the registry, strict extraction only.

Every adapter class is a ProviderAdapter subclass with a fixed provider_id.
Adapters are configured per provider (official URL/feed/selectors) from
sources.PROVIDER_SOURCES; no provider has a generic fallback.

Source-kind → adapter:
  RSS            -> fetch_rss_strict(feed_url)
  GITHUB_RELEASES -> fetch_github_releases(api_url, owner_repo)
  HTML_STRICT    -> fetch_html_strict(changelog_url, selectors from registry)
  NONE           -> no adapter (scheduler marks SOURCE_UNAVAILABLE)
"""
from __future__ import annotations

from .base import ProviderAdapter, RawEntry, FetchError
from .sources import (PROVIDER_SOURCES_BY_ID, ProviderSource, RSS,
                      GITHUB_RELEASES, HTML_STRICT, NONE)


def _selectors_for(source: ProviderSource) -> list[str]:
    """Concrete selectors for HTML_STRICT providers (registry hint + guards)."""
    base = (source.entry_selector or "").split(",")
    base = [s.strip() for s in base if s.strip()]
    # Guard selectors guarantee we never accept undated page chrome: every
    # candidate must still pass the date+link+title checks in the base class.
    guards = ["article", "section[class*=changelog]", "div[class*=changelog]",
              "[class*=release-note]", "[class*=changelog-item]", "li[class*=entry]"]
    selectors: list[str] = []
    for s in base + guards:
        if s not in selectors:
            selectors.append(s)
    return selectors


class AdapterFactory:
    """Builds a concrete adapter class per provider from the registry."""

    _cache: dict[str, type[ProviderAdapter]] = {}

    @classmethod
    def _make(cls, provider_id: str) -> type[ProviderAdapter]:
        source = PROVIDER_SOURCES_BY_ID.get(provider_id)
        if source is None:
            raise KeyError(f"unknown provider: {provider_id}")

        if source.source_kind == NONE:
            def _fetch_none(self) -> list[RawEntry]:  # noqa: N807
                raise FetchError(f"{provider_id}: no official machine-readable source")
            return type(f"{provider_id.title()}Adapter", (ProviderAdapter,),
                        {"provider_id": provider_id, "fetch": _fetch_none})

        if source.source_kind == RSS:
            def _fetch_rss(self) -> list[RawEntry]:
                if not self.source.feed_url:
                    raise FetchError(f"{self.provider_id}: RSS feed not configured")
                return self.fetch_rss_strict(self.source.feed_url)
            return type(f"{provider_id.title()}Adapter", (ProviderAdapter,),
                        {"provider_id": provider_id, "fetch": _fetch_rss})

        if source.source_kind == GITHUB_RELEASES:
            def _fetch_releases(self) -> list[RawEntry]:
                if not self.source.feed_url:
                    raise FetchError(f"{self.provider_id}: releases API not configured")
                owner_repo = self.source.feed_url.rstrip("/").split("/repos/")[-1]
                return self.fetch_github_releases(self.source.feed_url, owner_repo)
            return type(f"{provider_id.title()}Adapter", (ProviderAdapter,),
                        {"provider_id": provider_id, "fetch": _fetch_releases})

        if source.source_kind == HTML_STRICT:
            def _fetch_html(self) -> list[RawEntry]:
                return self.fetch_html_strict(
                    self.source.changelog_url,
                    _selectors_for(self.source),
                )
            return type(f"{provider_id.title()}Adapter", (ProviderAdapter,),
                        {"provider_id": provider_id, "fetch": _fetch_html})

        raise KeyError(f"{provider_id}: unsupported source kind {source.source_kind}")

    @classmethod
    def for_provider(cls, provider_id: str) -> type[ProviderAdapter]:
        if provider_id not in cls._cache:
            cls._cache[provider_id] = cls._make(provider_id)
        return cls._cache[provider_id]

    @classmethod
    def all(cls, provider_ids: list[str]) -> dict[str, type[ProviderAdapter]]:
        return {pid: cls.for_provider(pid) for pid in provider_ids}