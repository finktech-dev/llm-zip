# AGENTS.md

Instructions for AI coding agents working on llm-zip.
Read this before touching any file.

---

## Commands

```bash
# Install (dev)
pip install -e ".[dev]"

# Test — all tests use mocks, no models required
pytest

# Lint
ruff check .

# Type check
mypy llmzip

# Run API locally (requires .llmzip.config)
uvicorn llmzip.api.app:app --reload

# Run models server (split mode)
uvicorn llmzip.models_server.app:app --port 8001 --reload

# Download models to ./models/
llmzip download-models

# Docker — monolith
docker compose up -d

# Docker — split mode
docker compose -f docker-compose.split.yml up -d
```

---

## Import rules

These are enforced — never cross these boundaries:

```
api/            →  can import from: core/, pricing/, conversion/, config/
cli/            →  can import from: core/, pricing/, conversion/, config/
models_server/  →  can import from: core/, config/
core/           →  cannot import from: api/, cli/, models_server/
pricing/        →  cannot import from: core/
```

---

## Non-obvious constraints

**Models load once at startup, never inside a request handler.**
Both LLMLingua-2 and the sentence-transformer live in `app.state` and are injected via `Depends`. Loading a model inside a handler is a hard error.

**stderr for metrics, stdout for output — always.**
CLI commands print compressed text to stdout and all metrics/warnings to stderr (`typer.echo(..., err=True)`). Mixing them breaks pipes.

**Tests never load real models.**
Every test that touches `LinguaAdapter`, `SemanticScorer`, or file conversion uses mocks. Integration tests that require real models are marked `@pytest.mark.integration` and skipped by default.

**`llmzip.core` never calls any external AI API.**
The project compresses — it never calls OpenAI, Anthropic, Gemini, or any LLM on behalf of the user. Any code that does this gets rejected.

**API Key in config protects llm-zip's own endpoints.**
`API_KEY` in `[server]` is authentication for the llm-zip HTTP API itself. It has nothing to do with the user's LLM provider keys, which llm-zip never handles, stores, or sees.

**Pricing accuracy is model-specific.**
tiktoken is exact for OpenAI models. For Claude, Gemini, and DeepSeek, a character-ratio heuristic is used (±10% error). Never claim exact accuracy for non-OpenAI models. Mark `pricing_accuracy` accordingly.

**LLMLingua-2 has a compression floor.**
The model plateaus around 2–2.5× regardless of the requested ratio on some document types. Do not promise ratios above that. The `compression_ratio` in the response reflects actual output, not the requested ratio.

**`PromptCompressor` is thread-safe on CPU for inference.**
PyTorch forward passes do not mutate model state. The global lock around `compress_prompt()` was removed in v0.2.0 — do not re-add it.

---

## Code rules

### Do
- Strict type annotations on every function — parameters and return types
- `pydantic.BaseModel` for all request/response schemas
- `pathlib.Path` instead of string paths
- `httpx.AsyncClient` for async HTTP, `httpx.Client` for sync
- Raise specific exceptions — never bare `except:`
- Return early to avoid deep nesting
- One responsibility per file
- Functions under 40 lines — split if longer

### Don't
- `Any` from typing
- `dict` as a type hint when a Pydantic model should exist
- `print()` — use the logger
- `time.sleep()` in async context — use `asyncio.sleep()`
- Hardcoded model names or paths — read from config
- Silent exception swallowing
- Mutable default arguments
- Commented-out code in commits
- f-strings in logger calls — use `%s` formatting

---

## Adding a new endpoint

1. Schema goes in `llmzip/api/schemas.py`
2. Route goes in `llmzip/api/routes/<name>.py`
3. Register the router in `llmzip/api/app.py`
4. Rate limiting uses the `@limiter.limit` decorator from `llmzip/api/limiter.py`
5. Config is injected via `Depends(get_config)` — never read `.llmzip.config` directly in a route

## Adding a new CLI command

1. Command function goes in `llmzip/cli/<name>_cmd.py`
2. Register in `llmzip/cli/main.py`
3. All user-facing strings go through `llmzip/i18n/t()` — no hardcoded English in CLI output
4. Add the new key to all five language files: `en.py`, `es.py`, `pt.py`, `zh.py`, `ja.py`

## Adding a new model to fallback prices

1. Edit `llmzip/pricing/fallback.py`
2. Update `PRICES_LAST_UPDATED`
3. Add `# unverified` comment if not confirmed against live billing

---

## Permanent out of scope

- Calling any LLM API on behalf of the user
- Storing, logging, or proxying the user's LLM provider API keys
- Storing or caching compressed texts
- A database of any kind
- A web UI or dashboard
- Cloud-hosted SaaS version
