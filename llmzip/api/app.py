import asyncio
import hmac
import importlib.metadata
import logging
import os
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import cast

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from llmzip.api import limiter as limiter_module
from llmzip.api.limiter import limiter
from llmzip.api.routes import compress, compress_file, estimate, health, info, models
from llmzip.api.routes.health import set_models_loaded
from llmzip.config.loader import AppConfig, load
from llmzip.core.lingua_adapter import LinguaAdapter
from llmzip.core.remote_lingua import RemoteLinguaAdapter
from llmzip.core.remote_scorer import RemoteSemanticScorer
from llmzip.core.semantic_scorer import SemanticScorer
from llmzip.logging_config import setup_logging
from llmzip.pricing.resolver import configure as configure_pricing


class _HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        return not any(
            path in message
            for path in ["GET /health", "GET /ready", "GET /health/live", "GET /health/ready"]
        )


logging.getLogger("uvicorn.access").addFilter(_HealthCheckFilter())
setup_logging()
logger = logging.getLogger("llmzip.api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    config: AppConfig = app.state.config

    if config.rate_limit_enabled:
        limiter_module.set_limits(config.rate_limit_rpm, config.rate_limit_rpd)
        limiter.enabled = True

    if config.cache_dir is not None:
        os.environ.setdefault("LLMZIP_CACHE_DIR", str(config.cache_dir))
        config.cache_dir.mkdir(parents=True, exist_ok=True)

    configure_pricing(config.pricing_cache_ttl)

    if config.deploy_mode == "split":
        logger.info("Operating in SPLIT mode. Connecting to remote models at %s", config.models_url)

        # Persistent async HTTP client shared across all compress_file requests in split mode.
        # Avoids a new TCP handshake per file upload — same rationale as RemoteLinguaAdapter.
        app.state.http_client = httpx.AsyncClient(
            timeout=120.0,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )

        # Polling for remote service to be ready
        retries = 60
        ready = False
        async with httpx.AsyncClient() as client:
            for i in range(retries):
                try:
                    response = await client.get(f"{config.models_url}/ready", timeout=5.0)
                    if response.status_code == 200 and response.json().get("models_loaded"):
                        ready = True
                        break
                except Exception:
                    pass

                logger.info("Waiting for remote models service... (%d/%d)", i + 1, retries)
                await asyncio.sleep(5)

        if not ready:
            logger.critical("Remote models service failed to load within 5 minutes.")
            raise RuntimeError("Remote models service unavailable")

        app.state.lingua = RemoteLinguaAdapter(
            config.models_url, timeout=float(config.inference_timeout)
        )
        app.state.scorer = RemoteSemanticScorer(
            config.models_url, timeout=float(config.scorer_timeout)
        )
        set_models_loaded(True)
    else:
        logger.info("Operating in MONOLITH mode. Loading models locally.")
        models_dir = Path(app.state.__dict__.get("models_dir", "models"))

        lingua = LinguaAdapter(
            model_name=config.compression_model,
            models_dir=models_dir,
            chunk_size=config.chunk_size,
        )
        lingua.load()
        app.state.lingua = lingua

        scorer = SemanticScorer(
            models_dir=models_dir,
            model_id=config.scorer_model,
            timeout=config.scorer_timeout,
        )
        scorer.load()
        app.state.scorer = scorer
        set_models_loaded(True)

    logger.info("llm-zip ready on port %d", config.port)

    yield

    set_models_loaded(False)
    # Close persistent HTTP clients (RemoteLinguaAdapter / RemoteSemanticScorer)
    # so their connection pools are drained cleanly on shutdown.
    for attr in ("lingua", "scorer"):
        adapter = getattr(app.state, attr, None)
        if adapter is not None and hasattr(adapter, "close"):
            adapter.close()
    # Close the async HTTP client used by compress_file in split mode.
    http_client = getattr(app.state, "http_client", None)
    if http_client is not None:
        await http_client.aclose()
    logger.info("llm-zip shutting down")


def create_app() -> FastAPI:
    config = load()

    app = FastAPI(
        title="llm-zip",
        description="Context compression sidecar for LLM applications.",
        version=importlib.metadata.version("llm-zip"),
        lifespan=lifespan,
    )
    app.state.config = config

    if config.rate_limit_enabled:
        app.state.limiter = limiter
        app.add_exception_handler(
            RateLimitExceeded,
            cast(
                Callable[[Request, Exception], Response | Awaitable[Response]],
                _rate_limit_exceeded_handler,
            ),
        )
        app.add_middleware(SlowAPIMiddleware)

    @app.middleware("http")
    async def auth_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # request.app.state.config is set in lifespan.
        # Fallback for tests or startup edge cases.
        config: AppConfig | None = getattr(request.app.state, "config", None)

        if config is None or config.api_key is None:
            return await call_next(request)

        # Public endpoints
        allowed_paths = {
            "/health",
            "/ready",
            "/health/live",
            "/health/ready",
            "/v1/info",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/v1/health",
            "/v1/ready",  # safety check for prefixed routes if any
        }
        if request.url.path in allowed_paths or request.url.path.startswith(
            ("/docs", "/redoc", "/openapi.json")
        ):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

        provided_key = auth_header.split(" ")[1]
        # Use hmac.compare_digest to prevent timing attacks: constant-time comparison
        # regardless of how many characters match, so an attacker cannot infer the
        # key's length or prefix by measuring response times.
        if not hmac.compare_digest(provided_key, config.api_key):
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

        return await call_next(request)

    app.include_router(health.router)
    app.include_router(models.router)
    app.include_router(estimate.router)
    app.include_router(info.router)
    app.include_router(compress.router)
    app.include_router(compress_file.router)

    return app


def get_app() -> FastAPI:
    return create_app()


if __name__ != "__main__":
    try:
        app = create_app()
    except SystemExit:
        # Allows importing the module in tests without a config present
        app = FastAPI()
