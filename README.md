# 🗜️ llm-zip

<p align="center">
  <a href="https://github.com/FinkTech/llm-zip/releases"><img src="https://img.shields.io/badge/version-0.1.0-blue?style=for-the-badge" alt="Version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/API-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"></a>
  <a href="https://www.docker.com/"><img src="https://img.shields.io/badge/Docker-ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker"></a>
</p>

<p align="center">
  <a href="https://github.com/microsoft/LLMLingua"><img src="https://img.shields.io/badge/Powered_by-LLMLingua--2-FF6F00?style=flat-square" alt="LLMLingua-2"></a>
  <a href="https://github.com/microsoft/markitdown"><img src="https://img.shields.io/badge/Files_via-MarkItDown-0078D4?style=flat-square&logo=microsoft&logoColor=white" alt="MarkItDown"></a>
  <a href="https://github.com/BerriAI/litellm"><img src="https://img.shields.io/badge/Pricing-LiteLLM-7C3AED?style=flat-square" alt="LiteLLM"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json&style=flat-square" alt="Ruff"></a>
</p>

<p align="center">
  <strong>Context compression sidecar for LLM applications.<br>Reduce token costs 3–5× before calling any AI API.</strong>
</p>

<p align="center">
  <a href="#why-llm-zip-exists">Why</a> ·
  <a href="#how-it-works">How it works</a> ·
  <a href="#quickstart">Quickstart</a> ·
  <a href="#the-cli-experience">CLI</a> ·
  <a href="#what-you-get-back">API response</a> ·
  <a href="#markitdown-integration">File support</a> ·
  <a href="#-the-science--benchmarks">Benchmarks</a> ·
  <a href="#limitations--caveats">Limitations</a> ·
  <a href="#contributing">Contributing</a>
</p>

---

## Why llm-zip exists

AI inference is getting expensive. As context windows grow and agentic workflows multiply, the tokens you send to GPT, Claude, or Gemini compound fast — and the "free ride" subsidy era is ending.

llm-zip was built out of a simple need: compress context before it reaches the model, without changing anything else in the stack. No proxy. No middleware. No API keys. Just a sidecar you call over HTTP, that hands back a smaller text and tells you exactly how much you saved.

It started as an internal tool for large-scale RAG pipelines. It's open source because the problem is universal.

---

## How it works

```text
Your app  ──→  POST /v1/compress  ──→  llm-zip
                                           │
                              compresses with LLMLingua-2
                              scores semantic preservation
                              calculates USD savings
                                           │
              compressed text + metrics  ◄─┘

Your app  ──→  calls OpenAI / Anthropic / Gemini
               with the smaller context
```

llm-zip never touches your API keys or your model calls. It only compresses.

---

## Quickstart

> **Requires Docker.** First-time model download is ~700MB and takes 2–5 min.

**Step 1 — Configure**
```bash
cp .llmzip.config.example .llmzip.config
nano .llmzip.config
```

**Step 2 — Download models** *(only on first run)*
```bash
docker-compose run llmzip download-models
```

**Step 3 — Start**
```bash
docker-compose up -d
```

→ API: `http://localhost:8000` · Docs: `http://localhost:8000/docs`

---

## The CLI Experience

llm-zip isn't just an API — it comes with a UNIX-friendly CLI powered by Typer and Rich. It supports `stdin` pipes, outputs clean JSON, and tracks live model prices.

```bash
# Check current prices (fetches live from LiteLLM)
$ llmzip prices -p anthropic

Rates from LiteLLM as of 2026-06-05
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Model                                     ┃ Input $/M ┃ Output $/M ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ anthropic.claude-3-5-sonnet-20241022-v2:0 │    3.0000 │    15.0000 │
│ anthropic.claude-3-haiku-20240307-v1:0    │    0.2500 │     1.2500 │
└───────────────────────────────────────────┴───────────┴────────────┘
```

> Model names come directly from LiteLLM and may use provider-specific naming (e.g. Bedrock-style). The exact list depends on live data at execution time.

```bash
# Compress directly from the terminal via pipes
$ cat huge_context.txt | llmzip compress --ratio 0.4 --model gpt-4o-mini > compressed.txt
✓ 24000 → 9600 tokens (2.5×) | score: 0.92 | saved: ~$0.0021 (gpt-4o-mini)
```

---

## What you get back

```json
{
  "compressed": "...",
  "original_tokens": 8400,
  "compressed_tokens": 1680,
  "compression_ratio": 5.0,
  "preservation_score": 0.91,
  "estimated_savings": {
    "gpt-4o-mini":           "$0.0010",
    "claude-haiku-4-5":      "$0.0013",
    "gemini-2.5-flash-lite": "$0.0006"
  },
  "skipped": false,
  "warning": null
}
```

