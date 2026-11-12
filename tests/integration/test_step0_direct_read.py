# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : tests/integration/test_direct_read.py
# Version      : 0.1.0
# Date         : 2026-11-12
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Integration test for the step 0 direct read flow (task T2.1, TI-01 in tests/plan_tests.md)."""

from pathlib import Path

import pytest

from personaldocagent.acquisition.direct_read import read_direct
from personaldocagent.config import AnalysisPolicy, Config, PerimeterConfig, RoutingConfig
from personaldocagent.db.connection import connect, init_db
from personaldocagent.routing import run_step0_checks


def _config(root: Path) -> Config:
    return Config(
        perimeter=PerimeterConfig(allowed_roots=[str(root)]),
        routing=RoutingConfig(
            default_route="reject",
            formats={
                "direct_read": [".txt", ".md", ".html", ".htm", ".docx", ".odt"],
                "ocr": [".pdf"],
            },
        ),
        policy=AnalysisPolicy(),
    )


def test_step0_accepted_file_is_read_directly(tmp_path):
    """TI-01: a permitted direct_read file passes the step 0 checks and is read."""
    root = tmp_path / "collection"
    root.mkdir()
    target = root / "note.txt"
    target.write_text("contenu du document", encoding="utf-8")
    init_db(tmp_path / "test.db")
    conn = connect(tmp_path / "test.db")
    try:
        journal = tmp_path / "rejections.log"
        step0 = run_step0_checks(target, _config(root), conn, journal)
        assert step0.accepted is True
        assert step0.route == "direct_read"
        result = read_direct(target)
        assert result.route == step0.route
        assert result.text == "contenu du document"
        assert not journal.exists()
    finally:
        conn.close()


def test_step0_rejected_file_is_logged_and_not_readable(tmp_path):
    """TI-01: an unsupported format is rejected and journalled without being read."""
    root = tmp_path / "collection"
    root.mkdir()
    target = root / "data.xyz"
    target.write_text("contenu interne", encoding="utf-8")
    init_db(tmp_path / "test.db")
    conn = connect(tmp_path / "test.db")
    try:
        journal = tmp_path / "rejections.log"
        step0 = run_step0_checks(target, _config(root), conn, journal)
        assert step0.accepted is False
        assert step0.reason == "unsupported_format"
        assert "unsupported_format" in journal.read_text(encoding="utf-8")
        with pytest.raises(ValueError, match="Unsupported extension"):
            read_direct(target)
    finally:
        conn.close()
