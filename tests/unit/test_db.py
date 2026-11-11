# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : tests/unit/test_db.py
# Version      : 0.1.0
# Date         : 2026-11-11
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Unit tests for the SQLite schema and the FTS5 index."""

import sqlite3

import pytest

from personaldocagent.db.connection import connect, init_db

TABLES = {
    "document",
    "document_agent",
    "document_subject",
    "document_description",
    "category",
    "document_category",
    "issuer",
    "conversion",
}


def _tables(conn) -> set:
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


@pytest.fixture
def base(tmp_path):
    path = tmp_path / "test.db"
    init_db(path)
    return path


@pytest.fixture
def conn(base):
    c = connect(base)
    yield c
    c.close()


def _insert_document(conn, source="doc.pdf", text="EDF invoice of March, amount 87.40 EUR"):
    conn.execute(
        "INSERT INTO document (source_file, date_added) VALUES (?, '2026-11-01')",
        (source,),
    )
    doc_id = conn.execute(
        "SELECT doc_id FROM document WHERE source_file = ?", (source,)
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO conversion (doc_id, extracted_text, model, conversion_date) "
        "VALUES (?, ?, 'mistral-ocr-latest', '2026-11-01')",
        (doc_id, text),
    )
    conn.commit()
    return doc_id


def test_init_db_creates_the_eight_tables_plus_fts(conn):
    tables = _tables(conn)
    assert TABLES <= tables
    assert "conversion_fts" in tables


def test_init_db_creates_the_fts_triggers(conn):
    triggers = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'trigger'")}
    assert {"conversion_fts_ai", "conversion_fts_ad", "conversion_fts_au"} <= triggers


def test_init_db_is_idempotent(tmp_path):
    path = tmp_path / "test.db"
    init_db(path)
    init_db(path)
    conn = connect(path)
    try:
        assert TABLES <= _tables(conn)
    finally:
        conn.close()


def test_foreign_key_enforced(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO document (source_file, date_added, issuer_id) "
            "VALUES ('a.pdf', '2026-11-01', 999)"
        )


def test_status_outside_list_rejected(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO document (source_file, date_added, status) "
            "VALUES ('a.pdf', '2026-11-01', 'archived')"
        )


def test_source_file_unique(conn):
    conn.execute("INSERT INTO document (source_file, date_added) VALUES ('a.pdf', '2026-11-01')")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO document (source_file, date_added) VALUES ('a.pdf', '2026-11-02')")


def test_issuer_label_unique(conn):
    conn.execute("INSERT INTO issuer (label) VALUES ('EDF')")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO issuer (label) VALUES ('EDF')")


def test_issuer_id_nullable(conn):
    conn.execute("INSERT INTO document (source_file, date_added) VALUES ('a.pdf', '2026-11-01')")
    row = conn.execute("SELECT issuer_id FROM document WHERE source_file = 'a.pdf'").fetchone()
    assert row["issuer_id"] is None


def test_fts5_fulltext_search(conn):
    _insert_document(conn, "a.pdf", "EDF invoice of March, amount 87.40 EUR")
    _insert_document(conn, "b.pdf", "Syndicate meeting minutes of April 12")
    rows = conn.execute("SELECT rowid FROM conversion_fts WHERE conversion_fts MATCH 'invoice'").fetchall()
    assert len(rows) == 1


def test_fts5_follows_update_and_delete(conn):
    doc_id = _insert_document(conn, "a.pdf", "EDF invoice of March")
    conn.execute("UPDATE conversion SET extracted_text = 'Bank statement' WHERE doc_id = ?", (doc_id,))
    conn.commit()
    assert conn.execute("SELECT rowid FROM conversion_fts WHERE conversion_fts MATCH 'invoice'").fetchall() == []
    assert len(conn.execute("SELECT rowid FROM conversion_fts WHERE conversion_fts MATCH 'statement'").fetchall()) == 1
    conn.execute("DELETE FROM conversion WHERE doc_id = ?", (doc_id,))
    conn.commit()
    assert conn.execute("SELECT rowid FROM conversion_fts WHERE conversion_fts MATCH 'statement'").fetchall() == []


def test_document_delete_cascades_into_fts(conn):
    doc_id = _insert_document(conn)
    conn.execute("DELETE FROM document WHERE doc_id = ?", (doc_id,))
    conn.commit()
    assert conn.execute("SELECT count(*) FROM conversion WHERE doc_id = ?", (doc_id,)).fetchone()[0] == 0
    assert conn.execute("SELECT count(*) FROM conversion_fts WHERE conversion_fts MATCH 'invoice'").fetchone()[0] == 0
