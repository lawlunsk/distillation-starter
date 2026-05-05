#!/usr/bin/env python3
"""Find semantically similar knowledge notes for an inbox source file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from config_loader import (
    configured_dir,
    infer_note_type,
    is_excluded,
    load_config,
    relative_to_vault,
    vault_path,
)

try:
    import numpy as np
except ImportError:  # pragma: no cover - exercised by users without numpy
    np = None


def parse_ajson(filepath: Path):
    try:
        content = filepath.read_text(encoding="utf-8").strip().rstrip(",")
        if not content:
            return
        data = json.loads("{" + content + "}")
        for key, entry in data.items():
            yield key, entry
    except (json.JSONDecodeError, OSError):
        return


def extract_vector(filepath: Path, model_key: str, dims: int):
    for key, entry in parse_ajson(filepath):
        if not key.startswith("smart_sources:"):
            continue
        path = entry.get("path")
        vec = entry.get("embeddings", {}).get(model_key, {}).get("vec")
        if path and vec and len(vec) == dims:
            return path, np.array(vec, dtype=np.float32)
    return None


def load_vectors(config: dict, scope_prefix: str):
    smart = config["smart_connections"]
    multi_dir = vault_path(config, smart["multi_dir"])
    model_key = smart["model_key"]
    dims = int(smart["vector_dimensions"])
    vectors = []
    if not multi_dir.exists():
        return vectors
    for ajson_file in multi_dir.glob("*.ajson"):
        result = extract_vector(ajson_file, model_key, dims)
        if not result:
            continue
        rel_path, vec = result
        if not rel_path.startswith(scope_prefix):
            continue
        if is_excluded(config, rel_path):
            continue
        vectors.append((rel_path, vec))
    return vectors


def find_source_vector(config: dict, source_rel: str):
    smart = config["smart_connections"]
    multi_dir = vault_path(config, smart["multi_dir"])
    if not multi_dir.exists():
        return None
    source_name = Path(source_rel).name
    fallback = None
    for ajson_file in multi_dir.glob("*.ajson"):
        result = extract_vector(
            ajson_file,
            smart["model_key"],
            int(smart["vector_dimensions"]),
        )
        if not result:
            continue
        rel_path, vec = result
        if rel_path == source_rel:
            return vec
        if Path(rel_path).name == source_name and fallback is None:
            fallback = vec
    return fallback


def cosine(a, b) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", help="Source path, relative to vault root")
    parser.add_argument("--config", help="Path to config.yml")
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--min-sim", type=float, default=None)
    parser.add_argument("--scope", default=None, help="Candidate scope prefix, relative to vault root")
    args = parser.parse_args()

    if not args.source:
        parser.print_help()
        return

    config = load_config(args.config)
    smart = config["smart_connections"]
    knowledge_rel = str(config["knowledge_dir"]).strip("/") + "/"
    scope = args.scope or knowledge_rel
    min_sim = args.min_sim
    if min_sim is None:
        min_sim = float(smart.get("candidate_min_similarity", 0.0))

    source_path = vault_path(config, args.source)
    source_rel = relative_to_vault(config, source_path)

    if not smart.get("enabled", True):
        print(json.dumps({
            "source": source_rel,
            "candidates": [],
            "warning": "Smart Connections is disabled in config. Use index reading or manual search as fallback.",
        }, ensure_ascii=False, indent=2))
        return

    if np is None:
        print(json.dumps({
            "source": source_rel,
            "candidates": [],
            "warning": "numpy is not installed. Install numpy to enable semantic candidate search.",
        }, ensure_ascii=False, indent=2))
        return

    source_vec = find_source_vector(config, source_rel)
    if source_vec is None:
        print(json.dumps({
            "source": source_rel,
            "candidates": [],
            "warning": "No Smart Connections vector found for source. Read indexes and nearby notes manually.",
        }, ensure_ascii=False, indent=2))
        return

    candidate_vectors = load_vectors(config, scope)
    scored = []
    for rel_path, vec in candidate_vectors:
        sim = cosine(source_vec, vec)
        if sim >= min_sim:
            scored.append({
                "path": rel_path,
                "similarity": round(sim, 4),
                "type": infer_note_type(config, rel_path),
            })
    scored.sort(key=lambda item: item["similarity"], reverse=True)

    print(json.dumps({
        "source": source_rel,
        "total_compared": len(candidate_vectors),
        "candidates": scored[:args.top],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

