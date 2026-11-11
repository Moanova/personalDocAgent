"""Voie lecture directe : TXT, MD, HTML nettoyé, DOCX, ODT."""

from pathlib import Path

from ..contracts import ResultatAcquisition


def lire(chemin: Path) -> ResultatAcquisition:
    """Lire un document en lecture directe et retourner le résultat d'acquisition (texte brut)."""
    raise NotImplementedError
