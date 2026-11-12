# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : tests/integration/test_pipeline_persist.py
# Version      : 0.1.0
# Date         : 2026-11-12
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""End-to-end integration test for steps 0-1 (task T3.3, TI-05 in tests/plan_tests.md)."""

from pathlib import Path

from personaldocagent.cli import main
from personaldocagent.db.connection import connect


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


def test_pipeline_end_to_end_persists_and_is_idempotent(tmp_path, monkeypatch, capsys):
    """TI-05: corpus with good/bad files -> 2 written, FTS works, rejections journalled, 2nd run is a no-op."""
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "collection"
    (root / "sub").mkdir(parents=True)
    (root / "a.txt").write_text("note alpha", encoding="utf-8")
    (root / "sub" / "b.html").write_text("<p>page beta</p>", encoding="utf-8")
    (root / "c.xyz").write_text("nope", encoding="utf-8")
    (root / "broken.docx").write_bytes(b"not a docx")
    cfg = tmp_path / "config"
    _write_config(cfg, root)
    db = tmp_path / "data" / "app.db"

    rc = main(["--config", str(cfg), "--base", str(db), "pipeline"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "2 document(s) acquired" in out
    assert "2 written, 0 duplicate(s)" in out

    conn = connect(db)
    try:
        assert conn.execute("SELECT COUNT(*) FROM document").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM conversion").fetchone()[0] == 2
        row = conn.execute(
            "SELECT rowid FROM conversion_fts WHERE conversion_fts MATCH 'alpha'"
        ).fetchone()
        assert row is not None
        statuses = {
            r[0] for r in conn.execute("SELECT status FROM document").fetchall()
        }
        assert statuses == {"active"}
    finally:
        conn.close()

    journal = (tmp_path / "data" / "rejections.log").read_text(encoding="utf-8")
    assert "unsupported_format" in journal
    assert "conversion_failed" in journal

    rc = main(["--config", str(cfg), "--base", str(db), "pipeline"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "0 document(s) acquired" in out
    assert "0 written" in out
    journal = (tmp_path / "data" / "rejections.log").read_text(encoding="utf-8")
    assert journal.count("duplicate") == 2
    conn = connect(db)
    try:
        assert conn.execute("SELECT COUNT(*) FROM document").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM conversion").fetchone()[0] == 2
    finally:
        conn.close()
