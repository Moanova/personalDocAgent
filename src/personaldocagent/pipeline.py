"""Orchestration déterministe des étapes 0-7 du pipeline d'indexation."""

from pathlib import Path

from .contracts import ResultatEcriture


def executer(repertoire_config: Path, racine: Path) -> list[ResultatEcriture]:
    """Exécuter le pipeline complet sur les fichiers d'une racine autorisée."""
    raise NotImplementedError
