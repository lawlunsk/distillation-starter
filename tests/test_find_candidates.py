import json
from pathlib import Path

import pytest

from find_candidates import cosine, extract_vector, load_vectors, parse_ajson

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

pytestmark = pytest.mark.skipif(not HAS_NUMPY, reason="numpy not installed")


def write_ajson(path: Path, key: str, rel_path: str, model_key: str, vec: list):
    content = json.dumps({key: {"path": rel_path, "embeddings": {model_key: {"vec": vec}}}})
    path.write_text(content.strip("{}").strip() + ",\n")


class TestCosine:
    def test_identical_vectors(self):
        a = np.array([1.0, 0.0, 0.0])
        assert cosine(a, a) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        a = np.array([1.0, 0.0, 0.0])
        b = np.array([0.0, 1.0, 0.0])
        assert cosine(a, b) == pytest.approx(0.0)

    def test_zero_vector(self):
        a = np.array([1.0, 0.0, 0.0])
        zero = np.array([0.0, 0.0, 0.0])
        assert cosine(a, zero) == 0.0
        assert cosine(zero, a) == 0.0

    def test_opposite_vectors(self):
        a = np.array([1.0, 0.0])
        b = np.array([-1.0, 0.0])
        assert cosine(a, b) == pytest.approx(-1.0)


class TestParseAjson:
    def test_parses_valid_file(self, tmp_path):
        f = tmp_path / "data.ajson"
        write_ajson(f, "smart_sources:Inbox/note.md", "Inbox/note.md", "test-model", [1.0, 0.0, 0.0])
        entries = list(parse_ajson(f))
        assert len(entries) == 1
        key, entry = entries[0]
        assert entry["path"] == "Inbox/note.md"

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.ajson"
        f.write_text("")
        assert list(parse_ajson(f)) == []

    def test_malformed_json(self, tmp_path):
        f = tmp_path / "bad.ajson"
        f.write_text("this is not json,")
        assert list(parse_ajson(f)) == []


class TestExtractVector:
    def test_extracts_matching_vector(self, tmp_path):
        f = tmp_path / "data.ajson"
        write_ajson(f, "smart_sources:Inbox/note.md", "Inbox/note.md", "test-model", [1.0, 0.0, 0.0])
        result = extract_vector(f, "test-model", 3)
        assert result is not None
        path, vec = result
        assert path == "Inbox/note.md"
        assert list(vec) == pytest.approx([1.0, 0.0, 0.0])

    def test_returns_none_for_wrong_dims(self, tmp_path):
        f = tmp_path / "data.ajson"
        write_ajson(f, "smart_sources:Inbox/note.md", "Inbox/note.md", "test-model", [1.0, 0.0])
        assert extract_vector(f, "test-model", 3) is None

    def test_returns_none_for_wrong_model(self, tmp_path):
        f = tmp_path / "data.ajson"
        write_ajson(f, "smart_sources:Inbox/note.md", "Inbox/note.md", "other-model", [1.0, 0.0, 0.0])
        assert extract_vector(f, "test-model", 3) is None

    def test_skips_non_smart_sources_key(self, tmp_path):
        f = tmp_path / "data.ajson"
        content = json.dumps({"other:key": {"path": "x.md", "embeddings": {"test-model": {"vec": [1.0, 0.0, 0.0]}}}})
        f.write_text(content.strip("{}").strip() + ",\n")
        assert extract_vector(f, "test-model", 3) is None


class TestLoadVectors:
    def test_loads_knowledge_vectors(self, config, vault):
        multi_dir = vault / ".smart-env" / "multi"
        f = multi_dir / "concepts.ajson"
        write_ajson(
            f,
            "smart_sources:Knowledge/Concepts/Note.md",
            "Knowledge/Concepts/Note.md",
            "test-model",
            [1.0, 0.0, 0.0],
        )
        vectors = load_vectors(config, "Knowledge/")
        assert len(vectors) == 1
        assert vectors[0][0] == "Knowledge/Concepts/Note.md"

    def test_excludes_inbox_from_knowledge_scope(self, config, vault):
        multi_dir = vault / ".smart-env" / "multi"
        f = multi_dir / "inbox.ajson"
        write_ajson(f, "smart_sources:Inbox/note.md", "Inbox/note.md", "test-model", [1.0, 0.0, 0.0])
        vectors = load_vectors(config, "Knowledge/")
        assert vectors == []

    def test_returns_empty_when_no_multi_dir(self, config):
        config["smart_connections"]["multi_dir"] = ".smart-env/nonexistent"
        assert load_vectors(config, "Knowledge/") == []
