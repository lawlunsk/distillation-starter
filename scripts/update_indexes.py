#!/usr/bin/env python3
"""Update configured Markdown indexes after creating or enriching notes."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path

from config_loader import (
    configured_dir,
    infer_note_type,
    load_config,
    relative_to_vault,
    vault_path,
)


def read_frontmatter(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    content = path.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        return {}
    frontmatter = {}
    current_key = None
    for line in match.group(1).splitlines():
        list_item = re.match(r"^\s+-\s*(.+)\s*$", line)
        if list_item and current_key:
            previous = frontmatter.get(current_key, "")
            frontmatter[current_key] = previous + (", " if previous else "") + list_item.group(1).strip()
            continue
        if ":" not in line:
            current_key = None
            continue
        key, _, value = line.partition(":")
        current_key = key.strip()
        frontmatter[current_key] = value.strip().strip('"').strip("'")
    return frontmatter


def extract_domain(tags: str, fallback: str) -> str:
    domain_match = re.search(r"[\w-]+/[\w-]+", tags)
    if domain_match:
        return domain_match.group(0)
    tag_match = re.search(r"[\w-]+", tags)
    if tag_match:
        return tag_match.group(0)
    return "navigation" if fallback == "map" else "uncategorized"


def build_entry(title: str, type_name: str, domain: str, description: str, grade: str) -> str:
    return f"- [[{title}]] - {type_name} - {domain} - {description} - {grade}"


def index_path_for(config: dict, type_name: str) -> Path | None:
    index_name = config.get("index_files", {}).get(type_name)
    if not index_name:
        return None
    return configured_dir(config, "indexes_dir") / index_name


def already_indexed(index_path: Path, title: str) -> bool:
    return index_path.exists() and f"[[{title}]]" in index_path.read_text(encoding="utf-8")


def append_to_index(config: dict, index_path: Path, entry: str, domain: str):
    index_path.parent.mkdir(parents=True, exist_ok=True)
    if not index_path.exists():
        index_path.write_text(f"# {index_path.stem}\n\n{entry}\n", encoding="utf-8")
        return
    content = index_path.read_text(encoding="utf-8")
    section = config.get("domain_sections", {}).get(domain.split("/")[0].lower())
    if section:
        pattern = re.compile(rf"^##\s+{re.escape(section)}\s*$", re.MULTILINE)
        match = pattern.search(content)
        if match:
            rest = content[match.end():]
            next_h2 = re.search(r"\n##\s", rest)
            insert_pos = match.end() + next_h2.start() if next_h2 else len(content)
            content = content[:insert_pos].rstrip() + "\n" + entry + "\n" + content[insert_pos:]
            index_path.write_text(content, encoding="utf-8")
            return
    content = content.rstrip() + "\n" + entry + "\n"
    index_path.write_text(content, encoding="utf-8")


def update_description(index_path: Path, title: str, description: str) -> bool:
    content = index_path.read_text(encoding="utf-8")
    pattern = re.compile(r"(- \[\[" + re.escape(title) + r"\]\] - \S+ - \S+ - )(.+)( - [^\s\n-]+\s*$)", re.MULTILINE)
    new_content, count = pattern.subn(lambda m: m.group(1) + description + m.group(3), content, count=1)
    if count:
        index_path.write_text(new_content, encoding="utf-8")
        return True
    return False


def count_notes(config: dict, type_name: str) -> int:
    dir_name = config.get("note_types", {}).get(type_name)
    if not dir_name:
        return 0
    target = configured_dir(config, "knowledge_dir") / dir_name
    if not target.exists():
        return 0
    excluded = {"README.md", "AGENTS.md", "CLAUDE.md"}
    return sum(1 for f in target.rglob("*.md") if f.name not in excluded and not f.name.startswith("_"))


def update_global_index(config: dict) -> dict:
    index_name = config.get("index_files", {}).get("global")
    if not index_name:
        return {"updated": False, "reason": "No global index configured"}
    path = configured_dir(config, "indexes_dir") / index_name
    if not path.exists():
        return {"updated": False, "reason": "Global index not found"}
    content = path.read_text(encoding="utf-8")
    counts = {type_name: count_notes(config, type_name) for type_name in config.get("note_types", {})}
    for key, value in counts.items():
        content = re.sub(rf"(`?{re.escape(key)}`?\s*:\s*)(\d+)(\s*notes?)", rf"\g<1>{value}\3", content, count=1)
    today = date.today().isoformat()
    content = re.sub(r"^(updated:\s*)\d{4}-\d{2}-\d{2}", rf"\g<1>{today}", content, count=1, flags=re.MULTILINE)
    content = re.sub(r"## Last updated\s*\n[^\n]*", f"## Last updated\n{today}", content)
    path.write_text(content, encoding="utf-8")
    return {"updated": True, "counts": counts}


def process_note(config: dict, note_path: Path, action: str, description: str | None, grade: str) -> dict:
    fm = read_frontmatter(note_path)
    rel_path = relative_to_vault(config, note_path)
    type_name = fm.get("type", "").lower() or infer_note_type(config, rel_path)
    title = note_path.stem
    result = {"note": rel_path, "title": title, "type": type_name, "indexed": False, "action": action}
    index_path = index_path_for(config, type_name)
    if not index_path:
        result["message"] = f"No index configured for type {type_name}"
        return result
    if already_indexed(index_path, title):
        if action == "enrich" and description:
            result["message"] = "Description updated" if update_description(index_path, title, description) else "Existing entry kept"
        else:
            result["message"] = "Already indexed"
        result["indexed"] = True
        return result
    tags = fm.get("tags", "")
    domain = extract_domain(tags, type_name)
    status_or_grade = fm.get("status", "active") if type_name == "map" else grade
    entry = build_entry(title, type_name, domain, description or "To complete", status_or_grade)
    append_to_index(config, index_path, entry, domain)
    result["indexed"] = True
    result["entry"] = entry
    result["message"] = f"Entry added to {index_path.name}"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="Note paths")
    parser.add_argument("--config", help="Path to config.yml")
    parser.add_argument("--action", choices=["create", "enrich"], default="create")
    parser.add_argument("--description")
    parser.add_argument("--grade", choices=["dense", "intermediate", "fragile", "legacy"], default="intermediate")
    args = parser.parse_args()
    if not args.paths:
        parser.print_help()
        return
    config = load_config(args.config)
    processed = []
    for item in args.paths:
        note_path = vault_path(config, item)
        if not note_path.exists():
            processed.append({"note": item, "error": "File not found"})
            continue
        processed.append(process_note(config, note_path, args.action, args.description, args.grade))
    print(json.dumps({"processed": processed, "global_index": update_global_index(config)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

