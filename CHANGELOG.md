# Changelog

All notable changes to llm-zip will be documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

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
- Docker — two containers with persistent model volume
- `MIN_TOKENS_TO_COMPRESS` threshold — texts below it returned as-is with `skipped: true`
- `FILE_CONVERSION` feature flag
- Optional rate limiting, off by default
- Configurable batch workers
