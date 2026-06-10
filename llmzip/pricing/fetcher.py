import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

LITELLM_PRICES_URL = (
    "https://raw.githubusercontent.com/BerriAI/litellm/main/"
    "model_prices_and_context_window.json"
)
_TIMEOUT_SECONDS = 5.0


def fetch_prices() -> dict[str, dict[str, float | str]] | None:
    """
    Fetches current model prices from LiteLLM's public JSON.
    Returns a normalized dict {model_name: {input: float, output: float}}
    or None if the fetch fails.
    """
    try:
        response = httpx.get(LITELLM_PRICES_URL, timeout=_TIMEOUT_SECONDS)
        response.raise_for_status()
        raw = response.json()
        return _normalize(raw)
    except Exception as exc:
        logger.warning("LiteLLM price fetch failed: %s — using fallback", exc)
        return None


def _normalize(raw: dict[str, object]) -> dict[str, dict[str, float | str]]:
    prices: dict[str, dict[str, float | str]] = {}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for model, data in raw.items():
        if not isinstance(data, dict):
            continue
        input_price = data.get("input_cost_per_token")
        output_price = data.get("output_cost_per_token")
        if input_price is None or output_price is None:
            continue
        # LiteLLM stores per-token; convert to per-million
        prices[model] = {
            "input": float(input_price) * 1_000_000,
            "output": float(output_price) * 1_000_000,
        }

    prices["_meta"] = {
        "note": f"Rates from LiteLLM as of {today}",
        "source": "litellm",
    }
    return prices
