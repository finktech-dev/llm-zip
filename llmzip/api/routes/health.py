import threading
from pathlib import Path
from fastapi import APIRouter
from llmzip.api.schemas import HealthResponse, ReadyResponse

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
