"""Provider adapter registry — ALL 44 providers (strict official sources).

FETCHERS maps provider_id -> ProviderAdapter class built from
changelog/sources.py via the AdapterFactory. There is no generic fallback:
each provider's adapter uses only its own official source.
"""
from __future__ import annotations

from ..adapters import AdapterFactory
from ..sources import ALL_PROVIDER_IDS

FETCHERS: dict[str, type] = AdapterFactory.all(list(ALL_PROVIDER_IDS))

__all__ = ["FETCHERS"]