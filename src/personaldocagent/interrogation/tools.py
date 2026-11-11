# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : interrogation/tools.py
# Version      : 0.1.0
# Date         : 2026-11-11
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""The four read-only tools exposed to the query agent."""

import sqlite3

from ..contracts import SearchFilters


def search_documents(conn: sqlite3.Connection, filters: SearchFilters) -> list[dict]:
    """Search on metadata (category, issuer, dates, type, status, keywords)."""
    raise NotImplementedError


def search_fulltext(conn: sqlite3.Connection, expression: str) -> list[dict]:
    """FTS5 search in the extracted texts (conversion table)."""
    raise NotImplementedError


def read_document(conn: sqlite3.Connection, doc_id: int) -> dict:
    """Extracted text and description of a document, with truncation of very long texts."""
    raise NotImplementedError


def aggregate(conn: sqlite3.Connection, restricted_query: dict) -> dict:
    """Sums and counts on whitelisted fields only (amounts via json_extract)."""
    raise NotImplementedError
