"""Voie OCR : handoff vers mistral-ocr-latest, persistance dans la table conversion."""

from pathlib import Path

from ..contracts import ResultatAcquisition


def convertir(chemin: Path) -> ResultatAcquisition:
    """Convertir un PDF ou une image en Markdown structuré via l'API OCR de Mistral."""
    raise NotImplementedError
