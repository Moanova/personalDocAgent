# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : tests/integration/test_pipeline_write.py
# Version      : 0.1.0
# Date         : 2026-11-12
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""End-to-end test for step 4 persistence + quality report (tasks T6.2/T6.3, TI-08)."""

import json
import shutil
from pathlib import Path

from personaldocagent.cli import main
from personaldocagent.contracts import AnalysisRecord
from personaldocagent.db.connection import connect
from personaldocagent.pipeline import analyze_base, run

ROOT = Path(__file__).resolve().parents[2]


def _write_config(cfg: Path, root: Path) -> None:
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "perimeter_access.yaml").write_text(
        f"allowed_roots: ['{root}']\nexclusions: []\nfollow_symlinks: false\n",
        encoding="utf-8",
    )
    (cfg / "routing.yaml").write_text(
        "default_route: reject\nformats:\n  direct_read: [.txt, .md]\n  ocr: [.pdf]\n",
        encoding="utf-8",
    )
    (cfg / "analysis_policy.yaml").write_text(
        "max_keywords: 10\njson_naming_convention: snake_case\nauto_confidence_threshold: 0.9\n",
        encoding="utf-8",
    )
    shutil.copy(ROOT / "config" / "classification.yaml", cfg / "classification.yaml")


def _fake_analyze(text, categories, policy, client=None):
    if "EDF" in text:
        return AnalysisRecord(1, "EDF", ["facture"], "Facture EDF", {"amount_eur": 10.0}, 0.99)
    return AnalysisRecord(1, "Inconnu SA", ["courrier"], "Courrier", {}, 0.5)


def test_pipeline_persists_analysis_and_reports_quality(tmp_path, monkeypatch, capsys):
    """TI-08: analyze_base(persist=True, with_issuers=True) writes full records; rerun is idempotent; CLI reports."""
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "collection"
    root.mkdir()
    (root / "a.txt").write_text("Facture EDF mars 2026", encoding="utf-8")
    (root / "b.txt").write_text("Courrier divers", encoding="utf-8")
    cfg = tmp_path / "config"
    _write_config(cfg, root)
    base = tmp_path / "data" / "app.db"

    assert sum(1 for r in run(cfg, base) if r.written) == 2
    conn = connect(base)
    conn.execute("INSERT INTO issuer (label) VALUES ('EDF')")
    conn.commit()
    conn.close()

    monkeypatch.setattr("personaldocagent.pipeline.analyze", _fake_analyze)
    records = analyze_base(cfg, base, with_issuers=True, persist=True)
    assert len(records) == 2

    conn = connect(base)
    try:
        rows = conn.execute(
            "SELECT source_file, dc_title, attributes, confidence, issuer_id FROM document ORDER BY doc_id"
        ).fetchall()
        assert rows[0]["dc_title"] == "a"
        assert json.loads(rows[0]["attributes"]) == {"amount_eur": 10.0}
        assert rows[0]["confidence"] == 0.99
        assert rows[0]["issuer_id"] == 1
        assert rows[1]["issuer_id"] is None
        assert rows[1]["confidence"] == 0.5
        for doc_id in (1, 2):
            assert conn.execute(
                "SELECT COUNT(*) FROM document_subject WHERE doc_id = ?", (doc_id,)
            ).fetchone()[0] == 1
            assert conn.execute(
                "SELECT COUNT(*) FROM document_description WHERE doc_id = ?", (doc_id,)
            ).fetchone()[0] == 1
            assert conn.execute(
                "SELECT COUNT(*) FROM document_category WHERE doc_id = ?", (doc_id,)
            ).fetchone()[0] == 1
    finally:
        conn.close()

    analyze_base(cfg, base, with_issuers=True, persist=True)
    conn = connect(base)
    try:
        assert conn.execute("SELECT COUNT(*) FROM document_subject").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM document_category").fetchone()[0] == 2
    finally:
        conn.close()

    rc = main(["--config", str(cfg), "--base", str(base), "pipeline", "--analyze"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Step 2 analysis: 2 analyzed" in out
    assert "Issuers: 1 known, 1 pending" in out
    assert "Quality: 2 document(s), 1 pending issuer(s), 1 low-confidence" in out
