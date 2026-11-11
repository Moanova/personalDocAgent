# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : tests/unit/test_config.py
# Version      : 0.1.0
# Date         : 2026-11-11
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Unit tests for the YAML configuration loading."""

import pytest

from personaldocagent.config import load_config


def test_loads_repo_config(config_dir):
    """The repository config loads with the expected routes and defaults."""
    config = load_config(config_dir)
    assert config.perimeter.follow_symlinks is False
    assert ".pdf" in config.routing.formats["ocr"]
    assert ".docx" in config.routing.formats["direct_read"]
    assert config.routing.default_route == "reject"
    assert config.policy.max_keywords > 0


def test_missing_files_raise_file_not_found(tmp_path):
    """An empty configuration directory raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path)


def test_unknown_field_is_rejected(tmp_path):
    """An unknown YAML key raises TypeError (strict dataclass validation)."""
    (tmp_path / "perimeter_access.yaml").write_text("unknown_field: 1\n", encoding="utf-8")
    (tmp_path / "routing.yaml").write_text("{}\n", encoding="utf-8")
    (tmp_path / "analysis_policy.yaml").write_text("{}\n", encoding="utf-8")
    with pytest.raises(TypeError):
        load_config(tmp_path)
