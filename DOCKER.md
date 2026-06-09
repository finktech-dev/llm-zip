# Docker Deployment — llm-zip

llm-zip supports two deployment modes: **monolith** (single container, simplest setup) and **split** (two separate containers, for production with horizontal scaling). This document covers both in detail.

---

## Table of Contents

1. [Requirements](#requirements)
2. [Initial Setup](#initial-setup)
3. [Monolith Mode](#monolith-mode)
4. [Split Mode](#split-mode)
5. [Environment Variables](#environment-variables)
6. [All Configuration Options](#all-configuration-options)
7. [Logs](#logs)
8. [Troubleshooting](#troubleshooting)
9. [Kubernetes](#kubernetes-v030)

---

## Requirements

- Docker 24.0+
- Docker Compose 2.20+
- **Minimum RAM:** 4 GB (for `bert-base`) / 8 GB (for `xlm-roberta-large`)
- **Disk space:** ~3 GB free for model weights

---

## Initial Setup

Before starting either mode, create your config file:

```bash
cp .llmzip.config.example .llmzip.config
```

The only **required** field is `MAX_TOKENS` under `[server]`. The server will not start without it. Edit the file and set a value appropriate for your hardware:

```ini
[server]
MAX_TOKENS=100000    # maximum tokens accepted per request
```

All other fields have sensible defaults in the `.example` file.

---

## Monolith Mode

A single container handles everything: loads LLMLingua-2 and the SemanticScorer, and serves the API on port 8000.

```
┌─────────────────────────────────────────┐
│              llmzip-api                 │
│                                         │
│  FastAPI  →  port 8000 (public)         │
│  LLMLingua-2  (in-process)              │
│  SemanticScorer  (in-process)           │
└──────────────────┬──────────────────────┘
                   │
            llmzip_models (Docker volume)
            ~700 MB, persists across restarts
```

**When to use:** local development, single-server deployments, environments where horizontal scaling is not needed.

### Start

```bash
docker compose up -d
```

### Stream logs

```bash
docker compose logs -f
```

### Wait for models to load

Models take **2–5 minutes** on the first run (download + load). Subsequent starts take ~30–60 seconds (load from volume).

```bash
# Poll until ready
watch -n 5 'curl -s http://localhost:8000/health/ready | python -m json.tool'

# Response when ready (HTTP 200):
# {
#     "status": "ok",
#     "models_loaded": true,
#     "deploy_mode": "monolith"
# }

# Response while loading (HTTP 503):
# {
#     "detail": "Models loading"
# }
```

### First request

```bash
curl -s -X POST http://localhost:8000/v1/compress \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Your very long text here that you want to compress before sending to an LLM...",
    "ratio": 0.5,
    "model": "gpt-4o-mini"
  }' | python -m json.tool
```

### Custom port

```bash
LLMZIP_PORT=9000 docker compose up -d
```

### Stop

```bash
# Stop containers (keeps model cache)
docker compose down

# Stop and delete model cache (forces re-download on next start)
docker compose down -v
```

---

## Split Mode

Two separate containers: `llmzip-models` handles ML inference, `llmzip-api` handles HTTP. The API is stateless and can scale horizontally without duplicating the ~700 MB model weights in each instance.

```
                     ┌──────────────────────────────┐
  Client  ─────────▶ │         llmzip-api           │
                     │  FastAPI → port 8000          │
                     │  stateless, horizontally      │
                     │  scalable                     │
                     │  Dockerfile.api (~200 MB)     │
                     └──────────────┬───────────────┘
                                    │ internal HTTP
                                    │ http://llmzip-models:8001
                     ┌──────────────▼───────────────┐
                     │       llmzip-models           │
                     │  Inference server → 8001      │
                     │  LLMLingua-2                  │
                     │  SemanticScorer               │
                     │  Dockerfile.models (~3 GB)    │
                     └──────────────┬───────────────┘
                                    │
                             llmzip_models (volume)
                             ~700 MB, shared
```

**When to use:** production with multiple API replicas, behind a load balancer, or when you want to separate ML compute cost from HTTP serving cost.

### Differences from monolith mode

|               | Monolith                          | Split                                             |
| :------------ | :-------------------------------- | :------------------------------------------------ |
| Compose file  | `docker-compose.yml`              | `docker-compose.split.yml`                        |
| Containers    | 1                                 | 2                                                 |
| API image     | `Dockerfile` (~3 GB with ML deps) | `Dockerfile.api` (~200 MB, no ML)                 |
| Models image  | —                                 | `Dockerfile.models` (~3 GB)                       |
| API scaling   | No (carries models with it)       | Yes (`--scale llmzip-api=N`)                      |
| `DEPLOY_MODE` | `monolith`                        | `split` (set automatically by the compose file)   |

### Start

```bash
docker compose -f docker-compose.split.yml up -d
```

### Startup sequence

Split mode has a defined startup sequence:

1. `llmzip-models` starts and begins loading LLMLingua-2 (~2–5 min)
2. Docker polls `http://localhost:8001/ready` every 15 seconds
3. Once `llmzip-models` passes its healthcheck, Docker starts `llmzip-api`
4. `llmzip-api` also polls `http://llmzip-models:8001/ready` internally (up to 5 minutes, 60 attempts × 5 seconds)
5. Once models are ready, `llmzip-api` returns `200` on `/health/ready`

This is fully automatic — no manual intervention needed.

```bash
# Watch the full startup process
docker compose -f docker-compose.split.yml logs -f
```

### Scale the API horizontally

```bash
# 3 API replicas, single model server
docker compose -f docker-compose.split.yml up -d --scale llmzip-api=3
```

> **Known limitation:** rate limiting counters are in-memory per process. With 3 replicas and `REQUESTS_PER_MINUTE=60`, the effective limit is 180 req/min (60 × 3). See [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md).

### Check service health

```bash
# Overall status
docker compose -f docker-compose.split.yml ps

# Models service healthcheck (internal port, accessible from host)
curl -s http://localhost:8001/health/ready | python -m json.tool

# API healthcheck (public port)
curl -s http://localhost:8000/health/ready | python -m json.tool
```

### Stop

```bash
docker compose -f docker-compose.split.yml down
```

---

## Environment Variables

These can be set in a `.env` file in the project root or passed directly to `docker compose`.

| Variable | Default | Description |
|---|---|---|
| `LLMZIP_PORT` | `8000` | Host port mapped to the API container |
| `COMPRESSION_MODEL` | `bert-base` | Compression model. Options: `bert-base`, `xlm-roberta-large` |
| `SCORER_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | Embeddings model for preservation score |
| `SCORER_TIMEOUT` | `30` | Seconds before scorer returns `null` instead of blocking |
| `MODELS_URL` | `http://llmzip-models:8001` | *(Split mode only)* URL of the models service |
| `DEPLOY_MODE` | `monolith` | `monolith` or `split`. Split compose sets this automatically. |
| `LOG_LEVEL` | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_FILE` | `logs/llmzip.log` | Path for the rotating JSON log file |
| `LOG_JSON` | `false` | Set `true` to disable colored stderr output |

### Example `.env` file

```env
LLMZIP_PORT=8000
COMPRESSION_MODEL=bert-base
SCORER_TIMEOUT=30
LOG_LEVEL=INFO
```

---

## All Configuration Options

The `.llmzip.config` file is mounted read-only into the API container. The models service reads its parameters from environment variables.

```ini
[server]
; REQUIRED — maximum tokens per request. Tune to your hardware.
MAX_TOKENS=100000

; Maximum file size for /v1/compress/file (in MB). Default: 50
MAX_FILE_SIZE_MB=50

; Texts with fewer tokens than this are returned as-is (skipped=true)
MIN_TOKENS_TO_COMPRESS=500

; Internal server port (host port is controlled by LLMZIP_PORT env var)
PORT=8000

; Optional API key to protect all /v1/* endpoints
; Format: Authorization: Bearer <your-key>
; Leave empty to disable authentication.
API_KEY=

; Deployment mode: monolith (default) or split
; In split mode, the API delegates inference to llmzip-models via MODELS_URL
DEPLOY_MODE=monolith

; URL of the models service (only used when DEPLOY_MODE=split)
MODELS_URL=http://llmzip-models:8001

[compression]
; Default compression ratio — 0.1 (aggressive) to 0.9 (light)
DEFAULT_RATIO=0.5

; Model used for savings estimation in responses
; Options: gpt-4o-mini, claude-haiku-4-5, gemini-2.5-flash-lite, deepseek-v4-flash
DEFAULT_MODEL=gpt-4o-mini

; Maximum number of texts per /v1/compress/batch request
MAX_BATCH_SIZE=25

; Parallel workers for batch processing
BATCH_WORKERS=4

; Compression model — bert-base uses ~4 GB RAM, xlm-roberta-large uses ~8 GB
COMPRESSION_MODEL=bert-base

; Chunk size in tokens for long texts
CHUNK_SIZE=400

; Embeddings model for preservation score calculation
SCORER_MODEL=paraphrase-multilingual-MiniLM-L12-v2

; Scorer timeout in seconds. 0 = no timeout.
SCORER_TIMEOUT=30

[pricing]
; Seconds between LiteLLM price refreshes (0 = always fetch)
CACHE_TTL=3600

[rate_limit]
; Enable rate limiting (disabled by default)
ENABLED=false
REQUESTS_PER_MINUTE=60
REQUESTS_PER_DAY=10000

[features]
; Enables file compression (PDF, Word, Excel, PowerPoint) via MarkItDown
; Adds ~200 MB of dependencies
FILE_CONVERSION=true
```

---

## Logs

llm-zip writes logs to two destinations simultaneously:

**1. Stderr (console)** — colored, human-readable format for development:
```
[2026-06-08 15:32:01] INFO  llmzip.api.routes.compress  compress ok
[2026-06-08 15:32:05] WARNING  llmzip.core.semantic_scorer  scorer timeout after 30s
```

**2. Rotating file** — JSON Lines format for production parsing and log aggregators (Datadog, Loki, CloudWatch):
```json
{"ts":"2026-06-08T15:32:01.123Z","level":"INFO","logger":"llmzip.api.routes.compress","event":"compress_ok","tokens_in":1200,"tokens_out":580,"ratio":0.483,"model":"gpt-4o-mini","elapsed_ms":1234,"skipped":false}
{"ts":"2026-06-08T15:32:05.456Z","level":"WARNING","logger":"llmzip.core.semantic_scorer","event":"scorer_timeout","timeout_s":30}
```

The log file rotates at 10 MB, keeping up to 5 files (50 MB total).

### View container logs

```bash
# Monolith
docker compose logs -f llmzip-api

# Split — both services
docker compose -f docker-compose.split.yml logs -f

# Split — models service only
docker compose -f docker-compose.split.yml logs -f llmzip-models
```

### Tail the JSON log file from inside the container

```bash
docker exec llmzip-api tail -f logs/llmzip.log
```

### Disable colors (for CI/CD environments)

```bash
LOG_JSON=true docker compose up -d
```

---

## Troubleshooting

### `/health/ready` returns 503 and never changes

Models are still loading. This is normal on first run or after deleting the volume. Wait 2–5 minutes and keep polling:

```bash
watch -n 10 'curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health/ready'
# You expect to see: 503 503 503 ... 200
```

If still 503 after 10 minutes, check the logs:

```bash
docker compose logs llmzip-api | grep -E "ERROR|CRITICAL"
```

### Models re-download on every `docker compose up`

The `llmzip_models` volume was deleted. Always use `docker compose down` without the `-v` flag:

```bash
# Correct — preserves the volume
docker compose down

# Wrong — deletes the volume and forces re-download
docker compose down -v
```

Verify the volume exists:

```bash
docker volume ls | grep llmzip
# → local     llmzip_llmzip_models
```

### `llmzip-api` never starts in split mode

The API waits for `llmzip-models` to pass its healthcheck before starting. If `llmzip-models` never becomes healthy, the API will not start. Check the models service logs:

```bash
docker compose -f docker-compose.split.yml logs llmzip-models
```

Common causes:
- **OOM killed** — not enough RAM. Switch to `bert-base` instead of `xlm-roberta-large`.
- **Permission denied on `/app/models`** — volume ownership issue (see below).

### Volume permission error (Linux)

```bash
docker compose run --rm llmzip-models chown -R 1000:1000 /app/models
```

### Port 8000 already in use

```bash
# Use a different port
LLMZIP_PORT=9001 docker compose up -d

# Find what's using the port
lsof -i :8000          # macOS / Linux
netstat -ano | findstr :8000   # Windows
```

### All requests return 401

`API_KEY` is set in your `.llmzip.config`. Add the header to your requests:

```bash
curl -X POST http://localhost:8000/v1/compress \
  -H "Authorization: Bearer your-key-here" \
  -H "Content-Type: application/json" \
  -d '{"text": "...", "ratio": 0.5}'
```

To check whether auth is enabled without exposing the key:

```bash
curl -s http://localhost:8000/v1/info | python -m json.tool
# Look for: "auth_enabled": true
```

### Unexpected 429 errors with multiple API replicas

Each `llmzip-api` replica has its own in-memory rate limit counter. With 3 replicas and `REQUESTS_PER_MINUTE=60`, the effective limit is 180 req/min (60 × 3). This is a known limitation. See [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md).

### OOM killed

LLMLingua-2 with `bert-base` requires ~4 GB of available RAM. With `xlm-roberta-large` it's ~8 GB.

```ini
# .llmzip.config — use the lighter model
[compression]
COMPRESSION_MODEL=bert-base
```

If Docker Desktop has a memory limit configured, increase it in Preferences → Resources → Memory.

---

## Kubernetes (v0.3.0+)

Full Kubernetes support is planned for v0.3.0. The split architecture maps directly to a Kubernetes deployment:

- `llmzip-models` → `StatefulSet` with 1 replica + `PersistentVolumeClaim` for model weights
- `llmzip-api` → `Deployment` that scales horizontally, no persistent storage needed

In v0.2.x, health checks can be configured as follows while official Kubernetes support is pending:

```yaml
# llmzip-api Deployment
containers:
  - name: llmzip-api
    livenessProbe:
      httpGet:
        path: /health/live    # Always 200 if the process is running
        port: 8000
      initialDelaySeconds: 10
      periodSeconds: 10
      failureThreshold: 3

    readinessProbe:
      httpGet:
        path: /health/ready   # 200 only when models are loaded, 503 otherwise
        port: 8000
      initialDelaySeconds: 30
      periodSeconds: 15
      failureThreshold: 10    # 10 × 15s = 2.5 min tolerance

# llmzip-models StatefulSet
containers:
  - name: llmzip-models
    livenessProbe:
      httpGet:
        path: /health/live
        port: 8001
      initialDelaySeconds: 10
      periodSeconds: 10

    readinessProbe:
      httpGet:
        path: /health/ready
        port: 8001
      initialDelaySeconds: 60    # Models take longer on first start
      periodSeconds: 15
      failureThreshold: 20       # 20 × 15s = 5 minutes of tolerance
```

ConfigMap for the configuration file:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: llmzip-config
data:
  .llmzip.config: |
    [server]
    MAX_TOKENS=100000
    DEPLOY_MODE=split
    MODELS_URL=http://llmzip-models-svc:8001

    [compression]
    DEFAULT_MODEL=gpt-4o-mini
    COMPRESSION_MODEL=bert-base
```
