import sqlite3
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]


def test_cli_charger_arbre_peuple_la_base(tmp_path):
    base = tmp_path / "fonds.db"
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
            "--config", str(RACINE / "config"),
            "charger-arbre",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(base)
    try:
        n = conn.execute("SELECT count(*) FROM categorie").fetchone()[0]
        non_classe = conn.execute(
            "SELECT count(*) FROM categorie WHERE parent_id IS NULL AND libelle = 'Non classé'"
        ).fetchone()[0]
    finally:
        conn.close()
    assert n >= 50
    assert non_classe == 1
