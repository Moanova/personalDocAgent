# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : tests/integration/test_pipeline_analyze.py
# Version      : 0.1.0
# Date         : 2026-11-12
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""End-to-end integration test for step 2 analysis (task T4.3, TI-06 in tests/plan_tests.md)."""

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

from personaldocagent.cli import main
from personaldocagent.pipeline import analyze_base, run

ROOT = Path(__file__).resolve().parents[2]

PAYLOAD = {
    "category_id": 1,
    "issuer_candidate": "EDF",
    "keywords": ["facture"],
    "summary": "Facture analysée",
    "attributes": {"amount_eur": 123.45},
    "confidence": 0.9,
}


class _FakeClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

        def complete(*, model, messages, response_format=None):
            self.calls += 1
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]
            )

        self.chat = SimpleNamespace(complete=complete)


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
    shutil.copy(ROOT / "config" / "classification.yaml", cfg / "classification.yaml")


def _corpus(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "collection"
    root.mkdir()
    (root / "a.txt").write_text("Facture EDF mars 2026, 123,45 EUR", encoding="utf-8")
    (root / "b.md").write_text("# Note\n\nRappel divers.", encoding="utf-8")
    cfg = tmp_path / "config"
    _write_config(cfg, root)
    return cfg, tmp_path / "data" / "app.db"


def test_analyze_base_analyzes_persisted_documents(tmp_path, monkeypatch):
    """TI-06: run() persists 2 documents, analyze_base() returns one valid AnalysisRecord each."""
    monkeypatch.chdir(tmp_path)
    cfg, base = _corpus(tmp_path)
    results = run(cfg, base)
    assert sum(1 for r in results if r.written) == 2
    client = _FakeClient(PAYLOAD)
    records = analyze_base(cfg, base, client=client)
    assert len(records) == 2
    assert client.calls == 2
    for record in records:
        assert record.category_id == 1
        assert record.issuer_candidate == "EDF"
        assert record.attributes == {"amount_eur": 123.45}
        assert 0.0 <= record.confidence <= 1.0


def test_analyze_base_skips_failing_document(tmp_path, monkeypatch, capsys):
    """TI-06 (résilience): un document dont l'analyse échoue est ignoré, les autres sont analysés."""
    monkeypatch.chdir(tmp_path)
    cfg, base = _corpus(tmp_path)
    run(cfg, base)

    class _FlakyClient:
        def __init__(self):
            self.calls = 0
            self.chat = SimpleNamespace(complete=self._complete)

        def _complete(self, *, model, messages, response_format=None):
            self.calls += 1
            if self.calls == 2:
                raise ValueError("Analysis completion failed: invalid JSON")
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(PAYLOAD)))]
            )

    records = analyze_base(cfg, base, client=_FlakyClient())
    assert len(records) == 1
    assert records[0].category_id == 1
    err = capsys.readouterr().err
    assert "skipped" in err


def test_cli_pipeline_analyze_flag(tmp_path, monkeypatch, capsys):
    """TI-06 (CLI): pipeline --analyze runs step 2 and reports the count (analyze_base monkeypatched)."""
    monkeypatch.chdir(tmp_path)
    cfg, base = _corpus(tmp_path)
    fake_records = [object(), object()]
    monkeypatch.setattr(
        "personaldocagent.pipeline.analyze_base",
        lambda config_dir, db, client=None, with_issuers=False: fake_records,
    )
    rc = main(["--config", str(cfg), "--base", str(base), "pipeline", "--analyze"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "2 document(s) acquired" in out
    assert "2 written" in out
    assert "Step 2 analysis: 2 analyzed" in out
