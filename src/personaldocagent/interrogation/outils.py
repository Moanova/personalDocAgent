"""Les quatre outils de lecture seule exposés à l'agent d'interrogation."""

import sqlite3

from ..contracts import FiltresRecherche


def rechercher_documents(conn: sqlite3.Connection, filtres: FiltresRecherche) -> list[dict]:
    """Recherche sur les métadonnées (catégorie, émetteur, dates, type, statut, mots-clés)."""
    raise NotImplementedError


def rechercher_plein_texte(conn: sqlite3.Connection, expression: str) -> list[dict]:
    """Recherche FTS5 dans les textes extraits (table conversion)."""
    raise NotImplementedError


def lire_document(conn: sqlite3.Connection, doc_id: int) -> dict:
    """Texte extrait et description d'un document, avec troncation des textes longs."""
    raise NotImplementedError


def agreger(conn: sqlite3.Connection, requete_restreinte: dict) -> dict:
    """Sommes et comptages sur champs whitelistés uniquement (montants via json_extract)."""
    raise NotImplementedError
