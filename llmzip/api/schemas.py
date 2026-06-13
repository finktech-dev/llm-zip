from typing import Literal

from pydantic import BaseModel, Field, field_validator


class CompressRequest(BaseModel):
    text: str = Field(..., min_length=1)
    ratio: float = Field(default=0.5, ge=0.1, le=0.9)
    model: str | None = Field(default=None)


class CompressResponse(BaseModel):
    compressed: str
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    preservation_score: float | None
    estimated_savings: dict[str, str]
    pricing_accuracy: str
    pricing_note: str
    skipped: bool
    warning: str | None


class BatchItem(BaseModel):
    text: str = Field(..., min_length=1)
    ratio: float = Field(default=0.5, ge=0.1, le=0.9)
    model: str | None = Field(default=None)


class BatchRequest(BaseModel):
    texts: list[BatchItem] = Field(..., min_length=1)

    @field_validator("texts")
    @classmethod
    def check_batch_size(cls, v: list[BatchItem]) -> list[BatchItem]:
        # max enforced at route level using config — this is a hard safety cap
        if len(v) > 100:
            raise ValueError("Batch size cannot exceed 100")
        return v


class BatchResultItem(BaseModel):
    index: int
    status: Literal["ok", "error"]
    compressed: str | None = None
    original_tokens: int | None = None
    compressed_tokens: int | None = None
    compression_ratio: float | None = None
    preservation_score: float | None = None
    estimated_savings: dict[str, str] | None = None
    warning: str | None = None
    skipped: bool = False
    reason: str | None = None


class BatchResponse(BaseModel):
    results: list[BatchResultItem]
    summary: dict[str, int]


class ModelEntry(BaseModel):
    model: str
    input_per_million_usd: float
    output_per_million_usd: float
    source: str


class ModelsResponse(BaseModel):
    models: list[ModelEntry]
    pricing_note: str


class HealthResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    status: str
    models_loaded: bool


class LiveResponse(BaseModel):
    status: str


class ReadyDetailResponse(BaseModel):
    status: str
    models_loaded: bool
    deploy_mode: str


class InfoResponse(BaseModel):
    version: str
    compression_model: str
    scorer_model: str
    deploy_mode: str
    features: dict[str, bool]
    limits: dict[str, int | float]


class EstimateRequest(BaseModel):
    text: str = Field(..., min_length=1)
    ratio: float = Field(default=0.5, ge=0.1, le=0.9)
    model: str | None = Field(default=None)


class EstimateResponse(BaseModel):
    original_tokens: int
    estimated_compressed_tokens: int
    estimated_compression_ratio: float
    estimated_savings: dict[str, str]
    pricing_accuracy: str
    pricing_note: str
    would_compress: bool
    warning: str | None
