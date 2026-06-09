import logging
import time
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, Request

from llmzip.api.limiter import limiter, get_rpm_limit, get_rpd_limit
from llmzip.api.dependencies import get_config, get_lingua, get_scorer
from llmzip.api.schemas import CompressResponse
from llmzip.config.loader import AppConfig
from llmzip.core.protocols import Compressor, Scorer
from llmzip.core.savings_calculator import calculate_savings
from llmzip.core.token_counter import count_tokens

logger = logging.getLogger("llmzip.api.routes.compress_file")
router = APIRouter(prefix="/v1")


@router.post("/compress/file", response_model=CompressResponse, tags=["compression"])
@limiter.limit(get_rpm_limit)
@limiter.limit(get_rpd_limit)
async def compress_file(
    file: UploadFile,
    request: Request,
    ratio: float = 0.5,
    model: str | None = None,
    config: AppConfig = Depends(get_config),
    lingua: Compressor = Depends(get_lingua),
    scorer: Scorer = Depends(get_scorer),
) -> CompressResponse:
    start = time.perf_counter()
    model = model or config.default_model

    if not config.file_conversion_enabled:
        raise HTTPException(
            status_code=501,
            detail="File conversion is disabled. Set FILE_CONVERSION=true in .llmzip.config.",
        )

    if not (0.1 <= ratio <= 0.9):
        raise HTTPException(status_code=400, detail="ratio must be between 0.1 and 0.9")

    # Lazy import: avoids loading markitdown at startup when FILE_CONVERSION is disabled.
    from llmzip.conversion.file_converter import SUPPORTED_EXTENSIONS, convert

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: '{suffix}'. Supported: {sorted(SUPPORTED_EXTENSIONS)}",
        )

    # Check Content-Length header first
    content_length = request.headers.get("content-length")
    if content_length:
        size_mb = int(content_length) / (1024 * 1024)
        if size_mb > config.max_file_size_mb:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"File exceeds MAX_FILE_SIZE_MB ({config.max_file_size_mb}MB). "
                    f"Got ~{size_mb:.1f}MB. "
                    f"Increase MAX_FILE_SIZE_MB in [server] config to allow larger files."
                ),
            )

    # Read with size check (streaming fallback)
    MAX_BYTES = config.max_file_size_mb * 1024 * 1024
    content = await file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"File exceeds MAX_FILE_SIZE_MB ({config.max_file_size_mb}MB). "
                f"Increase MAX_FILE_SIZE_MB in [server] config to allow larger files."
            ),
        )

    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.close()
    tmp_path = Path(tmp.name)
    try:
        tmp_path.write_bytes(content)
        conversion = convert(tmp_path)
    except RuntimeError as exc:
        logger.warning(
            "compress error",
            extra={
                "event": "compress_error",
                "error": "conversion_failed",
                "status_code": 422,
            },
        )
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    if not conversion.text or len(conversion.text.strip()) < 10:
        raise HTTPException(
            status_code=422,
            detail="File conversion produced no extractable text.",
        )

    text = conversion.text
    original_tokens, accuracy = count_tokens(text, model)

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
                f"Extracted text has ~{original_tokens:,} tokens, which exceeds MAX_TOKENS "
                f"({config.max_tokens:,}). Consider splitting the text or "
                f"increasing MAX_TOKENS in your [server] config."
            ),
        )

    if original_tokens < config.min_tokens_to_compress:
        savings = calculate_savings(text, text, config.default_model)
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
            compressed=text,
            original_tokens=original_tokens,
            compressed_tokens=original_tokens,
            compression_ratio=1.0,
            preservation_score=1.0,
            estimated_savings=savings.estimated_savings,
            pricing_accuracy=accuracy,
            pricing_note=savings.pricing_note,
            skipped=True,
            warning=conversion.warning,
        )

    result = lingua.compress(text, ratio, model)
    score = scorer.score(text, result.compressed_text)
    savings = calculate_savings(text, result.compressed_text, model)
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

    warning = result.warning or conversion.warning
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

