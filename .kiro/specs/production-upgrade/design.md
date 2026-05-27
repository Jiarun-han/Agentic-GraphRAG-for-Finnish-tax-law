# Design: Production Upgrade — 5 Features

## Overview

Transform the hackathon prototype into a production-ready system with: testing, containerization, observability, incremental updates, and user feedback.

---

## 1. Testing (pytest + mock LLM)

### File Structure
```
tests/
├── conftest.py              # Shared fixtures (mock LLM, mock retriever, sample nodes)
├── unit/
│   ├── test_planner.py      # Planner JSON parsing, fallback logic
│   ├── test_clarifier.py    # Clarification detection
│   ├── test_verifier.py     # Audit JSON parsing, claim matching
│   ├── test_retriever.py    # Vector search, keyword search, graph traversal
│   ├── test_evaluate.py     # key_facts_coverage normalization
│   └── test_llm_client.py   # Retry logic, JSON parsing
├── integration/
│   ├── test_pipeline.py     # Full answer() with mocked LLM
│   └── test_api.py          # FastAPI TestClient, /ask and /health
└── fixtures/
    ├── sample_nodes.json    # 50 representative nodes for testing
    └── mock_responses.json  # Canned LLM responses for deterministic tests
```

### Tech Choices
- **pytest** + **pytest-asyncio** for async API tests
- **unittest.mock.patch** to mock `llm_client.llm()` — no real API calls in tests
- **FastAPI TestClient** for API integration tests
- **Coverage target**: 80%+ on agent.py, retriever.py, llm_client.py

### Key Fixtures
```python
@pytest.fixture
def mock_llm(monkeypatch):
    """Replace LLM calls with deterministic responses."""
    responses = json.load(open("tests/fixtures/mock_responses.json"))
    call_count = {"n": 0}
    def fake_llm(system, user, model=None, max_tokens=None):
        idx = call_count["n"] % len(responses)
        call_count["n"] += 1
        return responses[idx]
    monkeypatch.setattr("llm_client._get_client", lambda: None)
    monkeypatch.setattr("llm_client.llm", fake_llm)

@pytest.fixture
def mini_retriever(tmp_path):
    """Retriever with 50 nodes for fast testing."""
    # Build mini embeddings + graph from fixtures/sample_nodes.json
    ...
```

---

## 2. Dockerfile (one-click deploy)

### File Structure
```
Dockerfile                   # Multi-stage: build embeddings model cache + run API
docker-compose.prod.yml      # Full stack: API + frontend + optional Neo4j
.dockerignore
```

### Dockerfile Design
```dockerfile
# Stage 1: Python dependencies + model cache
FROM python:3.10-slim AS base
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Pre-download embedding model into image
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-small')"

# Stage 2: Application
FROM base AS app
COPY . .
# Data files must be mounted or built at runtime
EXPOSE 8000
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.prod.yml
```yaml
services:
  api:
    build: .
    ports: ["8000:8000"]
    env_file: .env
    volumes:
      - ./data:/app/data:ro
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s

  frontend:
    build: ./frontend
    ports: ["8080:8080"]
    depends_on: [api]
```

---

## 3. Request Tracing + Token Counting

### Design
Add a `RequestContext` that flows through the entire pipeline:

```python
# tracing.py
@dataclass
class RequestTrace:
    request_id: str = field(default_factory=lambda: uuid4().hex[:12])
    start_time: float = field(default_factory=time.time)
    llm_calls: list[LLMCall] = field(default_factory=list)
    retrieval_stats: dict = field(default_factory=dict)

@dataclass
class LLMCall:
    agent: str           # "planner", "generator", "auditor", etc.
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    success: bool
```

### Integration Points
- `llm_client.llm()` → records each call into the active trace
- `agent.answer()` → creates trace, passes through, returns it in response
- `api.py` → logs trace summary, adds `X-Request-Id` header
- API response includes `trace` field (optional, enabled via query param `?trace=true`)

### Token Counting
- Use OpenAI response's `usage.prompt_tokens` + `usage.completion_tokens`
- Accumulate per-request total
- Log: `INFO | req-abc123 | 4 LLM calls | 3,200 tokens | 45.2s | confidence=high`

---

## 4. Incremental Update Pipeline

### Design
Instead of rebuilding everything when new regulations are published:

```
scripts/
├── update_corpus.py     # Fetch only new/changed HTML files
├── update_nodes.py      # Parse only new files → append to parsed_nodes.jsonl
├── update_graph.py      # Add new nodes + edges to existing graph
└── update_index.py      # Embed only new nodes → append to embeddings
```

### Data Versioning
```
data/
├── metadata.json        # {"version": "2026-05-27", "node_count": 240191, "embed_model": "e5-small"}
├── changelog.json       # [{"date": "2026-05-28", "added": 150, "removed": 0, "reason": "Vero update"}]
```

### update_index.py Logic
```python
def incremental_embed(new_nodes: list[dict]):
    """Append new embeddings without rebuilding entire index."""
    existing = np.load(EMBED_FILE)["matrix"]
    existing_ids = json.load(open(INDEX_FILE))

    new_vecs = model.encode([...])
    combined = np.vstack([existing, new_vecs])
    combined_ids = existing_ids + [n["id"] for n in new_nodes]

    np.savez_compressed(EMBED_FILE, matrix=combined)
    json.dump(combined_ids, open(INDEX_FILE, "w"))
```

---

## 5. User Feedback Mechanism

### API Endpoints
```
POST /feedback
{
  "request_id": "abc123",
  "rating": "correct" | "partially_correct" | "wrong",
  "correction": "The actual rate is 25%, not 32%",  // optional
  "missing_info": "Should mention the 84-month validity"  // optional
}

GET /feedback/stats
→ {"total": 150, "correct": 95, "partial": 30, "wrong": 25, "accuracy": 63%}
```

### Storage
```
data/feedback/
├── feedback.jsonl       # Append-only log of all feedback
└── corrections.json     # Curated corrections for fine-tuning prompts
```

### Feedback Loop (future)
1. Collect feedback → `feedback.jsonl`
2. Weekly: analyze wrong answers → identify retrieval gaps
3. Add missing documents to corpus or adjust Planner few-shots
4. Re-evaluate on question bank to measure improvement

### Frontend Integration
After each answer, show thumbs up/down buttons:
```tsx
<FeedbackButtons requestId={data.request_id} />
```

---

## Implementation Order

| Phase | Feature | Depends On | Effort |
|-------|---------|-----------|--------|
| 1 | Testing | Nothing | 3-4 hours |
| 2 | Tracing + Token counting | Nothing | 2 hours |
| 3 | Dockerfile | Testing (for CI) | 1-2 hours |
| 4 | User Feedback | Tracing (request_id) | 2-3 hours |
| 5 | Incremental Updates | Nothing | 3-4 hours |

**Total: ~12-15 hours of work**

---

## Config Additions (.env)

```env
# Tracing
TRACE_ENABLED=true
LOG_LEVEL=INFO

# Feedback
FEEDBACK_DIR=data/feedback

# Docker
API_WORKERS=2
```
