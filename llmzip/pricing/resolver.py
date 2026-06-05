import logging
import time
from datetime import datetime

from llmzip.pricing.fallback import FALLBACK_PRICES
from llmzip.pricing.fetcher import fetch_prices

logger = logging.getLogger(__name__)

_cache: dict[str, dict[str, float]] = {}
_cache_timestamp: float = 0.0
_cache_ttl: int = 3600  # default, overridden by config at startup


def configure(cache_ttl: int) -> None:
    global _cache_ttl
    _cache_ttl = cache_ttl


def resolve_prices() -> dict[str, dict[str, float]]:
    global _cache, _cache_timestamp

    now = time.monotonic()
    if _cache and (now - _cache_timestamp) < _cache_ttl:
        return _cache

    fetched = fetch_prices()
    if fetched is not None:
        _cache = fetched
        _cache_timestamp = now
        logger.debug("Prices refreshed from LiteLLM")
        return _cache

    # fetch failed — merge fallback with a note
    today = datetime.utcnow().strftime("%Y-%m-%d")
    fallback_with_meta = dict(FALLBACK_PRICES)
    fallback_with_meta["_meta"] = {  # type: ignore[assignment]
        "note": f"Rates from llm-zip fallback as of {today} (LiteLLM unavailable)"
    }

    # don't update cache timestamp on fallback — retry next request
    return fallback_with_meta
