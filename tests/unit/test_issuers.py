# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : tests/unit/test_issuers.py
# Version      : 0.1.0
# Date         : 2026-11-12
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Unit tests for issuer matching/creation (tasks T5.1/T5.2, TU-34 to TU-38 in tests/plan_tests.md)."""

import pytest

from personaldocagent.config import AnalysisPolicy
from personaldocagent.db.connection import connect, init_db
from personaldocagent.issuers import create_issuer, match_issuer, resolve_issuer

POLICY = AnalysisPolicy(max_keywords=10, json_naming_convention="snake_case", auto_confidence_threshold=0.9)


@pytest.fixture
def conn(tmp_path):
    init_db(tmp_path / "test.db")
    c = connect(tmp_path / "test.db")
    yield c
    c.close()


def _seed(conn, *labels):
    for label in labels:
        conn.execute("INSERT INTO issuer (label) VALUES (?)", (label,))
    conn.commit()


def test_match_exact_normalized(conn):
    """TU-34: exact hit on the normalized label (case/whitespace-insensitive) -> known."""
    _seed(conn, "EDF")
    m = match_issuer(conn, "  edf ")
    assert m.status == "known"
    assert m.issuer_id == 1


def test_match_approximate_single_hit(conn):
    """TU-35: a single approximate hit -> known."""
    _seed(conn, "EDF SA")
    m = match_issuer(conn, "EDF")
    assert m.status == "known"
    assert m.issuer_id == 1


def test_match_approximate_multiple_hits_ambiguous(conn):
    """TU-36: several approximate hits -> ambiguous with proposed_label."""
    _seed(conn, "EDF SA", "EDF Énergie")
    m = match_issuer(conn, "EDF")
    assert m.status == "ambiguous"
    assert m.issuer_id is None
    assert m.proposed_label == "EDF"


def test_match_no_hit_unknown(conn):
    """TU-37: no hit -> unknown with proposed_label."""
    _seed(conn, "EDF")
    m = match_issuer(conn, "Unknown Corp")
    assert m.status == "unknown"
    assert m.proposed_label == "Unknown Corp"


def test_resolve_issuer_auto_create_and_pending(conn):
    """TU-38: confidence >= threshold -> auto-create (known); below -> stays unknown; create is idempotent."""
    m = match_issuer(conn, "Nouvel Émetteur")
    assert m.status == "unknown"
    r = resolve_issuer(conn, m, "Nouvel Émetteur", 0.95, POLICY)
    assert r.status == "known" and r.issuer_id == 1
    assert conn.execute("SELECT COUNT(*) FROM issuer").fetchone()[0] == 1
    m2 = match_issuer(conn, "Autre Inconnu")
    r2 = resolve_issuer(conn, m2, "Autre Inconnu", 0.5, POLICY)
    assert r2.status == "unknown"
    assert conn.execute("SELECT COUNT(*) FROM issuer").fetchone()[0] == 1
    assert create_issuer(conn, "  nouvel émetteur ") == 1
    assert conn.execute("SELECT COUNT(*) FROM issuer").fetchone()[0] == 1
