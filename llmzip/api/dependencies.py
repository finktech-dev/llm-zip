from fastapi import Request
from llmzip.config.loader import AppConfig
from llmzip.core.protocols import Compressor, Scorer

def get_config(request: Request) -> AppConfig:
    return request.app.state.config

def get_lingua(request: Request) -> Compressor:
    return request.app.state.lingua

def get_scorer(request: Request) -> Scorer:
    return request.app.state.scorer

def get_warning(msg: str | None, accuracy: str, model: str) -> str | None:
    warning = None
    if accuracy != "exact":
        warning = f"Model '{model}' token count is estimated (±10%). Exact counting is supported for OpenAI models (gpt-*, o1, o3, o4)."
    
    if msg:
        if warning:
            warning += f". {msg}"
        else:
            warning = msg
    return warning
