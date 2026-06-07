from pathlib import Path
from fastapi import APIRouter
from llmzip.api.schemas import HealthResponse, ReadyResponse

router = APIRouter()
_READY_MARKER = Path("models/.ready")


def set_models_loaded(value: bool) -> None:
    if value:
        _READY_MARKER.touch()
    else:
        _READY_MARKER.unlink(missing_ok=True)


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/ready", response_model=ReadyResponse, tags=["system"])
def ready() -> ReadyResponse:
    loaded = _READY_MARKER.exists()
    return ReadyResponse(status="ok" if loaded else "loading", models_loaded=loaded)
