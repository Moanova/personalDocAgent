# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : pipeline.py
# Version      : 0.1.0
# Date         : 2026-11-11
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Deterministic orchestration of pipeline steps 0-7."""

from pathlib import Path

from .contracts import WriteResult


def run(config_dir: Path, root: Path) -> list[WriteResult]:
    """Run the full pipeline over the files of an allowed root."""
    raise NotImplementedError
