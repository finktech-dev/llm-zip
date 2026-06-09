from importlib.metadata import version
from fastapi import APIRouter, Depends
from llmzip.api.schemas import InfoResponse
from llmzip.api.dependencies import get_config
from llmzip.config.loader import AppConfig

router = APIRouter(prefix="/v1")

@router.get("/info", response_model=InfoResponse, tags=["system"])
def info(config: AppConfig = Depends(get_config)) -> InfoResponse:
    return InfoResponse(
        version=version("llm-zip"),
        compression_model=config.compression_model,
        scorer_model=config.scorer_model,
        deploy_mode=config.deploy_mode,
        features={
            "auth_enabled": config.api_key is not None,
            "rate_limit_enabled": config.rate_limit_enabled,
            "file_conversion_enabled": config.file_conversion_enabled,
        },
        limits={
            "max_tokens": config.max_tokens,
            "min_tokens_to_compress": config.min_tokens_to_compress,
            "max_batch_size": config.max_batch_size,
            "max_file_size_mb": config.max_file_size_mb,
            "default_ratio": config.default_ratio,
        },
    )
