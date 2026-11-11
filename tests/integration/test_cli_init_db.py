import sqlite3
import subprocess
import sys


def test_cli_init_db_cree_la_base_et_les_tables(tmp_path):
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
