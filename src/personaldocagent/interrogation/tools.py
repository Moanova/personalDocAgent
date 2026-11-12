# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : interrogation/tools.py
# Version      : 0.2.1
# Date         : 2026-11-12
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""The four read-only tools exposed to the query agent (never any file path)."""

import re
import sqlite3

from ..contracts import SearchFilters

MAX_TEXT_CHARS = 4000
FTS_LIMIT = 20

_SNAKE_KEY = re.compile(r"^[a-z][a-z0-9_]*$")


def _build_where(filters: dict) -> tuple[str, list]:
    """Build a parameterized WHERE clause from a filters dict (issuer, category, dates, type, status, keyword)."""
    clauses, params = [], []
    if filters.get("issuer_id") is not None:
        clauses.append("d.issuer_id = ?")
        params.append(filters["issuer_id"])
    if filters.get("category_id") is not None:
        clauses.append(
            "EXISTS (SELECT 1 FROM document_category dc WHERE dc.doc_id = d.doc_id AND dc.category_id = ?)"
        )
        params.append(filters["category_id"])
    if filters.get("date_from"):
        clauses.append("d.dc_date >= ?")
        params.append(filters["date_from"])
    if filters.get("date_to"):
        clauses.append("d.dc_date <= ?")
        params.append(filters["date_to"])
    if filters.get("dc_type"):
        clauses.append("d.dc_type = ?")
        params.append(filters["dc_type"])
    if filters.get("status"):
        clauses.append("d.status = ?")
        params.append(filters["status"])
    if filters.get("keyword"):
        clauses.append(
            "EXISTS (SELECT 1 FROM document_subject ds WHERE ds.doc_id = d.doc_id AND ds.value = ?)"
        )
        params.append(filters["keyword"])
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


def search_documents(conn: sqlite3.Connection, filters: SearchFilters | dict | None = None) -> list[dict]:
    """Search on metadata (category, issuer, dates, type, status, keywords).

    Accepts a SearchFilters dataclass or a plain dict (as sent by the agent's tool calls);
    no filters means all documents.
    """
    if filters is None:
        raw = {}
    elif isinstance(filters, dict):
        raw = filters
    else:
        raw = vars(filters)
    active = {k: v for k, v in raw.items() if v is not None}
    where, params = _build_where(active)
    rows = conn.execute(
        f"""
        SELECT d.doc_id, d.dc_title, d.dc_date, d.dc_type, d.status, i.label AS issuer
        FROM document d LEFT JOIN issuer i ON i.issuer_id = d.issuer_id
        {where}
        ORDER BY d.doc_id
        """,
        params,
    ).fetchall()
    return [dict(row) for row in rows]


def search_fulltext(conn: sqlite3.Connection, expression: str) -> list[dict]:
    """FTS5 search in the extracted texts (conversion table); returns doc_id, title and an excerpt."""
    try:
        rows = conn.execute(
            """
            SELECT c.doc_id, d.dc_title, snippet(conversion_fts, 0, '[', ']', '…', 12) AS excerpt
            FROM conversion_fts f
            JOIN conversion c ON c.rowid = f.rowid
            JOIN document d ON d.doc_id = c.doc_id
            WHERE conversion_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (expression, FTS_LIMIT),
        ).fetchall()
    except sqlite3.OperationalError as exc:
        raise ValueError(f"invalid fulltext expression: {exc}") from exc
    return [dict(row) for row in rows]


def read_document(conn: sqlite3.Connection, doc_id: int, max_chars: int = MAX_TEXT_CHARS) -> dict:
    """Extracted text and description of a document, with truncation of very long texts."""
    doc = conn.execute(
        "SELECT doc_id, dc_title, dc_date, dc_type, status, issuer_id FROM document WHERE doc_id = ?",
        (doc_id,),
    ).fetchone()
    if doc is None:
        raise ValueError(f"unknown doc_id: {doc_id}")
    conv = conn.execute(
        "SELECT extracted_text FROM conversion WHERE doc_id = ? ORDER BY conversion_date DESC LIMIT 1",
        (doc_id,),
    ).fetchone()
    text = conv["extracted_text"] if conv else ""
    truncated = len(text) > max_chars
    if truncated:
        text = text[:max_chars] + " […]"
    descriptions = [
        row[0]
        for row in conn.execute(
            "SELECT value FROM document_description WHERE doc_id = ?", (doc_id,)
        ).fetchall()
    ]
    return {
        "doc_id": doc["doc_id"],
        "title": doc["dc_title"],
        "dc_date": doc["dc_date"],
        "dc_type": doc["dc_type"],
        "status": doc["status"],
        "issuer_id": doc["issuer_id"],
        "descriptions": descriptions,
        "text": text,
        "truncated": truncated,
    }


def aggregate(conn: sqlite3.Connection, restricted_query: dict) -> dict:
    """Sums and counts on whitelisted fields only (amounts via json_extract on the attributes column)."""
    op = restricted_query.get("op")
    filters = restricted_query.get("filters") or {}
    where, params = _build_where(filters)
    if op == "count":
        value = conn.execute(f"SELECT COUNT(*) FROM document d {where}", params).fetchone()[0]
    elif op == "sum":
        key = restricted_query.get("attribute")
        if not key or not _SNAKE_KEY.match(key):
            raise ValueError(f"attribute not whitelisted: {key!r}")
        value = conn.execute(
            f"SELECT COALESCE(SUM(json_extract(d.attributes, ?)), 0) FROM document d {where}",
            [f"$.{key}", *params],
        ).fetchone()[0]
    else:
        raise ValueError(f"unsupported aggregate op: {op!r}")
    return {"op": op, "value": value, "filters": filters}
