#!/usr/bin/env python3
"""Shared configuration helpers for Distillation Starter scripts."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "vault_root": ".",
    "inbox_dir": "Inbox",
    "knowledge_dir": "Knowledge",
    "archive_dir": "Archives/Inbox",
    "log_path": "System/distillation-log.md",
    "indexes_dir": "System/Indexes",
    "note_types": {
        "concept": "Concepts",
        "pivot": "Pivots",
        "framework": "Frameworks",
        "howto": "HowTo",
        "map": "Maps",
    },
    "index_files": {
        "global": "Index - Global.md",
        "concept": "Index - Concepts.md",
        "pivot": "Index - Pivots.md",
        "framework": "Index - Frameworks.md",
        "howto": "Index - HowTo.md",
        "map": "Index - Maps.md",
    },
    "smart_connections": {
        "enabled": True,
        "multi_dir": ".smart-env/multi",
        "model_key": "Xenova/multilingual-e5-small",
        "vector_dimensions": 384,
        "candidate_min_similarity": 0.0,
        "crossref_similarity_threshold": 0.88,
    },
    "exclusions": {
        "files": ["README.md", "AGENTS.md", "CLAUDE.md"],
        "path_contains": ["Sources/", "Templates/"],
    },
    "domain_sections": {},
}


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value == "":
        return ""
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if value.lower() in {"null", "none", "~"}:
        return None
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part.strip()) for part in inner.split(",")]
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    return value


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse the small YAML subset used by config.example.yml."""
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()

        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if value == "":
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _parse_scalar(value)

    return root


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def find_config_path(explicit: str | None = None) -> Path | None:
    if explicit:
        return Path(explicit).expanduser()
    env_path = os.getenv("DISTILLATION_CONFIG")
    if env_path:
        return Path(env_path).expanduser()
    cwd_config = Path.cwd() / "config.yml"
    if cwd_config.exists():
        return cwd_config
    return None


def load_config(explicit: str | None = None) -> dict[str, Any]:
    config = DEFAULT_CONFIG
    config_path = find_config_path(explicit)
    if config_path and config_path.exists():
        parsed = _parse_simple_yaml(config_path.read_text(encoding="utf-8"))
        config = _deep_merge(DEFAULT_CONFIG, parsed)
        config["_config_path"] = str(config_path.resolve())
    else:
        config = dict(DEFAULT_CONFIG)
        config["_config_path"] = None

    vault_root = Path(str(config["vault_root"])).expanduser()
    if not vault_root.is_absolute() and config.get("_config_path"):
        vault_root = (Path(config["_config_path"]).parent / vault_root).resolve()
    else:
        vault_root = vault_root.resolve()
    config["vault_root"] = str(vault_root)
    return config


def vault_path(config: dict[str, Any], path_value: str | Path) -> Path:
    path = Path(path_value).expanduser()
    if path.is_absolute():
        return path
    return Path(config["vault_root"]) / path


def relative_to_vault(config: dict[str, Any], path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path(config["vault_root"]).resolve()))
    except ValueError:
        return str(path)


def configured_dir(config: dict[str, Any], key: str) -> Path:
    return vault_path(config, str(config[key]))


def note_type_dirs(config: dict[str, Any]) -> dict[str, str]:
    return dict(config.get("note_types", {}))


def infer_note_type(config: dict[str, Any], rel_path: str) -> str:
    normalized = rel_path.replace("\\", "/")
    for type_name, dir_name in note_type_dirs(config).items():
        marker = f"/{dir_name.strip('/')}/"
        if marker in f"/{normalized}":
            return type_name
    return "unknown"


def is_excluded(config: dict[str, Any], rel_path: str) -> bool:
    name = Path(rel_path).name
    exclusions = config.get("exclusions", {})
    if name in set(exclusions.get("files", [])):
        return True
    return any(part in rel_path for part in exclusions.get("path_contains", []))