Prices are fetched live from [LiteLLM](https://github.com/BerriAI/litellm) with local caching — no manual database updates needed.

---

## MarkItDown Integration

One of the practical problems that motivated llm-zip was RAG over internal documents. In private systems — invoices, reports, manuals, internal specs — the source content lives in PDFs, Word files, and spreadsheets.

llm-zip integrates [MarkItDown](https://github.com/microsoft/markitdown) as an optional preprocessing layer. When `FILE_CONVERSION=true`, you can send a file directly to `/v1/compress/file` and get back compressed text ready for your RAG pipeline.

```bash
curl -X POST http://localhost:8000/v1/compress/file \
  -F "file=@invoice.pdf" \
  -F "ratio=0.5"
```

Supported formats: PDF, Word (`.docx`), Excel (`.xlsx`), PowerPoint (`.pptx`), and more.

---

## Key Features

| | Feature | Detail |
|---|---|---|
| 📄 | **Text and files** | Compress plain text or upload PDFs, Word, Excel, and PowerPoint directly |
| 🖥️ | **CPU-Friendly** | Default model requires only ~700MB of RAM — no GPU needed |
| 🌐 | **Global i18n** | CLI in English, Spanish, Portuguese, Chinese, and Japanese |
| ⚙️ | **Configurable thresholds** | Define when llm-zip should and shouldn't intervene (`MIN_TOKENS_TO_COMPRESS`) |
| 🚫 | **Ignore rules** | Exclude texts or system prompts via `.llmzipignore` and `.llmzipignore.local` |
| 🔒 | **Self-hosted** | Your data never leaves your infrastructure |

---

## Environment Variables

For CI or Docker deployments, you can override defaults with environment variables:

| Variable | Description |
|---|---|
| `LLMZIP_LANG` | Forces CLI language (`en`, `es`, `pt`, `zh`, `ja`). Overrides system locale. |
| `MODELS_URL` | Overrides internal DNS for the models container. Defaults to `http://llmzip-models:8001`. |

---

## 📊 The Science & Benchmarks

llm-zip is powered by Microsoft's LLMLingua-2. According to their [research paper evaluated on the LongBench dataset](https://arxiv.org/abs/2403.12968):

- **Compression sweet spot:** optimal performance between **2× and 5× compression**
- **Quality retention:** **90–98% Exact Match performance** vs. uncompressed prompts
- **Latency reduction:** end-to-end latency improvement of **1.6× to 2.9×** (task-agnostic, no prompt needed to start)

<details>
<summary>📋 Hardware benchmarks (click to expand)</summary>

> Community-maintained — submit your real-world results via PR.

| Hardware                     | Model     | Input Tokens | Time to Compress |
| :--------------------------- | :-------- | :----------- | :--------------- |
| Standard CPU (AWS t3.medium) | bert-base | 15,000       | ~1.2s            |
| M-Series Mac (M2 Pro)        | bert-base | 30,000       | ~0.8s            |

</details>

<details>
<summary>📋 Use-case benchmarks (click to expand)</summary>

> Community-maintained — submit your real-world results via PR.

| Use case               | Tokens in | Tokens out | Ratio | Preservation | Est. saving (gpt-4o-mini) |
| :--------------------- | :-------- | :--------- | :---- | :----------- | :------------------------ |
| News article (EN)      | 2,400     | 720        | 3.3×  | 0.93         | $0.00026                  |
| Technical docs (EN)    | 8,400     | 1,680      | 5.0×  | 0.89         | $0.00101                  |
| RAG context (ES)       | 12,000    | 3,600      | 3.3×  | 0.91         | $0.00126                  |
| Long chat history (EN) | 6,000     | 1,200      | 5.0×  | 0.88         | $0.00068                  |

</details>

---

## Limitations & Caveats

- **Language support** — LLMLingua-2 was trained on English meeting transcripts. Spanish and other languages work but may see 10–15% lower compression quality. Community benchmarks are welcome.
- **Extractive compression** — tokens are removed, not rewritten. Some nuance may be lost at aggressive ratios (above 0.7).
- **Pricing accuracy** — savings are *estimates*. Non-OpenAI tokenizers use a character-ratio heuristic with a ±10% margin of error.
- **Format loss** — file conversion extracts plain text only. Layout, tables, and complex formatting are not preserved.
- **Production testing** — this is v0.1.0. Concurrent batch processing should be monitored closely in high-throughput environments.

---

## Contributing

The most valuable contributions right now are benchmark results across different languages, domains, and models. If you use llm-zip in a real project, a PR with your numbers helps everyone calibrate expectations.

Bug reports, feature requests, and code contributions are also welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

```bash
git clone https://github.com/FinkTech/llm-zip.git
cd llm-zip
pip install -e ".[dev]"
pytest
```

---

## License & Disclaimer

MIT © [Ariel A. Fink](https://github.com/FinkTech)

Built utilizing [LLMLingua-2](https://github.com/microsoft/LLMLingua) and [MarkItDown](https://github.com/microsoft/markitdown) open-source libraries.

*This project is an independent, community-driven open-source tool. It is not affiliated with, endorsed by, or sponsored by Microsoft Corporation, OpenAI, Anthropic, or any other LLM provider. All trademarks and registered trademarks are the property of their respective owners.*
