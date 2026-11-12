# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : tests/unit/test_query_agent.py
# Version      : 0.1.0
# Date         : 2026-11-12
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Unit tests for the query agent ask() loop (task T7.2, TU-50 to TU-52 in tests/plan_tests.md)."""

import json
from types import SimpleNamespace

import pytest

from personaldocagent.db.connection import connect, init_db
from personaldocagent.interrogation.agent import ask, load_history, save_history


def _tool_call(tid: str, name: str, arguments: dict) -> SimpleNamespace:
    return SimpleNamespace(
        id=tid,
        function=SimpleNamespace(name=name, arguments=json.dumps(arguments)),
    )


def _response(content: str | None = None, tool_calls=None) -> SimpleNamespace:
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeClient:
    """Queued fake of the Mistral client: each complete() pops the next scripted response."""

    def __init__(self, responses: list):
        self.responses = list(responses)
        self.calls = []

        def complete(*, model, messages, tools=None, response_format=None):
            self.calls.append(
                {"model": model, "messages": [dict(m) for m in messages], "tools": tools}
            )
            assert self.responses, "fake client ran out of scripted responses"
            return self.responses.pop(0)

        self.chat = SimpleNamespace(complete=complete)


@pytest.fixture
def conn(tmp_path):
    init_db(tmp_path / "test.db")
    c = connect(tmp_path / "test.db")
    c.execute("INSERT INTO issuer (label) VALUES ('EDF')")
    c.execute(
        "INSERT INTO document (doc_id, dc_title, dc_date, dc_type, status, issuer_id, source_file, date_added, attributes)"
        " VALUES (1, 'Facture EDF mars', '2026-03-15', 'Facture', 'active', 1, '/c/a.pdf', '2026-11-12', '{\"amount_eur\": 123.45}')"
    )
    c.execute(
        "INSERT INTO conversion (doc_id, extracted_text, model, conversion_date) VALUES"
        " (1, 'Facture EDF mars 2026, montant 123,45 EUR', 'direct_read', '2026-11-12T10:00:00+00:00')"
    )
    c.commit()
    yield c
    c.close()


def test_ask_dispatches_tool_calls_and_returns_anchored_answer(conn, tmp_path, monkeypatch):
    """TU-50: tool_call -> dispatch on tools.py -> final answer anchored to doc_id + title."""
    monkeypatch.chdir(tmp_path)
    client = FakeClient(
        [
            _response(
                tool_calls=[_tool_call("call-1", "search_documents", {"filters": {"issuer_id": 1}})]
            ),
            _response(tool_calls=[_tool_call("call-2", "search_fulltext", {"expression": "EDF"})]),
            _response(
                content="La facture EDF de mars 2026 s'élève à 123,45 EUR [doc 1 - Facture EDF mars]."
            ),
        ]
    )
    history: list = []
    answer = ask(
        "Combien a coûté la facture EDF de mars ?", history=history, conn=conn, client=client
    )
    assert answer == "La facture EDF de mars 2026 s'élève à 123,45 EUR [doc 1 - Facture EDF mars]."
    assert len(client.calls) == 3
    assert history[0]["role"] == "system"
    assert history[1]["role"] == "user"
    assert history[2]["role"] == "assistant"
    assert history[2]["tool_calls"][0]["function"]["name"] == "search_documents"
    tool_msg = history[3]
    assert tool_msg["role"] == "tool" and tool_msg["tool_call_id"] == "call-1"
    payload = json.loads(tool_msg["content"])
    assert payload[0]["doc_id"] == 1 and payload[0]["issuer"] == "EDF"
    assert "source_file" not in payload[0]
    fts_msg = json.loads(history[5]["content"])
    assert fts_msg[0]["doc_id"] == 1 and "EDF" in fts_msg[0]["excerpt"]
    assert history[6]["role"] == "assistant" and history[6]["content"] == answer
    advertised = {t["function"]["name"] for t in client.calls[0]["tools"]}
    assert advertised == {"search_documents", "search_fulltext", "read_document", "aggregate"}


def test_history_and_query_journal_are_persisted(conn, tmp_path, monkeypatch):
    """TU-51: save_history/load_history roundtrip (JSON) + query journal under data/query.log."""
    monkeypatch.chdir(tmp_path)
    client = FakeClient([_response(content="Aucun document ne correspond.")])
    history: list = []
    ask("Y a-t-il des relevés bancaires ?", history=history, conn=conn, client=client)
    hist_path = tmp_path / "data" / "my_history.json"
    save_history(hist_path, history)
    assert hist_path.is_file()
    assert load_history(hist_path) == history
    assert load_history(tmp_path / "absent.json") == []
    journal = (tmp_path / "data" / "query.log").read_text(encoding="utf-8")
    assert "Q: Y a-t-il des relevés bancaires ?" in journal
    assert "A: Aucun document ne correspond." in journal


def test_unknown_tool_raises_value_error(conn, tmp_path, monkeypatch):
    """TU-52: unknown tool name -> explicit ValueError, the loop stops."""
    monkeypatch.chdir(tmp_path)
    client = FakeClient(
        [_response(tool_calls=[_tool_call("call-1", "delete_everything", {})])]
    )
    with pytest.raises(ValueError, match="unknown tool"):
        ask("efface tout", history=[], conn=conn, client=client)


def test_tool_value_error_is_fed_back_to_the_model(conn, tmp_path, monkeypatch):
    """TU-52: invalid tool arguments -> {\"error\": ...} sent back, the loop continues."""
    monkeypatch.chdir(tmp_path)
    client = FakeClient(
        [
            _response(tool_calls=[_tool_call("call-1", "read_document", {"doc_id": 99})]),
            _response(content="Ce document n'existe pas."),
        ]
    )
    history: list = []
    answer = ask("lis le document 99", history=history, conn=conn, client=client)
    assert answer == "Ce document n'existe pas."
    assert json.loads(history[3]["content"]) == {"error": "unknown doc_id: 99"}


def test_tool_missing_argument_is_fed_back_to_the_model(conn, tmp_path, monkeypatch):
    """TU-52 (regression): tool called without a required argument -> TypeError caught,
    sent back as {\"error\": ...}, the loop continues instead of crashing."""
    monkeypatch.chdir(tmp_path)
    client = FakeClient(
        [
            _response(tool_calls=[_tool_call("call-1", "read_document", {})]),
            _response(content="Précise le numéro du document à lire."),
        ]
    )
    history: list = []
    answer = ask("lis un document", history=history, conn=conn, client=client)
    assert answer == "Précise le numéro du document à lire."
    error = json.loads(history[3]["content"])["error"]
    assert "doc_id" in error


def test_assistant_chunk_content_is_normalized_to_text(conn, tmp_path, monkeypatch):
    """TU-51 (regression): a message content made of chunks (ThinkChunk/TextChunk) is stored
    as plain text, so the history stays JSON-serializable and save_history() works."""
    monkeypatch.chdir(tmp_path)
    think_chunk = SimpleNamespace(thinking=[SimpleNamespace(text="réflexion interne")])
    text_chunk = SimpleNamespace(text="Voici la réponse [doc 1 - Facture EDF mars].")
    client = FakeClient([_response(content=[think_chunk, text_chunk])])
    history: list = []
    answer = ask("montant ?", history=history, conn=conn, client=client)
    assert answer == "Voici la réponse [doc 1 - Facture EDF mars]."
    assert history[2]["content"] == "Voici la réponse [doc 1 - Facture EDF mars]."
    json.dumps(history)
    hist_path = tmp_path / "data" / "h.json"
    save_history(hist_path, history)
    assert load_history(hist_path) == history
