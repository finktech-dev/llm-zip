# Changelog

All notable changes to llm-zip will be documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [0.3.2] — 2026-07-16

### Added

- **Token preservation** (`--preserve` / `preserve_tokens`): Tokens passed to this option are
  guaranteed to survive compression unchanged. Useful for structured text where removing certain
  markers (e.g. `"ERROR:"`, `"def "`, `"class "`) would corrupt the output semantics. Repeatable
  on the CLI (`--preserve "ERROR:" --preserve "WARN:"`); per-item in batch requests, so each
  text in a batch can protect a different set of tokens. Wired end-to-end: CLI → API schemas →
  compress and batch routes → `LinguaAdapter` → models server in split mode.

### Fixed

- **Event loop blocking on large PDFs** (`api/routes/compress_file.py`): File conversion via
  MarkItDown/pdfminer.six is synchronous and can take 10–15 s on large documents. Running it
  inline in an `async` handler stalled the entire uvicorn event loop, serializing concurrent
  file requests. Moved to `asyncio.to_thread()`. Same fix applied to `calculate_savings()` calls
  in the same handler, which transitively reach `httpx.get()` on a cold price cache.
- **Sliding window O(n) on minified blobs** (`core/lingua_adapter.py`): Chunking of
  whitespace-free content (minified JSON, JS) used linear `end -= 1` search instead of the
  documented binary search, producing thousands of `tiktoken.encode()` calls per chunk.
  Replaced with correct `lo/hi/mid` binary search — processing drops from seconds to
  milliseconds on large minified inputs.
- **Timing attack on API key comparison** (`api/app.py`): Standard string equality
  short-circuits on the first mismatched character. Replaced with `hmac.compare_digest()`.
- **Corrupted price cache on unclean shutdown** (`pricing/disk_cache.py`): Writing directly to
  `prices.json` left a truncated file on `SIGKILL` or OOM, causing `JSONDecodeError` on the
  next startup. Now writes to `.tmp` first and replaces atomically via POSIX `rename(2)`.
- **Rate limit starvation behind proxy / Docker** (`api/limiter.py`): All clients resolved to
  the gateway IP behind nginx, Traefik, or Docker Compose, causing shared exhaustion of per-IP
  limits. Added `X-Forwarded-For` support via `_get_real_ip()`, enabled with
  `TRUST_PROXY_HEADERS=true`. Only enable behind a trusted proxy that controls the header.
- **`\n` deduplication in `force_tokens`** (`core/lingua_adapter.py`): The deduplication set
  was initialized with the two-character string `\\n` instead of the actual newline character,
  silently duplicating it when callers passed `"\n"` in `preserve_tokens`.
- **Thread-unsafe encoding cache** (`core/token_counter.py`): `_encoding_cache` had no lock,
  allowing concurrent `BATCH_WORKERS` threads to race on `tiktoken.encoding_for_model()` at
  startup. Fixed with double-checked locking.
- **Thread-unsafe ignore pattern cache** (`core/ignore.py`): Same race as above for
  `.llmzipignore` reads under batch workers. Fixed with `threading.Lock()`; added `reload()`
  for test isolation without module-level monkeypatching.
- **`preserve_tokens` silently ignored in compress routes** (`api/routes/compress.py`): The
  field was present in schemas but never forwarded to `lingua.compress()` in either the
  single-item or batch handler.
- **Scanned PDF error message** (`api/routes/compress_file.py`): 422 response for files that
  produce no extractable text now explicitly mentions that scanned or image-based PDFs have no
  text layer and must go through an OCR tool first.

### Changed

- **HTTP connection pooling in split mode** (`core/remote_lingua.py`, `core/remote_scorer.py`,
  `api/app.py`, `api/routes/compress_file.py`): All HTTP clients previously created a new
  connection per request. Migrated to persistent `httpx.Client` / `AsyncClient` instances with
  `max_keepalive_connections=10`, initialized at startup and closed cleanly on lifespan
  shutdown.
- **i18n key parity**: Added `config.error_prefix` to `en`, `es`, and `pt` modules. The key
  was already present in `zh` and `ja`; all five language modules are now fully in sync.

