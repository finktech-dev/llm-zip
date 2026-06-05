import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI


class _HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "GET /health" not in record.getMessage() and "GET /ready" not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(_HealthCheckFilter())

from llmzip.api.routes import compress, compress_file, health, models
from llmzip.api.routes.health import set_models_loaded
from llmzip.config.loader import AppConfig, load
from llmzip.core.lingua_adapter import LinguaAdapter
from llmzip.core.semantic_scorer import SemanticScorer
from llmzip.pricing.resolver import configure as configure_pricing

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    config: AppConfig = load()
    app.state.config = config

    configure_pricing(config.pricing_cache_ttl)

    models_dir = Path(app.state.__dict__.get("models_dir", "models"))

    lingua = LinguaAdapter(
        model_name=config.compression_model,
        models_dir=models_dir,
    )
    lingua.load()
    app.state.lingua = lingua

    scorer = SemanticScorer()
    scorer.load()
    app.state.scorer = scorer

    set_models_loaded(True)
    logger.info("llm-zip ready on port %d", config.port)

    yield

    set_models_loaded(False)
    logger.info("llm-zip shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="llm-zip",
        description="Context compression sidecar for LLM applications.",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(health.router)
    app.include_router(models.router)
    app.include_router(compress.router)
    app.include_router(compress_file.router)

    return app


app = create_app()
