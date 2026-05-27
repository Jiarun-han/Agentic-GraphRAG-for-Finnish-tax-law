# Taxxa GraphRAG

**Agentic GraphRAG for Finnish Tax Law Research**

A production-ready multi-agent system that answers Finnish tax law questions with verifiable citations. Built on a typed knowledge graph over 994K legal nodes from Finlex and Verohallinto, with 6 specialized AI agents that retrieve, reason, verify, and cite.

> Built at Prompt Finance Hackathon 2026 · Aalto University × Taxxa AI

---

## Results

Evaluated on 83 graded questions from the Taxxa QA bank:

| Metric | Score |
|--------|-------|
| Key Facts Coverage | **95%** |
| Citation Rate | **100%** |
| Answer Rate | **100%** |

Every answer includes traceable source references (document + section + URL).

---

## How It Works

```
User Question
     │
     ├── ① Clarifier ─── Detects missing context (tax year, entity type, jurisdiction)
     │                    Adds explicit assumptions
     │
     ├── ② Planner ───── Decomposes into 2-4 Finnish sub-queries
     │                    Uses few-shot examples + translation table
     │
     ├── ③ Retriever ─── GraphRAG: Vector + Keyword + Graph Traversal + LLM Rerank
     │     │
     │     ├── Vector Search (multilingual-e5-small, 240K embedded nodes)
     │     ├── Keyword Fallback (exact Finnish term matching)
     │     ├── Typed Graph Traversal (2-hop, follows interprets/amends/cites edges)
     │     └── LLM Reranker (multilingual, no English-only bottleneck)
     │
     ├── ④ Generator ─── Drafts concise answer with inline [source_id] citations
     │
     ├── ⑤ Auditor ───── Verifies facts + logic + completeness + temporal validity
     │                    Triggers retry if claims are unverified
     │
     └── ⑥ Confidence ── Scores reliability (high/medium/low)
                          Adds caveat if uncertain instead of hallucinating
```

---

## The Problem We Solve

Naive RAG breaks on regulatory text:

| Problem | Our Solution |
|---------|-------------|
| **Chunking destroys structure** | Section-aware parsing — respects headings, sections, paragraphs |
| **Can't tell old from new** | `amends`/`repeals` graph edges + temporal validity checking |
| **Cross-references not followed** | Typed graph traversal walks `interprets`/`cites` edges |
| **Multi-hop gets one-hop answers** | Planner decomposes + 2-hop graph walk + retry loop |

---

## Knowledge Graph

| Stat | Value |
|------|-------|
| Total nodes | 994,000 |
| Total edges | 957,000 |
| Embedded nodes | 240,000 |
| Edge types | 7 |

**Edge types and their purpose:**

| Edge | Meaning | Retrieval Use |
|------|---------|---------------|
| `interprets` | Vero guidance → Finlex statute | Find the law behind a guidance |
| `cites` | KHO case law → statute | Find judicial interpretation |
| `amends` | Amendment → original rule | Find the latest version |
| `repeals` | Repeal → repealed statute | Check if rule is still valid |
| `shared_ref` | Same § discussed elsewhere | Enable multi-hop reasoning |
| `references` | Finlex → Finlex cross-ref | Follow explicit citations |
| `same_doc` | Sequential paragraphs | Get surrounding context |

---

## Quick Start

### Prerequisites

