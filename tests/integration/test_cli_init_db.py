# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : tests/integration/test_cli_init_db.py
# Version      : 0.1.0
# Date         : 2026-11-11
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Integration test: the init-db CLI command creates the database and its tables."""

import sqlite3
import subprocess
import sys


def test_cli_init_db_creates_base_and_tables(tmp_path):
    base = tmp_path / "cli.db"
    result = subprocess.run(
        [sys.executable, "-m", "personaldocagent", "--base", str(base), "init-db"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert base.is_file()
    conn = sqlite3.connect(base)
    try:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    finally:
        conn.close()
    assert "document" in tables
    assert "conversion_fts" in tables
