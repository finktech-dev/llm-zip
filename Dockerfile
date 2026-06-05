FROM python:3.11-slim

# system deps for LLMLingua-2, sentence-transformers, MarkItDown
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN pip install --no-cache-dir -e .

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV MODELS_DIR=/app/models

EXPOSE 8000

CMD ["uvicorn", "llmzip.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
