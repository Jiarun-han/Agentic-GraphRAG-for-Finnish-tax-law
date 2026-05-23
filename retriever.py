"""
Hybrid retrieval: vector search → graph traversal → reranker.

Usage:
    retriever = Retriever()
    results = retriever.retrieve("What is the capital income tax rate?", top_k=5)
"""
import json, pickle, os, sys
from pathlib import Path
from typing import Optional
import numpy as np
import networkx as nx

# Load .env if present
_env = Path(__file__).parent / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        if _line.strip() and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

NODES_FILE  = Path(__file__).parent / "data/parsed_nodes.jsonl"
GRAPH_FILE  = Path(__file__).parent / "data/graph.pkl"
EMBED_FILE  = Path(__file__).parent / "data/embeddings.npz"
INDEX_FILE  = Path(__file__).parent / "data/node_ids.json"

EMBED_MODEL_NAME = "intfloat/multilingual-e5-small"

# ── embedding backend ─────────────────────────────────────────────────────────

_embed_model = None

def get_embedding(texts: list[str]) -> np.ndarray:
    """Return (N, D) float32 array using local sentence-transformers."""
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        _embed_model = SentenceTransformer(EMBED_MODEL_NAME)
        print(f"  Loaded embedding model: {EMBED_MODEL_NAME}")
    vecs = _embed_model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return np.array(vecs, dtype=np.float32)


# ── reranker (LLM-based, multilingual) ────────────────────────────────────────

def rerank(query: str, passages: list[dict], top_k: int = 15) -> list[dict]:
    """Rerank passages using LLM as judge (multilingual, no extra model needed)."""
    if not passages or len(passages) <= top_k:
        return passages

    # Build a compact list of candidates for LLM to rank
    candidates = []
    for i, p in enumerate(passages[:30]):
        title = (p.get("doc_title") or "")[:60]
        section = (p.get("section") or "")[:40]
        text_snippet = (p.get("text") or "")[:100]
        candidates.append(f"{i}: {title} | {section} | {text_snippet}")

    from agent import llm
    rerank_prompt = f"""Given the question, rank these document passages by relevance. Return ONLY the indices of the top {top_k} most relevant passages as a JSON array of integers, most relevant first.

Question: {query}

Passages:
{chr(10).join(candidates)}

Return ONLY a JSON array like [3, 0, 7, 1, ...]. No other text."""

    raw = llm(rerank_prompt, "", model=None)

    # Parse the ranked indices
    import re
    try:
        indices = json.loads(raw)
        if isinstance(indices, list):
            ranked = []
            for idx in indices[:top_k]:
                if isinstance(idx, int) and 0 <= idx < len(passages):
                    passages[idx]["rerank_score"] = top_k - len(ranked)
                    ranked.append(passages[idx])
            if ranked:
                return ranked
    except Exception:
        pass

    # Fallback: try to extract numbers
    numbers = re.findall(r'\d+', raw)
    if numbers:
        ranked = []
        for n in numbers[:top_k]:
            idx = int(n)
            if 0 <= idx < len(passages):
                passages[idx]["rerank_score"] = top_k - len(ranked)
                ranked.append(passages[idx])
        if ranked:
            return ranked

    # If LLM rerank fails, return original order
    return passages[:top_k]


# ── build / load vector index ─────────────────────────────────────────────────

def build_index(batch_size: int = 256):
    """Embed relevant nodes and save to disk."""

    CORE_STATUTES = {
        "tuloverolaki", "arvonlisäverolaki", "ennakkoperintälaki",
        "elinkeinoverolaki", "perintö- ja lahjaverolaki", "perintöverolaki",
        "verotusmenettelylaki", "kirjanpitolaki", "osakeyhtiölaki",
        "työsopimuslaki", "maatilatalouden tuloverolaki",
    }

    KEEP_KEYWORDS = {
        "vero", "verotus", "pääomatulo", "ansiotulo", "lähdevero",
        "ennakonpidätys", "lahjavero", "yleisradiovero", "avainhenkilö",
        "arvonlisä", "alv", "osinkotulo",
        "tyel", "työeläke", "eläkevakuutus", "sairausvakuutus",
        "ravintoetu", "luontoisetu", "matkakuluvähennys",
        "verovapaa", "veronalainen", "arpajaisvoitto",
        "bloggaaja", "blogista", "somekana",
    }

    print("Loading and filtering nodes (strict mode)...")
    nodes = []
    with NODES_FILE.open(encoding="utf-8") as f:
        for line in f:
            n = json.loads(line)
            if n["source"] == "vero":
                nodes.append(n)
            else:
                title_lower = n.get("doc_title", "").lower()
                text_lower = n.get("text", "").lower()
                combined = title_lower + " " + text_lower
                is_core = any(s in title_lower for s in CORE_STATUTES)
                has_keyword = any(kw in combined for kw in KEEP_KEYWORDS)
                if is_core or has_keyword:
                    nodes.append(n)

    print(f"Filtered to {len(nodes)} relevant nodes")
    print(f"Embedding in batches of {batch_size} using {EMBED_MODEL_NAME}...")

    all_vecs = []
    for i in range(0, len(nodes), batch_size):
        batch = nodes[i:i+batch_size]
        texts = [f"passage: {n.get('doc_title','')} | {n.get('section','')} | {n['text']}"[:512]
                 for n in batch]
        vecs = get_embedding(texts)
        all_vecs.append(vecs)
        if i % 5000 == 0:
            print(f"  {i}/{len(nodes)} ({100*i//len(nodes) if len(nodes) > 0 else 0}%)", flush=True)

    matrix = np.vstack(all_vecs)
    np.savez_compressed(EMBED_FILE, matrix=matrix)
    with INDEX_FILE.open("w") as f:
        json.dump([n["id"] for n in nodes], f)
    print(f"Index saved: {matrix.shape}")


