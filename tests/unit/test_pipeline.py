# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : tests/unit/test_pipeline.py
# Version      : 0.1.0
# Date         : 2026-11-12
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Unit tests for the step 0 orchestration (task T2.3, TU-15 to TU-19 in tests/plan_tests.md)."""

from pathlib import Path

import pytest

from personaldocagent.acquisition.ocr import OCR_MODEL
from personaldocagent.config import AnalysisPolicy, Config, PerimeterConfig, RoutingConfig
from personaldocagent.contracts import AcquisitionResult
from personaldocagent.db.connection import connect, init_db
from personaldocagent.pipeline import acquire, chunk_text


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


@pytest.fixture
def root(tmp_path):
    r = tmp_path / "collection"
    r.mkdir()
    return r


@pytest.fixture
def conn(tmp_path):
    init_db(tmp_path / "test.db")
    c = connect(tmp_path / "test.db")
    yield c
    c.close()


@pytest.fixture
def journal(tmp_path):
    return tmp_path / "rejections.log"


def test_chunk_text_short_text_single_segment():
    """TU-15: short text stays in one segment; empty text yields no segment."""
    assert chunk_text("abc", max_chars=10) == ["abc"]
    assert chunk_text("", max_chars=10) == []


def test_chunk_text_prefers_paragraph_boundaries():
    """TU-15: split on paragraph boundaries while respecting max_chars."""
    chunks = chunk_text("aaaa\n\nbbbb\n\ncccc", max_chars=9)
    assert chunks == ["aaaa", "bbbb", "cccc"]
    assert all(len(chunk) <= 9 for chunk in chunks)


def test_chunk_text_hard_splits_long_paragraph():
    """TU-15: a paragraph longer than max_chars is hard-split."""
    chunks = chunk_text("x" * 25, max_chars=10)
    assert chunks == ["x" * 10, "x" * 10, "x" * 5]


def test_acquire_direct_read_route(root, conn, journal):
    """TU-16: a permitted .txt produces one direct_read AcquisitionResult."""
    f = root / "note.txt"
    f.write_text("contenu", encoding="utf-8")
    results = acquire(_config(root), root, conn, journal)
    assert len(results) == 1
    assert results[0].route == "direct_read"
    assert results[0].text == "contenu"
    assert not journal.exists()


def test_acquire_rejections_journalled_and_run_continues(root, conn, journal):
    """TU-17: unsupported format and duplicate are journalled; the run continues."""
    bad = root / "data.xyz"
    bad.write_text("x", encoding="utf-8")
    good = root / "ok.txt"
    good.write_text("ok", encoding="utf-8")
    dup = root / "dup.txt"
    dup.write_text("dup", encoding="utf-8")
    conn.execute(
        "INSERT INTO document (source_file, date_added) VALUES (?, '2026-11-12')",
        (str(dup.resolve()),),
    )
    conn.commit()
    results = acquire(_config(root), root, conn, journal)
    assert [r.source_file for r in results] == [str(good.resolve())]
    log = journal.read_text(encoding="utf-8")
    assert "unsupported_format" in log
    assert str(bad.resolve()) in log
    assert "duplicate" in log
    assert str(dup.resolve()) in log


def test_acquire_conversion_failure_is_journalled(root, conn, journal):
    """TU-18: a corrupt file is journalled as conversion_failed; no exception propagates."""
    broken = root / "broken.docx"
    broken.write_bytes(b"not a docx")
    good = root / "ok.txt"
    good.write_text("ok", encoding="utf-8")
    results = acquire(_config(root), root, conn, journal)
    assert len(results) == 1
    assert results[0].text == "ok"
    assert "conversion_failed" in journal.read_text(encoding="utf-8")


def test_acquire_dispatches_ocr_route_with_injected_converter(root, conn, journal):
    """TU-19: a .pdf goes to the injected OCR converter (no network call)."""
    pdf = root / "scan.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    fake_result = AcquisitionResult(
        source_file=str(pdf.resolve()),
        route="ocr",
        text="texte ocr",
        model=OCR_MODEL,
        conversion_date="2026-11-12T10:00:00+00:00",
    )
    calls = []

    def fake_convert(path):
        calls.append(path)
        return fake_result

    results = acquire(_config(root), root, conn, journal, ocr_convert=fake_convert)
    assert results == [fake_result]
    assert calls == [pdf]
