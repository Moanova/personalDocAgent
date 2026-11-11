from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]


@pytest.fixture
def repertoire_config() -> Path:
    return RACINE / "config"
