# personalDocAgent

Applicatif Python indexant les documents stockés sur l'espace privé d'un particulier ou d'un foyer (documents administratifs, intellectuels, courants) pour les retrouver, les décrire et les organiser.

Principes de conception (détaillés dans `docs/conception/conception.md`) : base SQLite fichier unique sans serveur, pipeline déterministe en Python avec étapes agentiques Mistral (OCR, analyse de contenu), périmètre d'accès au système de fichiers en deny by default, prompts versionnés dans le code source.

## Installation

```bash
pip install -e ".[dev]"
```

## Usage

```bash
python -m personaldocagent --help
personaldocagent init-db        # créer la base SQLite à partir du schéma
personaldocagent charger-arbre  # charger la graine YAML de l'arbre de classification
personaldocagent pipeline       # exécuter le pipeline d'indexation (étapes 0-7)
personaldocagent interroger     # interroger le fonds en langage naturel
```

## Tests

```bash
python -m pytest
```

## Structure

- `src/personaldocagent/` : code source (src layout)
- `config/` : paramétrage externe en YAML (périmètre d'accès, table de routage, politique d'analyse, graine de l'arbre de classification)
- `tests/` : tests unitaires (`unit/`) et d'intégration (`integration/`)
- `data/` : base SQLite et journaux (gitignoré)
- `docs/` : conception et suivi de projet
