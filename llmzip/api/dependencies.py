from typing import cast

from fastapi import Request

from llmzip.config.loader import AppConfig
from llmzip.core.protocols import Compressor, Scorer


def get_config(request: Request) -> AppConfig:
    return cast(AppConfig, request.app.state.config)

def get_lingua(request: Request) -> Compressor:
    return cast(Compressor, request.app.state.lingua)

def get_scorer(request: Request) -> Scorer:
    return cast(Scorer, request.app.state.scorer)

def get_warning(compression_warning: str | None, accuracy: str, model: str) -> str | None:
    parts: list[str] = []
    if compression_warning:
        parts.append(compression_warning)
    if accuracy != "exact":
        parts.append(
            f"Model '{model}' token count is estimated (±10%). "
            "Exact counting is supported for OpenAI models (gpt-*, o1, o3, o4)."
        )
    return " | ".join(parts) if parts else None
