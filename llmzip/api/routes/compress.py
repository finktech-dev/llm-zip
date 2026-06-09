import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import APIRouter, Depends, HTTPException, Request

from llmzip.api.limiter import limiter, get_rpm_limit, get_rpd_limit
from llmzip.api.schemas import (
    BatchRequest,
    BatchResponse,
    BatchResultItem,
    CompressRequest,
    CompressResponse,
)
from llmzip.api.dependencies import get_config, get_lingua, get_scorer, get_warning
from llmzip.config.loader import AppConfig
from llmzip.core.protocols import Compressor, Scorer
from llmzip.core.savings_calculator import calculate_savings
from llmzip.core.token_counter import count_tokens

logger = logging.getLogger("llmzip.api.routes.compress")
router = APIRouter(prefix="/v1")


@router.post("/compress", response_model=CompressResponse, tags=["compression"])
@limiter.limit(get_rpm_limit)
@limiter.limit(get_rpd_limit)
def compress(
    req: CompressRequest,
    request: Request,
    config: AppConfig = Depends(get_config),
    lingua: Compressor = Depends(get_lingua),
    scorer: Scorer = Depends(get_scorer),
) -> CompressResponse:
    start = time.perf_counter()
    model = req.model or config.default_model

    original_tokens, accuracy = count_tokens(req.text, model)

    if original_tokens > config.max_tokens:
        logger.warning(
            "compress error",
            extra={
                "event": "compress_error",
                "error": "text_too_long",
                "tokens_in": original_tokens,
                "status_code": 413,
            },
        )
        raise HTTPException(
            status_code=413,
            detail=(
                f"Text has ~{original_tokens:,} tokens, which exceeds MAX_TOKENS "
                f"({config.max_tokens:,}). Consider splitting the text or "
                f"increasing MAX_TOKENS in your [server] config."
            ),
        )

    if original_tokens < config.min_tokens_to_compress:
        savings = calculate_savings(req.text, req.text, config.default_model)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "compress ok",
            extra={
                "event": "compress_ok",
                "tokens_in": original_tokens,
                "tokens_out": original_tokens,
                "ratio": 1.0,
                "model": model,
                "elapsed_ms": elapsed_ms,
                "skipped": True,
            },
        )
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
            warning=get_warning(None, accuracy, model),
        )

    result = lingua.compress(req.text, req.ratio, model)
    score = scorer.score(req.text, result.compressed_text)
    savings = calculate_savings(req.text, result.compressed_text, model)
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    logger.info(
        "compress ok",
        extra={
            "event": "compress_ok",
            "tokens_in": original_tokens,
            "tokens_out": result.compressed_tokens,
            "ratio": round(result.compression_ratio, 3),
            "model": model,
            "elapsed_ms": elapsed_ms,
            "skipped": False,
        },
    )

    warning = result.warning
    if accuracy != "exact":
        msg = f"Model '{model}' token count is estimated (±10%). Exact counting is supported for OpenAI models (gpt-*, o1, o3, o4)."
        warning = f"{warning}. {msg}" if warning else msg

    return CompressResponse(
        compressed=result.compressed_text,
        original_tokens=result.original_tokens,
        compressed_tokens=result.compressed_tokens,
        compression_ratio=round(result.compression_ratio, 3),
        preservation_score=score,
        estimated_savings=savings.estimated_savings,
        pricing_accuracy=accuracy,
        pricing_note=savings.pricing_note,
        skipped=False,
        warning=warning,
    )


@router.post("/compress/batch", response_model=BatchResponse, tags=["compression"])
@limiter.limit(get_rpm_limit)
@limiter.limit(get_rpd_limit)
def compress_batch(
    req: BatchRequest,
    request: Request,
    config: AppConfig = Depends(get_config),
    lingua: Compressor = Depends(get_lingua),
    scorer: Scorer = Depends(get_scorer),
) -> BatchResponse:
    if len(req.texts) > config.max_batch_size:
        raise HTTPException(
            status_code=400,
            detail=f"Batch size {len(req.texts)} exceeds MAX_BATCH_SIZE ({config.max_batch_size}).",
        )

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

        # Collect results in a dict to avoid pre-populating a list with "pending" values.
        # This approach is runtime-portable and avoids implicit reliance on CPython's GIL.
        item_results: dict[int, BatchResultItem] = {}
        for future in as_completed(futures):
            item_result = future.result()
            # Assignment by key is atomic in CPython due to the GIL.
            # If porting to a runtime without a GIL, a lock or thread-safe queue would be required.
            item_results[item_result.index] = item_result

    # Reconstruct the ordered list of results for the response
    results = [item_results[i] for i in range(len(req.texts))]

    succeeded = sum(1 for r in results if r.status == "ok")
    failed = sum(1 for r in results if r.status == "error")

    return BatchResponse(
        results=results,
        summary={"total": len(results), "succeeded": succeeded, "failed": failed},
    )
