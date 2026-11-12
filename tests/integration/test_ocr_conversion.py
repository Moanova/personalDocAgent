# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : tests/integration/test_ocr_conversion.py
# Version      : 0.1.0
# Date         : 2026-11-12
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Integration test for the conversion persistence flow (task T2.2, TI-02 in tests/plan_tests.md)."""

from pathlib import Path

from personaldocagent.acquisition.ocr import OCR_MODEL, load_conversion, save_conversion
from personaldocagent.config import AnalysisPolicy, Config, PerimeterConfig, RoutingConfig
from personaldocagent.contracts import AcquisitionResult
from personaldocagent.db.connection import connect, init_db
from personaldocagent.routing import run_step0_checks


def _config(root: Path) -> Config:
    return Config(
        perimeter=PerimeterConfig(allowed_roots=[str(root)]),
        routing=RoutingConfig(
            default_route="reject",
            formats={"direct_read": [".txt"], "ocr": [".pdf", ".png"]},
        ),
        policy=AnalysisPolicy(),
    )


def test_ocr_route_and_conversion_persistence(tmp_path):
    """TI-02: a PDF is routed to ocr by step 0; its conversion is persisted once and searchable in FTS5."""
    root = tmp_path / "collection"
    root.mkdir()
    target = root / "scan.pdf"
    target.write_bytes(b"%PDF-1.4 fake")
    init_db(tmp_path / "test.db")
    conn = connect(tmp_path / "test.db")
    try:
        step0 = run_step0_checks(target, _config(root), conn, tmp_path / "rejections.log")
        assert step0.accepted is True
        assert step0.route == "ocr"

        conn.execute(
            "INSERT INTO document (source_file, date_added) VALUES (?, '2026-11-12')",
            (str(target.resolve()),),
        )
        conn.commit()
        result = AcquisitionResult(
            source_file=str(target.resolve()),
            route="ocr",
            text="Relevé bancaire janvier 2026",
            model=OCR_MODEL,
            conversion_date="2026-11-12T10:00:00+00:00",
        )
        assert save_conversion(conn, 1, result) is True
        assert save_conversion(conn, 1, result) is False
        assert load_conversion(conn, 1, OCR_MODEL) == "Relevé bancaire janvier 2026"
        row = conn.execute(
            "SELECT rowid FROM conversion_fts WHERE conversion_fts MATCH 'bancaire'"
        ).fetchone()
        assert row is not None
    finally:
        conn.close()
