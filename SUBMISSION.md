# Submission: Agentic GraphRAG for Finnish Tax Law

## Architecture Overview

```
Question
  │
  ├─→ Clarifier (detect missing context: tax year, entity type, jurisdiction)
  │
  ├─→ Planner (decompose into 2-4 sub-queries with Finnish legal terms)
  │
  ├─→ Retriever × N sub-queries
  │     ├── Vector Search (multilingual-e5-small, cosine similarity)
  │     ├── Graph Expansion (prioritize semantic edges: interprets, cites, amends)
  │     └── Cross-Encoder Reranker (ms-marco-MiniLM-L-6-v2)
  │
  ├─→ Answer Generator (DeepSeek-V4-Pro, with mandatory citations)
  │
  ├─→ Verifier (fact-check each claim against source passages)
  │
  └─→ Retry Loop (if unverified claims found → re-retrieve → re-generate)
        │
        └─→ Final Answer with inline citations [source_id] (Document, Section)
```

## Design Decisions

### 1. Parse, Don't Chunk
We parse the Finlex and Vero HTML corpus respecting document structure (headings, sections, paragraphs) rather than naive 512-token chunking. Each node preserves:
- Document title and section hierarchy
- Statute cross-references (extracted via regex)
- Hyperlinks to other documents (finlex.fi, vero.fi)

### 2. Typed Knowledge Graph
Built with NetworkX. Edge types:
- `same_doc` — sequential nodes within a document (structural navigation)
- `interprets` — Vero guidance → Finlex statute (operational interpretation)
- `cites` — KHO case law → statute (judicial interpretation)
- `shared_ref` — nodes that reference the same statute section (enables multi-hop)
- `amends` — amendment document → original statute (temporal reasoning)
- `repeals` — repealing document → repealed statute (validity tracking)
- `references` — finlex → finlex cross-references

### 3. Hybrid Retrieval with Reranker
- **Vector search** (multilingual-e5-small) finds semantic entry points
- **Purposeful graph traversal** — not blind BFS, but typed edge following:
  - `interprets` → find the actual law behind a guidance document
  - `amends` → find the latest version of a rule
  - `cites` → find case law applying a statute
  - `shared_ref` → find other documents discussing the same provision
  - `same_doc` → get surrounding context paragraphs
- Each retrieved node is labeled with WHY it was found (e.g. "UNDERLYING LAW", "NEWER AMENDMENT")
- **Cross-encoder reranker** (ms-marco-MiniLM-L-6-v2) for final precision ranking

### 4. Multi-Agent Pipeline
Four specialized agents, each with a focused prompt:

| Agent | Role |
|-------|------|
| **Clarifier** | Detects missing context (tax year, entity type, jurisdiction) and makes explicit assumptions |
| **Planner** | Decomposes question into 2-4 sub-queries with Finnish legal terms |
| **Answer Generator** | Synthesizes answer from sources with mandatory inline citations |
| **Verifier** | Fact-checks each claim against source passages, flags conflicts |

### 5. Retry Retrieval
If the Verifier finds unverified claims, the system automatically:
1. Uses the unverified claims as new search queries
2. Retrieves additional context
3. Re-generates the answer with expanded sources

This handles multi-hop questions where the first retrieval pass misses a needed source.

## What We Tried

1. **bge-m3 embeddings** — best quality for Finnish but too slow for iteration (568M params). Used multilingual-e5-small for development, plan to switch back for final submission.
2. **URL-based graph edges** — attempted to resolve finlex.fi hyperlinks to create cross-document edges. Partially successful (statute_refs + shared_ref edges work well).
3. **Strict node filtering** — reduced 1M+ nodes to ~260K tax-relevant ones for tractable embedding.

## Tech Stack

- **LLM**: DeepSeek-V4-Pro via Featherless AI (OpenAI-compatible API)
- **Embeddings**: intfloat/multilingual-e5-small (local, sentence-transformers)
- **Graph**: NetworkX (in-memory, pickle serialized)
- **Language**: Python 3.10+

## How to Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up .env (copy from .env.example, add your API key)
cp .env.example .env

# 3. Parse corpus (if not already done)
python parse_corpus.py

# 4. Build graph
python build_graph.py

# 5. Build embeddings index
python retriever.py --build

# 6. Ask a question
python agent.py "What is the capital income tax rate for income exceeding 30000 euros?"

# 7. Run evaluation
python evaluate.py --limit 5    # quick test
python evaluate.py              # full 83 questions
```

## Evaluation Results

Evaluated on the full 83-question bank (`data/question_bank.json`):

```
Avg key_facts coverage: 0.700 (70%)
% with citations:       90.4%
% answered:             100.0%
```

- **70% key facts coverage** — the system correctly identifies and states the majority of critical facts (rates, thresholds, dates) from the corpus
- **90.4% citation rate** — nearly all answers include traceable source references (document + section)
- **100% answer rate** — the system always produces a response, using confidence caveats when uncertain rather than refusing to answer
