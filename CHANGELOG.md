# Changelog

All notable changes to llm-zip will be documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [0.1.9] — 2026-06-06

### Added

- **Smart Chunking**: New paragraph-based chunking logic for long texts. Documents are now split into segments (default: 400 tokens) to ensure optimal BERT performance and prevent context window errors.
- **Benchmarks**: Added real-world internal test results to README, including academic papers and technical manuals.

---

## [0.1.8] — 2026-06-06

### Fixed

- **Concurrency**: Fixed race condition in `resolver.py`: fetch now runs outside the lock, preventing concurrent HTTP requests to LiteLLM.
- **System**: Fixed `health.py` ready endpoint returning incorrect status under multi-worker uvicorn deployments.

---

## [0.1.7] — 2026-06-06

### Fixed

- **Pricing**: Fixed incorrect fallback prices for GPT-5.5, GPT-5.4 family, Gemini 3.x, and DeepSeek V4 (verified 2026-06-06)
- **Models**: Added missing models to fallback: `gpt-5.4`, `gpt-4.1-nano`, `claude-opus-4-6`
- **Performance**: Fixed redundant `count_tokens` call in `/v1/compress` route
- **i18n**: Compression failure warnings now route through i18n instead of returning raw strings
- **Refactor**: Centralized `FEATURED_MODELS` into `core/featured_models.py`, removing duplicate definitions in `savings_calculator.py` and `compress_cmd.py`

---

## [0.1.6] — 2026-06-06

### Fixed

- **Syntax Error**: literal newline artifact in `lingua_adapter.py` - `force_tokens=["\n"]` had a raw newline character instead of the escape sequence, causing a `SyntaxError` on startup
- **Name Error**: missing `from typing import NoReturn` import in `loader.py` causing a `NameError` on startup

---

## [0.1.5] — 2026-06-06

### Fixed

- **Model default**: `CompressRequest` and `BatchItem` no longer hardcode `gpt-4o-mini` - model now falls back to `config.default_model` from `.llmzip.config` when not specified in the request
- **Pricing concurrency**: added `threading.Lock` with double-checked locking to `resolver.py` - prevents simultaneous LiteLLM fetches under concurrent batch load
- **Pricing source field**: `_meta` in fetcher and resolver now includes an explicit `"source"` field (`"litellm"` or `"fallback"`) instead of inferring it from the note string
- **NoReturn type**: `_fail()` in `loader.py` now correctly typed as `NoReturn`
- **Tempfile on Windows**: `convert_bytes()` in `file_converter.py` now closes the tempfile before passing it to MarkItDown, fixing `PermissionError` on Windows

---

## [0.1.4] — 2026-06-06

### Fixed

- **Threading**: `threading.Lock` and `count_tokens` import were missing from `lingua_adapter.py` — batch compression under concurrency would crash at runtime
- **Model cache**: `SemanticScorer` now accepts and uses `models_dir`, ensuring the CLI and API both download the scorer model to the same volume
- **Corrupt code**: `compress_file.py` had corrupted trailing code from a previous patch — cleaned up
- **Dynamic version**: `importlib.metadata` import was missing from `app.py` despite the dynamic version call being present
- **Tempfile**: `NamedTemporaryFile` fix from v0.1.1 was not present in the built wheel — reapplied
---

## [0.1.3] — 2026-06-06

### Fixed

- **Critical**: `POST /v1/compress` was calling `lingua.compress()` without the `target_model` argument, causing a `TypeError` on every request
- **Dynamic version**: API version in Swagger UI was hardcoded as `0.1.0`; now reads dynamically from package metadata

---

## [0.1.2] — 2026-06-06

### Fixed

- **Docker**: removed redundant `llmzip-models` service — single `llmzip-api` container now mounts the models volume directly
- **Model cache**: `LinguaAdapter` passes `cache_dir` to `PromptCompressor` and `SemanticScorer` passes `cache_folder` to `SentenceTransformer`, forcing downloads to `/app/models` instead of the global HuggingFace cache — models persist across restarts without re-downloading
- **Config filename**: renamed `llmzip.config.example` to `.llmzip.config.example` to match the filename the code actually expects

---

## [0.1.1] — 2026-06-06

### Fixed

- **Token consistency**: `LinguaAdapter` now uses `count_tokens()` (tiktoken/char-ratio) instead of word-count approximation — `compression_ratio` and `estimated_savings` are now calculated from the same metric
- **Thread safety**: added `threading.Lock` around `compress_prompt()` to prevent race conditions under concurrent batch requests
- **Pricing resilience**: `resolver.py` tracks failed fetch attempts with a 30s cooldown, preventing request stampedes when LiteLLM is unavailable; stale cache is served before falling back to hardcoded prices
- **Secure tempfile**: replaced deprecated `mktemp()` with `NamedTemporaryFile` in `POST /v1/compress/file`
- **Config consistency**: `POST /v1/compress/file` now falls back to `config.default_model` when no model is specified, instead of hardcoding `gpt-4o-mini`
- **CLI parity**: `_maybe_convert` in the CLI now validates that file conversion produces extractable text, matching the API behavior
- **Token matching**: OpenAI model detection uses an ordered list of substrings (most-specific first) instead of a prefix dict, fixing ambiguous matches like `gpt-4o` vs `gpt-4`

---

## [0.1.0] — 2026-06-04

Initial release.

### Added

- `POST /v1/compress` — compress a single text with LLMLingua-2
- `POST /v1/compress/batch` — compress up to N texts in parallel (configurable)
- `POST /v1/compress/file` — convert and compress PDF, Word, Excel, PowerPoint via MarkItDown
- `GET /v1/models` — list supported models with live prices from LiteLLM
- `GET /health` and `GET /ready`
- CLI: `llmzip compress`, `llmzip prices`, `llmzip download-models`
- Preservation score via `paraphrase-multilingual-MiniLM-L12-v2` (English + Spanish)
- Token counting — exact via tiktoken for OpenAI, heuristic for others (marked in response)
- Live pricing from LiteLLM with fallback to hardcoded values
- `.llmzip.config` — INI config validated at startup, service won't start with missing values
- `.llmzipignore` / `.llmzipignore.local` — ignore rules for texts and file patterns
- Docker — single container with persistent model volume
- `MIN_TOKENS_TO_COMPRESS` threshold — texts below it returned as-is with `skipped: true`
- `FILE_CONVERSION` feature flag
- Optional rate limiting, off by default
- Configurable batch workers
