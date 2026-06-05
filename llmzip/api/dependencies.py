from fastapi import Request
from llmzip.config.loader import AppConfig
from llmzip.core.lingua_adapter import LinguaAdapter
from llmzip.core.semantic_scorer import SemanticScorer


def get_config(request: Request) -> AppConfig:
    return request.app.state.config


def get_lingua(request: Request) -> LinguaAdapter:
    return request.app.state.lingua


def get_scorer(request: Request) -> SemanticScorer:
    return request.app.state.scorer
