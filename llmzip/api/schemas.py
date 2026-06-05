from pydantic import BaseModel, Field, field_validator


class CompressRequest(BaseModel):
    text: str = Field(..., min_length=1)
    ratio: float = Field(default=0.5, ge=0.1, le=0.9)
    model: str = Field(default="gpt-4o-mini")


class CompressResponse(BaseModel):
    compressed: str
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    preservation_score: float
    estimated_savings: dict[str, str]
    pricing_accuracy: str
    pricing_note: str
    skipped: bool
    warning: str | None


class BatchItem(BaseModel):
    text: str = Field(..., min_length=1)
    ratio: float = Field(default=0.5, ge=0.1, le=0.9)
    model: str = Field(default="gpt-4o-mini")


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
    status: str           # "ok" | "error"
    compressed: str | None = None
    compression_ratio: float | None = None
    preservation_score: float | None = None
    estimated_savings: dict[str, str] | None = None
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
