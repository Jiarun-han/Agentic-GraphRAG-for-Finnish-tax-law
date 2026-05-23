"""
Build a typed knowledge graph from parsed_nodes.jsonl.
Outputs: data/graph.pkl  (NetworkX DiGraph)

Edge types:
  - same_doc      : consecutive nodes in same document (structural)
  - references    : finlex → finlex cross-reference
  - interprets    : vero guidance → finlex statute
  - cites         : KHO case law → statute
  - shared_ref    : nodes referencing the same statute section
  - amends        : amendment document → original statute
  - repeals       : repealing document → repealed statute
  - related_vero  : vero → vero (cross-linked guidance)
"""
import json, re, pickle, sys
from pathlib import Path
from collections import defaultdict
import networkx as nx

NODES_FILE = Path(__file__).parent / "data/parsed_nodes.jsonl"
GRAPH_FILE = Path(__file__).parent / "data/graph.pkl"

# ── Known statute abbreviations ───────────────────────────────────────────────

KNOWN_ABBREVS = {
    "TVL": "Tuloverolaki",
    "AVL": "Arvonlisäverolaki",
    "EPL": "Ennakkoperintälaki",
    "EVL": "Elinkeinoverolaki",
    "PerVL": "Perintö- ja lahjaverolaki",
    "VML": "Verotusmenettelylaki",
    "OVML": "Oma-aloitteisten verojen verotusmenettelylaki",
    "MVL": "Maatilatalouden tuloverolaki",
    "KPL": "Kirjanpitolaki",
    "OYL": "Osakeyhtiölaki",
    "TSL": "Työsopimuslaki",
    "VeroHL": "Veronkantolaki",
}

# Patterns indicating amendment/repeal in Finnish document titles
AMEND_PATTERNS = [
    r"muuttamisesta",       # "about amending"
    r"muutoksesta",         # "about change"
    r"muutos",              # "change/amendment"
]
REPEAL_PATTERNS = [
    r"kumoamisesta",        # "about repealing"
    r"kumotaan",            # "is repealed"
]


def load_nodes() -> list[dict]:
    nodes = []
    with NODES_FILE.open(encoding="utf-8") as f:
        for line in f:
            nodes.append(json.loads(line))
    return nodes


def build_abbrev_index(nodes: list[dict]) -> dict[str, list[str]]:
    """Map statute abbreviation → list of node ids whose doc_title matches."""
    idx: dict[str, list[str]] = defaultdict(list)
    for node in nodes:
        title = node.get("doc_title", "")
        for abbrev, full in KNOWN_ABBREVS.items():
            if full.lower() in title.lower() or abbrev in title:
                idx[abbrev].append(node["id"])
    return idx


def build_title_index(nodes: list[dict]) -> dict[str, str]:
    """Map normalized doc_title → first node id (for amends/repeals resolution)."""
    idx: dict[str, str] = {}
    for node in nodes:
        title = node.get("doc_title", "").lower().strip()
        if title and title not in idx:
            idx[title] = node["id"]
    return idx


def detect_amend_repeal(title: str) -> tuple[str | None, str | None]:
    """
    Detect if a document title indicates an amendment or repeal.
    Returns (rel_type, target_statute_hint) or (None, None).
    """
    title_lower = title.lower()

    for pattern in REPEAL_PATTERNS:
        if re.search(pattern, title_lower):
            return "repeals", title_lower

    for pattern in AMEND_PATTERNS:
        if re.search(pattern, title_lower):
            return "amends", title_lower

    return None, None


def extract_target_from_amend_title(title: str, abbrev_idx: dict) -> str | None:
    """Try to find which statute an amendment targets based on title keywords."""
    title_lower = title.lower()
    for abbrev, full in KNOWN_ABBREVS.items():
        if full.lower() in title_lower or abbrev.lower() in title_lower:
            targets = abbrev_idx.get(abbrev, [])
            if targets:
                return targets[0]
    return None


