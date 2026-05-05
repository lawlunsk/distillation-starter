#!/usr/bin/env python3
"""Run a local lint on notes touched during a distillation session."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from config_loader import configured_dir, load_config, relative_to_vault, vault_path

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def frontmatter(content: str) -> dict[str, str]:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        return {}
    data = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def wikilinks(content: str) -> set[str]:
    return set(re.findall(r"\[\[([^\]|]+?)(?:\|[^\]]+)?\]\]", content))


def all_notes(config: dict) -> list[Path]:
    knowledge = configured_dir(config, "knowledge_dir")
    return list(knowledge.rglob("*.md")) if knowledge.exists() else []


def backlinks(config: dict, title: str, exclude: Path) -> list[str]:
    pattern = re.compile(r"\[\[" + re.escape(title) + r"(\||\]\])")
    matches = []
    for note in all_notes(config):
        if note.resolve() == exclude.resolve():
            continue
        if pattern.search(read_text(note)):
            matches.append(relative_to_vault(config, note))
    return matches


def parse_ajson(filepath: Path):
    try:
        content = filepath.read_text(encoding="utf-8").strip().rstrip(",")
        if not content:
            return
        for key, entry in json.loads("{" + content + "}").items():
            yield key, entry
    except (json.JSONDecodeError, OSError):
        return


def load_vectors(config: dict) -> dict[str, object]:
    if np is None:
        return {}
    smart = config["smart_connections"]
    multi_dir = vault_path(config, smart["multi_dir"])
    vectors = {}
    if not multi_dir.exists():
        return vectors
    for ajson_file in multi_dir.glob("*.ajson"):
        for key, entry in parse_ajson(ajson_file):
            if not key.startswith("smart_sources:"):
                continue
            rel_path = entry.get("path", "")
            if not rel_path.startswith(str(config["knowledge_dir"]).strip("/") + "/"):
                continue
            vec = entry.get("embeddings", {}).get(smart["model_key"], {}).get("vec")
            if vec and len(vec) == int(smart["vector_dimensions"]):
                vectors[rel_path] = np.array(vec, dtype=np.float32)
    return vectors


def cosine(a, b) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def missing_crossrefs(config: dict, note_path: Path, vectors: dict, threshold: float) -> list[dict]:
    if np is None:
        return []
    rel_path = relative_to_vault(config, note_path)
    if rel_path not in vectors:
        return []
    content = read_text(note_path)
    existing = wikilinks(content)
    scored = []
    for other_path, other_vec in vectors.items():
        if other_path == rel_path:
            continue
        other_title = Path(other_path).stem
        if other_title in existing:
            continue
        sim = cosine(vectors[rel_path], other_vec)
        if sim >= threshold:
            scored.append({
                "from": note_path.stem,
                "to": other_title,
                "to_path": other_path,
                "similarity": round(sim, 4),
            })
    scored.sort(key=lambda item: item["similarity"], reverse=True)
    return scored[:5]


def capture_debts(config: dict, note_path: Path) -> list[str]:
    known = {note.stem.lower() for note in all_notes(config)}
    content = re.sub(r"^---\s*\n.*?\n---\s*\n", "", read_text(note_path), flags=re.DOTALL)
    debts = set()
    patterns = [
        r"(?:the\s+)?concept\s+of\s+([A-Z][\w\s'-]{2,50})",
        r"(?:the\s+)?notion\s+of\s+([A-Z][\w\s'-]{2,50})",
        r"(?:the\s+)?principle\s+of\s+([A-Z][\w\s'-]{2,50})",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, content):
            candidate = match.group(1).strip().rstrip(",.;:")
            if candidate.lower() not in known:
                debts.add(candidate)
    return sorted(debts)


def incomplete_sections(note_path: Path) -> list[str]:
    content = read_text(note_path)
    fm = frontmatter(content)
    if fm.get("type", "").lower() != "concept":
        return []
    missing = []
    match = re.search(r"###\s+Limits and counterexamples\s*\n(.*?)(?=\n###|\n##|\Z)", content, re.DOTALL | re.IGNORECASE)
    if not match or len(match.group(1).strip()) < 20:
        missing.append("Limits and counterexamples")
    return missing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="Touched note paths")
    parser.add_argument("--config", help="Path to config.yml")
    parser.add_argument("--sim-threshold", type=float)
    args = parser.parse_args()
    if not args.paths:
        parser.print_help()
        return
    config = load_config(args.config)
    threshold = args.sim_threshold or float(config["smart_connections"]["crossref_similarity_threshold"])
    vectors = load_vectors(config)
    report = {
        "orphans": [],
        "missing_crossrefs": [],
        "capture_debts": [],
        "missing_map": [],
        "incomplete_sections": [],
        "warnings": [],
    }
    if np is None:
        report["warnings"].append("numpy is not installed; semantic cross-reference lint skipped.")
    elif not vectors:
        report["warnings"].append("No Smart Connections vectors found; semantic cross-reference lint skipped.")
    for item in args.paths:
        note_path = vault_path(config, item)
        if not note_path.exists():
            continue
        rel = relative_to_vault(config, note_path)
        if not backlinks(config, note_path.stem, note_path):
            report["orphans"].append(rel)
        report["missing_crossrefs"].extend(missing_crossrefs(config, note_path, vectors, threshold))
        report["capture_debts"].extend(capture_debts(config, note_path))
        map_value = frontmatter(read_text(note_path)).get("map", "").strip()
        if map_value.lower() in {"", "null", "none", "~", "[[]]"}:
            report["missing_map"].append(rel)
        missing = incomplete_sections(note_path)
        if missing:
            report["incomplete_sections"].append({"note": rel, "missing": missing})
    report["capture_debts"] = sorted(set(report["capture_debts"]))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

