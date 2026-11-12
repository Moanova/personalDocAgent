# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : tests/unit/test_cli.py
# Version      : 0.1.0
# Date         : 2026-11-11
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Unit tests for the CLI."""

import pytest

from personaldocagent.cli import main


def test_global_help_lists_commands(capsys):
    """--help exits 0 and lists the four subcommands."""
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for command in ("init-db", "load-tree", "pipeline", "query"):
        assert command in out


def test_unknown_command_is_rejected():
    """An unknown subcommand exits with a non-zero code."""
    with pytest.raises(SystemExit) as exc:
        main(["no-such-command"])
    assert exc.value.code != 0


def test_unimplemented_command_raises_not_implemented():
    """A not-yet-implemented subcommand raises NotImplementedError (query, later EPIC)."""
    with pytest.raises(NotImplementedError):
        main(["query"])


def test_init_db_creates_the_database(tmp_path):
    """init-db with --base creates the database file."""
    base = tmp_path / "sub" / "test.db"
    assert main(["--base", str(base), "init-db"]) == 0
    assert base.is_file()
