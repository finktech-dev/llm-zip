from fastapi import Request
from llmzip.config.loader import AppConfig
from llmzip.core.protocols import Compressor, Scorer

def get_config(request: Request) -> AppConfig:
    return request.app.state.config

def get_lingua(request: Request) -> Compressor:
    return request.app.state.lingua

def get_scorer(request: Request) -> Scorer:
    return request.app.state.scorer
