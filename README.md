# personalDocAgent

> English version: [README.en.md](README.en.md)

Applicatif Python indexant les documents stockés sur l'espace privé d'un particulier ou d'un foyer (documents administratifs, intellectuels, courants) pour les retrouver, les décrire et les organiser.

Principes de conception (détaillés dans `docs/conception/conception.md`) : base SQLite fichier unique sans serveur, pipeline déterministe en Python avec étapes agentiques Mistral (OCR, analyse de contenu), périmètre d'accès au système de fichiers en deny by default, prompts versionnés dans le code source.

Standards de codage : scripts, classes, méthodes et variables en anglais avec docstring et en-tête standard ; documentation projet en français ; `AGENTS.md` et `README.md` en français, `README.en.md` pour la version anglaise.

![Status: In development](https://img.shields.io/badge/Statut-En%20développement-orange)
![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg?logo=python)

## Installation

```bash
pip install -e ".[dev]"
```

## Utilisation

Deux modes d'exécution : **pipeline** (indexation par lots) et **query** (interrogation en langage naturel). Les commandes s'invoquent indifféremment via le script installé (`personaldocagent ...`) ou `python -m personaldocagent ...`.

### Prérequis

- La variable d'environnement `MISTRAL_API_KEY` doit être renseignée (étapes agentes : OCR, analyse de contenu, interrogation).
- Créer `config/perimeter_access.yaml` à partir de `config/perimeter_access.yaml.exemple` (ce fichier est gitignoré) et y renseigner `allowed_roots` : liste YAML des dossiers autorisés, par ex. `allowed_roots: ['C:\Users\vous\Documents\pda-corpus']`. Les `exclusions` (globs, ex. `'C:\**'`) sont prioritaires sur les racines autorisées.

### Exemples de périmètre (`config/perimeter_access.yaml`)

`allowed_roots` et `exclusions` sont des **listes YAML** (et non des valeurs séparées par des virgules). Autoriser un dossier autorise aussi tous ses sous-dossiers. Une `exclusion` est **toujours prioritaire** sur une autorisation : un dossier exclu n'est jamais lu, même sous une racine autorisée. Dans les globs, `**` (double étoile) traverse les dossiers ; une seule `*` reste dans un seul nom de dossier. Par défaut, tout ce qui n'est pas autorisé est refusé.

```yaml
# Exemple 1 : autoriser un dossier et tout ce qu'il contient
allowed_roots: ['C:\Users\vous\Documents\pda-corpus']
exclusions: []
follow_symlinks: false
```

```yaml
# Exemple 2 : autoriser ce même dossier, sauf l'un de ses sous-dossiers
allowed_roots: ['C:\Users\vous\Documents\pda-corpus']
exclusions: ['C:\Users\vous\Documents\pda-corpus\brouillons\**']
follow_symlinks: false
```

```yaml
# Exemple 3 : n'autoriser qu'un seul dossier du disque
# (le refus par défaut fait le reste ; si vous excluez explicitement la racine,
#  utilisez 'C:\' et surtout pas 'C:\**' : l'exclusion étant prioritaire,
#  'C:\**' bloquerait aussi le dossier autorisé)
allowed_roots: ['C:\Users\vous\Documents\pda-corpus']
exclusions: ['C:\']
follow_symlinks: false
```

### Options globales

Placées avant la sous-commande :

- `--config DIR` : répertoire des fichiers YAML de configuration (défaut : `./config`) ;
- `--base PATH` : chemin de la base SQLite (défaut : `data/personaldocagent.db`).

### Commandes

| Commande | Options | Description |
|---|---|---|
| `init-db` | — | Crée la base SQLite à partir du schéma (`src/personaldocagent/db/schema.sql`). |
| `load-tree` | — | Charge la graine YAML de l'arbre de classification (`config/classification.yaml`). |
| `pipeline` | `--analyze` | Indexe les documents du périmètre autorisé : étape 0 acquisition (lecture directe ou OCR Mistral selon `config/routing.yaml`), étape 1 sauvegarde des documents et de leur texte extrait dans la base de données. Avec `--analyze` : étape 2 analyse de contenu par le modèle, rattachement des émetteurs, écriture des fiches complètes et rapport de qualité. |
| `query` | `--question "..."` | Interroge le fonds en langage naturel ; les réponses sont ancrées aux documents (doc_id + titre). Sans `--question`, session interactive (fin par `exit`, `quit` ou Ctrl-D). Historique dans `data/query_history.json`, journal des requêtes dans `data/query.log`. |

### Exemples

```bash
# 1. Préparer la base et l'arbre de classification
personaldocagent init-db
personaldocagent load-tree

# 2. Indexer le périmètre configuré, avec analyse de contenu
personaldocagent pipeline --analyze

# 3. Interroger le fonds
personaldocagent query --question "Quel est le montant de ma facture EDF de mars 2026 ?"
personaldocagent query   # session interactive
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
