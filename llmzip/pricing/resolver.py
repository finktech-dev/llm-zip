import logging
import threading
import time
from datetime import datetime

from llmzip.pricing.fallback import FALLBACK_PRICES
from llmzip.pricing.fetcher import fetch_prices

logger = logging.getLogger(__name__)

_cache: dict[str, dict[str, float]] = {}
_cache_timestamp: float = 0.0
_cache_ttl: int = 3600

_last_fetch_attempt: float = 0.0
_FETCH_COOLDOWN: float = 30.0  # seconds between retries if LiteLLM is down
_fetch_lock = threading.Lock()


def configure(cache_ttl: int) -> None:
    global _cache_ttl
    _cache_ttl = cache_ttl


def resolve_prices() -> dict[str, dict[str, float]]:
    global _cache, _cache_timestamp, _last_fetch_attempt

    now = time.monotonic()

    # valid cache — return directly
    if _cache and (now - _cache_timestamp) < _cache_ttl:
        return _cache

    # cooldown active — don't retry yet, return stale cache or fallback
    if (now - _last_fetch_attempt) < _FETCH_COOLDOWN:
        if _cache:
            return _cache
        return _make_fallback()

    with _fetch_lock:
        # double-check if another thread updated it while waiting for lock
        now = time.monotonic()
        if _cache and (now - _cache_timestamp) < _cache_ttl:
            return _cache
        
        # also re-check cooldown
        if (now - _last_fetch_attempt) < _FETCH_COOLDOWN:
            if _cache:
                return _cache
            return _make_fallback()

        _last_fetch_attempt = now
        fetched = fetch_prices()

        if fetched is not None:
            _cache = fetched
            _cache_timestamp = now
            logger.debug("Prices refreshed from LiteLLM")
            return _cache

    # fetch failed — use stale cache if available, else fallback
    if _cache:
        logger.warning("LiteLLM unavailable — serving stale cache")
        return _cache

    return _make_fallback()


def _make_fallback() -> dict[str, dict[str, float]]:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    fallback_with_meta = dict(FALLBACK_PRICES)
    fallback_with_meta["_meta"] = {  # type: ignore[assignment]
        "note": f"Rates from llm-zip fallback as of {today} (LiteLLM unavailable)",
        "source": "fallback",
    }
    return fallback_with_meta
