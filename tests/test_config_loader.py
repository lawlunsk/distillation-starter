import os
from pathlib import Path

import pytest

from config_loader import (
    _deep_merge,
    _parse_scalar,
    _parse_simple_yaml,
    infer_note_type,
    is_excluded,
    load_config,
    relative_to_vault,
    vault_path,
)


class TestParseScalar:
    def test_bool_true(self):
        assert _parse_scalar("true") is True

    def test_bool_false(self):
        assert _parse_scalar("False") is False

    def test_null(self):
        assert _parse_scalar("null") is None
        assert _parse_scalar("~") is None

    def test_int(self):
        assert _parse_scalar("42") == 42
        assert _parse_scalar("-3") == -3

    def test_float(self):
        assert _parse_scalar("3.14") == 3.14

    def test_string(self):
        assert _parse_scalar("hello") == "hello"

    def test_quoted_string(self):
        assert _parse_scalar('"my value"') == "my value"
        assert _parse_scalar("'my value'") == "my value"

    def test_list(self):
        assert _parse_scalar("[a, b, c]") == ["a", "b", "c"]

    def test_empty_list(self):
        assert _parse_scalar("[]") == []

    def test_empty_string(self):
        assert _parse_scalar("") == ""


class TestParseSimpleYaml:
    def test_flat_keys(self):
        result = _parse_simple_yaml("vault_root: /my/vault\ninbox_dir: Inbox\n")
        assert result["vault_root"] == "/my/vault"
        assert result["inbox_dir"] == "Inbox"

    def test_nested_keys(self):
        text = "smart_connections:\n  enabled: true\n  vector_dimensions: 384\n"
        result = _parse_simple_yaml(text)
        assert result["smart_connections"]["enabled"] is True
        assert result["smart_connections"]["vector_dimensions"] == 384

    def test_comments_ignored(self):
        result = _parse_simple_yaml("# comment\nvault_root: /vault # inline\n")
        assert result["vault_root"] == "/vault"

    def test_empty_text(self):
        assert _parse_simple_yaml("") == {}

    def test_list_value(self):
        result = _parse_simple_yaml("files: [README.md, CLAUDE.md]\n")
        assert result["files"] == ["README.md", "CLAUDE.md"]


class TestDeepMerge:
    def test_flat_override(self):
        result = _deep_merge({"a": 1, "b": 2}, {"b": 99})
        assert result == {"a": 1, "b": 99}

    def test_nested_merge(self):
        base = {"sc": {"enabled": True, "dims": 384}}
        override = {"sc": {"dims": 3}}
        result = _deep_merge(base, override)
        assert result["sc"]["enabled"] is True
        assert result["sc"]["dims"] == 3

    def test_nested_override_with_scalar(self):
        base = {"sc": {"enabled": True}}
        override = {"sc": "disabled"}
        result = _deep_merge(base, override)
        assert result["sc"] == "disabled"

    def test_does_not_mutate_base(self):
        base = {"a": {"x": 1}}
        _deep_merge(base, {"a": {"x": 2}})
        assert base["a"]["x"] == 1


class TestLoadConfig:
    def test_defaults_when_no_file(self):
        config = load_config("/nonexistent/path.yml")
        assert config["inbox_dir"] == "Inbox"
        assert config["knowledge_dir"] == "Knowledge"
        assert config["_config_path"] is None

    def test_loads_and_merges_file(self, tmp_path):
        cfg = tmp_path / "config.yml"
        cfg.write_text("vault_root: /my/vault\ninbox_dir: MyInbox\n")
        config = load_config(str(cfg))
        assert config["inbox_dir"] == "MyInbox"
        assert config["knowledge_dir"] == "Knowledge"

    def test_relative_vault_root_resolved_against_config_dir(self, tmp_path):
        cfg = tmp_path / "config.yml"
        cfg.write_text("vault_root: vault\n")
        config = load_config(str(cfg))
        assert config["vault_root"] == str((tmp_path / "vault").resolve())

    def test_env_var_config_path(self, tmp_path, monkeypatch):
        cfg = tmp_path / "env_config.yml"
        cfg.write_text("inbox_dir: EnvInbox\n")
        monkeypatch.setenv("DISTILLATION_CONFIG", str(cfg))
        config = load_config()
        assert config["inbox_dir"] == "EnvInbox"


class TestVaultPath:
    def test_absolute_path_returned_as_is(self, config):
        result = vault_path(config, "/absolute/path")
        assert result == Path("/absolute/path")

    def test_relative_path_resolved_against_vault(self, config, vault):
        result = vault_path(config, "Inbox/file.md")
        assert result == vault / "Inbox" / "file.md"


class TestRelativeToVault:
    def test_path_inside_vault(self, config, vault):
        path = vault / "Knowledge" / "Concepts" / "Note.md"
        result = relative_to_vault(config, path)
        assert result == "Knowledge/Concepts/Note.md"

    def test_path_outside_vault(self, config):
        result = relative_to_vault(config, Path("/some/other/path.md"))
        assert result == "/some/other/path.md"


class TestInferNoteType:
    def test_concept(self, config):
        assert infer_note_type(config, "Knowledge/Concepts/My note.md") == "concept"

    def test_map(self, config):
        assert infer_note_type(config, "Knowledge/Maps/Product.md") == "map"

    def test_unknown(self, config):
        assert infer_note_type(config, "Knowledge/Unknown/Note.md") == "unknown"

    def test_inbox_is_unknown(self, config):
        assert infer_note_type(config, "Inbox/article.md") == "unknown"


class TestIsExcluded:
    def test_excluded_filename(self, config):
        assert is_excluded(config, "Knowledge/Concepts/README.md") is True

    def test_excluded_path_contains(self, config):
        assert is_excluded(config, "Knowledge/Templates/note.md") is True

    def test_not_excluded(self, config):
        assert is_excluded(config, "Knowledge/Concepts/My note.md") is False
