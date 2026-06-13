# Known Limitations — llm-zip

This document lists known limitations of the current release, their impact, and the planned resolution where applicable.

---

## Rate Limiting — In-Memory Counters (v0.2.x)

**What it means:** The rate limiter (`slowapi`) stores request counters in each process's memory. With a single container (monolith mode or a single `llmzip-api` replica), this works exactly as configured.

**When it becomes a problem:** If you run multiple `llmzip-api` replicas behind a load balancer, each replica maintains its own independent counter. With `REQUESTS_PER_MINUTE=60` and 3 replicas, the effective limit is 180 req/min (60 × 3), not 60.

**Workaround:** Set `REQUESTS_PER_MINUTE` to `target_rpm / number_of_replicas`. For 3 replicas and a desired limit of 60 req/min, set `REQUESTS_PER_MINUTE=20`.

**Planned fix:** Redis-backed shared counters in a future release. Not scheduled for v0.3.0.

---

## Metrics — In-Memory, Not Persistent (v0.3.0+)

**What it means:** The `/v1/status` endpoint (planned for v0.3.0) will store metrics (total requests, tokens compressed, savings) in each process's memory.

**When it becomes a problem:** Metrics reset on every container restart. With multiple replicas, each replica reports its own independent counters.

**Workaround:** Use the structured JSON logs in `logs/llmzip.log` for persistent metric aggregation. Each compression event is logged with `tokens_in`, `tokens_out`, `elapsed_ms`, and other fields that can be aggregated by any log pipeline (Datadog, Loki, CloudWatch, etc.).

**Planned fix:** Persistent metrics storage is not currently scheduled. The log-based approach is the recommended production solution.

---

## Model Loading — Single Instance, No Redundancy (all versions)

**What it means:** In split mode, `llmzip-models` is a single instance. There is no failover. If the models container crashes, all inference requests fail until it recovers.

**When it becomes a problem:** High-availability deployments where downtime for model restarts is not acceptable.

**Workaround:** Use Docker's `restart: unless-stopped` policy (already set in the provided compose files) to automatically restart the container on failure. In Kubernetes, the `StatefulSet` restarts the pod automatically.

**Planned fix:** Model server redundancy is not currently scheduled.

---

## File Conversion — No Progress Feedback for Large Files (all versions)

**What it means:** `POST /v1/compress/file` reads and converts the entire file before responding. For large PDFs or Word documents, the request can take 30–60 seconds with no intermediate feedback.

**When it becomes a problem:** HTTP clients with short timeout settings, or UIs that need progress indication.

**Workaround:** Increase your HTTP client timeout. For files larger than a few MB, consider using `/v1/compress/batch/async` (planned for v0.3.0) which returns a `job_id` immediately and allows polling for results.

**Planned fix:** Streaming response for `/v1/compress/file` is on the v0.4.0 roadmap.

---

## Batch Async Jobs — Not Persistent (v0.3.0+)

**What it means:** When `/v1/compress/batch/async` is implemented in v0.3.0, job state will be stored in memory with a configurable TTL. Jobs are lost if the container restarts.

**When it becomes a problem:** Long-running jobs that outlive a container restart or deployment.

**Workaround:** Resubmit the job after a restart. Keep job TTL (`JOB_TTL_SECONDS`) short enough that stale jobs don't accumulate.

**Planned fix:** Persistent job storage is not currently scheduled.

---

## Audio / Video Support — Not Available (all versions)

**What it means:** `.mp3`, `.wav`, and video files are not supported by `/v1/compress/file`. MarkItDown supports audio transcription via an optional extra (`markitdown[audio-transcription]`), but llm-zip does not expose this yet.

**When it becomes a problem:** Workflows that need to compress meeting transcriptions or podcast content before sending to an LLM.

**Planned fix:** Optional audio support via `pip install llm-zip[audio]` is planned for v0.5.0, or earlier if there is user demand or a community contribution.

---

## `/v1/estimate` vs compression floor (all versions)

**What it means:** The estimate endpoint calculates `estimated_compression_ratio` as a linear function of the requested ratio (`1 / ratio`). For example, `ratio=0.9` results in `1.11x`.

**When it becomes a problem:** In practice, LLMLingua-2 plateaus at approximately 2x compression regardless of the requested ratio on very dense or already concise documents. Users might be surprised if `/v1/estimate` suggests a lower ratio than what is physically achievable by the model.

**Workaround:** Treat the output of `/v1/estimate` as a theoretical upper bound for savings calculations, not as a guaranteed physical result of the compression process.