# ── Retriever class ───────────────────────────────────────────────────────────

# Edge types and their traversal purpose
EDGE_PURPOSES = {
    "interprets":  "Find the law that this guidance interprets",
    "cites":       "Find the statute this case law applies",
    "shared_ref":  "Find other documents discussing the same legal provision",
    "amends":      "Find the latest version of this rule",
    "repeals":     "Check if this rule has been repealed",
    "references":  "Find cross-referenced statutes",
    "same_doc":    "Get surrounding context from the same document",
}

class Retriever:
    def __init__(self):
        data = np.load(EMBED_FILE)
        self.matrix = data["matrix"]
        norms = np.linalg.norm(self.matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1
        self.matrix = self.matrix / norms

        with INDEX_FILE.open() as f:
            self.node_ids: list[str] = json.load(f)

        with GRAPH_FILE.open("rb") as f:
            self.G: nx.DiGraph = pickle.load(f)

        self.node_map: dict[str, dict] = {
            nid: self.G.nodes[nid] for nid in self.G.nodes
        }

        # Build keyword index for BM25-style fallback search
        self._keyword_index: dict[str, list[str]] = {}  # keyword → [node_ids]
        for nid in self.node_ids:
            node = self.node_map.get(nid)
            if not node:
                continue
            text = (node.get("text") or "").lower()
            # Index important terms
            import re
            for term in re.findall(r'[a-zäöå]{4,}', text):
                if term not in self._keyword_index:
                    self._keyword_index[term] = []
                if len(self._keyword_index[term]) < 100:  # cap per keyword
                    self._keyword_index[term].append(nid)

    def _keyword_search(self, query: str, top_k: int = 10) -> list[str]:
        """Simple keyword matching fallback when vector search fails."""
        import re
        query_terms = set(re.findall(r'[a-zäöå0-9]{3,}', query.lower()))
        # Count how many query terms each node matches
        node_scores: dict[str, int] = {}
        for term in query_terms:
            for nid in self._keyword_index.get(term, []):
                node_scores[nid] = node_scores.get(nid, 0) + 1
        # Sort by match count
        ranked = sorted(node_scores.items(), key=lambda x: x[1], reverse=True)
        return [nid for nid, _ in ranked[:top_k]]

    def _vector_search(self, query: str, top_k: int) -> list[tuple[str, float]]:
        q_vec = get_embedding([f"query: {query}"])[0]
        q_vec = q_vec / (np.linalg.norm(q_vec) + 1e-9)
        scores = self.matrix @ q_vec
        top_idx = np.argsort(scores)[::-1][:top_k]
        return [(self.node_ids[i], float(scores[i])) for i in top_idx]

    def _graph_traverse(self, seed_ids: list[str], hops: int = 2) -> dict[str, dict]:
        """
        Purposeful graph traversal for GraphRAG.
        
        Strategy:
        1. From seed nodes (vector hits), follow semantic edges to find:
           - The LAW behind a guidance (interprets edge)
           - The LATEST VERSION of a rule (amends edge)
           - RELATED PROVISIONS discussed together (shared_ref edge)
           - CASE LAW applying a statute (cites edge)
        2. For each seed, also grab immediate same_doc neighbors for context
        3. Track WHY each node was reached (the edge path)
        """
        collected: dict[str, dict] = {}  # nid → {node_data, path, reason}

        for seed_id in seed_ids:
            if seed_id not in self.G:
                continue

            # Layer 1: Immediate same_doc context (prev + next paragraphs)
            for nbr in list(self.G.successors(seed_id)) + list(self.G.predecessors(seed_id)):
                edge = self.G.edges.get((seed_id, nbr)) or self.G.edges.get((nbr, seed_id))
                if edge and edge.get("rel") == "same_doc":
                    if nbr not in collected:
                        collected[nbr] = {"reason": "same_document_context", "hop": 1}

            # Layer 2: Semantic edges (the real GraphRAG value)
            frontier = {seed_id}
            visited = {seed_id}
            for hop in range(hops):
                next_frontier = set()
                for nid in frontier:
                    if nid not in self.G:
                        continue

                    # Follow outgoing semantic edges
                    for nbr in self.G.successors(nid):
                        if nbr in visited:
                            continue
                        edge_data = self.G.edges[nid, nbr]
                        rel = edge_data.get("rel", "")

                        if rel == "interprets":
                            # Vero → Finlex: get the actual law text
                            collected[nbr] = {"reason": "law_being_interpreted", "hop": hop+1}
                            next_frontier.add(nbr)
                            visited.add(nbr)

                        elif rel == "amends":
                            # Amendment → Original: check for newer version
                            collected[nbr] = {"reason": "amended_provision", "hop": hop+1}
                            next_frontier.add(nbr)
                            visited.add(nbr)

                        elif rel == "repeals":
                            # Repeal → Original: mark as potentially outdated
                            collected[nbr] = {"reason": "repealed_check", "hop": hop+1}
                            next_frontier.add(nbr)
                            visited.add(nbr)

                        elif rel == "cites":
                            # Case law → Statute: judicial interpretation
                            collected[nbr] = {"reason": "case_law_application", "hop": hop+1}
                            next_frontier.add(nbr)
                            visited.add(nbr)

                        elif rel == "shared_ref":
                            # Same legal provision discussed elsewhere
                            collected[nbr] = {"reason": "related_provision", "hop": hop+1}
                            next_frontier.add(nbr)
                            visited.add(nbr)

                        elif rel == "references":
                            # Cross-reference to another statute
                            collected[nbr] = {"reason": "cross_reference", "hop": hop+1}
                            next_frontier.add(nbr)
                            visited.add(nbr)

                    # Follow incoming semantic edges (reverse direction)
                    for nbr in self.G.predecessors(nid):
                        if nbr in visited:
                            continue
                        edge_data = self.G.edges[nbr, nid]
                        rel = edge_data.get("rel", "")

                        if rel == "interprets":
                            # Another guidance also interprets this law
                            collected[nbr] = {"reason": "another_interpretation", "hop": hop+1}
                            next_frontier.add(nbr)
                            visited.add(nbr)

                        elif rel == "amends":
                            # A newer amendment exists for this provision
                            collected[nbr] = {"reason": "newer_amendment", "hop": hop+1}
                            next_frontier.add(nbr)
                            visited.add(nbr)

                        elif rel == "cites":
                            # Case law that cites this provision
                            collected[nbr] = {"reason": "cited_by_case_law", "hop": hop+1}
                            next_frontier.add(nbr)
                            visited.add(nbr)

                        elif rel == "shared_ref":
                            collected[nbr] = {"reason": "related_provision", "hop": hop+1}
                            next_frontier.add(nbr)
                            visited.add(nbr)

                frontier = next_frontier

        return collected

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        graph_hops: int = 2,
        max_results: int = 25,
        use_reranker: bool = True,
    ) -> list[dict]:
        # 1. Vector search: find entry points
        seed_pairs = self._vector_search(query, top_k)
        seed_ids = [nid for nid, _ in seed_pairs]
        seed_scores = {nid: score for nid, score in seed_pairs}

        # 1b. Keyword search fallback: catch what vector search misses
        keyword_hits = self._keyword_search(query, top_k=5)
        for nid in keyword_hits:
            if nid not in seed_scores:
                seed_ids.append(nid)
                seed_scores[nid] = 0.5  # moderate score for keyword hits

        # 2. GraphRAG traversal: purposeful expansion
        graph_nodes = self._graph_traverse(seed_ids, hops=graph_hops)

        # 3. Collect all candidates with metadata
        results = []

        # Add seed nodes (direct vector hits)
        for nid, score in seed_pairs:
            node = self.node_map.get(nid)
            if node:
                results.append({
                    **node,
                    "retrieval_score": score,
                    "graph_reason": "direct_vector_hit",
                    "graph_hop": 0,
                })

        # Add keyword hits
        for nid in keyword_hits:
            if nid in {r["id"] for r in results}:
                continue
            node = self.node_map.get(nid)
            if node:
                results.append({
                    **node,
                    "retrieval_score": 0.5,
                    "graph_reason": "keyword_match",
                    "graph_hop": 0,
                })

        # Add graph-expanded nodes
        for nid, meta in graph_nodes.items():
            if nid in seed_scores and nid in {r["id"] for r in results}:
                continue
            node = self.node_map.get(nid)
            if node:
                results.append({
                    **node,
                    "retrieval_score": seed_scores.get(nid, 0.0),
                    "graph_reason": meta["reason"],
                    "graph_hop": meta["hop"],
                })

        # Sort: seeds first, then by hop distance
        results.sort(key=lambda x: (-x["retrieval_score"], x["graph_hop"]))

        # 4. Rerank if enabled
        if use_reranker and len(results) > 5:
            candidates = results[:max_results * 2]
            results = rerank(query, candidates, top_k=max_results)
        else:
            results = results[:max_results]

        return results


if __name__ == "__main__":
    # For index building, use: python build_quick_index.py
    # This entry point is for testing retrieval only
    r = Retriever()
    q = " ".join(sys.argv[1:]) or "pääomatulovero capital income tax rate TVL 124"
    hits = r.retrieve(q, top_k=5)
    for h in hits:
        score_key = "rerank_score" if "rerank_score" in h else "retrieval_score"
        print(f"[{h[score_key]:.3f}] {h.get('doc_title','')} | {h.get('section','')}")
        print(f"  {h.get('text','')[:120]}")
        print()
