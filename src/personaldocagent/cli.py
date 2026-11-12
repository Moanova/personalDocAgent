# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : cli.py
# Version      : 0.7.1
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
    query_parser = subcommands.add_parser("query", help="Query the collection in natural language.")
    query_parser.add_argument(
        "--question",
        type=str,
        default=None,
        help="One-shot question; without it, an interactive REPL is started.",
    )

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
            records = analyze_base(args.config, args.base, with_issuers=True, persist=True)
            print(f"Step 2 analysis: {len(records)} analyzed")
            from .config import load_config
            from .db.connection import connect
            from .pipeline import quality_report

            conn = connect(args.base)
            try:
                known = conn.execute(
                    "SELECT COUNT(*) FROM document WHERE issuer_id IS NOT NULL"
                ).fetchone()[0]
                pending = conn.execute(
                    "SELECT COUNT(*) FROM document WHERE issuer_id IS NULL"
                ).fetchone()[0]
                report = quality_report(conn, load_config(args.config).policy)
            finally:
                conn.close()
            print(f"Issuers: {known} known, {pending} pending")
            print(
                f"Quality: {report['documents']} document(s), "
                f"{report['pending_issuers']} pending issuer(s), "
                f"{report['low_confidence']} low-confidence"
            )
        return 0

    if args.command == "query":
        from .db.connection import connect
        from .interrogation.agent import DEFAULT_HISTORY_PATH, ask, load_history, save_history

        conn = connect(args.base)
        history = load_history(DEFAULT_HISTORY_PATH)
        try:
            if args.question is not None:
                print(ask(args.question, history=history, conn=conn))
            else:
                print("Interactive query mode (type 'exit' or 'quit', or Ctrl-D, to leave).")
                while True:
                    try:
                        question = input("Question> ").strip()
                    except (EOFError, KeyboardInterrupt):
                        print()
                        break
                    if not question:
                        continue
                    if question.lower() in ("exit", "quit"):
                        break
                    try:
                        print(ask(question, history=history, conn=conn))
                    except Exception as exc:
                        print(f"Erreur: {exc}")
        finally:
            save_history(DEFAULT_HISTORY_PATH, history)
            conn.close()
        return 0

    raise NotImplementedError(f"Command '{args.command}' is not implemented.")