---

## [0.3.1] — 2026-06-15

### Added

- **Ignore system** (`.llmzipignore` / `.llmzipignore.local`): File patterns and paths listed
  in these files are excluded from compression and batch processing. Supports the same glob
  syntax as `.gitignore`. `.llmzipignore.local` is intended for machine-local overrides and
  should not be committed.

### Fixed

- **Dynamic package version** (`core/app.py`): `__version__` is now read via
  `importlib.metadata` at runtime instead of being imported at module level, preventing startup
  crashes when the package metadata is unavailable during testing (ISSUE-02).
- **Monolith Dockerfile** (`Dockerfile`): Replaced the heavyweight multi-stage build with a
  lightweight single-stage image for the monolith deployment mode. The ready marker path now
  falls back to the `MODELS_DIR` environment variable (ISSUE-03).
- **Module-level app instantiation in tests** (`tests/`): Removed top-level `app` import that
  caused premature startup and `SystemExit` when `.llmzip.config` was missing during test
  collection. Switched to lazy loading (ISSUE-04, ISSUE-08).
- **LLMLingua-2 empty output fallback** (`core/lingua_adapter.py`): Added reliable fallback
  when `compress_prompt()` returns an empty result due to over-compression or extreme ratio
  thresholds. Previously the response would be an empty string (ISSUE-05).
- **Configurable timeouts in split mode** (`core/remote_lingua.py`, `core/remote_scorer.py`):
  `inference_timeout` and `scorer_timeout` from config are now strictly passed through to the
  remote HTTP clients. Previously the values were read but not applied (ISSUE-06).
- **`/v1/compress/file` form validation** (`api/routes/compress_file.py`): Resolved 422
  validation errors caused by missing explicit `Form()` parameter annotations on the endpoint
  (ISSUE-10).
- **`filename` key conflict in structured logging** (`api/routes/compress_file.py`): Logging
  calls that passed `filename` as an `extra` key conflicted with Python's internal `LogRecord`
  attribute of the same name, raising a `KeyError`. Renamed to `input_filename` (ISSUE-11).
- **Warning generation** (`api/`): Centralized and unified warning string construction using
  `" | "` as delimiter throughout all routes, replacing inconsistent ad-hoc formatting
  (ISSUE-09).
- **Pricing resolver lock contention** (`pricing/resolver.py`): Refactored local cache checks
  to run before acquiring the fetch lock, preventing redundant lock contentions and duplicate
  LiteLLM fetches under concurrent load. Updated fallback pricing metadata to 2026-06-14.
- **Model downloader port** (`cli/download_models.py`): The interactive model downloader now
  parses the target port dynamically from `MODELS_URL` instead of hardcoding `8001`.
- **Test contamination** (`tests/`): Resolved cross-test state leakage and Dockerfile factory
  pattern issues that caused intermittent failures in CI (ISSUE-04, ISSUE-08).

### Changed

- **Warning generation logic** (`api/`): `get_warning()` extracted into a single shared
  utility. All routes now produce warning strings through this function (ISSUE-09).

---

## [0.3.0] — 2026-06-14

### Added

- **Disk cache for pricing** (`pricing/disk_cache.py`): LiteLLM prices persist to
  `~/.llmzip/prices.json` between restarts. Configurable via `LLMZIP_CACHE_DIR` env var or
  `[storage] CACHE_DIR` in config. Falls back to cached data up to 7 days old if LiteLLM is
  unreachable.
- **Offline-first tiktoken**: `TIKTOKEN_CACHE_DIR` is set automatically on `token_counter`
  import. Docker images pre-download `cl100k_base` and `o200k_base` encodings at build time —
  no network calls at runtime.
- **Batch BERT inference**: `LinguaAdapter.compress()` now passes all chunks in a single
  `compress_prompt(List[str])` call instead of looping. 3–5× latency reduction on large inputs.
- **Proxied file conversion in split mode**: The lightweight API container forwards
  `/v1/compress/file` uploads to the models container via a new `/infer/convert_file` internal
  endpoint, keeping the API image free of heavy conversion dependencies.
