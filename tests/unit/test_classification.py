# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : tests/unit/test_classification.py
# Version      : 0.1.0
# Date         : 2026-11-11
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Unit tests for the classification tree loading and flat export."""

import pytest

from personaldocagent.classification import export_flat, load_tree
from personaldocagent.db.connection import connect, init_db

MINIMAL_SEED = """
- label: Finances
  children:
    - label: Banque
      children:
        - label: Relevés de compte
- label: Non classé
"""


@pytest.fixture
def conn(tmp_path):
    init_db(tmp_path / "test.db")
    c = connect(tmp_path / "test.db")
    yield c
    c.close()


@pytest.fixture
def seed(tmp_path):
    p = tmp_path / "seed.yaml"
    p.write_text(MINIMAL_SEED, encoding="utf-8")
    return p


def test_loads_tree_with_depths_and_parents(conn, seed):
    n = load_tree(conn, seed)
    assert n == 4
    rows = {r["label"]: r for r in conn.execute("SELECT * FROM category")}
    assert rows["Finances"]["depth"] == 1
    assert rows["Finances"]["parent_id"] is None
    assert rows["Banque"]["depth"] == 2
    assert rows["Banque"]["parent_id"] == rows["Finances"]["category_id"]
    assert rows["Relevés de compte"]["depth"] == 3
    assert rows["Non classé"]["depth"] == 1
    assert all(r["active"] == 1 for r in rows.values())


def test_reload_is_idempotent(conn, seed):
    load_tree(conn, seed)
    n = load_tree(conn, seed)
    assert n == 4
    assert conn.execute("SELECT count(*) FROM category").fetchone()[0] == 4


def test_loads_repo_seed(conn, config_dir):
    n = load_tree(conn, config_dir / "classification.yaml")
    assert n >= 50
    row = conn.execute(
        "SELECT depth FROM category WHERE parent_id IS NULL AND label = 'Non classé'"
    ).fetchone()
    assert row is not None and row["depth"] == 1
    assert conn.execute("SELECT max(depth) FROM category").fetchone()[0] == 3


def test_invalid_seed_raises_value_error(conn, tmp_path):
    p = tmp_path / "seed.yaml"
    p.write_text("just_a_string\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_tree(conn, p)


def test_export_flat_indents_and_filters_inactive(conn, seed):
    load_tree(conn, seed)
    conn.execute("UPDATE category SET active = 0 WHERE label = 'Non classé'")
    conn.commit()
    export = export_flat(conn)
    lines = export.splitlines()
    assert any(l.endswith(": Finances") and not l.startswith(" ") for l in lines)
    assert any(l.startswith("  ") and l.endswith(": Banque") for l in lines)
    assert any(l.startswith("    ") and l.endswith(": Relevés de compte") for l in lines)
    assert "Non classé" not in export
    for line in lines:
        category_id = int(line.strip().split(":")[0])
        assert str(category_id) in line
