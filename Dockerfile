# Multi-stage Dockerfile for Taxxa GraphRAG API
# Stage 1: Install dependencies + cache embedding model
FROM python:3.10-slim AS base

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download embedding model into image (avoids download at runtime)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-small')"

# Stage 2: Application
FROM base AS app

WORKDIR /app
COPY config.py llm_client.py tracing.py agent.py retriever.py api.py evaluate.py ./
COPY build_graph.py build_quick_index.py parse_corpus.py ./
COPY scripts/ ./scripts/

# Data directory (mount at runtime)
RUN mkdir -p data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
