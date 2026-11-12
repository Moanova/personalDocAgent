# personalDocAgent

> French version: [README.md](README.md)

Python application indexing the documents stored in a private individual or household space (administrative, intellectual and everyday documents) to find, describe and organize them.

Design principles (detailed in `docs/conception/conception.md`, in French): single-file SQLite database, no server; deterministic Python pipeline with agent-driven Mistral steps (OCR, content analysis); file-system access perimeter in deny by default; prompts versioned in the source code.

Coding standards: scripts, classes, methods and variables in English with docstrings and a standard header; project documentation in French; `AGENTS.md` and `README.md` in French, this file is the English README.

## Installation

```bash
pip install -e ".[dev]"
```

## Usage

Two execution modes: **pipeline** (batch indexing) and **query** (natural-language querying). Both are invoked either through the installed script (`personaldocagent ...`) or `python -m personaldocagent ...`.

### Prerequisites

- The `MISTRAL_API_KEY` environment variable must be set (agent-driven steps: OCR, content analysis, querying).
- Create `config/perimeter_access.yaml` from `config/perimeter_access.yaml.exemple` (this file is gitignored) and fill in `allowed_roots`: a YAML list of the allowed folders, e.g. `allowed_roots: ['C:\Users\you\Documents\pda-corpus']`. `exclusions` (globs, e.g. `'C:\**'`) take priority over allowed roots.

### Global options

Placed before the subcommand:

- `--config DIR`: directory of the YAML configuration files (default: `./config`);
- `--base PATH`: path of the SQLite database (default: `data/personaldocagent.db`).

### Commands

| Command | Options | Description |
|---|---|---|
| `init-db` | \u2014 | Create the SQLite database from the schema (`src/personaldocagent/db/schema.sql`). |
| `load-tree` | \u2014 | Load the YAML seed of the classification tree (`config/classification.yaml`). |
| `pipeline` | `--analyze` | Index the documents of the allowed perimeter: step 0 acquisition (direct read or Mistral OCR depending on `config/routing.yaml`), step 1 persistence. With `--analyze`: step 2 model-driven content analysis, issuer matching, full record writing and quality report. |
| `query` | `--question "..."` | Query the collection in natural language; answers are anchored to documents (doc_id + title). Without `--question`, interactive session (end with `exit`, `quit` or Ctrl-D). History in `data/query_history.json`, query journal in `data/query.log`. |

### Examples

```bash
# 1. Prepare the database and the classification tree
personaldocagent init-db
personaldocagent load-tree

# 2. Index the configured perimeter, with content analysis
personaldocagent pipeline --analyze

# 3. Query the collection
personaldocagent query --question "What is the amount of my March 2026 EDF invoice?"
personaldocagent query   # interactive session
```

## Tests

```bash
python -m pytest
```

## Structure

- `src/personaldocagent/` : source code (src layout)
- `config/` : external YAML configuration (access perimeter, routing table, analysis policy, classification tree seed)
- `tests/` : unit (`unit/`) and integration (`integration/`) tests
- `data/` : SQLite database and logs (gitignored)
- `docs/` : design and project tracking (in French)
