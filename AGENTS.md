# AGENTS.md

Context and rules for AI agents working on llm-zip.
Read this before touching any file.

---

## What this project is

llm-zip is a self-hosted context compression sidecar for LLM applications.
It compresses text before it reaches an AI API, reducing token costs 3–5×.
It never calls any AI API. It never handles API keys. It only compresses.

It started as an internal tool to reduce costs in private RAG systems.
Savings estimates for some models are based on published pricing and approximations —
not internal production benchmarks. Where this is the case it's marked in the code
and flagged in CLI output with a warning.

---

## Stack

- Python 3.10+, FastAPI, Typer, Pydantic v2
- LLMLingua-2 (compression), sentence-transformers (preservation score)
- MarkItDown (file conversion), tiktoken (token counting), httpx (HTTP)

---

## Import rules

```
api/ and cli/  →  can import from core/, pricing/, conversion/, config/
core/          →  cannot import from api/ or cli/
pricing/       →  cannot import from core/
```

Never create imports that cross these boundaries.

---

## Code rules

### Always
- Strict type annotations on every function — parameters and return types
- `pydantic.BaseModel` for all request/response schemas
- `pathlib.Path` instead of string paths
- `httpx.AsyncClient` for async HTTP, `httpx.get` for sync
- Raise specific exceptions, never bare `except:`
- Return early — avoid deep nesting
- Functions under 40 lines — split if longer
- One responsibility per file

### Never
- `Any` from typing
- `dict` as a type hint when a Pydantic model should exist
- `print()` — use the logger
- Hardcoded paths — use `pathlib.Path` and config values
- Silent exception swallowing
- Calls to any external AI API
- Storing or logging request content
- Mutable default arguments
- `time.sleep()` in async context — use `asyncio.sleep()`

### Naming
- Modules: `snake_case` — Classes: `PascalCase` — Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE` — Private functions: `_prefix`

### Comments
- Rare and intentional — comment the *why*, never the *what*
- No commented-out code in commits

---

## Models in memory

Both LLMLingua-2 and the sentence-transformer are loaded once at FastAPI startup via `lifespan`.
They live in `app.state` and are injected via `Depends`.
Never load a model inside a request handler.

---

## Pricing

Fetched from LiteLLM at startup, cached for `CACHE_TTL` seconds.
On failure, fall back to `pricing/fallback.py` silently.
Update `PRICES_LAST_UPDATED` when editing fallback prices.
If a model's savings estimate is not backed by production benchmarks,
mark it with a `# unverified` comment in `fallback.py`.

---

## Error handling

- API errors: `{"error": "message", "code": "ERROR_CODE"}`
- HTTP codes: 400 bad input, 413 too large, 422 validation, 500 internal, 501 feature disabled
- CLI errors: print to stderr, exit code 2
- Batch: never fail the entire batch for one item failure

---

## Config

`.llmzip.config` is required. The loader validates all values at startup.
The service must not start with invalid or missing required config.
Required: `MAX_TOKENS`, `MIN_TOKENS_TO_COMPRESS`, `DEFAULT_RATIO`, `DEFAULT_MODEL`.

---

## What is permanently out of scope

- Calling any AI API on behalf of the user
- Storing or caching compressed texts
- User authentication or API keys
- A database of any kind
- A web UI or dashboard
- Cloud-hosted SaaS version
