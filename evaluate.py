"""
Evaluate the pipeline against question_bank.json.
Metrics:
  - key_facts_coverage : fraction of answer_key_facts found in system answer
  - has_citation       : answer contains at least one [source_id] citation
  - answered           : system produced a non-empty answer

Usage:
    python evaluate.py [--limit N] [--out results.json]
"""
import json, argparse, time
from pathlib import Path
from agent import answer as agent_answer
from retriever import Retriever

QB_FILE = Path(__file__).parent / "data/question_bank.json"

def key_facts_coverage(system_answer: str, key_facts: list[str]) -> float:
    if not key_facts:
        return 1.0  # no key facts to check → pass
    import re

    def normalize_text(text: str) -> str:
        """Normalize text for flexible matching."""
        t = text.lower()
        # "32 percent" / "32 prosenttia" / "32 %" → "32%"
        t = re.sub(r'(\d+\.?\d*)\s*percent', r'\1%', t)
        t = re.sub(r'(\d+\.?\d*)\s*prosenttia', r'\1%', t)
        t = re.sub(r'(\d+\.?\d*)\s*%', r'\1%', t)
        # "30 000" → "30000"
        t = re.sub(r'(\d+)\s+(\d{3})', r'\1\2', t)
        # "7,500" → "7500" (English thousands separator)
        t = re.sub(r'(\d+),(\d{3})\b', r'\1\2', t)
        # "60.0" → "60" (trailing .0)
        t = re.sub(r'(\d+)\.0\b', r'\1', t)
        # Normalize decimal separators: "0,27" ↔ "0.27"
        # Replace comma decimals with dot: "0,27" → "0.27"
        t = re.sub(r'(\d+),(\d{1,2})\b', r'\1.\2', t)
        return t

    ans_norm = normalize_text(system_answer)

    hits = 0
    for fact in key_facts:
        fact_norm = normalize_text(fact)

        # Extract key numbers (with %) and important terms
        numbers = re.findall(r"\d+[\.,]?\d*%?", fact_norm)
        # Also extract numbers from original (handles "0.27" etc)
        numbers += re.findall(r"\d+\.\d+", fact.lower())
        # Deduplicate
        numbers = list(dict.fromkeys(numbers))
        # Key terms (4+ chars, skip common words)
        skip_words = {"that", "this", "from", "with", "have", "been", "which", "their",
                      "under", "also", "most", "than", "more", "only", "does", "into"}
        terms = [w for w in re.findall(r"[a-zäöå]{4,}", fact_norm) if w not in skip_words][:5]

        # Strategy 1: All key numbers found in answer
        if numbers and all(n in ans_norm for n in numbers[:3]):
            hits += 1
            continue

        # Strategy 2: Most numbers + some terms found
        num_found = sum(1 for n in numbers if n in ans_norm)
        term_found = sum(1 for t in terms if t in ans_norm)
        if numbers and num_found >= max(1, len(numbers) * 0.5) and term_found >= 1:
            hits += 1
            continue

        # Strategy 3: Direct substring match (first 50 chars of fact)
        if fact_norm[:50] in ans_norm:
            hits += 1
            continue

        # Strategy 4: Key phrase match (for non-numeric facts)
        if not numbers and term_found >= 2:
            hits += 1
            continue

    return hits / len(key_facts)

def has_citation(system_answer: str) -> bool:
    """Check if answer contains meaningful citations (not just any number)."""
    import re
    patterns = [
        r"\[(?:finlex|vero)::",          # [finlex::... or [vero::...
        r"\[\w+::\w+::\d+\]",            # [source::doc::num]
        r"\(Verohallinto,",              # (Verohallinto, ...)
        r"\(Finlex,",                    # (Finlex, ...)
        r"TVL \d+\s*§",                  # TVL 124 §
        r"AVL \d+\s*§",                  # AVL 117 §
        r"EPL \d+\s*§",                  # EPL 25 §
        r"\d{1,4}/\d{4}",               # 1551/1995 (statute number/year)
    ]
    return any(re.search(p, system_answer) for p in patterns)

def run_eval(limit: int = None, out_file: str = "data/eval_results.json"):
    with QB_FILE.open(encoding="utf-8") as f:
        qb = json.load(f)

    entries = qb["entries"]
    if limit:
        entries = entries[:limit]

    print(f"Loading retriever...")
    retriever = Retriever()

    results = []
    total_coverage = 0.0
    total_cited = 0
    total_answered = 0

    for i, entry in enumerate(entries):
        qid   = entry["id"]
        tier  = entry.get("tier", "?")
        q     = entry["question"]
        kf    = entry.get("answer_key_facts", [])
        ref_a = entry.get("answer", "")

        print(f"[{i+1}/{len(entries)}] {qid} ({tier}) ...", end=" ", flush=True)
        t0 = time.time()

        try:
            result = agent_answer(q, retriever, verbose=False, fast=True)
            sys_ans = result["answer"]
            coverage = key_facts_coverage(sys_ans, kf)
            cited    = has_citation(sys_ans) or bool(result["citations"])
            answered = bool(sys_ans.strip())
        except Exception as e:
            sys_ans  = f"ERROR: {e}"
            coverage = 0.0
            cited    = False
            answered = False
            result   = {}

        elapsed = time.time() - t0
        total_coverage += coverage
        total_cited    += int(cited)
        total_answered += int(answered)

        print(f"coverage={coverage:.2f} cited={cited} ({elapsed:.1f}s)")

        results.append({
            "id": qid,
            "tier": tier,
            "question": q,
            "reference_answer": ref_a[:300],
            "system_answer": sys_ans[:600],
            "key_facts_coverage": coverage,
            "has_citation": cited,
            "answered": answered,
            "citations": result.get("citations", []),
            "conflicts": result.get("conflicts", []),
            "elapsed_s": round(elapsed, 1),
        })

    n = len(entries)
    summary = {
        "total": n,
        "avg_key_facts_coverage": round(total_coverage / n, 3),
        "pct_cited": round(total_cited / n * 100, 1),
        "pct_answered": round(total_answered / n * 100, 1),
    }

    output = {"summary": summary, "results": results}
    Path(out_file).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "="*50)
    print(f"Results ({n} questions):")
    print(f"  Avg key_facts coverage : {summary['avg_key_facts_coverage']:.3f}")
    print(f"  % with citations       : {summary['pct_cited']}%")
    print(f"  % answered             : {summary['pct_answered']}%")
    print(f"Saved → {out_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Evaluate only first N questions")
    parser.add_argument("--out",   type=str, default="data/eval_results.json")
    args = parser.parse_args()
    run_eval(limit=args.limit, out_file=args.out)
