# Contributing to llm-zip

llm-zip started as an internal tool to reduce inference costs in private RAG systems. It's open source because the problem is universal — if you're using LLMs at scale, you're paying for tokens you don't need.

---

## Honesty about the numbers

Savings estimates for some models are based on published pricing and token counting approximations — not internal production benchmarks. Where this is the case, it's marked in the code and flagged with a warning in the CLI output.

If you run llm-zip in production and have real numbers, that's exactly what this project needs.

---

## What we need most

- **Benchmark results** — real numbers from real workloads. Language, domain, model, ratio, preservation score, hardware. Submit via PR to the benchmarks table in the README.
- **Pricing corrections** — if a price in `llmzip/pricing/fallback.py` is wrong, fix it and update `PRICES_LAST_UPDATED`.
- **Bug reports** — open an issue with a minimal reproduction.
- **Non-English language results** — especially Spanish, Portuguese, and other languages where LLMLingua-2 behavior is less documented.

---

## Setup

```bash
git clone https://github.com/FinkTech/llm-zip.git
cd llm-zip
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .llmzip.config.example .llmzip.config
pytest
```

---

## Before opening a PR

- `pytest` passes
- `ruff check .` clean
- `mypy llmzip` clean
- One thing per PR

---

## Code rules

See [AGENTS.md](AGENTS.md). Short version: strict types, no `Any`, no `print()`, no bare `except:`, one responsibility per file, `core/` never imports from `api/` or `cli/`.

---

## What won't be merged

- Anything that calls an external AI API
- User authentication or API key management
- A database, a web UI, or a dashboard
- Anything that stores or logs request content

---

## License

By contributing you agree your work will be licensed under MIT.
