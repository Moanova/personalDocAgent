# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : tests/conftest.py
# Version      : 0.1.0
# Date         : 2026-11-11
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Shared pytest fixtures."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def config_dir() -> Path:
    """Configuration directory of the repository."""
    return ROOT / "config"
