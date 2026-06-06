import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from llmzip.api.dependencies import get_config, get_lingua, get_scorer
from llmzip.api.schemas import CompressResponse
from llmzip.config.loader import AppConfig
from llmzip.core.lingua_adapter import LinguaAdapter
from llmzip.core.savings_calculator import calculate_savings
from llmzip.core.semantic_scorer import SemanticScorer
from llmzip.core.token_counter import count_tokens

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1")


@router.post("/compress/file", response_model=CompressResponse, tags=["compression"])
async def compress_file(
    file: UploadFile,
    ratio: float = 0.5,
    model: str | None = None,
    config: AppConfig = Depends(get_config),
    lingua: LinguaAdapter = Depends(get_lingua),
    scorer: SemanticScorer = Depends(get_scorer),
) -> CompressResponse:
    model = model or config.default_model

    if not config.file_conversion_enabled:
        raise HTTPException(
            status_code=501,
            detail="File conversion is disabled. Set FILE_CONVERSION=true in .llmzip.config.",
        )

    if not (0.1 <= ratio <= 0.9):
        raise HTTPException(status_code=400, detail="ratio must be between 0.1 and 0.9")

    from llmzip.conversion.file_converter import SUPPORTED_EXTENSIONS, convert

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: '{suffix}'. Supported: {sorted(SUPPORTED_EXTENSIONS)}",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    tmp_path = Path(tempfile.mktemp(suffix=suffix))
    try:
        tmp_path.write_bytes(content)
        conversion = convert(tmp_path)
    except RuntimeError as exc:
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
        raise HTTPException(
            status_code=413,
            detail=f"Extracted text exceeds MAX_TOKENS ({config.max_tokens}). Got ~{original_tokens} tokens.",
        )

    if original_tokens < config.min_tokens_to_compress:
        savings = calculate_savings(text, text, config.default_model)
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
        warning=result.warning or conversion.warning,
    )
sion.warning,
    )
