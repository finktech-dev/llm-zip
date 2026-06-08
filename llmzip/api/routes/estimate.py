import logging
from fastapi import APIRouter, Depends, HTTPException

from llmzip.api.schemas import EstimateRequest, EstimateResponse
from llmzip.api.dependencies import get_config
from llmzip.config.loader import AppConfig
from llmzip.core.savings_calculator import calculate_savings
from llmzip.core.token_counter import count_tokens

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

    savings = calculate_savings(
        original_text=req.text,
        compressed_text=None,
        default_model=model,
        simulated_ratio=req.ratio
    )

    return EstimateResponse(
        original_tokens=original_tokens,
        estimated_compressed_tokens=estimated_compressed_tokens,
        estimated_compression_ratio=estimated_compression_ratio,
        estimated_savings=savings.estimated_savings,
        pricing_accuracy=savings.pricing_accuracy,
        pricing_note=savings.pricing_note,
        would_compress=would_compress,
        warning=None,
    )