def build_graph(nodes: list[dict]) -> nx.DiGraph:
    G = nx.DiGraph()

    # Add all nodes
    for node in nodes:
        G.add_node(node["id"], **node)

    abbrev_idx = build_abbrev_index(nodes)
    title_idx = build_title_index(nodes)

    # Group by doc for same_doc edges
    doc_groups: dict[str, list[str]] = defaultdict(list)
    for node in nodes:
        doc_groups[node["file"]].append(node["id"])

    # 1. same_doc edges (sequential within document)
    print("  Adding same_doc edges...")
    same_doc_count = 0
    for doc_id, nids in doc_groups.items():
        for i in range(len(nids) - 1):
            G.add_edge(nids[i], nids[i+1], rel="same_doc")
            same_doc_count += 1

    # 2. Cross-reference edges via statute_refs
    print("  Adding statute_ref edges...")
    ref_count = 0
    for node in nodes:
        refs = node.get("statute_refs", [])
        for ref in refs:
            m = re.match(r"([A-ZÄÖÅ]{2,6})", ref)
            if not m:
                continue
            abbrev = m.group(1)
            targets = abbrev_idx.get(abbrev, [])
            if not targets:
                continue
            target = targets[0]
            if target == node["id"]:
                continue
            if node["source"] == "vero":
                rel = "interprets"
            elif node.get("doc_type") == "case_law":
                rel = "cites"
            else:
                rel = "references"
            G.add_edge(node["id"], target, rel=rel, ref_text=ref)
            ref_count += 1

    # 3. Shared-reference edges
    print("  Adding shared-reference edges...")
    ref_to_nodes: dict[str, list[str]] = defaultdict(list)
    for node in nodes:
        refs = node.get("statute_refs", [])
        for ref in refs:
            ref_to_nodes[ref].append(node["id"])

    shared_ref_count = 0
    for ref, nids in ref_to_nodes.items():
        if len(nids) < 2 or len(nids) > 50:
            continue
        for i in range(min(len(nids), 10)):
            for j in range(i+1, min(len(nids), 10)):
                if nids[i] != nids[j]:
                    G.add_edge(nids[i], nids[j], rel="shared_ref", ref_text=ref)
                    shared_ref_count += 1

    # 4. Amends/repeals edges (from document titles)
    print("  Adding amends/repeals edges...")
    amend_count = 0
    repeal_count = 0
    for node in nodes:
        if node["source"] != "finlex":
            continue
        title = node.get("doc_title", "")
        rel_type, _ = detect_amend_repeal(title)
        if rel_type:
            target = extract_target_from_amend_title(title, abbrev_idx)
            if target and target != node["id"]:
                G.add_edge(node["id"], target, rel=rel_type)
                if rel_type == "amends":
                    amend_count += 1
                else:
                    repeal_count += 1

    # 5. URL-based interprets edges (vero → finlex via links)
    print("  Adding URL-based edges...")
    url_count = 0
    for node in nodes:
        if node["source"] != "vero":
            continue
        links = node.get("links", [])
        for url in links:
            if "finlex.fi" in url:
                # Try to resolve to a known statute
                for abbrev, full in KNOWN_ABBREVS.items():
                    if full.lower().replace(" ", "").replace("-", "") in url.lower().replace(" ", "").replace("-", ""):
                        targets = abbrev_idx.get(abbrev, [])
                        if targets:
                            G.add_edge(node["id"], targets[0], rel="interprets", url=url)
                            url_count += 1
                            break

    print(f"  URL-based edges: {url_count}")
    print(f"  Amends: {amend_count}, Repeals: {repeal_count}")

    return G


if __name__ == "__main__":
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf-8-sig"):
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    print("Loading nodes...")
    nodes = load_nodes()
    print(f"  {len(nodes)} nodes")

    print("Building graph...")
    G = build_graph(nodes)
    print(f"\n  {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    edge_types = {}
    for _, _, d in G.edges(data=True):
        r = d.get("rel", "unknown")
        edge_types[r] = edge_types.get(r, 0) + 1
    for rel, cnt in sorted(edge_types.items()):
        print(f"    {rel}: {cnt}")

    with GRAPH_FILE.open("wb") as f:
        pickle.dump(G, f)
    print(f"\nGraph saved -> {GRAPH_FILE}")
