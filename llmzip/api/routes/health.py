from fastapi import APIRouter
from llmzip.api.schemas import HealthResponse, ReadyResponse

router = APIRouter()

# set by app.py lifespan once models are loaded
_models_loaded = False


def set_models_loaded(value: bool) -> None:
    global _models_loaded
    _models_loaded = value


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/ready", response_model=ReadyResponse, tags=["system"])
def ready() -> ReadyResponse:
    return ReadyResponse(status="ok" if _models_loaded else "loading", models_loaded=_models_loaded)
