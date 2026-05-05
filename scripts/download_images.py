#!/usr/bin/env python3
"""Download external Markdown images from an inbox source into local assets."""

from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from config_loader import configured_dir, load_config, relative_to_vault, vault_path

MIN_IMAGE_SIZE = 500
REQUEST_TIMEOUT = 10
USER_AGENT = "Mozilla/5.0"
CONTENT_TYPE_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}


def find_image_refs(content: str) -> list[tuple[str, str, str]]:
    return [(m.group(0), m.group(1), m.group(2)) for m in re.finditer(r"!\[([^\]]*)\]\((https?://[^\)\"\s]+)\)", content)]


def resolve_url(url: str) -> str:
    if "substackcdn.com/image/fetch/" in url:
        match = re.search(r"(https?%3A%2F%2F\S+)$", url)
        if match:
            return urllib.parse.unquote(match.group(1))
    return url


def ext_from_content_type(content_type: str, url: str) -> str:
    ext = CONTENT_TYPE_TO_EXT.get(content_type.split(";")[0].strip())
    if ext:
        return ext
    for suffix in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"):
        if suffix in url.lower():
            return ".jpg" if suffix == ".jpeg" else suffix
    return ".png"


def safe_stem(name: str) -> str:
    sanitized = re.sub(r"[^\w-]", "_", name)
    return re.sub(r"_+", "_", sanitized).strip("_")[:50] or "source"


def download(url: str, dest_stem: Path) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
            content_type = response.headers.get("Content-Type", "image/png")
            data = response.read()
        if len(data) < MIN_IMAGE_SIZE:
            return {"ok": False, "reason": f"Too small ({len(data)} bytes)"}
        path = dest_stem.with_suffix(ext_from_content_type(content_type, url))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return {"ok": True, "path": path, "size": len(data), "content_type": content_type}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "reason": f"HTTP {exc.code} {exc.reason}"}
    except urllib.error.URLError as exc:
        return {"ok": False, "reason": f"URL error: {exc.reason}"}
    except Exception as exc:  # pragma: no cover
        return {"ok": False, "reason": str(exc)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", help="Source path relative to vault root")
    parser.add_argument("--config", help="Path to config.yml")
    args = parser.parse_args()
    if not args.source:
        parser.print_help()
        return
    config = load_config(args.config)
    source_path = vault_path(config, args.source)
    if not source_path.exists():
        print(json.dumps({"error": f"Source not found: {args.source}"}))
        raise SystemExit(1)
    inbox = configured_dir(config, "inbox_dir")
    assets_dir = inbox / "assets" / safe_stem(source_path.stem)
    content = source_path.read_text(encoding="utf-8")
    refs = find_image_refs(content)
    new_content = content
    results = []
    for idx, (full_match, _alt, url) in enumerate(refs, start=1):
        resolved = resolve_url(url)
        result = download(resolved, assets_dir / f"img-{idx:03d}")
        if result["ok"]:
            local = relative_to_vault(config, result["path"])
            new_content = new_content.replace(full_match, f"![[{local}]]", 1)
            results.append({"index": idx, "ok": True, "local": local, "size_kb": round(result["size"] / 1024, 1)})
        else:
            results.append({"index": idx, "ok": False, "reason": result["reason"]})
    if any(item["ok"] for item in results):
        source_path.write_text(new_content, encoding="utf-8")
    print(json.dumps({
        "source": relative_to_vault(config, source_path),
        "images_found": len(refs),
        "downloaded": sum(1 for item in results if item["ok"]),
        "details": results,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

