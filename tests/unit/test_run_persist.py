# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : tests/unit/test_run_persist.py
# Version      : 0.1.0
# Date         : 2026-11-12
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Unit tests for run() steps 0-1 (task T3.2, TU-25 and TU-26 in tests/plan_tests.md)."""

from pathlib import Path

from personaldocagent.db.connection import connect
from personaldocagent.pipeline import run


def _write_config(cfg: Path, root: Path) -> None:
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "perimeter_access.yaml").write_text(
        f"allowed_roots: ['{root}']\nexclusions: []\nfollow_symlinks: false\n",
        encoding="utf-8",
    )
    (cfg / "routing.yaml").write_text(
        "default_route: reject\n"
        "formats:\n"
        "  direct_read: [.txt, .md, .html, .htm, .docx, .odt]\n"
        "  ocr: [.pdf, .jpg, .jpeg, .png, .tif, .tiff, .webp]\n",
        encoding="utf-8",
    )
    (cfg / "analysis_policy.yaml").write_text(
        "max_keywords: 10\njson_naming_convention: snake_case\nauto_confidence_threshold: 0.9\n",
        encoding="utf-8",
    )


def _corpus(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "collection"
    root.mkdir()
    (root / "a.txt").write_text("contenu a", encoding="utf-8")
    (root / "b.md").write_text("contenu b", encoding="utf-8")
    cfg = tmp_path / "config"
    _write_config(cfg, root)
    return root, cfg, tmp_path / "data" / "app.db"


def test_run_writes_documents_and_conversions(tmp_path, monkeypatch):
    """TU-25: run() persists document+conversion rows and returns WriteResult(written=True)."""
    monkeypatch.chdir(tmp_path)
    _, cfg, base = _corpus(tmp_path)
    results = run(cfg, base)
    assert len(results) == 2
    assert all(r.written and r.reason is None for r in results)
    conn = connect(base)
    try:
        assert conn.execute("SELECT COUNT(*) FROM document").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM conversion").fetchone()[0] == 2
        row = conn.execute(
            "SELECT rowid FROM conversion_fts WHERE conversion_fts MATCH 'contenu'"
        ).fetchone()
        assert row is not None
    finally:
        conn.close()


def test_run_twice_is_idempotent(tmp_path, monkeypatch):
    """TU-26: second run -> duplicates rejected at step 0 (journalled), nothing acquired, db unchanged."""
    monkeypatch.chdir(tmp_path)
    _, cfg, base = _corpus(tmp_path)
    first = run(cfg, base)
    assert len(first) == 2
    assert all(r.written for r in first)
    second = run(cfg, base)
    assert second == []
    journal = (tmp_path / "data" / "rejections.log").read_text(encoding="utf-8")
    assert journal.count("duplicate") == 2
    conn = connect(base)
    try:
        assert conn.execute("SELECT COUNT(*) FROM document").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM conversion").fetchone()[0] == 2
    finally:
        conn.close()
