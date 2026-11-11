"""Connexion et initialisation de la base SQLite."""

import sqlite3
from pathlib import Path

SCHEMA = Path(__file__).with_name("schema.sql")


def connecter(chemin_base: Path) -> sqlite3.Connection:
    """Ouvrir une connexion à la base SQLite avec clés étrangères activées."""
    conn = sqlite3.connect(Path(chemin_base))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(chemin_base: Path) -> None:
    """Créer la base à partir de db/schema.sql (idempotent grâce aux IF NOT EXISTS)."""
    chemin_base = Path(chemin_base)
    chemin_base.parent.mkdir(parents=True, exist_ok=True)
    conn = connecter(chemin_base)
    try:
        conn.executescript(SCHEMA.read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()
