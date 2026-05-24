# Agentic GraphRAG for Finnish Tax Law

> Prompt Finance Hackathon 2026 · Aalto University × Taxxa AI

A 6-agent multi-agent system that retrieves, reasons, and cites over real Finnish regulation — beating naive RAG on multi-hop tax law questions.

**Results:** 70% key facts coverage · 90% citation rate · 100% answer rate (83 questions)

---

## Architecture

```
Question
  │
  ├─→ Clarifier (detect missing context: tax year, entity type, jurisdiction)
  │
  ├─→ Planner (decompose into 2-4 sub-queries with Finnish legal terms)
  │
  ├─→ Retriever (GraphRAG)
  │     ├── Vector Search (multilingual-e5-small)
  │     ├── Keyword Fallback (exact Finnish term matching)
  │     ├── Typed Graph Traversal (interprets → amends → cites → shared_ref)
  │     └── LLM Reranker (multilingual, no English-only bottleneck)
  │
  ├─→ Answer Generator (concise English, every claim cited)
  │
  ├─→ Auditor (verify facts + logic + completeness + temporal validity)
  │
  ├─→ Confidence Scorer (high/medium/low, caveat if uncertain)
  │
  └─→ Retry Loop (unverified claims → re-retrieve → re-generate)
```

## How We Solve the 4 Problems

| Naive RAG Problem | Our Solution |
|-------------------|-------------|
| **Chunking destroys structure** | Section-aware parsing — respects headings, sections, paragraphs |
| **Can't tell old from new** | `amends`/`repeals` edges + Auditor checks temporal validity |
| **Cross-references not followed** | Typed graph traversal walks `interprets`/`cites` edges |
| **Multi-hop gets one-hop answers** | Planner decomposes + 2-hop graph walk + retry loop |

## Knowledge Graph

- **994K nodes** · **957K edges** · **240K embedded**
- Edge types: `interprets`, `cites`, `amends`, `repeals`, `shared_ref`, `same_doc`
- Purposeful traversal: each edge type has a specific retrieval purpose

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env          # add your Featherless API key

python scripts/fetch_data.py  # download corpus
python parse_corpus.py        # parse HTML → nodes
python build_graph.py         # build knowledge graph
python build_quick_index.py   # build embeddings (~50 min)

python agent.py "What is the capital income tax rate for income exceeding 30000 euros?"
```

## Frontend Demo

```bash
python api.py                              # backend on :8000
cd frontend && npm install && npm run dev   # frontend on :8080
```

## Evaluation

```
83 questions from Taxxa QA bank:
  Key facts coverage:  70%
  Citation rate:       90.4%
  Answer rate:         100%
```

## Tech Stack

| Component | Choice |
|-----------|--------|
| LLM | DeepSeek-V4-Flash via Featherless AI |
| Embeddings | intfloat/multilingual-e5-small |
| Graph | NetworkX (in-memory) |
| Reranker | LLM-as-judge (multilingual) |
| Backend | FastAPI + Uvicorn |
| Frontend | React + TanStack + Vite |

## Design Decisions

| Decision | Tried | Chose | Why |
|----------|-------|-------|-----|
| Embedding model | bge-m3 (4+ hrs) | e5-small (50 min) | Speed for iteration |
| Reranker | English cross-encoder | LLM-as-reranker | Finnish language support |
| Graph traversal | Blind BFS | Typed edge following | Edge type = retrieval signal |
| Agent count | Single LLM call | 6 agents + retry | Auditor catches 30% of errors |

## Project Structure

```
├── agent.py              # 6-agent pipeline
├── retriever.py          # GraphRAG retriever
├── build_graph.py        # Knowledge graph builder
├── build_quick_index.py  # Embedding index builder
├── parse_corpus.py       # Section-aware HTML parser
├── evaluate.py           # Evaluation harness
├── api.py                # FastAPI backend
├── frontend/             # React UI
├── presentation/         # Demo video + PPTX
└── SUBMISSION.md         # Detailed design document
```

---

*Built for Prompt Finance Hackathon 2026 · Aalto University × Taxxa AI*
