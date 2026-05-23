"""
Agentic GraphRAG pipeline.

Agents:
  Planner   – decompose question into sub-queries
  Retriever – hybrid search per sub-query
  Verifier  – check each claim has a source node
  Clarifier – detect missing conditions (jurisdiction, tax year, entity type)

Usage:
    python agent.py "What is the capital income tax rate?"
"""
import os, json, textwrap
from pathlib import Path
from typing import Optional
from retriever import Retriever

# Load .env if present
_env = Path(__file__).parent / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        if _line.strip() and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# ── LLM client ────────────────────────────────────────────────────────────────

def llm(system: str, user: str, model: Optional[str] = None) -> str:
    """Single LLM call via Featherless AI (OpenAI-compatible)."""
    from openai import OpenAI

    api_key  = os.getenv("FEATHERLESS_API_KEY")
    base_url = os.getenv("FEATHERLESS_BASE_URL", "https://api.featherless.ai/v1")
    model    = model or os.getenv("FEATHERLESS_MODEL", "deepseek-ai/DeepSeek-V4-Pro")

    client = OpenAI(api_key=api_key, base_url=base_url)
    resp = client.chat.completions.create(
        model=model,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    )
    return resp.choices[0].message.content.strip()


# ── Agent: Planner ────────────────────────────────────────────────────────────

PLANNER_SYS = """You are a Finnish tax law research planner.
Given a question, decompose it into 2-4 focused sub-queries that together cover the answer.

CRITICAL RULES:
- Every sub-query MUST contain Finnish legal terms (the corpus is in Finnish)
- Include the Finnish name of the relevant statute (e.g. tuloverolaki, ennakkoperintälaki, arvonlisäverolaki)
- Include Finnish keywords for the concept (e.g. pääomatulovero, ennakonpidätys, lahjavero, avainhenkilö)
- Include specific numbers/rates if mentioned in the question
- Include section references if obvious (e.g. TVL 124 §, EPL 9 §)

Common translations:
- capital income tax = pääomatulovero (TVL 124 §)
- withholding tax = ennakonpidätys, lähdevero
- gift tax = lahjavero, perintö- ja lahjaverolaki
- key personnel = avainhenkilö, avainhenkilölaki
- commuting deduction = matkakuluvähennys, asunnon ja työpaikan väliset matkat
- broadcasting tax = yleisradiovero
- pension insurance = eläkevakuutus, TyEL
- VAT = arvonlisävero, ALV

Return a JSON array of strings. Each string should be a mix of Finnish terms + key numbers.
Example: ["pääomatulovero 30 prosenttia 34 prosenttia TVL 124 §", "30000 euroa korotettu veroprosentti pääomatulo"]
Return ONLY the JSON array, no other text."""

def plan(question: str) -> list[str]:
    raw = llm(PLANNER_SYS, question)
    # Try to parse as JSON array
    try:
        queries = json.loads(raw)
        if isinstance(queries, list):
            return [str(q) for q in queries if len(str(q)) > 3]
    except Exception:
        pass
    # Try to fix common issues: missing brackets, markdown code blocks
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1].strip()
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
    if not cleaned.startswith("["):
        cleaned = '["' + cleaned
    if not cleaned.endswith("]"):
        cleaned = cleaned + '"]'
    # Fix unquoted items
    cleaned = cleaned.replace("', '", '", "').replace("',", '",')
    try:
        queries = json.loads(cleaned)
        if isinstance(queries, list):
            return [str(q) for q in queries if len(str(q)) > 3]
    except Exception:
        pass
    # Extract quoted strings
    import re
    parts = re.findall(r'"([^"]{4,})"', raw)
    if parts:
        return parts
    # fallback: use original question with Finnish keywords added
    return [question]


# ── Agent: Clarifier ──────────────────────────────────────────────────────────

CLARIFIER_SYS = """You are a Finnish tax law assistant.
Identify if the question is missing critical context needed to give a precise answer.
Check for: jurisdiction (Finland vs Åland vs foreign), tax year, entity type (individual/company/partnership),
transaction type, residency status.
If the question is sufficiently specified, return: {"needs_clarification": false}
If clarification is needed, return: {"needs_clarification": true, "missing": ["tax year", "entity type"], "assumption": "Assuming tax year 2026 and Finnish resident individual."}
Return ONLY valid JSON."""

