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

```bash
python -m personaldocagent --help
personaldocagent init-db     # create the SQLite database from the schema
personaldocagent load-tree   # load the YAML seed of the classification tree
personaldocagent pipeline    # run the indexing pipeline (steps 0-7)
personaldocagent query       # query the collection in natural language
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
