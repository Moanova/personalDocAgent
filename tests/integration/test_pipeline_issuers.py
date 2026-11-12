# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : tests/integration/test_pipeline_issuers.py
# Version      : 0.1.0
# Date         : 2026-11-12
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""End-to-end test for issuer resolution in the pipeline (task T5.3, TI-07 in tests/plan_tests.md)."""

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
        "default_route: reject\n"
        "formats:\n"
        "  direct_read: [.txt, .md]\n"
        "  ocr: [.pdf]\n",
        encoding="utf-8",
    )
    (cfg / "analysis_policy.yaml").write_text(
        "max_keywords: 10\njson_naming_convention: snake_case\nauto_confidence_threshold: 0.9\n",
        encoding="utf-8",
    )
    shutil.copy(ROOT / "config" / "classification.yaml", cfg / "classification.yaml")


def _fake_analyze(text, categories, policy, client=None):
    """Fake analyze(): EDF document -> known-candidate with high confidence; other -> unknown, low."""
    if "EDF" in text:
        return AnalysisRecord(
            category_id=1,
            issuer_candidate="EDF",
            keywords=["facture"],
            summary="Facture EDF",
            attributes={"amount_eur": 10.0},
            confidence=0.99,
        )
    return AnalysisRecord(
        category_id=1,
        issuer_candidate="Inconnu SA",
        keywords=["courrier"],
        summary="Courrier divers",
        attributes={},
        confidence=0.5,
    )


def test_pipeline_assigns_known_issuer_and_keeps_pending(tmp_path, monkeypatch, capsys):
    """TI-07: known issuer -> document.issuer_id set; low-confidence unknown -> NULL; CLI reports issuers."""
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "collection"
    root.mkdir()
    (root / "a.txt").write_text("Facture EDF mars 2026", encoding="utf-8")
    (root / "b.txt").write_text("Courrier divers", encoding="utf-8")
    cfg = tmp_path / "config"
    _write_config(cfg, root)
    base = tmp_path / "data" / "app.db"

    results = run(cfg, base)
    assert sum(1 for r in results if r.written) == 2
    conn = connect(base)
    try:
        conn.execute("INSERT INTO issuer (label) VALUES ('EDF')")
        conn.commit()
    finally:
        conn.close()

    monkeypatch.setattr("personaldocagent.pipeline.analyze", _fake_analyze)
    records = analyze_base(cfg, base, with_issuers=True)
    assert len(records) == 2

    conn = connect(base)
    try:
        rows = dict(
            (Path(r[0]).name, r[1])
            for r in conn.execute("SELECT source_file, issuer_id FROM document").fetchall()
        )
        assert rows["a.txt"] == 1
        assert rows["b.txt"] is None
        assert conn.execute("SELECT COUNT(*) FROM issuer").fetchone()[0] == 1
    finally:
        conn.close()

    rc = main(["--config", str(cfg), "--base", str(base), "pipeline", "--analyze"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Step 2 analysis: 2 analyzed" in out
    assert "Issuers: 1 known, 1 pending" in out
