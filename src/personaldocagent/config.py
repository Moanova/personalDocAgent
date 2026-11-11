# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : config.py
# Version      : 0.1.0
# Date         : 2026-11-11
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Loading and validation of the external YAML configuration files."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class PerimeterConfig:
    """File-system access policy: allowed roots, exclusions, symlink handling."""

    allowed_roots: list[str] = field(default_factory=list)
    exclusions: list[str] = field(default_factory=list)
    follow_symlinks: bool = False


@dataclass
class RoutingConfig:
    """Routing table: file extension to processing route."""

    default_route: str = "reject"
    formats: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class AnalysisPolicy:
    """Analysis policy: keyword cap, JSON naming convention, confidence threshold."""

    max_keywords: int = 10
    json_naming_convention: str = "snake_case"
    auto_confidence_threshold: float = 0.9


@dataclass
class Config:
    """Aggregate of all external configuration sections."""

    perimeter: PerimeterConfig
    routing: RoutingConfig
    policy: AnalysisPolicy


def _load_yaml(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_config(directory: Path) -> Config:
    """Load and validate the YAML files of the configuration directory."""
    directory = Path(directory)
    perimeter = _load_yaml(directory / "perimeter_access.yaml")
    routing = _load_yaml(directory / "routing.yaml")
    policy = _load_yaml(directory / "analysis_policy.yaml")
    return Config(
        perimeter=PerimeterConfig(**perimeter),
        routing=RoutingConfig(**routing),
        policy=AnalysisPolicy(**policy),
    )