def clarify(question: str) -> dict:
    raw = llm(CLARIFIER_SYS, question)
    try:
        return json.loads(raw)
    except Exception:
        pass
    # Try to extract JSON from response
    import re
    m = re.search(r'\{.*\}', raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except Exception:
            pass
    return {"needs_clarification": False}


# ── Agent: Verifier ───────────────────────────────────────────────────────────

VERIFIER_SYS = """You are a Finnish tax law auditor. Given a question, a draft answer, and source passages, perform a comprehensive audit:

PART 1 - FACT VERIFICATION:
For each factual claim in the answer, find the best matching source passage.
Check that numbers (rates, thresholds, amounts) match EXACTLY.

PART 2 - LOGIC & COMPLETENESS:
- Does the answer address ALL parts of the question?
- Are there logical contradictions?
- Are the cited rules still current (check dates)?
- If multiple sources discuss the same topic, do they agree?
- Are there important exceptions or conditions the answer omits?

Return JSON:
{
  "verified_claims": [{"claim": "...", "source_id": "...", "source_text": "..."}],
  "unverified_claims": ["claims not found in sources"],
  "conflicts": ["conflicting sources or outdated info"],
  "logic_ok": true/false,
  "completeness_ok": true/false,
  "missing_info": ["important info from sources that answer omits"]
}
Return ONLY valid JSON."""

def verify(answer: str, context_nodes: list[dict], question: str = "") -> dict:
    sources = "\n\n".join(
        f"[{n['id']}] ({(n.get('doc_title') or '')[:40]} | {(n.get('section') or '')[:30]}):\n{(n.get('text') or '')[:300]}"
        for n in context_nodes[:15]
    )
    user = f"QUESTION:\n{question}\n\nDRAFT ANSWER:\n{answer}\n\nSOURCES:\n{sources}"
    raw = llm(VERIFIER_SYS, user)
    try:
        result = json.loads(raw)
        return result
    except Exception:
        pass
    # Try to extract JSON from response
    import re
    m = re.search(r'\{.*\}', raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except Exception:
            pass
    return {"verified_claims": [], "unverified_claims": [], "conflicts": [],
            "logic_ok": True, "completeness_ok": True, "missing_info": []}


# ── Agent: Logic Checker ──────────────────────────────────────────────────────

LOGIC_CHECKER_SYS = """You are a Finnish tax law logic auditor. Given a question, a draft answer, and source passages, perform these checks:

1. LOGICAL CONSISTENCY: Does the answer contradict itself? Are the conclusions logically sound given the premises?
2. COMPLETENESS: Does the answer address ALL parts of the question? Are there obvious follow-up conditions or exceptions that should be mentioned?
3. TEMPORAL VALIDITY: Are the rules cited still current? Check for:
   - Dates mentioned in sources (effective from/until)
   - If a source says "from 1 January 2026" and we're in 2026, is the new rule applied?
   - If multiple dates appear, is the MOST RECENT rule used?
4. CROSS-SOURCE CONSISTENCY: If multiple sources discuss the same topic, do they agree? If not, which is authoritative?
5. MISSING CONTEXT: Are there important conditions, exceptions, or edge cases that the sources mention but the answer omits?

Return JSON:
{
  "logic_ok": true/false,
  "completeness_ok": true/false,
  "temporal_ok": true/false,
  "cross_source_ok": true/false,
  "issues": ["description of each issue found"],
  "suggestions": ["how to fix each issue"],
  "missing_info": ["important information from sources that the answer omits"]
}
Return ONLY valid JSON."""

def check_logic(question: str, answer: str, context_nodes: list[dict]) -> dict:
    sources = "\n\n".join(
        f"[{n['id']}] ({n['doc_title']} | {n.get('section','')}):\n{n['text'][:250]}"
        for n in context_nodes[:12]
    )
    user = f"QUESTION:\n{question}\n\nDRAFT ANSWER:\n{answer}\n\nSOURCES:\n{sources}"
    raw = llm(LOGIC_CHECKER_SYS, user)
    try:
        return json.loads(raw)
    except Exception:
        return {"logic_ok": True, "completeness_ok": True, "temporal_ok": True,
                "cross_source_ok": True, "issues": [], "suggestions": [], "missing_info": []}


# ── Agent: Confidence Scorer ──────────────────────────────────────────────────

CONFIDENCE_SYS = """You are a confidence assessor for a Finnish tax law QA system.
Given a question, the system's answer, verification results, and logic check results, assess the overall confidence.

Consider:
1. How many claims are verified vs unverified?
2. Are there any logical issues or conflicts?
3. Does the answer fully address the question?
4. Are the sources authoritative and current?
5. Is the answer specific (exact numbers/dates) or vague?

Return JSON:
{
  "confidence": 0.0-1.0,
  "confidence_label": "high" / "medium" / "low",
  "reasoning": "one sentence explaining the confidence level",
  "should_caveat": true/false,
  "caveat_text": "text to prepend if confidence is low, e.g. 'Based on available sources, but some details could not be verified:'"
}
Return ONLY valid JSON."""

def score_confidence(question: str, answer: str, verification: dict, logic_check: dict) -> dict:
    user = (
        f"QUESTION: {question}\n\n"
        f"ANSWER: {answer[:500]}\n\n"
        f"VERIFICATION: {json.dumps(verification, ensure_ascii=False)[:500]}\n\n"
        f"LOGIC CHECK: {json.dumps(logic_check, ensure_ascii=False)[:500]}"
    )
    raw = llm(CONFIDENCE_SYS, user)
    try:
        return json.loads(raw)
    except Exception:
        return {"confidence": 0.5, "confidence_label": "medium",
                "reasoning": "Could not assess", "should_caveat": False, "caveat_text": ""}


# ── Agent: Answer Generator ───────────────────────────────────────────────────

ANSWER_SYS = """You are a Finnish tax law expert. Give precise, concise answers in plain English.

RULES:
1. Start with the direct answer in one clear sentence.
2. Add 1-2 sentences of supporting context if needed.
3. Cite each claim with [source_id] at the end of the sentence. Use the exact source IDs from the SOURCES section.
4. Do NOT use markdown formatting (no **, no ##).
5. Do NOT quote Finnish text. Summarize in English.
6. Do NOT list historical versions unless specifically asked.
7. Keep answers under 100 words for simple questions.
8. For multi-part questions, number each part (1. 2. 3.)

Example:
"The capital income tax rate for income exceeding 30,000 euros is 34%. Income up to 30,000 euros is taxed at 30%. [vero::Verotettavan tulon laskeminen henkiloverotuksessa::165]"
"""

def generate_answer(question: str, context_nodes: list[dict], assumption: str = "") -> str:
    # Group sources by their graph traversal reason for better context
    context_parts = []
    for n in context_nodes[:25]:
        reason = n.get("graph_reason", "direct_hit")
        reason_label = {
            "direct_vector_hit": "DIRECT MATCH",
            "law_being_interpreted": "UNDERLYING LAW",
            "amended_provision": "AMENDED RULE",
            "newer_amendment": "NEWER AMENDMENT",
            "repealed_check": "POSSIBLY REPEALED",
            "case_law_application": "CASE LAW",
            "cited_by_case_law": "CITED IN CASE LAW",
            "related_provision": "RELATED PROVISION",
            "cross_reference": "CROSS-REFERENCE",
            "same_document_context": "CONTEXT",
            "another_interpretation": "ANOTHER INTERPRETATION",
        }.get(reason, "SOURCE")

        context_parts.append(
            f"[{n['id']}] ({reason_label})\n"
            f"Publisher: {n.get('source','unknown')} | Document: {n['doc_title']} | "
            f"Section: {n.get('section','N/A')} | Type: {n.get('doc_type','')}\n"
            f"Text: {n['text'][:600]}"
        )

    context = "\n\n".join(context_parts)
    prefix = f"[Assumption: {assumption}]\n\n" if assumption else ""
    user = f"{prefix}QUESTION: {question}\n\nSOURCES (labeled by how they were found via graph traversal):\n{context}"
    return llm(ANSWER_SYS, user)


# ── URL resolver ──────────────────────────────────────────────────────────────

def _resolve_url(node: dict) -> str:
    """Resolve a node to its source URL on finlex.fi or vero.fi."""
    source = node.get("source", "")
    doc_title = node.get("doc_title", "")
    file_path = node.get("file", "")

    if source == "vero":
        # Vero guidance URLs follow pattern: https://www.vero.fi/syventavat-vero-ohjeet/ohje-hakusivu/DOCID/
        # We can construct a search URL from the title
        title_slug = doc_title.replace(" ", "+").replace("ä", "%C3%A4").replace("ö", "%C3%B6")
        return f"https://www.vero.fi/syventavat-vero-ohjeet/ohje-hakusivu/?query={title_slug}"
    elif source == "finlex":
        # Finlex URLs: https://www.finlex.fi/fi/laki/ajantasa/
        # For case law: https://www.finlex.fi/fi/oikeus/kho/
        doc_type = node.get("doc_type", "")
        if doc_type == "case_law":
            # KHO:2019:80 → https://finlex.fi/fi/oikeus/kho/vuosikirjat/
            return f"https://www.finlex.fi/fi/oikeus/kho/"
        else:
            # Statutes: use title for search
            title_slug = doc_title.replace(" ", "+")
            return f"https://www.finlex.fi/fi/laki/ajantasa/?search={title_slug}"
    return ""


# ── Main pipeline ─────────────────────────────────────────────────────────────

def answer(question: str, retriever: Retriever, verbose: bool = False, fast: bool = False) -> dict:
    # 1. Clarify (skip in fast mode)
    assumption = "Assuming tax year 2026, Finnish resident, unless stated otherwise."
    if not fast:
        clarification = clarify(question)
        assumption = clarification.get("assumption", "") or assumption

    # 2. Plan
    sub_queries = plan(question)
    if question not in sub_queries:
        sub_queries.append(question)
    if verbose:
        print(f"Sub-queries: {sub_queries}")

    # 3. Retrieve per sub-query (GraphRAG)
    all_nodes: dict[str, dict] = {}
    for sq in sub_queries:
        hits = retriever.retrieve(sq, top_k=8, graph_hops=2, max_results=15)
        for h in hits:
            if h["id"] not in all_nodes or h.get("rerank_score", h.get("retrieval_score", 0)) > all_nodes[h["id"]].get("rerank_score", all_nodes[h["id"]].get("retrieval_score", 0)):
                all_nodes[h["id"]] = h

    # 4. Filter by relevance score
    score_key = "rerank_score" if any("rerank_score" in n for n in all_nodes.values()) else "retrieval_score"
    context_nodes = sorted(all_nodes.values(), key=lambda x: x.get(score_key, 0), reverse=True)

    if len(context_nodes) > 5:
        top_score = context_nodes[0].get(score_key, 1)
        threshold = top_score * 0.3 if score_key == "rerank_score" else 0.3
        context_nodes = [n for n in context_nodes if n.get(score_key, 0) > threshold] or context_nodes[:10]

    if verbose:
        print(f"Context nodes: {len(context_nodes)}")
        for n in context_nodes[:5]:
            title = (n.get('doc_title') or '')[:50]
            section = (n.get('section') or '')[:30]
            print(f"  [{n.get(score_key, 0):.3f}] {title} | {section}")

    # 5. Generate answer
    draft = generate_answer(question, context_nodes, assumption)

    # 6. Audit: verify claims + check logic (merged into one LLM call)
    audit = verify(draft, context_nodes, question)
    if verbose and audit.get("missing_info"):
        print(f"  Missing info: {audit['missing_info']}")

    # 7. If unverified claims or incomplete → retry with expanded retrieval
    unverified = audit.get("unverified_claims", [])
    has_issues = not audit.get("logic_ok", True) or not audit.get("completeness_ok", True)

    if (unverified and len(unverified) <= 5) or has_issues:
        if verbose:
            print(f"  Retrying: {len(unverified)} unverified, logic_ok={audit.get('logic_ok')}")

        retry_queries = unverified[:3]
        if audit.get("missing_info"):
            retry_queries.extend(audit["missing_info"][:2])

        for claim in retry_queries:
            extra_hits = retriever.retrieve(claim, top_k=5, graph_hops=2, max_results=10)
            for h in extra_hits:
                if h["id"] not in all_nodes:
                    all_nodes[h["id"]] = h

        context_nodes = sorted(all_nodes.values(), key=lambda x: x.get(score_key, 0), reverse=True)
        if len(context_nodes) > 30:
            context_nodes = context_nodes[:30]

        draft = generate_answer(question, context_nodes, assumption)
        audit = verify(draft, context_nodes, question)

    # 8. Confidence scoring (skip in fast mode)
    if fast:
        confidence = {"confidence": 0.7, "confidence_label": "medium", "should_caveat": False, "caveat_text": ""}
    else:
        confidence = score_confidence(question, draft, audit, audit)
    if verbose:
        print(f"  Confidence: {confidence.get('confidence_label', '?')} ({confidence.get('confidence', 0):.2f})")

    # 9. Apply caveat if low confidence
    final_answer = draft
    if confidence.get("should_caveat") and confidence.get("caveat_text"):
        final_answer = f"{confidence['caveat_text']}\n\n{draft}"

    # 10. Build citations list (from verified claims + regex extraction from answer)
    citations = []
    for vc in audit.get("verified_claims", []):
        sid = vc.get("source_id", "")
        node = all_nodes.get(sid, {})
        if node:
            citations.append({
                "source_id": sid,
                "doc_title": node.get("doc_title", ""),
                "section": node.get("section", ""),
                "file": node.get("file", ""),
                "url": _resolve_url(node),
                "claim": vc.get("claim", ""),
            })

    # Also extract citations from answer text via regex
    if not citations:
        import re
        cited_ids = re.findall(r'\[([^\]]+)\]', final_answer)
        for cid in cited_ids[:5]:
            node = all_nodes.get(cid, {})
            if node:
                citations.append({
                    "source_id": cid,
                    "doc_title": node.get("doc_title", ""),
                    "section": node.get("section", ""),
                    "file": node.get("file", ""),
                    "url": _resolve_url(node),
                    "claim": "",
                })

    return {
        "question": question,
        "assumption": assumption,
        "sub_queries": sub_queries,
        "answer": final_answer,
        "citations": citations,
        "unverified_claims": audit.get("unverified_claims", []),
        "conflicts": audit.get("conflicts", []),
        "logic_issues": audit.get("missing_info", []),
        "confidence": confidence.get("confidence", 0.5),
        "confidence_label": confidence.get("confidence_label", "medium"),
        "context_node_count": len(context_nodes),
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    question = " ".join(sys.argv[1:]) or "What is the capital income tax rate for income exceeding 30000 euros?"

    print("Loading retriever...")
    r = Retriever()

    print(f"\n{'='*60}")
    print(f"  QUESTION: {question}")
    print(f"{'='*60}\n")

    result = answer(question, r, verbose=True)

    # Clean output
    print(f"\n{'='*60}")
    print(f"  ANSWER  [Confidence: {result.get('confidence_label', '?')}]")
    print(f"{'='*60}\n")
    print(result["answer"])

    if result["assumption"]:
        print(f"\n  Assumption: {result['assumption']}")

    if result["citations"]:
        print(f"\n{'-'*60}")
        print("  SOURCES")
        print(f"{'-'*60}")
        for i, c in enumerate(result["citations"], 1):
            title = c.get('doc_title', '')[:50]
            section = c.get('section') or ''
            url = c.get('url', '')
            print(f"  [{i}] {title}")
            if section:
                print(f"      Section: {section}")
            if url:
                print(f"      URL: {url}")

    if result.get("unverified_claims"):
        print(f"\n  Unverified: {len(result['unverified_claims'])} claim(s) could not be verified")

    if result.get("conflicts"):
        print(f"\n  Conflicts: {len(result['conflicts'])} source conflict(s) detected")

    print(f"\n{'='*60}")
    print(f"  Stats: {result.get('context_node_count', 0)} sources analyzed | {len(result.get('sub_queries', []))} sub-queries")
    print(f"{'='*60}")
