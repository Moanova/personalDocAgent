# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : tests/integration/test_cli_load_tree.py
# Version      : 0.1.0
# Date         : 2026-11-11
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Integration test: the load-tree CLI command populates the category table from the repo seed."""

import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_cli_load_tree_populates_the_base(tmp_path):
    base = tmp_path / "collection.db"
    init = subprocess.run(
        [sys.executable, "-m", "personaldocagent", "--base", str(base), "init-db"],
        capture_output=True,
        text=True,
    )
    assert init.returncode == 0, init.stderr
    result = subprocess.run(
        [
            sys.executable, "-m", "personaldocagent",
            "--base", str(base),
            "--config", str(ROOT / "config"),
            "load-tree",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(base)
    try:
        n = conn.execute("SELECT count(*) FROM category").fetchone()[0]
        unclassified = conn.execute(
            "SELECT count(*) FROM category WHERE parent_id IS NULL AND label = 'Non classé'"
        ).fetchone()[0]
    finally:
        conn.close()
    assert n >= 50
    assert unclassified == 1