- **Docker overhaul**: Multi-stage builds, non-root `llmzip` user, stdlib Python healthchecks
  (no `curl`), Alpine-based API container (~50 MB), CPU-only PyTorch for the models container
  (~800 MB vs ~3 GB previously).
- **Test suite**: Added `test_api_v1`, `test_chunker_stress`, `test_i18n`,
  `test_negative_cases`, and `test_token_resilience`.

### Fixed

- **Startup permissions in Docker**: Fixed `PermissionError` crash caused by the `logs/`
  directory not being owned by the non-root user before the context switch.
- **Batch token precision**: `original_tokens` and `compressed_tokens` returned `None` in
  batch results; now correctly populated for both successful and skipped items.
- **`count_tokens` resilience**: Now accepts `str | None` and no longer caches transient
  tiktoken network errors — retries work correctly after a connectivity failure.
- **Pricing fetch race condition** (`pricing/resolver.py`): Removed the `fetch_needed`
  intermediary variable that allowed duplicate LiteLLM fetches under concurrent load.
- **Batch result visibility**: Added `skipped` and `warning` fields to `BatchResultItem`
  schema.
- **Skipped compression pricing**: Skipped paths now use the user-requested model for price
  estimation instead of the system default.
- **i18n**: Completed pricing accuracy translation keys across all five languages.

### Changed

- **`resolve_prices()` return type**: Now returns `tuple[dict[str, PriceEntry], dict[str, str]]`
  — prices and metadata cleanly separated. Breaking change for direct consumers of the pricing
  module.
- **`fetch_prices()` return type**: Returns the same `(prices, meta)` tuple to match
  `resolve_prices()`.
- **Pricing fallback**: Added `PriceEntry` TypedDict for strict typing. Updated fallback prices
  for GPT-5.x, Claude 4.x, Gemini 3.x, and DeepSeek V4 families (verified 2026-06-14).

---

## [0.2.2] — 2026-06-10

### Added

- **CI/CD pipelines**: `ci.yml` runs ruff → mypy → pytest on Python 3.10/3.11/3.12 for every
  push and PR to `main` and `develop`. `release.yml` triggers on `v*.*.*` tags to build and
  publish to PyPI.
- **i18n key** `compress.warning.chunk_truncated` added in all five supported languages.

### Fixed

- **Sub-sentence chunking fallback**: Paragraphs exceeding `chunk_size` tokens are now split
  at sentence boundaries (`[.!?]` followed by whitespace) before being passed to BERT, with
  sentences grouped into chunks the same way paragraphs are. Prevents unnecessary truncation on
  dense but readable prose.
- **Truncation warning**: When a segment cannot be subdivided further (single sentence or
  punctuation-free block exceeds `chunk_size`), the response now includes
  `compress.warning.chunk_truncated`. Previously truncation was silent.

---

## [0.2.1] — 2026-06-09

### Added

- **Health probes**: K8s-compliant `/health/live` and `/health/ready` endpoints.
- **Info endpoint**: `/v1/info` exposes version, compression model, scorer model, deploy mode,
  enabled features, and configured limits.
- **Structured logging**: JSON file logging to `logs/llmzip.log` with rotating handlers and
  colored console output.
- **File size validation**: `MAX_FILE_SIZE_MB` limit enforced on `/v1/compress/file`.
- **CLI**: `llmzip version` command.

### Fixed

- **Docker dependencies**: `sentence-transformers` was missing from the API container image,
  causing `ModuleNotFoundError` on semantic scoring calls.
- **Dependency scope**: Moved `llmlingua` and `markitdown` to the optional `[inference]` extra
  in `pyproject.toml` to keep the base install lightweight.
- **`NameError` in compress routes**: `get_warning` was called before being defined, causing
  500 errors on all compression requests.

---

## [0.2.0] — 2026-06-07

### Added

- **Split deploy mode** (`DEPLOY_MODE=split`): Separates the API layer from the inference
  engine. `llmzip-models` runs as an independent internal service exposing `/infer/compress`
  and `/infer/score`; `llmzip-api` delegates via `RemoteLinguaAdapter` and
  `RemoteSemanticScorer`. Added `Dockerfile.api`, `Dockerfile.models`, and
  `docker-compose.split.yml`. `MODELS_URL` is overridable via environment variable.
