"""
Incremental index updater.
Embeds only new nodes and appends to existing index without full rebuild.

Usage:
    python scripts/update_index.py --new-nodes data/new_nodes.jsonl
"""
import json
import time
import argparse
from pathlib import Path
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).parents[1]))

from config import config, logger


def incremental_embed(new_nodes_file: Path):
    """Embed new nodes and append to existing index."""
    from sentence_transformers import SentenceTransformer

    EMBED_FILE = config.embed_file
    INDEX_FILE = config.index_file
    METADATA_FILE = config.data_dir / "metadata.json"
    CHANGELOG_FILE = config.data_dir / "changelog.json"

    # Load existing index
    if EMBED_FILE.exists() and INDEX_FILE.exists():
        existing_matrix = np.load(EMBED_FILE)["matrix"]
        existing_ids = json.load(INDEX_FILE.open())
        logger.info(f"Existing index: {existing_matrix.shape[0]} nodes")
    else:
        existing_matrix = np.zeros((0, 384), dtype=np.float32)
        existing_ids = []
        logger.info("No existing index, creating new one")

    # Load new nodes
    new_nodes = []
    existing_id_set = set(existing_ids)
    with open(new_nodes_file, encoding="utf-8") as f:
        for line in f:
            n = json.loads(line)
            if n["id"] not in existing_id_set:
                new_nodes.append(n)

    if not new_nodes:
        logger.info("No new nodes to embed")
        return

    logger.info(f"Embedding {len(new_nodes)} new nodes...")

    # Embed new nodes
    model = SentenceTransformer(config.embed_model)
    batch_size = 256
    all_vecs = []

    for i in range(0, len(new_nodes), batch_size):
        batch = new_nodes[i:i+batch_size]
        texts = [f"passage: {n.get('doc_title','')} | {n.get('section','')} | {n['text']}"[:512]
                 for n in batch]
        vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        all_vecs.append(np.array(vecs, dtype=np.float32))
        if i % 5000 == 0:
            logger.info(f"  {i}/{len(new_nodes)}")

    new_matrix = np.vstack(all_vecs)

    # Combine
    combined_matrix = np.vstack([existing_matrix, new_matrix])
    combined_ids = existing_ids + [n["id"] for n in new_nodes]

    # Save
    np.savez_compressed(EMBED_FILE, matrix=combined_matrix)
    with INDEX_FILE.open("w") as f:
        json.dump(combined_ids, f)

    logger.info(f"Index updated: {existing_matrix.shape[0]} → {combined_matrix.shape[0]} nodes")

    # Update metadata
    metadata = {
        "version": time.strftime("%Y-%m-%d"),
        "node_count": len(combined_ids),
        "embed_model": config.embed_model,
        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    METADATA_FILE.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    # Append to changelog
    changelog = []
    if CHANGELOG_FILE.exists():
        changelog = json.loads(CHANGELOG_FILE.read_text(encoding="utf-8"))
    changelog.append({
        "date": time.strftime("%Y-%m-%d"),
        "added": len(new_nodes),
        "removed": 0,
        "total": len(combined_ids),
        "reason": f"Incremental update from {new_nodes_file.name}",
    })
    CHANGELOG_FILE.write_text(json.dumps(changelog, indent=2), encoding="utf-8")

    logger.info("Metadata and changelog updated")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Incrementally update the embedding index")
    parser.add_argument("--new-nodes", type=Path, required=True, help="JSONL file with new nodes")
    args = parser.parse_args()

    if not args.new_nodes.exists():
        logger.error(f"File not found: {args.new_nodes}")
        exit(1)

    incremental_embed(args.new_nodes)
