"""Table de routage (extension vers voie de traitement) et contrôles déterministes de l'étape 0."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .config import Config, Routage
from .perimetre import JOURNAL_REJETS_DEFAUT, est_autorise, journaliser_rejet


@dataclass
class ControleResultat:
    """Résultat des trois contrôles de l'étape 0 : chemin autorisé, format accepté, non-duplicata."""

    accepte: bool
    voie: str
    raison: str | None = None


def voie_de(chemin: Path, routage: Routage) -> str:
    """Voie de traitement d'un fichier selon son extension (insensible à la casse), sinon voie_par_defaut."""
    ext = Path(chemin).suffix.lower()
    for voie, extensions in routage.formats.items():
        if ext in {e.lower() for e in extensions}:
            return voie
    return routage.voie_par_defaut


def est_duplicata(chemin: Path, conn: sqlite3.Connection) -> bool:
    """Un document existe-t-il déjà en base pour ce fichier source (chemin canonique) ?"""
    canon = str(Path(chemin).resolve())
    return conn.execute("SELECT 1 FROM document WHERE fichier_source = ?", (canon,)).fetchone() is not None


def controles_etape0(
    chemin: Path,
    config: Config,
    conn: sqlite3.Connection,
    journal: Path = JOURNAL_REJETS_DEFAUT,
) -> ControleResultat:
    """Enchaîner les trois contrôles avant conversion ; chaque rejet est journalisé sans lecture du fichier."""
    if not est_autorise(chemin, config.perimetre):
        journaliser_rejet(chemin, "hors_perimetre", journal)
        return ControleResultat(False, "rejeter", "hors_perimetre")
    voie = voie_de(chemin, config.routage)
    if voie == "rejeter":
        journaliser_rejet(chemin, "format_non_supporte", journal)
        return ControleResultat(False, voie, "format_non_supporte")
    if est_duplicata(chemin, conn):
        journaliser_rejet(chemin, "duplicata", journal)
        return ControleResultat(False, voie, "duplicata")
    return ControleResultat(True, voie)
