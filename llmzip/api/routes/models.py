from fastapi import APIRouter

from llmzip.api.schemas import ModelEntry, ModelsResponse
from llmzip.pricing.resolver import resolve_prices

router = APIRouter(prefix="/v1")


@router.get("/models", response_model=ModelsResponse, tags=["models"])
def list_models() -> ModelsResponse:
    prices = resolve_prices()
    meta = prices.get("_meta", {})
    note = str(meta.get("note", "")) if isinstance(meta, dict) else ""

    entries: list[ModelEntry] = []
    for model, data in prices.items():
        if model == "_meta" or not isinstance(data, dict):
            continue
        entries.append(
            ModelEntry(
                model=model,
                input_per_million_usd=float(data["input"]),
                output_per_million_usd=float(data["output"]),
                source=str(meta.get("source", "fallback")),
            )
        )

    entries.sort(key=lambda e: e.model)
    return ModelsResponse(models=entries, pricing_note=note)
