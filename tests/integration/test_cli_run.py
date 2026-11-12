# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : tests/integration/test_cli_run.py
# Version      : 0.1.0
# Date         : 2026-11-12
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Integration test for the pipeline CLI command (task T2.4, TI-04 in tests/plan_tests.md)."""

from pathlib import Path

from personaldocagent.cli import main


def write_test_config(cfg: Path, root: Path) -> None:
    """Write the three YAML configuration files (same keys as the repository config/)."""
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


def test_cli_pipeline_end_to_end(tmp_path, monkeypatch, capsys):
    """TI-04: .txt acquired, .xyz rejected and journalled in the isolated cwd, no network call."""
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "collection"
    root.mkdir()
    (root / "a.txt").write_text("aaa", encoding="utf-8")
    (root / "b.xyz").write_text("nope", encoding="utf-8")
    cfg = tmp_path / "config"
    write_test_config(cfg, root)
    db = tmp_path / "data" / "test.db"
    rc = main(["--config", str(cfg), "--base", str(db), "pipeline"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "1 document(s) acquired" in out
    journal = (tmp_path / "data" / "rejections.log").read_text(encoding="utf-8")
    assert "unsupported_format" in journal
    assert "b.xyz" in journal
