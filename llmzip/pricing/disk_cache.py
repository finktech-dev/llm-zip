import json
import logging
import os
import time
from pathlib import Path

from llmzip.pricing.fallback import PriceEntry

logger = logging.getLogger(__name__)

_CACHE_FILENAME = "prices.json"


def _cache_dir() -> Path:
    base = os.environ.get("LLMZIP_CACHE_DIR")
    if base:
        return Path(base)
    return Path.home() / ".llmzip"


def _cache_path() -> Path:
    return _cache_dir() / _CACHE_FILENAME


def load(ttl: int) -> tuple[dict[str, PriceEntry], dict[str, str]] | None:
    path = _cache_path()
    try:
        if not path.exists():
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))
        fetched_at = float(raw.get("_disk_meta", {}).get("fetched_at", 0))
        if (time.time() - fetched_at) > ttl:
            logger.debug(
                "Disk price cache expired (age=%ds ttl=%ds)",
                int(time.time() - fetched_at),
                ttl,
            )
            return None
        prices: dict[str, PriceEntry] = raw.get("prices", {})
        meta: dict[str, str] = raw.get("meta", {})
        logger.debug("Loaded prices from disk cache: %s", path)
        return prices, meta
    except Exception as exc:
        logger.warning("Failed to read disk price cache: %s", exc)
        return None


def save(prices: dict[str, PriceEntry], meta: dict[str, str]) -> None:
    path = _cache_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "prices": prices,
            "meta": meta,
            "_disk_meta": {"fetched_at": time.time()},
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        logger.debug("Saved prices to disk cache: %s", path)
    except Exception as exc:
        logger.warning("Failed to write disk price cache: %s", exc)
