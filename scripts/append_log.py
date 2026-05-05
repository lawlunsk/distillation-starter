#!/usr/bin/env python3
"""Append a Markdown entry to the configured distillation log."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path

from config_loader import load_config, relative_to_vault, vault_path


def default_header(today: str) -> str:
    return f"""---
created: {today}
updated: {today}
type: log
status: active
tags: [log, distillation]
---

# Distillation Log

> One entry per distillation session. Newest entries first.

---

"""


def ensure_log(path: Path):
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    path.write_text(default_header(today), encoding="utf-8")


def append_entry(log_path: Path, entry_text: str):
    ensure_log(log_path)
    content = log_path.read_text(encoding="utf-8")
    today = date.today().isoformat()
    content = re.sub(
        r"^(updated:\s*)\d{4}-\d{2}-\d{2}",
        lambda m: m.group(1) + today,
        content,
        count=1,
        flags=re.MULTILINE,
    )
    parts = content.split("\n---\n\n", 2)
    if len(parts) >= 3:
        new_content = parts[0] + "\n---\n\n" + parts[1] + "\n---\n\n" + entry_text.rstrip() + "\n\n" + parts[2]
    else:
        new_content = content.rstrip() + "\n\n" + entry_text.rstrip() + "\n"
    log_path.write_text(new_content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("entry_file", nargs="?", help="Markdown file containing the log entry")
    parser.add_argument("--config", help="Path to config.yml")
    args = parser.parse_args()
    if not args.entry_file:
        parser.print_help()
        return
    config = load_config(args.config)
    entry_path = Path(args.entry_file).expanduser()
    if not entry_path.is_absolute():
        entry_path = Path.cwd() / entry_path
    if not entry_path.exists():
        print(json.dumps({"appended": False, "error": f"Entry file not found: {entry_path}"}))
        raise SystemExit(1)
    log_path = vault_path(config, str(config["log_path"]))
    append_entry(log_path, entry_path.read_text(encoding="utf-8"))
    print(json.dumps({"appended": True, "log_path": relative_to_vault(config, log_path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

