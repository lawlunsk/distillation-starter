import pytest


@pytest.fixture
def vault(tmp_path):
    (tmp_path / "Inbox").mkdir()
    (tmp_path / "Knowledge" / "Concepts").mkdir(parents=True)
    (tmp_path / "Knowledge" / "Maps").mkdir(parents=True)
    (tmp_path / "Knowledge" / "Frameworks").mkdir(parents=True)
    (tmp_path / "Knowledge" / "HowTo").mkdir(parents=True)
    (tmp_path / "Archives" / "Inbox").mkdir(parents=True)
    (tmp_path / "System" / "Indexes").mkdir(parents=True)
    (tmp_path / ".smart-env" / "multi").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def config(vault):
    return {
        "vault_root": str(vault),
        "inbox_dir": "Inbox",
        "knowledge_dir": "Knowledge",
        "archive_dir": "Archives/Inbox",
        "log_path": "System/distillation-log.md",
        "indexes_dir": "System/Indexes",
        "note_types": {
            "concept": "Concepts",
            "pivot": "Pivots",
            "framework": "Frameworks",
            "howto": "HowTo",
            "map": "Maps",
        },
        "index_files": {
            "global": "Index - Global.md",
            "concept": "Index - Concepts.md",
            "pivot": "Index - Pivots.md",
            "framework": "Index - Frameworks.md",
            "howto": "Index - HowTo.md",
            "map": "Index - Maps.md",
        },
        "smart_connections": {
            "enabled": True,
            "multi_dir": ".smart-env/multi",
            "model_key": "test-model",
            "vector_dimensions": 3,
            "candidate_min_similarity": 0.0,
            "crossref_similarity_threshold": 0.88,
        },
        "exclusions": {
            "files": ["README.md", "AGENTS.md", "CLAUDE.md"],
            "path_contains": ["Templates/"],
        },
        "domain_sections": {},
        "_config_path": None,
    }
