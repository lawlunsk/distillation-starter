from pathlib import Path

import pytest

from update_indexes import (
    already_indexed,
    append_to_index,
    build_entry,
    count_notes,
    extract_domain,
    process_note,
    read_frontmatter,
    update_description,
    update_global_index,
)


CONCEPT_CONTENT = """\
---
created: 2026-01-01
updated: 2026-01-01
type: concept
status: draft
map: "[[Product thinking]]"
tags: [product, design]
---

# Useful friction

## Summary
A concept summary.

### Limits and counterexamples
Friction becomes harmful on low-risk, frequent actions.
"""


class TestReadFrontmatter:
    def test_parses_basic_fields(self, tmp_path):
        f = tmp_path / "note.md"
        f.write_text(CONCEPT_CONTENT)
        fm = read_frontmatter(f)
        assert fm["type"] == "concept"
        assert fm["status"] == "draft"

    def test_returns_empty_when_no_frontmatter(self, tmp_path):
        f = tmp_path / "note.md"
        f.write_text("# Just a title\n\nNo frontmatter here.")
        assert read_frontmatter(f) == {}

    def test_returns_empty_when_missing(self, tmp_path):
        f = tmp_path / "missing.md"
        assert read_frontmatter(f) == {}


class TestExtractDomain:
    def test_domain_slash_format(self):
        assert extract_domain("[product/design]", "concept") == "product/design"

    def test_single_tag(self):
        assert extract_domain("[product]", "concept") == "product"

    def test_empty_tags_concept(self):
        assert extract_domain("", "concept") == "uncategorized"

    def test_empty_tags_map(self):
        assert extract_domain("", "map") == "navigation"


class TestBuildEntry:
    def test_format(self):
        entry = build_entry("Useful friction", "concept", "product", "pauses protect attention", "intermediate")
        assert entry == "- [[Useful friction]] - concept - product - pauses protect attention - intermediate"


class TestAlreadyIndexed:
    def test_returns_true_when_present(self, tmp_path):
        idx = tmp_path / "index.md"
        idx.write_text("- [[Useful friction]] - concept - product - desc - intermediate\n")
        assert already_indexed(idx, "Useful friction") is True

    def test_returns_false_when_absent(self, tmp_path):
        idx = tmp_path / "index.md"
        idx.write_text("- [[Other note]] - concept - product - desc - intermediate\n")
        assert already_indexed(idx, "Useful friction") is False

    def test_returns_false_when_missing(self, tmp_path):
        idx = tmp_path / "missing.md"
        assert already_indexed(idx, "Anything") is False


class TestUpdateDescription:
    def test_updates_existing_description(self, tmp_path):
        idx = tmp_path / "index.md"
        idx.write_text("- [[My note]] - concept - product - old description - intermediate\n")
        result = update_description(idx, "My note", "new description")
        assert result is True
        assert "new description" in idx.read_text()
        assert "old description" not in idx.read_text()

    def test_returns_false_when_title_not_found(self, tmp_path):
        idx = tmp_path / "index.md"
        idx.write_text("- [[Other]] - concept - product - desc - intermediate\n")
        assert update_description(idx, "My note", "new") is False


class TestCountNotes:
    def test_counts_md_files(self, config, vault):
        concepts = vault / "Knowledge" / "Concepts"
        (concepts / "Note A.md").write_text("# A")
        (concepts / "Note B.md").write_text("# B")
        assert count_notes(config, "concept") == 2

    def test_excludes_readme(self, config, vault):
        concepts = vault / "Knowledge" / "Concepts"
        (concepts / "Note.md").write_text("# Note")
        (concepts / "README.md").write_text("# README")
        assert count_notes(config, "concept") == 1

    def test_returns_zero_for_missing_dir(self, config):
        assert count_notes(config, "pivot") == 0

    def test_returns_zero_for_unknown_type(self, config):
        assert count_notes(config, "nonexistent") == 0


class TestProcessNote:
    def test_creates_entry_in_index(self, config, vault):
        note = vault / "Knowledge" / "Concepts" / "Useful friction.md"
        note.write_text(CONCEPT_CONTENT)
        idx = vault / "System" / "Indexes" / "Index - Concepts.md"
        result = process_note(config, note, "create", "pauses protect attention", "intermediate")
        assert result["indexed"] is True
        assert "[[Useful friction]]" in idx.read_text()

    def test_skips_if_already_indexed(self, config, vault):
        note = vault / "Knowledge" / "Concepts" / "Useful friction.md"
        note.write_text(CONCEPT_CONTENT)
        idx = vault / "System" / "Indexes" / "Index - Concepts.md"
        idx.write_text("- [[Useful friction]] - concept - product - desc - intermediate\n")
        result = process_note(config, note, "create", None, "intermediate")
        assert result["indexed"] is True
        assert result["message"] == "Already indexed"

    def test_unknown_type_no_index(self, config, vault):
        note = vault / "Knowledge" / "Concepts" / "Mystery.md"
        note.write_text("---\ntype: custom\n---\n\n# Mystery\n")
        result = process_note(config, note, "create", None, "intermediate")
        assert result["indexed"] is False


class TestUpdateGlobalIndex:
    def test_updates_counts(self, config, vault):
        idx = vault / "System" / "Indexes" / "Index - Global.md"
        idx.write_text(
            "---\ncreated: 2026-01-01\nupdated: 2026-01-01\n---\n\n"
            "# Index - Global\n\n## Counts\n\n- concept: 0 notes\n\n## Last updated\n2026-01-01\n"
        )
        (vault / "Knowledge" / "Concepts" / "Note.md").write_text("# Note")
        result = update_global_index(config)
        assert result["updated"] is True
        assert result["counts"]["concept"] == 1
        assert "concept: 1 notes" in idx.read_text()

    def test_returns_not_updated_when_missing(self, config):
        result = update_global_index(config)
        assert result["updated"] is False
