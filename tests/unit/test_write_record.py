# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : tests/unit/test_write_record.py
# Version      : 0.1.0
# Date         : 2026-11-12
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Unit tests for step 4 write_record and quality report (tasks T6.1/T6.3, TU-42 to TU-45)."""

import json

import pytest

from personaldocagent.config import AnalysisPolicy
from personaldocagent.contracts import AnalysisRecord
from personaldocagent.db.connection import connect, init_db
from personaldocagent.pipeline import pending_review, quality_report, write_record

POLICY = AnalysisPolicy(max_keywords=10, json_naming_convention="snake_case", auto_confidence_threshold=0.9)


@pytest.fixture
def conn(tmp_path):
    init_db(tmp_path / "test.db")
    c = connect(tmp_path / "test.db")
    yield c
    c.close()


def _record(confidence=0.95, category_id=1):
    return AnalysisRecord(
        category_id=category_id,
        issuer_candidate="EDF",
        keywords=["facture"],
        summary="Résumé",
        attributes={"amount_eur": 12.3},
        confidence=confidence,
    )


def _doc(conn, name="facture-edf.pdf", issuer_id=None):
    conn.execute(
        "INSERT INTO document (source_file, date_added, status, issuer_id) VALUES (?, '2026-11-12', 'active', ?)",
        (f"/collection/{name}", issuer_id),
    )
    conn.commit()
    return conn.execute(
        "SELECT doc_id FROM document WHERE source_file = ?", (f"/collection/{name}",)
    ).fetchone()[0]


def test_write_record_full(conn):
    """TU-42: attributes JSON + confidence + dc_title fallback + child rows."""
    conn.execute("INSERT INTO category (label, depth, active) VALUES ('Factures', 2, 1)")
    conn.commit()
    doc_id = _doc(conn)
    res = write_record(conn, doc_id, _record(category_id=1))
    assert res.written is True
    row = conn.execute(
        "SELECT dc_title, attributes, confidence FROM document WHERE doc_id = ?", (doc_id,)
    ).fetchone()
    assert row["dc_title"] == "facture-edf"
    assert json.loads(row["attributes"]) == {"amount_eur": 12.3}
    assert row["confidence"] == 0.95
    assert conn.execute(
        "SELECT value FROM document_subject WHERE doc_id = ?", (doc_id,)
    ).fetchone()[0] == "facture"
    assert conn.execute(
        "SELECT value FROM document_description WHERE doc_id = ?", (doc_id,)
    ).fetchone()[0] == "Résumé"
    cat = conn.execute(
        "SELECT category_id, is_primary FROM document_category WHERE doc_id = ?", (doc_id,)
    ).fetchone()
    assert cat["category_id"] == 1
    assert cat["is_primary"] == 1


def test_write_record_idempotent(conn):
    """TU-43: second write_record on the same record adds no duplicate child rows."""
    conn.execute("INSERT INTO category (label, depth, active) VALUES ('Factures', 2, 1)")
    conn.commit()
    doc_id = _doc(conn)
    write_record(conn, doc_id, _record())
    write_record(conn, doc_id, _record())
    for table in ("document_subject", "document_description", "document_category"):
        assert conn.execute(f"SELECT COUNT(*) FROM {table} WHERE doc_id = ?", (doc_id,)).fetchone()[0] == 1


def test_init_db_migrates_confidence_column(tmp_path):
    """TU-44: init_db re-adds the confidence column on a database created before it existed."""
    db = tmp_path / "old.db"
    init_db(db)
    conn = connect(db)
    conn.execute("ALTER TABLE document DROP COLUMN confidence")
    conn.commit()
    conn.close()
    init_db(db)
    conn = connect(db)
    try:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(document)").fetchall()}
        assert "confidence" in columns
    finally:
        conn.close()


def test_quality_report_and_pending_review(conn):
    """TU-45: counts by status/category, pending issuers, low confidence; pending_review list."""
    conn.execute("INSERT INTO category (label, depth, active) VALUES ('Factures', 2, 1)")
    conn.execute("INSERT INTO issuer (label) VALUES ('EDF')")
    conn.commit()
    d1 = _doc(conn, "a.pdf", issuer_id=1)
    d2 = _doc(conn, "b.pdf")
    write_record(conn, d1, _record(confidence=0.95))
    write_record(conn, d2, _record(confidence=0.5))
    report = quality_report(conn, POLICY)
    assert report["documents"] == 2
    assert report["by_status"] == {"active": 2}
    assert report["by_category"] == {"Factures": 2}
    assert report["pending_issuers"] == 1
    assert report["low_confidence"] == 1
    assert pending_review(conn, POLICY) == [d2]