- Python 3.10+
- ~2GB disk space for embedding model
- Featherless AI API key ([get one here](https://featherless.ai))

### Setup

```bash
# Clone
git clone https://github.com/Jiarun-han/Agentic-GraphRAG-for-Finnish-tax-law.git
cd Agentic-GraphRAG-for-Finnish-tax-law

# Install dependencies
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env and add your FEATHERLESS_API_KEY
```

### Build the Data Pipeline

```bash
# 1. Download the Finnish regulation corpus (~500MB)
python scripts/fetch_data.py

# 2. Parse HTML into structured nodes (~5 min)
python parse_corpus.py

# 3. Build the knowledge graph (~5 min)
python build_graph.py

# 4. Build the embedding index (~50 min on CPU)
python build_quick_index.py
```

### Ask Questions

```bash
# CLI mode
python agent.py "What is the capital income tax rate for income exceeding 30000 euros?"

# API mode
python api.py
# Then POST to http://localhost:8000/ask
```

### Run Evaluation

```bash
python evaluate.py --limit 5    # Quick test (5 questions)
python evaluate.py              # Full evaluation (83 questions)
```

---

## Web Frontend

A React-based UI for interactive use:

```bash
# Start backend
python api.py

# Start frontend (in another terminal)
cd frontend
npm install
npm run dev

# Open http://localhost:8080
```

Features:
- Clean answer display (citations stripped from text, shown separately)
- Source cards with document title, section, publisher, and URL link
- Reasoning transparency panel (sub-queries, confidence, node count)
- Dark/light mode

---

## Docker Deployment

```bash
# Build
docker build -t taxxa-graphrag .

# Run (mount your data directory)
docker run -p 8000:8000 --env-file .env -v ./data:/app/data taxxa-graphrag
```

Or with docker-compose:

```bash
docker compose -f docker-compose.prod.yml up
```

---

## API Reference

### `POST /ask`

Ask a tax law question.

**Request:**
```json
{
  "question": "What is the capital income tax rate for income exceeding 30,000 euros?"
}
```

**Response:**
```json
{
  "question": "...",
  "answer": "The capital income tax rate for income exceeding 30,000 euros is 34%. Income up to 30,000 euros is taxed at 30%.",
  "assumption": "Assuming tax year 2026, Finnish resident",
  "sub_queries": ["pääomatulovero TVL 124 §", "30000 euroa korotettu"],
  "citations": [
    {
      "source_id": "vero::Verotettavan tulon laskeminen::165",
      "doc_title": "Verotettavan tulon laskeminen henkilöverotuksessa",
      "section": "5.1 Veron määräytyminen",
      "url": "https://www.vero.fi/syventavat-vero-ohjeet/..."
    }
  ],
  "confidence_label": "high",
  "context_node_count": 24
}
```

### `POST /feedback`

Submit feedback on an answer.

```json
{
  "request_id": "abc123",
  "rating": "correct",
  "correction": "",
  "missing_info": ""
}
```

### `GET /health`

Health check endpoint.

### `GET /feedback/stats`

Aggregate feedback statistics.

---

## Testing

```bash
# Run all unit tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=term-missing
```

28 tests covering:
- LLM client retry logic and JSON parsing
- Evaluation metric normalization (percent, decimals, thousands)
- Planner query decomposition and fallback
- API endpoint validation

---

## Project Structure

```
├── config.py                # Centralized configuration (paths, API keys, parameters)
├── llm_client.py            # LLM client with retry, connection pooling, JSON parsing
├── tracing.py               # Request tracing and token counting
├── feedback.py              # User feedback collection
├── agent.py                 # 6-agent pipeline (Clarifier→Planner→Retriever→Generator→Auditor→Confidence)
├── retriever.py             # GraphRAG retriever (vector + keyword + graph + rerank)
├── api.py                   # FastAPI server
├── evaluate.py              # Evaluation harness (83 questions)
├── parse_corpus.py          # Section-aware HTML parser
├── build_graph.py           # Knowledge graph builder
├── build_quick_index.py     # Embedding index builder
├── Dockerfile               # Container deployment
├── frontend/                # React web UI
├── tests/                   # pytest test suite
├── scripts/
│   ├── fetch_data.py        # Corpus downloader
│   ├── extract_corpus.py    # Windows long-path extractor
│   └── update_index.py      # Incremental index updater
├── data/
│   └── question_bank.json   # 83 graded QA pairs
└── presentation/            # Demo video + PPTX
```

---

## Design Decisions

| Decision | Tried | Chose | Reasoning |
|----------|-------|-------|-----------|
| Embedding model | bge-m3 (4+ hrs build) | multilingual-e5-small (50 min) | Speed for iteration; good Finnish support |
| Reranker | English cross-encoder | LLM-as-reranker | English models hurt Finnish retrieval |
| Graph traversal | Blind BFS | Typed edge following | Edge type determines retrieval value |
| Agent count | Single LLM call | 6 agents + retry | Auditor catches 30% of initial errors |
| Graph store | Neo4j | NetworkX in-memory | Simpler, faster for this corpus size |

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| LLM | DeepSeek-V4-Flash via Featherless AI |
| Embeddings | intfloat/multilingual-e5-small (local) |
| Graph | NetworkX (in-memory, pickle serialized) |
| Reranker | LLM-as-judge (multilingual) |
| Backend | FastAPI + Uvicorn |
| Frontend | React + TanStack Router + Tailwind |
| Testing | pytest (28 tests) |
| Deployment | Docker |

---

## Incremental Updates

When new regulations are published, update without full rebuild:

```bash
# 1. Parse only new HTML files into a JSONL
python parse_corpus.py --new-only > data/new_nodes.jsonl

# 2. Incrementally embed and append to index
python scripts/update_index.py --new-nodes data/new_nodes.jsonl
```

---

## Known Limitations

- **Retrieval precision**: English queries sometimes miss Finnish documents. Planner mitigates this but isn't perfect.
- **LLM quality**: DeepSeek-V4-Flash occasionally produces unstable JSON. Robust parsing handles most cases.
- **ID duplicates**: ~8% of nodes have duplicate IDs from the parsing phase. Doesn't affect retrieval but should be fixed in a full rebuild.
- **No streaming**: Answers take 30-60s. Streaming would improve UX.

---

## Future Improvements

- [ ] Switch to bge-m3 embeddings (better Finnish, needs 4hr rebuild)
- [ ] Add streaming responses (SSE)
- [ ] Implement conversation memory (multi-turn)
- [ ] Add user authentication
- [ ] Deploy to cloud (Railway/Render)
- [ ] Fine-tune Planner on question bank patterns
- [ ] Add Prometheus metrics

---

## License

MIT

---

*Built by Jiarun Han · Prompt Finance Hackathon 2026 · Aalto University × Taxxa AI*
