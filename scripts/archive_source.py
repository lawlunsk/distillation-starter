#!/usr/bin/env python3
"""Archive a processed source file into the configured archive folder."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import date
from pathlib import Path

from config_loader import configured_dir, load_config, relative_to_vault, vault_path


def is_inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def unique_destination(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    i = 2
    while True:
        candidate = path.with_name(f"{stem}_{i}{suffix}")
        if not candidate.exists():
            return candidate
        i += 1


def archive(config: dict, source: str, books: bool = False) -> dict:
    source_path = vault_path(config, source)
    inbox_dir = configured_dir(config, "inbox_dir")
    if not is_inside(source_path, inbox_dir):
        return {
            "archived": False,
            "error": f"Refusing to archive outside configured inbox: {relative_to_vault(config, source_path)}",
        }
    if not source_path.exists() or not source_path.is_file():
        return {"archived": False, "error": f"Source not found: {relative_to_vault(config, source_path)}"}

    year = str(date.today().year)
    archive_root = configured_dir(config, "archive_dir")
    dest_dir = archive_root / ("Books" if books else "") / year
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = unique_destination(dest_dir / source_path.name)
    shutil.move(str(source_path), str(dest_path))
    return {
        "archived": True,
        "source": relative_to_vault(config, source_path),
        "destination": relative_to_vault(config, dest_path),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", help="Source path relative to vault root")
    parser.add_argument("--config", help="Path to config.yml")
    parser.add_argument("--books", action="store_true", help="Archive in Books/YYYY")
    args = parser.parse_args()
    if not args.source:
        parser.print_help()
        return
    config = load_config(args.config)
    result = archive(config, args.source, args.books)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result.get("archived") else 1)


if __name__ == "__main__":
    main()

