# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : tests/unit/test_persist.py
# Version      : 0.1.0
# Date         : 2026-11-12
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Unit tests for the step 1 persistence (task T3.1, TU-21 to TU-24 in tests/plan_tests.md)."""

from datetime import datetime

import pytest

from personaldocagent.acquisition.ocr import OCR_MODEL
from personaldocagent.contracts import AcquisitionResult
from personaldocagent.db.connection import connect, init_db
from personaldocagent.pipeline import persist


@pytest.fixture
def conn(tmp_path):
    init_db(tmp_path / "test.db")
    c = connect(tmp_path / "test.db")
    yield c
    c.close()


def _acq(name="scan.pdf", text="Facture EDF mars 2026", model=OCR_MODEL, route="ocr"):
    return AcquisitionResult(
        source_file=f"/collection/{name}",
        route=route,
        text=text,
        model=model,
        conversion_date="2026-11-12T10:00:00+00:00",
    )


def test_persist_writes_document_and_conversion(conn):
    """TU-21: deterministic document row + conversion row + WriteResult(written=True)."""
    res = persist(conn, _acq())
    assert res.written is True
    assert res.reason is None
    assert res.doc_id == 1
    row = conn.execute(
        "SELECT source_file, status, dc_format, date_added FROM document WHERE doc_id = ?",
        (res.doc_id,),
    ).fetchone()
    assert row["source_file"] == "/collection/scan.pdf"
    assert row["status"] == "active"
    assert row["dc_format"] == "application/pdf"
    datetime.fromisoformat(row["date_added"])
    conv = conn.execute(
        "SELECT extracted_text, model FROM conversion WHERE doc_id = ?", (res.doc_id,)
    ).fetchone()
    assert conv["extracted_text"] == "Facture EDF mars 2026"
    assert conv["model"] == OCR_MODEL


def test_persist_direct_read_model_fallback(conn):
    """TU-21: direct_read route stores model='direct_read' (conversion.model is NOT NULL)."""
    res = persist(conn, _acq(name="note.txt", model=None, route="direct_read"))
    assert res.written is True
    conv = conn.execute(
        "SELECT model FROM conversion WHERE doc_id = ?", (res.doc_id,)
    ).fetchone()
    assert conv["model"] == "direct_read"


def test_persist_idempotent_duplicate(conn):
    """TU-22: second persist on the same source_file -> written=False, reason='duplicate', no new rows."""
    first = persist(conn, _acq())
    second = persist(conn, _acq(text="autre texte"))
    assert second.written is False
    assert second.reason == "duplicate"
    assert second.doc_id == first.doc_id
    assert conn.execute("SELECT COUNT(*) FROM document").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM conversion").fetchone()[0] == 1


def test_persist_feeds_fts(conn):
    """TU-23: the FTS index receives the persisted text via the triggers."""
    persist(conn, _acq())
    row = conn.execute(
        "SELECT rowid FROM conversion_fts WHERE conversion_fts MATCH 'EDF'"
    ).fetchone()
    assert row is not None


def test_persist_mime_mapping(conn):
    """TU-24: dc_format from the extension, fallback application/octet-stream."""
    persist(conn, _acq(name="a.txt", model=None, route="direct_read"))
    row = conn.execute(
        "SELECT dc_format FROM document WHERE source_file = '/collection/a.txt'"
    ).fetchone()
    assert row["dc_format"] == "text/plain"
    persist(conn, _acq(name="b.zzz", model=None, route="direct_read"))
    row = conn.execute(
        "SELECT dc_format FROM document WHERE source_file = '/collection/b.zzz'"
    ).fetchone()
    assert row["dc_format"] == "application/octet-stream"
