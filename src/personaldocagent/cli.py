# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : cli.py
# Version      : 0.4.0
# Date         : 2026-11-12
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Command-line interface of personalDocAgent."""

import argparse
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    """Entry point of the personaldocagent CLI."""
    parser = argparse.ArgumentParser(
        prog="personaldocagent",
        description="Personal document agent: indexing, classification and querying of a personal document collection.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config"),
        help="Directory of the YAML configuration files (default: ./config).",
    )
    parser.add_argument(
        "--base",
        type=Path,
        default=Path("data") / "personaldocagent.db",
        help="Path of the SQLite database (default: data/personaldocagent.db).",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("init-db", help="Create the SQLite database from the schema (T1.2).")
    subcommands.add_parser("load-tree", help="Load the YAML seed of the classification tree (T1.3).")
    pipeline_parser = subcommands.add_parser(
        "pipeline", help="Run the indexing pipeline (steps 0-1; add --analyze for step 2)."
    )
    pipeline_parser.add_argument(
        "--analyze",
        action="store_true",
        help="Also run step 2 (agent-driven content analysis) on the persisted texts.",
    )
    subcommands.add_parser("query", help="Query the collection in natural language.")

    args = parser.parse_args(argv)

    if args.command == "init-db":
        from .db.connection import init_db

        init_db(args.base)
        print(f"Database initialized: {args.base}")
        return 0

    if args.command == "load-tree":
        from .classification import load_tree
        from .db.connection import connect

        seed = args.config / "classification.yaml"
        conn = connect(args.base)
        try:
            n = load_tree(conn, seed)
        finally:
            conn.close()
        print(f"{n} categories loaded from {seed}")
        return 0

    if args.command == "pipeline":
        from .perimeter import DEFAULT_REJECTION_LOG
        from .pipeline import analyze_base, run

        results = run(args.config, args.base)
        written = sum(1 for r in results if r.written)
        duplicates = sum(1 for r in results if not r.written and r.reason == "duplicate")
        print(f"Step 0 acquisition: {len(results)} document(s) acquired")
        print(f"Step 1 persistence: {written} written, {duplicates} duplicate(s)")
        print(f"Rejections journalled in {DEFAULT_REJECTION_LOG}")
        if args.analyze:
            records = analyze_base(args.config, args.base)
            print(f"Step 2 analysis: {len(records)} analyzed")
        return 0

    raise NotImplementedError(
        f"Command '{args.command}': to be implemented in a later EPIC (query mode)."
    )
