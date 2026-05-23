"""
Index builder: embed VERO nodes + Finlex core tax statutes + case law.
Writes progress to data/build_log.txt.
"""
import json, sys, os, time
from pathlib import Path
import numpy as np

os.environ["PYTHONUNBUFFERED"] = "1"

_env = Path(__file__).parent / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        if _line.strip() and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

_BASE = Path(__file__).parent
NODES_FILE = _BASE / "data/parsed_nodes.jsonl"
EMBED_FILE = _BASE / "data/embeddings.npz"
INDEX_FILE = _BASE / "data/node_ids.json"
LOG_FILE = _BASE / "data/build_log.txt"

EMBED_MODEL_NAME = "intfloat/multilingual-e5-small"

# Core statutes that the question bank tests
CORE_STATUTES = {
    "tuloverolaki", "arvonlisäverolaki", "ennakkoperintälaki",
    "elinkeinoverolaki", "perintö- ja lahjaverolaki",
    "verotusmenettelylaki", "kirjanpitolaki", "osakeyhtiölaki",
    "työsopimuslaki", "maatilatalouden tuloverolaki",
    "ennakkoperintäasetus", "veronkantolaki",
}

# Keywords to catch relevant finlex nodes
KEEP_KEYWORDS = {
    "vero", "verotus", "pääomatulo", "ansiotulo", "lähdevero",
    "ennakonpidätys", "lahjavero", "yleisradiovero", "avainhenkilö",
    "arvonlisä", "alv", "osinkotulo", "osinko",
    "tyel", "työeläke", "eläkevakuutus", "sairausvakuutus",
    "ravintoetu", "luontoisetu", "matkakuluvähennys",
    "verovapaa", "veronalainen", "arpajaisvoitto",
    "bloggaaja", "blogista", "somekana",
    "kho", "korkein hallinto",
}


def log(msg):
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")


def main():
    LOG_FILE.write_text("", encoding="utf-8")
    log("Starting FULL build (vero + finlex core)...")

    log("Loading and filtering nodes...")
    nodes = []
    vero_count = 0
    finlex_count = 0
    case_law_count = 0

    with NODES_FILE.open(encoding="utf-8") as f:
        for line in f:
            n = json.loads(line)
            # Always include ALL vero nodes
            if n["source"] == "vero":
                nodes.append(n)
                vero_count += 1
            # Include case law - only if strongly tax-related
            elif n.get("doc_type") == "case_law":
                text_lower = (n.get("doc_title", "") + " " + n.get("text", "")).lower()
                # Stricter filter for case law: must mention specific tax terms
                tax_terms = {"vero", "tvl", "avl", "epl", "evl", "pervl", "pääomatulo", "ansiotulo", "arvonlisä", "lähdevero"}
                if any(kw in text_lower for kw in tax_terms):
                    nodes.append(n)
                    case_law_count += 1
            # Include finlex core statutes + keyword matches
            else:
                title_lower = n.get("doc_title", "").lower()
                text_lower = n.get("text", "").lower()
                combined = title_lower + " " + text_lower
                is_core = any(s in title_lower for s in CORE_STATUTES)
                has_keyword = any(kw in combined for kw in KEEP_KEYWORDS)
                if is_core or has_keyword:
                    nodes.append(n)
                    finlex_count += 1

    log(f"Loaded {len(nodes)} nodes: vero={vero_count}, finlex={finlex_count}, case_law={case_law_count}")

    from sentence_transformers import SentenceTransformer
    log(f"Loading model: {EMBED_MODEL_NAME}")
    model = SentenceTransformer(EMBED_MODEL_NAME)
    log("Model loaded OK")

    batch_size = 256
    log(f"Embedding {len(nodes)} nodes in batches of {batch_size}...")
    t0 = time.time()

    all_vecs = []
    for i in range(0, len(nodes), batch_size):
        batch = nodes[i:i+batch_size]
        texts = [f"passage: {n.get('doc_title','')} | {n.get('section','')} | {n['text']}"[:512]
                 for n in batch]
        vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        all_vecs.append(np.array(vecs, dtype=np.float32))
        if i % 5120 == 0:
            elapsed = time.time() - t0
            log(f"  {i}/{len(nodes)} ({100*i//len(nodes)}%) - {elapsed:.0f}s elapsed")

    elapsed = time.time() - t0
    log(f"Encoding done in {elapsed:.0f}s")

    matrix = np.vstack(all_vecs)
    np.savez_compressed(EMBED_FILE, matrix=matrix)
    with INDEX_FILE.open("w") as f:
        json.dump([n["id"] for n in nodes], f)
    log(f"DONE! Index saved: {matrix.shape}, file size: {EMBED_FILE.stat().st_size // 1024 // 1024}MB")


if __name__ == "__main__":
    main()
