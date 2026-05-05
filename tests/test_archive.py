from pathlib import Path

import pytest

from archive_source import archive, is_inside, unique_destination


class TestIsInside:
    def test_child_inside_parent(self, tmp_path):
        child = tmp_path / "a" / "b.md"
        assert is_inside(child, tmp_path) is True

    def test_child_is_parent(self, tmp_path):
        assert is_inside(tmp_path, tmp_path) is True

    def test_child_outside_parent(self, tmp_path):
        other = tmp_path.parent
        child = tmp_path / "file.md"
        assert is_inside(other, child) is False


class TestUniqueDestination:
    def test_returns_path_when_free(self, tmp_path):
        target = tmp_path / "note.md"
        assert unique_destination(target) == target

    def test_increments_when_exists(self, tmp_path):
        target = tmp_path / "note.md"
        target.write_text("x")
        result = unique_destination(target)
        assert result == tmp_path / "note_2.md"

    def test_increments_past_existing_suffix(self, tmp_path):
        (tmp_path / "note.md").write_text("x")
        (tmp_path / "note_2.md").write_text("x")
        result = unique_destination(tmp_path / "note.md")
        assert result == tmp_path / "note_3.md"


class TestArchive:
    def test_happy_path(self, config, vault):
        source = vault / "Inbox" / "article.md"
        source.write_text("# Article")
        result = archive(config, "Inbox/article.md")
        assert result["archived"] is True
        assert not source.exists()
        dest = Path(result["destination"])
        assert dest.suffix == ".md"

    def test_refuses_outside_inbox(self, config, vault):
        note = vault / "Knowledge" / "Concepts" / "Note.md"
        note.write_text("# Note")
        result = archive(config, "Knowledge/Concepts/Note.md")
        assert result["archived"] is False
        assert "inbox" in result["error"].lower()
        assert note.exists()

    def test_missing_source(self, config):
        result = archive(config, "Inbox/nonexistent.md")
        assert result["archived"] is False
        assert "not found" in result["error"].lower()

    def test_books_flag_creates_books_subdir(self, config, vault):
        source = vault / "Inbox" / "book.md"
        source.write_text("# Book")
        result = archive(config, "Inbox/book.md", books=True)
        assert result["archived"] is True
        assert "Books" in result["destination"]

    def test_unique_destination_on_conflict(self, config, vault):
        from datetime import date
        year = str(date.today().year)
        dest_dir = vault / "Archives" / "Inbox" / year
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / "article.md").write_text("existing")

        source = vault / "Inbox" / "article.md"
        source.write_text("new")
        result = archive(config, "Inbox/article.md")
        assert result["archived"] is True
        assert "article_2" in result["destination"]
