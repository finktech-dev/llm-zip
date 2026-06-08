import logging
from fastapi import APIRouter, Depends, HTTPException

from llmzip.api.schemas import EstimateRequest, EstimateResponse
from llmzip.api.dependencies import get_config
from llmzip.config.loader import AppConfig
from llmzip.core.token_counter import count_tokens
from llmzip.pricing.resolver import resolve_prices
from llmzip.core.featured_models import FEATURED_MODELS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1")


@router.post("/estimate", response_model=EstimateResponse, tags=["compression"])
def estimate(
    req: EstimateRequest,
    config: AppConfig = Depends(get_config),
) -> EstimateResponse:
    model = req.model or config.default_model

    original_tokens, accuracy = count_tokens(req.text, model)

    if original_tokens > config.max_tokens:
        raise HTTPException(
            status_code=413,
            detail=f"Text exceeds MAX_TOKENS ({config.max_tokens}). Got ~{original_tokens} tokens.",
        )

    estimated_compressed_tokens = max(1, int(original_tokens * req.ratio))
    estimated_compression_ratio = round(1.0 / req.ratio, 2)
    would_compress = original_tokens >= config.min_tokens_to_compress

    prices = resolve_prices()
    
    # Logic similar to calculate_savings but with pre-calculated tokens
    savings: dict[str, str] = {}
    models_to_show = list(FEATURED_MODELS)
    if model not in models_to_show:
        models_to_show.insert(0, model)

    for m in models_to_show:
        price_entry = prices.get(m)
        if price_entry is None:
            continue

        m_orig, m_acc = count_tokens(req.text, m)
        m_comp = max(1, int(m_orig * req.ratio))
        tokens_saved = max(0, m_orig - m_comp)

        price_per_token = price_entry["input"] / 1_000_000
        saved_usd = tokens_saved * price_per_token

        savings[m] = f"${saved_usd:.6f}"
        if m_acc != "exact":
            accuracy = "estimated±10%"

    return EstimateResponse(
        original_tokens=original_tokens,
        estimated_compressed_tokens=estimated_compressed_tokens,
        estimated_compression_ratio=estimated_compression_ratio,
        estimated_savings=savings,
        pricing_accuracy=accuracy,
        pricing_note=prices.get("_meta", {}).get("note", ""),
        would_compress=would_compress,
        warning=None,
    )
