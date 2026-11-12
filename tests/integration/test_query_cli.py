# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : tests/integration/test_query_cli.py
# Version      : 0.1.0
# Date         : 2026-11-12
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Integration test for the query CLI (task T7.3, TI-09 in tests/plan_tests.md)."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from personaldocagent.cli import main
from personaldocagent.db.connection import connect, init_db


def _tool_call(tid: str, name: str, arguments: dict) -> SimpleNamespace:
    return SimpleNamespace(
        id=tid,
        function=SimpleNamespace(name=name, arguments=json.dumps(arguments)),
    )


def _response(content: str | None = None, tool_calls=None) -> SimpleNamespace:
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class _FakeClient:
    """Queued fake of the Mistral client injected into the query agent."""

    def __init__(self, responses: list):
        self.responses = list(responses)

        def complete(*, model, messages, tools=None, response_format=None):
            assert self.responses, "fake client ran out of scripted responses"
            return self.responses.pop(0)

        self.chat = SimpleNamespace(complete=complete)


@pytest.fixture
def seeded_base(tmp_path):
    base = tmp_path / "data" / "app.db"
    init_db(base)
    conn = connect(base)
    conn.execute("INSERT INTO issuer (label) VALUES ('EDF')")
    conn.execute(
        "INSERT INTO document (doc_id, dc_title, dc_date, dc_type, status, issuer_id, source_file, date_added, attributes)"
        " VALUES (1, 'Facture EDF mars', '2026-03-15', 'Facture', 'active', 1, '/c/a.pdf', '2026-11-12', '{\"amount_eur\": 123.45}')"
    )
    conn.execute(
        "INSERT INTO conversion (doc_id, extracted_text, model, conversion_date) VALUES"
        " (1, 'Facture EDF mars 2026, montant 123,45 EUR', 'direct_read', '2026-11-12T10:00:00+00:00')"
    )
    conn.commit()
    conn.close()
    return base


def test_query_one_shot_answers_with_doc_anchor(tmp_path, monkeypatch, capsys, seeded_base):
    """TI-09: query --question on a seeded base, fake client -> anchored answer, history + journal written."""
    monkeypatch.chdir(tmp_path)
    client = _FakeClient(
        [
            _response(tool_calls=[_tool_call("c1", "search_fulltext", {"expression": "EDF"})]),
            _response(content="123,45 EUR [doc 1 - Facture EDF mars]."),
        ]
    )
    monkeypatch.setattr("personaldocagent.interrogation.agent._client", lambda: client)
    rc = main(["--base", str(seeded_base), "query", "--question", "Montant de la facture EDF ?"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "[doc 1 - Facture EDF mars]" in out
    history = json.loads((tmp_path / "data" / "query_history.json").read_text(encoding="utf-8"))
    assert history[0]["role"] == "system"
    assert history[-1]["role"] == "assistant"
    assert history[-1]["content"] == "123,45 EUR [doc 1 - Facture EDF mars]."
    journal = (tmp_path / "data" / "query.log").read_text(encoding="utf-8")
    assert "Montant de la facture EDF ?" in journal
