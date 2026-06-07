import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import APIRouter, Depends, HTTPException

from llmzip.api.schemas import (
    BatchRequest,
    BatchResponse,
    BatchResultItem,
    CompressRequest,
    CompressResponse,
)
from llmzip.api.dependencies import get_lingua, get_scorer, get_config
from llmzip.config.loader import AppConfig
from llmzip.core.lingua_adapter import LinguaAdapter
from llmzip.core.savings_calculator import calculate_savings
from llmzip.core.semantic_scorer import SemanticScorer
from llmzip.core.token_counter import count_tokens

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1")


@router.post("/compress", response_model=CompressResponse, tags=["compression"])
def compress(
    req: CompressRequest,
    config: AppConfig = Depends(get_config),
    lingua: LinguaAdapter = Depends(get_lingua),
    scorer: SemanticScorer = Depends(get_scorer),
) -> CompressResponse:
    model = req.model or config.default_model

    original_tokens, accuracy = count_tokens(req.text, model)

    if original_tokens > config.max_tokens:
        raise HTTPException(
            status_code=413,
            detail=f"Text exceeds MAX_TOKENS ({config.max_tokens}). Got ~{original_tokens} tokens.",
        )

    if original_tokens < config.min_tokens_to_compress:
        savings = calculate_savings(req.text, req.text, config.default_model)
        return CompressResponse(
            compressed=req.text,
            original_tokens=original_tokens,
            compressed_tokens=original_tokens,
            compression_ratio=1.0,
            preservation_score=1.0,
            estimated_savings=savings.estimated_savings,
            pricing_accuracy=accuracy,
            pricing_note=savings.pricing_note,
            skipped=True,
            warning=None,
        )

    result = lingua.compress(req.text, req.ratio, model)
    score = scorer.score(req.text, result.compressed_text)
    savings = calculate_savings(req.text, result.compressed_text, model)

    return CompressResponse(
        compressed=result.compressed_text,
        original_tokens=result.original_tokens,
        compressed_tokens=result.compressed_tokens,
        compression_ratio=result.compression_ratio,
        preservation_score=score,
        estimated_savings=savings.estimated_savings,
        pricing_accuracy=accuracy,
        pricing_note=savings.pricing_note,
        skipped=False,
        warning=result.warning,
    )


@router.post("/compress/batch", response_model=BatchResponse, tags=["compression"])
def compress_batch(
    req: BatchRequest,
    config: AppConfig = Depends(get_config),
    lingua: LinguaAdapter = Depends(get_lingua),
    scorer: SemanticScorer = Depends(get_scorer),
) -> BatchResponse:
    if len(req.texts) > config.max_batch_size:
        raise HTTPException(
            status_code=400,
            detail=f"Batch size {len(req.texts)} exceeds MAX_BATCH_SIZE ({config.max_batch_size}).",
        )

    results: list[BatchResultItem] = [
        BatchResultItem(index=i, status="pending") for i in range(len(req.texts))
    ]

    def _process(index: int, item) -> BatchResultItem:
        try:
            model = item.model or config.default_model
            original_tokens, accuracy = count_tokens(item.text, model)

            if original_tokens > config.max_tokens:
                return BatchResultItem(
                    index=index, status="error", reason="above_max_tokens"
                )

            if original_tokens < config.min_tokens_to_compress:
                savings = calculate_savings(item.text, item.text, config.default_model)
                return BatchResultItem(
                    index=index,
                    status="ok",
                    compressed=item.text,
                    compression_ratio=1.0,
                    preservation_score=1.0,
                    estimated_savings=savings.estimated_savings,
                    reason="skipped_below_threshold",
                )

            compression = lingua.compress(item.text, item.ratio, model)
            score = scorer.score(item.text, compression.compressed_text)
            savings = calculate_savings(item.text, compression.compressed_text, model)

            return BatchResultItem(
                index=index,
                status="ok",
                compressed=compression.compressed_text,
                compression_ratio=compression.compression_ratio,
                preservation_score=score,
                estimated_savings=savings.estimated_savings,
            )
        except Exception as exc:
            logger.warning("Batch item %d failed: %s", index, exc)
            return BatchResultItem(index=index, status="error", reason=str(exc))

    with ThreadPoolExecutor(max_workers=config.batch_workers) as executor:
        futures = {
            executor.submit(_process, i, item): i
            for i, item in enumerate(req.texts)
        }
        for future in as_completed(futures):
            item_result = future.result()
            results[item_result.index] = item_result

    succeeded = sum(1 for r in results if r.status == "ok")
    failed = sum(1 for r in results if r.status == "error")

    return BatchResponse(
        results=results,
        summary={"total": len(results), "succeeded": succeeded, "failed": failed},
    )