- **Estimate endpoint**: `POST /v1/estimate` — dry-run savings calculation without performing
  compression.
- **API key authentication**: Optional `Authorization: Bearer <key>` header, configured via
  `API_KEY` in `[server]`.
- **Rate limiting**: `slowapi` integration with `REQUESTS_PER_MINUTE` and `REQUESTS_PER_DAY`
  knobs. Disabled by default.
- **Scorer reliability**: Configurable `SCORER_TIMEOUT` and `SCORER_MODEL`. Scoring runs under
  a timeout to prevent hanging requests on slow embedding models.

### Fixed

- **CLI `--json` output**: Human-readable metrics were printed even when `--json` was active,
  producing invalid JSON on stdout.
- **Token counting for OpenAI models**: `tiktoken.encoding_for_model()` now used for exact
  token counts, replacing fragile substring matching that misidentified `gpt-4o` as `gpt-4`.

### Changed

- **`LinguaAdapter` concurrency**: Removed global inference lock, allowing true parallel
  processing of batch items and chunks.

---

## [0.1.9] — 2026-06-07

### Added

- **Paragraph-based chunking**: Long texts are split into segments (default: 400 tokens) before
  being passed to BERT, ensuring optimal model performance and preventing context window errors.
- **Benchmarks**: Real-world test results added to README covering academic papers and technical
  manuals.

---

## [0.1.8] — 2026-06-06

### Fixed

- **Pricing fetch race condition** (`pricing/resolver.py`): LiteLLM fetch now runs outside the
  lock, preventing concurrent threads from issuing duplicate HTTP requests.
- **Multi-worker ready endpoint** (`api/routes/health.py`): Added disk-based ready marker so
  the `/ready` endpoint returns the correct status across multiple uvicorn workers.

---

## [0.1.7] — 2026-06-06

### Added

- **Fallback model coverage**: Added `gpt-5.4`, `gpt-4.1-nano`, and `claude-opus-4-6` to the
  hardcoded fallback price table.

### Fixed

- **Fallback prices**: Corrected incorrect values for the GPT-5.5, GPT-5.4, Gemini 3.x, and
  DeepSeek V4 families (verified 2026-06-06).
- **Redundant token count**: Removed a duplicate `count_tokens` call in `/v1/compress` that
  computed the same value twice per request.
- **i18n**: Compression failure warnings are now routed through the i18n layer instead of
  returning raw English strings regardless of the configured language.

### Changed

- **`FEATURED_MODELS`**: Centralized into `core/featured_models.py`, removing duplicate
  definitions that had drifted out of sync in `savings_calculator.py` and `compress_cmd.py`.

---

## [0.1.6] — 2026-06-06

### Fixed

- **Syntax error on startup** (`core/lingua_adapter.py`): A literal newline character had been
  introduced into the `force_tokens=["\n"]` string, causing a `SyntaxError` before the process
  could start.
- **`NameError` on startup** (`config/loader.py`): Missing `from typing import NoReturn` import
  caused a `NameError` when the config validation path was reached.

---

## [0.1.5] — 2026-06-06

### Fixed

- **Hardcoded model default**: `CompressRequest` and `BatchItem` no longer hardcode
  `gpt-4o-mini`; model now falls back to `config.default_model` from `.llmzip.config` when not
  specified in the request.
- **Pricing concurrency** (`pricing/resolver.py`): Added `threading.Lock` with double-checked
  locking to prevent simultaneous LiteLLM fetches under concurrent batch load.
- **Pricing `source` field**: `_meta` in fetcher and resolver now includes an explicit `source`
  field (`"litellm"` or `"fallback"`) instead of inferring it from the note string.
- **`NoReturn` type annotation**: `_fail()` in `config/loader.py` now correctly typed.
- **Tempfile on Windows** (`conversion/file_converter.py`): `convert_bytes()` now closes the
  tempfile before passing its path to MarkItDown, fixing `PermissionError` on Windows.

---

