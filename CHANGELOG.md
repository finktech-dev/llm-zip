# Changelog

All notable changes to llm-zip will be documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

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
