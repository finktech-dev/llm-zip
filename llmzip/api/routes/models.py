from fastapi import APIRouter

from llmzip.api.schemas import ModelEntry, ModelsResponse
from llmzip.pricing.resolver import resolve_prices

router = APIRouter(prefix="/v1")


@router.get("/models", response_model=ModelsResponse, tags=["models"])
def list_models() -> ModelsResponse:
    prices, meta = resolve_prices()
    note = meta.get("note", "")

    entries: list[ModelEntry] = []
    for model, data in prices.items():
        entries.append(
            ModelEntry(
                model=model,
                input_per_million_usd=data["input"],
                output_per_million_usd=data["output"],
                source=meta.get("source", "fallback"),
            )
        )

    entries.sort(key=lambda e: e.model)
    return ModelsResponse(models=entries, pricing_note=note)
