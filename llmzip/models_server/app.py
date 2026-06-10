import logging
import os
import threading
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from llmzip.core.lingua_adapter import LinguaAdapter
from llmzip.core.semantic_scorer import SemanticScorer

logger = logging.getLogger(__name__)

class CompressRequest(BaseModel):
    text: str
    ratio: float
    target_model: str

class ScoreRequest(BaseModel):
    original: str
    compressed: str

class HealthResponse(BaseModel):
    status: str

class ReadyResponse(BaseModel):
    status: str
    models_loaded: bool

_READY_MARKER = Path(os.environ.get("MODELS_DIR", "models")) / ".ready"
_models_loaded_event = threading.Event()

def set_models_loaded(value: bool) -> None:
    if value:
        _models_loaded_event.set()
        _READY_MARKER.touch()
    else:
        _models_loaded_event.clear()
        _READY_MARKER.unlink(missing_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Use environment variables directly to avoid dependency on .llmzip.config
    models_dir = Path(os.environ.get("MODELS_DIR", "models"))
    model_name = os.environ.get("COMPRESSION_MODEL", "bert-base")
    chunk_size = int(os.environ.get("CHUNK_SIZE", "400"))
    scorer_model = os.environ.get("SCORER_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
    scorer_timeout = int(os.environ.get("SCORER_TIMEOUT", "30"))
    
    # Initialize and load models
    lingua = LinguaAdapter(
        model_name=model_name,
        models_dir=models_dir,
        chunk_size=chunk_size,
    )
    lingua.load()
    app.state.lingua = lingua

    scorer = SemanticScorer(
        models_dir=models_dir,
        model_id=scorer_model,
        timeout=scorer_timeout,
    )
    scorer.load()
    app.state.scorer = scorer

    set_models_loaded(True)
    logger.info("llmzip-models ready (model: %s, scorer: %s)", model_name, scorer_model)

    yield

    set_models_loaded(False)
    logger.info("llmzip-models shutting down")

app = FastAPI(title="llmzip-models", lifespan=lifespan)

@app.get("/health", response_model=HealthResponse)
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/ready", response_model=ReadyResponse)
def ready() -> dict[str, str | bool]:
    loaded = _models_loaded_event.is_set() and _READY_MARKER.exists()
    return {"status": "ok" if loaded else "loading", "models_loaded": loaded}

@app.post("/infer/compress")
def infer_compress(req: CompressRequest) -> dict[str, str | int | float | None]:
    lingua: LinguaAdapter = app.state.lingua
    try:
        result = lingua.compress(req.text, req.ratio, req.target_model)
        return {
            "compressed_text": result.compressed_text,
            "original_tokens": result.original_tokens,
            "compressed_tokens": result.compressed_tokens,
            "compression_ratio": result.compression_ratio,
            "warning": result.warning
        }
    except Exception as e:
        logger.error(f"Inference error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.post("/infer/score")
def infer_score(req: ScoreRequest) -> dict[str, float | None]:
    scorer: SemanticScorer = app.state.scorer
    try:
        score = scorer.score(req.original, req.compressed)
        return {"score": score}
    except Exception as e:
        logger.error(f"Scoring error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
