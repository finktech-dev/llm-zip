import logging
import threading
import time

from llmzip.pricing.disk_cache import load as disk_load
from llmzip.pricing.disk_cache import save as disk_save
from llmzip.pricing.fallback import FALLBACK_META, FALLBACK_PRICES, PriceEntry
from llmzip.pricing.fetcher import fetch_prices

logger = logging.getLogger(__name__)

_cache_prices: dict[str, PriceEntry] = {}
_cache_meta: dict[str, str] = {}
_cache_timestamp: float = 0.0
_cache_ttl: int = 3600

_last_fetch_attempt: float = 0.0
_FETCH_COOLDOWN: float = 30.0
_fetch_lock = threading.Lock()


def configure(cache_ttl: int) -> None:
    global _cache_ttl
    _cache_ttl = cache_ttl


def resolve_prices() -> tuple[dict[str, PriceEntry], dict[str, str]]:
    global _cache_prices, _cache_meta, _cache_timestamp, _last_fetch_attempt

    now = time.monotonic()

    if _cache_prices and (now - _cache_timestamp) < _cache_ttl:
        return _cache_prices, _cache_meta

    if (now - _last_fetch_attempt) < _FETCH_COOLDOWN:
        return (_cache_prices, _cache_meta) if _cache_prices else (FALLBACK_PRICES, FALLBACK_META)

    with _fetch_lock:
        now = time.monotonic()
        if _cache_prices and (now - _cache_timestamp) < _cache_ttl:
            return _cache_prices, _cache_meta
        if (now - _last_fetch_attempt) < _FETCH_COOLDOWN:
            return (_cache_prices, _cache_meta) if _cache_prices else (FALLBACK_PRICES, FALLBACK_META)
        _last_fetch_attempt = now

    disk = disk_load(_cache_ttl)
    if disk is not None:
        prices, meta = disk
        with _fetch_lock:
            _cache_prices = prices
            _cache_meta = meta
            _cache_timestamp = time.monotonic()
        logger.debug("Prices loaded from disk cache")
        return _cache_prices, _cache_meta

    fetched = fetch_prices()
    if fetched is not None:
        prices, meta = fetched
        disk_save(prices, meta)
        with _fetch_lock:
            _cache_prices = prices
            _cache_meta = meta
            _cache_timestamp = time.monotonic()
        logger.debug("Prices refreshed from LiteLLM and written to disk")
        return _cache_prices, _cache_meta

    if _cache_prices:
        logger.warning("LiteLLM unavailable — serving stale RAM cache")
        return _cache_prices, _cache_meta

    stale = disk_load(ttl=86400 * 7)
    if stale is not None:
        logger.warning("LiteLLM unavailable — serving stale disk cache")
        return stale

    return FALLBACK_PRICES, FALLBACK_META
