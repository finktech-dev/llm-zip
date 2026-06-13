FROM python:3.11-alpine AS builder

RUN apk add --no-cache \
    build-base \
    libffi-dev \
    libmagic \
    libxml2-dev \
    libxslt-dev

WORKDIR /build

COPY requirements.api.txt .
RUN pip install --no-cache-dir -r requirements.api.txt

COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir .

FROM python:3.11-alpine AS runtime

RUN apk add --no-cache libmagic

RUN addgroup -S llmzip && adduser -S -G llmzip llmzip

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

ENV TIKTOKEN_CACHE_DIR=/app/.tiktoken_cache
RUN mkdir -p /app/.tiktoken_cache /app/logs && chown -R llmzip:llmzip /app/.tiktoken_cache /app/logs
RUN python -c "import tiktoken; [tiktoken.get_encoding(e) for e in ('cl100k_base', 'o200k_base')]"

COPY --chown=llmzip:llmzip . .

USER llmzip

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV MODELS_DIR=/app/models

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/ready')"

CMD ["uvicorn", "llmzip.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
