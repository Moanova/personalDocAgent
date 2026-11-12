# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : tests/unit/test_query_tools.py
# Version      : 0.1.0
# Date         : 2026-11-12
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Unit tests for the four read-only query tools (task T7.1, TU-46 to TU-49 in tests/plan_tests.md)."""

import pytest

from personaldocagent.contracts import SearchFilters
from personaldocagent.db.connection import connect, init_db
from personaldocagent.interrogation.tools import (
    aggregate,
    read_document,
    search_documents,
    search_fulltext,
)


@pytest.fixture
def conn(tmp_path):
    init_db(tmp_path / "test.db")
    c = connect(tmp_path / "test.db")
    c.execute("INSERT INTO category (label, depth, active) VALUES ('Factures', 2, 1)")
    c.execute("INSERT INTO issuer (label) VALUES ('EDF')")
    c.execute(
        "INSERT INTO document (doc_id, dc_title, dc_date, dc_type, status, issuer_id, source_file, date_added, attributes)"
        " VALUES (1, 'Facture EDF mars', '2026-03-15', 'Facture', 'active', 1, '/c/a.pdf', '2026-11-12', '{\"amount_eur\": 123.45}')"
    )
    c.execute(
        "INSERT INTO document (doc_id, dc_title, dc_date, dc_type, status, source_file, date_added, attributes)"
        " VALUES (2, 'Relevé bancaire janvier', '2026-01-31', 'Relevé', 'active', '/c/b.pdf', '2026-11-12', '{\"balance_eur\": 1250.0}')"
    )
    c.execute(
        "INSERT INTO document (doc_id, dc_title, status, source_file, date_added)"
        " VALUES (3, 'Note longue', 'active', '/c/c.txt', '2026-11-12')"
    )
    c.execute(
        "INSERT INTO conversion (doc_id, extracted_text, model, conversion_date) VALUES"
        " (1, 'Facture EDF mars 2026, montant 123,45 EUR, référence FA-2026-03', 'direct_read', '2026-11-12T10:00:00+00:00')"
    )
    c.execute(
        "INSERT INTO conversion (doc_id, extracted_text, model, conversion_date) VALUES"
        " (2, 'Relevé bancaire janvier 2026, solde 1250 EUR', 'direct_read', '2026-11-12T10:00:00+00:00')"
    )
    c.execute(
        "INSERT INTO conversion (doc_id, extracted_text, model, conversion_date) VALUES"
        " (3, ?, 'direct_read', '2026-11-12T10:00:00+00:00')",
        ("x" * 5000,),
    )
    c.execute("INSERT INTO document_subject (doc_id, value) VALUES (1, 'facture')")
    c.execute("INSERT INTO document_description (doc_id, value) VALUES (1, 'Facture EDF mars 2026')")
    c.execute(
        "INSERT INTO document_category (doc_id, category_id, is_primary, classification_date)"
        " VALUES (1, 1, 1, '2026-11-12T10:00:00+00:00')"
    )
    c.commit()
    yield c
    c.close()


def test_search_documents_filters(conn):
    """TU-46: metadata filters (issuer, keyword, dates, type, status)."""
    by_issuer = search_documents(conn, SearchFilters(issuer_id=1))
    assert [r["doc_id"] for r in by_issuer] == [1]
    assert by_issuer[0]["issuer"] == "EDF"
    assert "source_file" not in by_issuer[0]
    by_keyword = search_documents(conn, SearchFilters(keyword="facture"))
    assert [r["doc_id"] for r in by_keyword] == [1]
    by_date = search_documents(conn, SearchFilters(date_from="2026-02-01", date_to="2026-03-31"))
    assert [r["doc_id"] for r in by_date] == [1]
    by_type = search_documents(conn, SearchFilters(dc_type="Relevé"))
    assert [r["doc_id"] for r in by_type] == [2]
    assert search_documents(conn, SearchFilters(status="to_destroy")) == []


def test_search_fulltext_fts(conn):
    """TU-47: FTS5 MATCH returns doc_id, title and an excerpt containing the match."""
    hits = search_fulltext(conn, "EDF")
    assert [h["doc_id"] for h in hits] == [1]
    assert "EDF" in hits[0]["excerpt"]
    assert search_fulltext(conn, "inexistant") == []
    with pytest.raises(ValueError, match="invalid fulltext expression"):
        search_fulltext(conn, '"unbalanced')


def test_read_document_with_truncation(conn):
    """TU-48: text + description; very long texts are truncated."""
    doc = read_document(conn, 1)
    assert doc["title"] == "Facture EDF mars"
    assert "FA-2026-03" in doc["text"]
    assert doc["descriptions"] == ["Facture EDF mars 2026"]
    assert doc["truncated"] is False
    long_doc = read_document(conn, 3)
    assert long_doc["truncated"] is True
    assert len(long_doc["text"]) <= 4000 + 10
    with pytest.raises(ValueError, match="unknown doc_id"):
        read_document(conn, 99)


def test_aggregate_whitelist(conn):
    """TU-49: count, sum via json_extract on attributes; non-whitelisted input rejected."""
    assert aggregate(conn, {"op": "count"})["value"] == 3
    assert aggregate(conn, {"op": "count", "filters": {"issuer_id": 1}})["value"] == 1
    total = aggregate(conn, {"op": "sum", "attribute": "amount_eur"})
    assert total["value"] == 123.45
    with pytest.raises(ValueError, match="not whitelisted"):
        aggregate(conn, {"op": "sum", "attribute": "amount_eur\"; DROP TABLE document; --"})
    with pytest.raises(ValueError, match="unsupported aggregate op"):
        aggregate(conn, {"op": "drop"})
