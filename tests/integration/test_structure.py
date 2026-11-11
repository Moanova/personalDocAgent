# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : tests/integration/test_structure.py
# Version      : 0.1.0
# Date         : 2026-11-11
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Integration test: every skeleton module is importable and the module entry point answers --help."""

import importlib
import subprocess
import sys

MODULES = [
    "personaldocagent",
    "personaldocagent.cli",
    "personaldocagent.config",
    "personaldocagent.contracts",
    "personaldocagent.perimeter",
    "personaldocagent.routing",
    "personaldocagent.classification",
    "personaldocagent.pipeline",
    "personaldocagent.analysis",
    "personaldocagent.issuers",
    "personaldocagent.db",
    "personaldocagent.db.connection",
    "personaldocagent.acquisition",
    "personaldocagent.acquisition.direct_read",
    "personaldocagent.acquisition.ocr",
    "personaldocagent.interrogation",
    "personaldocagent.interrogation.tools",
    "personaldocagent.interrogation.agent",
]


def test_all_skeleton_modules_are_importable():
    for module in MODULES:
        importlib.import_module(module)


def test_module_entry_point_answers_help():
    result = subprocess.run(
        [sys.executable, "-m", "personaldocagent", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "personaldocagent" in result.stdout