## [0.1.4] — 2026-06-06

### Fixed

- **Missing imports in `lingua_adapter.py`**: `threading.Lock` and `count_tokens` were absent,
  crashing batch compression at runtime under any concurrency.
- **Scorer model path**: `SemanticScorer` now accepts and uses `models_dir`, ensuring the CLI
  and API write the scorer model to the same volume and avoid re-downloading on each startup.
- **Corrupted `compress_file.py`**: Trailing code corrupted by a previous patch was cleaned up.
- **Missing `importlib.metadata` import** (`api/app.py`): The dynamic version call was present
  but the import was absent, causing a `NameError` at startup.
- **`NamedTemporaryFile` fix missing from wheel**: The secure tempfile change from v0.1.1 was
  not included in the published package. Reapplied.

---

## [0.1.3] — 2026-06-06

### Fixed

- **`TypeError` on every compress request**: `POST /v1/compress` called `lingua.compress()`
  without the required `target_model` argument, making the endpoint completely non-functional.
- **Hardcoded version in Swagger UI**: API version now reads dynamically from package metadata
  instead of being hardcoded as `0.1.0`.

---

## [0.1.2] — 2026-06-06

### Fixed

- **Redundant `llmzip-models` service**: Removed the separate models container from the
  default monolith compose file — the single `llmzip-api` container now mounts the models
  volume directly.
- **Model cache paths**: `LinguaAdapter` passes `cache_dir` to `PromptCompressor` and
  `SemanticScorer` passes `cache_folder` to `SentenceTransformer`, forcing all downloads to
  `/app/models`. Models now persist across container restarts without re-downloading.
- **Config filename**: Renamed `llmzip.config.example` to `.llmzip.config.example` to match
  the filename the loader actually expects.

---

## [0.1.1] — 2026-06-06

### Fixed

- **Token count consistency**: `LinguaAdapter` now uses `count_tokens()` for both compression
  ratio and savings calculation. Previously used word-count approximation, producing mismatched
  metrics in the response.
- **Thread safety**: Added `threading.Lock` around `compress_prompt()` to prevent race
  conditions under concurrent batch requests.
- **Pricing resilience**: `resolver.py` now tracks failed fetch attempts with a 30 s cooldown,
  preventing request stampedes when LiteLLM is unreachable. Stale cache is served before
  falling back to hardcoded prices.
- **Secure tempfile**: Replaced deprecated `mktemp()` with `NamedTemporaryFile` in
  `POST /v1/compress/file`.
- **Model default in file compress**: `POST /v1/compress/file` now falls back to
  `config.default_model` when no model is specified.
- **CLI parity**: `_maybe_convert` in the CLI now validates that file conversion produced
  extractable text, matching the API behavior.
- **OpenAI model detection**: Switched to an ordered substring list (most-specific first) to
  fix ambiguous matches between `gpt-4o` and `gpt-4`.

---

## [0.1.0] — 2026-06-05

Initial release.

### Added

- `POST /v1/compress` — compress a single text with LLMLingua-2.
- `POST /v1/compress/batch` — compress up to N texts in parallel (configurable).
- `POST /v1/compress/file` — convert and compress PDF, Word, Excel, and PowerPoint via
  MarkItDown.
- `GET /v1/models` — list supported models with live prices from LiteLLM.
- `GET /health` and `GET /ready`.
- CLI: `llmzip compress`, `llmzip prices`, `llmzip download-models`.
- Preservation score via `paraphrase-multilingual-MiniLM-L12-v2`.
- Token counting — exact via tiktoken for OpenAI models, character-ratio heuristic for others
  (accuracy marked in response).
- Live pricing from LiteLLM with fallback to hardcoded values.
- `.llmzip.config` — INI config validated at startup; service refuses to start with missing
  required values.
- `.llmzipignore` / `.llmzipignore.local` — ignore rules for file patterns.
- Docker — single container with persistent model volume.
- `MIN_TOKENS_TO_COMPRESS` threshold — texts below it are returned as-is with `skipped: true`.
- `FILE_CONVERSION` feature flag.
- Optional rate limiting, disabled by default.
- Configurable batch workers.
