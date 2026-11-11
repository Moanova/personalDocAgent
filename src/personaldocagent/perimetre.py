"""Évaluation du périmètre d'accès au système de fichiers (deny by default).

Ordre d'évaluation (conception §3bis) : exclusion explicite > autorisation explicite > interdit.
La résolution canonique (realpath) est faite avant toute évaluation. L'applicatif est en lecture seule.
"""

import os
import re
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

from .config import PerimetreAcces

JOURNAL_REJETS_DEFAUT = Path("data") / "rejets.log"


def _glob_vers_regex(motif: str) -> re.Pattern:
    """Convertir un motif glob en regex : ** traverse les répertoires, * et ? restent dans un segment."""
    parties = []
    i = 0
    while i < len(motif):
        if motif.startswith("**/", i):
            parties.append("(?:[^/]+/)*")
            i += 3
        elif motif.startswith("**", i):
            parties.append(".*")
            i += 2
        elif motif[i] == "*":
            parties.append("[^/]*")
            i += 1
        elif motif[i] == "?":
            parties.append("[^/]")
            i += 1
        else:
            parties.append(re.escape(motif[i]))
            i += 1
    return re.compile("^" + "".join(parties) + "$")


def _est_exclu(canon: Path, exclusions: list[str]) -> bool:
    texte = str(canon)
    return any(_glob_vers_regex(motif).match(texte) for motif in exclusions)


def _est_sous_racine(canon: Path, racine: str) -> bool:
    try:
        canon.relative_to(Path(racine).resolve())
        return True
    except ValueError:
        return False


def est_autorise(chemin: Path, perimetre: PerimetreAcces) -> bool:
    """Évaluer un chemin contre les exclusions puis les racines autorisées (chemin résolu canoniquement)."""
    canon = Path(chemin).resolve()
    if _est_exclu(canon, perimetre.exclusions):
        return False
    return any(_est_sous_racine(canon, r) for r in perimetre.racines_autorisees)


def parcourir(racine: Path, perimetre: PerimetreAcces) -> Iterator[Path]:
    """Parcourir récursivement une racine autorisée : s'arrête dans les répertoires exclus, ne yield que les fichiers autorisés."""
    racine = Path(racine).resolve()
    if not est_autorise(racine, perimetre):
        return
    for dirpath, dirnames, filenames in os.walk(racine, followlinks=perimetre.suivre_liens_symboliques):
        dirnames[:] = [d for d in dirnames if not _est_exclu(Path(dirpath) / d, perimetre.exclusions)]
        for nom in filenames:
            chemin = Path(dirpath) / nom
            if est_autorise(chemin, perimetre):
                yield chemin


def journaliser_rejet(chemin: Path, raison: str, journal: Path = JOURNAL_REJETS_DEFAUT) -> None:
    """Ajouter une ligne horodatée au journal des rejets (le fichier est rejeté sans être lu)."""
    journal = Path(journal)
    journal.parent.mkdir(parents=True, exist_ok=True)
    horodatage = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with journal.open("a", encoding="utf-8") as f:
        f.write(f"{horodatage} | {raison} | {Path(chemin).resolve()}\n")
