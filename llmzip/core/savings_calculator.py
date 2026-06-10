from dataclasses import dataclass

from llmzip.core.featured_models import FEATURED_MODELS
from llmzip.core.token_counter import count_tokens
from llmzip.pricing.resolver import resolve_prices


@dataclass
class SavingsResult:
    estimated_savings: dict[str, str]
    pricing_accuracy: str
    pricing_note: str


def calculate_savings(
    original_text: str,
    compressed_text: str | None,
    default_model: str,
    simulated_ratio: float | None = None,
) -> SavingsResult:
    prices = resolve_prices()
    models_to_show = _build_model_list(default_model)

    savings: dict[str, str] = {}
    accuracy = "exact"
    
    original_cache: dict[str, int] = {}
    compressed_cache: dict[str, int] = {}

    for model in models_to_show:
        price_entry = prices.get(model)
        if price_entry is None:
            continue

        original_tokens, model_accuracy = count_tokens(original_text, model, cache=original_cache)
        
        if simulated_ratio is not None:
            compressed_tokens = max(1, int(original_tokens * simulated_ratio))
        else:
            compressed_tokens, _ = count_tokens(compressed_text or "", model, cache=compressed_cache)
            
            
        tokens_saved = max(0, original_tokens - compressed_tokens)

        # input token price per million → per token
        price_per_token = float(price_entry["input"]) / 1_000_000
        saved_usd = tokens_saved * price_per_token

        savings[model] = f"${saved_usd:.6f}"

        if model_accuracy != "exact":
            accuracy = "estimated±10%"

    return SavingsResult(
        estimated_savings=savings,
        pricing_accuracy=accuracy,
        pricing_note=str(prices.get("_meta", {}).get("note", "")),
    )


def _build_model_list(default_model: str) -> list[str]:
    models = list(FEATURED_MODELS)
    if default_model not in models:
        models.insert(0, default_model)
    return models
