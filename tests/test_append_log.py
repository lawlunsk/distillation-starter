import re
from datetime import date
from pathlib import Path

import pytest

from append_log import append_entry, default_header, ensure_log


class TestDefaultHeader:
    def test_contains_today(self):
        today = date.today().isoformat()
        header = default_header(today)
        assert today in header
        assert "Distillation Log" in header
        assert "type: log" in header


class TestEnsureLog:
    def test_creates_file_when_missing(self, tmp_path):
        log = tmp_path / "System" / "log.md"
        ensure_log(log)
        assert log.exists()
        content = log.read_text()
        assert "Distillation Log" in content

    def test_does_not_overwrite_existing(self, tmp_path):
        log = tmp_path / "log.md"
        log.write_text("existing content")
        ensure_log(log)
        assert log.read_text() == "existing content"


class TestAppendEntry:
    def test_creates_log_if_missing(self, tmp_path):
        log = tmp_path / "log.md"
        append_entry(log, "## 2026-01-01 - My session\n\nCreated: [[Note]]\n")
        assert log.exists()
        assert "My session" in log.read_text()

    def test_entry_appears_before_previous_entries(self, tmp_path):
        log = tmp_path / "log.md"
        today = date.today().isoformat()
        log.write_text(
            f"---\ncreated: {today}\nupdated: {today}\ntype: log\nstatus: active\n---\n\n"
            "---\n\n## Old session\n\nold content\n"
        )
        append_entry(log, "## New session\n\nnew content\n")
        content = log.read_text()
        assert content.index("New session") < content.index("Old session")

    def test_updates_frontmatter_date(self, tmp_path, monkeypatch):
        log = tmp_path / "log.md"
        log.write_text(
            "---\ncreated: 2026-01-01\nupdated: 2026-01-01\ntype: log\nstatus: active\n---\n\n"
            "---\n\n## Old session\n\ncontent\n"
        )
        today = date.today().isoformat()
        append_entry(log, "## New session\n\ncontent\n")
        content = log.read_text()
        assert f"updated: {today}" in content
