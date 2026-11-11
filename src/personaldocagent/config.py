"""Chargement et validation des fichiers de configuration YAML externes."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class PerimetreAcces:
    racines_autorisees: list[str] = field(default_factory=list)
    exclusions: list[str] = field(default_factory=list)
    suivre_liens_symboliques: bool = False


@dataclass
class Routage:
    voie_par_defaut: str = "rejeter"
    formats: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class PolitiqueAnalyse:
    nb_max_mots_cles: int = 10
    convention_nommage_json: str = "snake_case"
    seuil_confiance_auto: float = 0.9


@dataclass
class Config:
    perimetre: PerimetreAcces
    routage: Routage
    politique: PolitiqueAnalyse


def _charger_yaml(chemin: Path) -> dict:
    if not chemin.is_file():
        raise FileNotFoundError(f"Fichier de configuration introuvable : {chemin}")
    with chemin.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def charger_config(repertoire: Path) -> Config:
    """Charger et valider les fichiers YAML du répertoire de configuration."""
    repertoire = Path(repertoire)
    perimetre = _charger_yaml(repertoire / "perimetre_acces.yaml")
    routage = _charger_yaml(repertoire / "routage.yaml")
    politique = _charger_yaml(repertoire / "politique_analyse.yaml")
    return Config(
        perimetre=PerimetreAcces(**perimetre),
        routage=Routage(**routage),
        politique=PolitiqueAnalyse(**politique),
    )
