# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : issuers.py
# Version      : 0.2.0
# Date         : 2026-11-12
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Issuer matching and creation: exact then approximate search on normalized labels."""

import sqlite3

from .config import AnalysisPolicy
from .contracts import IssuerMatch


def _normalize(label: str) -> str:
    """Normalize an issuer label for comparison: trimmed, whitespace collapsed, casefolded."""
    return " ".join(label.split()).casefold()


def _all_issuers(conn: sqlite3.Connection) -> list[tuple[int, str]]:
    """Read the whole issuer reference (small by design) as (issuer_id, label) pairs."""
    return [
        (row[0], row[1])
        for row in conn.execute("SELECT issuer_id, label FROM issuer ORDER BY issuer_id").fetchall()
    ]


def match_issuer(conn: sqlite3.Connection, candidate: str) -> IssuerMatch:
    """Match an issuer candidate: known (exact or single approximate hit), ambiguous or unknown."""
    norm = _normalize(candidate)
    issuers = _all_issuers(conn)
    for issuer_id, label in issuers:
        if norm and _normalize(label) == norm:
            return IssuerMatch(status="known", issuer_id=issuer_id, proposed_label=candidate)
    hits = [
        issuer_id
        for issuer_id, label in issuers
        if norm and (norm in _normalize(label) or _normalize(label) in norm)
    ]
    if len(hits) == 1:
        return IssuerMatch(status="known", issuer_id=hits[0], proposed_label=candidate)
    if hits:
        return IssuerMatch(status="ambiguous", proposed_label=candidate)
    return IssuerMatch(status="unknown", proposed_label=candidate)


def create_issuer(conn: sqlite3.Connection, label: str, linked_category: str | None = None) -> int:
    """Create an issuer (idempotent on the normalized label); return its issuer_id."""
    norm = _normalize(label)
    for issuer_id, existing in _all_issuers(conn):
        if _normalize(existing) == norm:
            return issuer_id
    try:
        cursor = conn.execute(
            "INSERT INTO issuer (label, linked_category) VALUES (?, ?)", (label, linked_category)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.rollback()
        for issuer_id, existing in _all_issuers(conn):
            if _normalize(existing) == norm:
                return issuer_id
        raise


def resolve_issuer(
    conn: sqlite3.Connection,
    match: IssuerMatch,
    candidate: str,
    confidence: float,
    policy: AnalysisPolicy,
) -> IssuerMatch:
    """Apply the confidence rule: unknown + high confidence -> auto-create; otherwise keep the match."""
    if match.status == "unknown" and candidate and confidence >= policy.auto_confidence_threshold:
        issuer_id = create_issuer(conn, candidate)
        return IssuerMatch(status="known", issuer_id=issuer_id, proposed_label=candidate)
    return match
