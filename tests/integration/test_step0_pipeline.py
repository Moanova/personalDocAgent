# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : tests/integration/test_step0_pipeline.py
# Version      : 0.1.0
# Date         : 2026-11-12
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Integration test for the step 0 orchestration (task T2.3, TI-03 in tests/plan_tests.md)."""

from pathlib import Path

from personaldocagent.config import AnalysisPolicy, Config, PerimeterConfig, RoutingConfig
from personaldocagent.db.connection import connect, init_db
from personaldocagent.pipeline import acquire


def _config(root: Path, exclusions=()) -> Config:
    return Config(
        perimeter=PerimeterConfig(allowed_roots=[str(root)], exclusions=list(exclusions)),
        routing=RoutingConfig(
            default_route="reject",
            formats={
                "direct_read": [".txt", ".md", ".html", ".htm", ".docx", ".odt"],
                "ocr": [".pdf"],
            },
        ),
        policy=AnalysisPolicy(),
    )


def test_acquire_full_tree(tmp_path):
    """TI-03: txt+html acquired, excluded subdirectory never walked, .xyz rejected and journalled."""
    root = tmp_path / "collection"
    (root / "sub").mkdir(parents=True)
    (root / "archive").mkdir()
    (root / "a.txt").write_text("aaa", encoding="utf-8")
    (root / "sub" / "b.html").write_text("<p>bbb</p>", encoding="utf-8")
    (root / "archive" / "old.txt").write_text("secret", encoding="utf-8")
    (root / "c.xyz").write_text("nope", encoding="utf-8")
    config = _config(root, exclusions=[str((root / "archive").resolve())])
    init_db(tmp_path / "test.db")
    conn = connect(tmp_path / "test.db")
    try:
        journal = tmp_path / "rejections.log"
        results = acquire(config, root, conn, journal)
        by_name = {Path(r.source_file).name: r for r in results}
        assert set(by_name) == {"a.txt", "b.html"}
        assert by_name["a.txt"].text == "aaa"
        assert "bbb" in by_name["b.html"].text
        log = journal.read_text(encoding="utf-8")
        assert "unsupported_format" in log
        assert "c.xyz" in log
        assert "old.txt" not in log
    finally:
        conn.close()
