from pathlib import Path

import pytest

from lint_scope import (
    backlinks,
    capture_debts,
    frontmatter,
    incomplete_sections,
    wikilinks,
)


CONCEPT_WITH_LIMITS = """\
---
type: concept
map: "[[Product thinking]]"
---

# Useful friction

### Limits and counterexamples
Friction becomes harmful on low-risk, frequent actions.
"""

CONCEPT_WITHOUT_LIMITS = """\
---
type: concept
map: "[[Product thinking]]"
---

# Shallow concept

No limits section here.
"""

CONCEPT_WITH_EMPTY_LIMITS = """\
---
type: concept
---

# Concept

### Limits and counterexamples
Too short.
"""


class TestFrontmatter:
    def test_parses_type(self):
        fm = frontmatter(CONCEPT_WITH_LIMITS)
        assert fm["type"] == "concept"

    def test_empty_when_no_frontmatter(self):
        assert frontmatter("# Just a title") == {}


class TestWikilinks:
    def test_finds_links(self):
        content = "See [[Concept A]] and [[Concept B|alias]]."
        links = wikilinks(content)
        assert "Concept A" in links
        assert "Concept B" in links

    def test_empty_content(self):
        assert wikilinks("No links here.") == set()


class TestIncompleteSections:
    def test_concept_with_limits_is_complete(self, tmp_path):
        f = tmp_path / "note.md"
        f.write_text(CONCEPT_WITH_LIMITS)
        assert incomplete_sections(f) == []

    def test_concept_without_limits_flagged(self, tmp_path):
        f = tmp_path / "note.md"
        f.write_text(CONCEPT_WITHOUT_LIMITS)
        missing = incomplete_sections(f)
        assert "Limits and counterexamples" in missing

    def test_concept_with_empty_limits_flagged(self, tmp_path):
        f = tmp_path / "note.md"
        f.write_text(CONCEPT_WITH_EMPTY_LIMITS)
        missing = incomplete_sections(f)
        assert "Limits and counterexamples" in missing

    def test_non_concept_always_passes(self, tmp_path):
        f = tmp_path / "map.md"
        f.write_text("---\ntype: map\n---\n\n# A map\n\nNo limits needed.\n")
        assert incomplete_sections(f) == []


class TestBacklinks:
    def test_finds_backlink(self, config, vault):
        note = vault / "Knowledge" / "Concepts" / "Useful friction.md"
        note.write_text("# Useful friction\n")
        other = vault / "Knowledge" / "Maps" / "Product thinking.md"
        other.write_text("# Product thinking\n\nSee [[Useful friction]].\n")
        links = backlinks(config, "Useful friction", note)
        assert any("Product thinking" in link for link in links)

    def test_excludes_self(self, config, vault):
        note = vault / "Knowledge" / "Concepts" / "Self ref.md"
        note.write_text("# Self ref\n\nSee [[Self ref]].\n")
        links = backlinks(config, "Self ref", note)
        assert links == []

    def test_no_backlinks(self, config, vault):
        note = vault / "Knowledge" / "Concepts" / "Orphan.md"
        note.write_text("# Orphan\n")
        assert backlinks(config, "Orphan", note) == []


class TestCaptureDebts:
    def test_finds_unlisted_concept(self, config, vault):
        note = vault / "Knowledge" / "Concepts" / "Note.md"
        note.write_text(
            "---\ntype: concept\n---\n\n# Note\n\n"
            "The concept of Attention residue affects focus.\n"
        )
        debts = capture_debts(config, note)
        assert any("Attention residue" in d for d in debts)

    def test_skips_already_known_concept(self, config, vault):
        known = vault / "Knowledge" / "Concepts" / "Attention residue.md"
        known.write_text("# Attention residue\n")
        note = vault / "Knowledge" / "Concepts" / "Note.md"
        note.write_text(
            "---\ntype: concept\n---\n\n# Note\n\n"
            "The concept of Attention residue affects focus.\n"
        )
        debts = capture_debts(config, note)
        assert not any("Attention residue" in d for d in debts)
