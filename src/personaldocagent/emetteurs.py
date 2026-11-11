"""Rapprochement d'émetteur : recherche SQL exacte puis approximative (LIKE)."""

import sqlite3

from .contracts import ResultatRapprochement


def rapprocher(conn: sqlite3.Connection, candidat: str) -> ResultatRapprochement:
    """Rapprocher un émetteur candidat : connu, ambigu ou inconnu."""
    raise NotImplementedError
