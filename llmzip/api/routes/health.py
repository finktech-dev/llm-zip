import threading
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from llmzip.api.dependencies import get_config
from llmzip.api.schemas import HealthResponse, LiveResponse, ReadyDetailResponse, ReadyResponse
from llmzip.config.loader import AppConfig

router = APIRouter()
_READY_MARKER = Path("models/.ready")
_models_loaded_event = threading.Event()


def set_models_loaded(value: bool) -> None:
    if value:
        _models_loaded_event.set()
        _READY_MARKER.touch()
    else:
        _models_loaded_event.clear()
        _READY_MARKER.unlink(missing_ok=True)


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/ready", response_model=ReadyResponse, tags=["system"])
def ready() -> ReadyResponse:
    # Requires BOTH the in-process event and the filesystem marker to be true.
    # The event protects against multi-worker race conditions, while the marker
    # ensures Docker monolith/split deployment coordination works.
    loaded = _models_loaded_event.is_set() and _READY_MARKER.exists()
    return ReadyResponse(status="ok" if loaded else "loading", models_loaded=loaded)


@router.get("/health/live", response_model=LiveResponse, tags=["system"])
def health_live() -> LiveResponse:
    return LiveResponse(status="ok")


@router.get("/health/ready", response_model=ReadyDetailResponse, tags=["system"])
def ready_detail(config: AppConfig = Depends(get_config)) -> ReadyDetailResponse:
    loaded = _models_loaded_event.is_set() and _READY_MARKER.exists()
    if not loaded:
        raise HTTPException(status_code=503, detail="Models loading")
    return ReadyDetailResponse(status="ok", models_loaded=loaded, deploy_mode=config.deploy_mode)
