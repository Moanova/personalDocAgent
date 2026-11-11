import importlib
import subprocess
import sys

MODULES = [
    "personaldocagent",
    "personaldocagent.cli",
    "personaldocagent.config",
    "personaldocagent.contracts",
    "personaldocagent.perimetre",
    "personaldocagent.routage",
    "personaldocagent.classification",
    "personaldocagent.pipeline",
    "personaldocagent.analyse",
    "personaldocagent.emetteurs",
    "personaldocagent.db",
    "personaldocagent.db.connexion",
    "personaldocagent.acquisition",
    "personaldocagent.acquisition.lecture_directe",
    "personaldocagent.acquisition.ocr",
    "personaldocagent.interrogation",
    "personaldocagent.interrogation.outils",
    "personaldocagent.interrogation.agent",
]


def test_tous_les_modules_du_squelette_sont_importables():
    for module in MODULES:
        importlib.import_module(module)


def test_point_entree_module_repond_au_help():
    result = subprocess.run(
        [sys.executable, "-m", "personaldocagent", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "personaldocagent" in result.stdout
