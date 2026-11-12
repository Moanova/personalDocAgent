# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : tests/unit/test_analysis.py
# Version      : 0.1.0
# Date         : 2026-11-12
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Unit tests for the step 2 analysis (tasks T4.1/T4.2, TU-28 to TU-33 in tests/plan_tests.md)."""

import json
from types import SimpleNamespace

import pytest

from personaldocagent.analysis import analyze, category_ids_from_export, is_active_category
from personaldocagent.config import AnalysisPolicy
from personaldocagent.db.connection import connect, init_db

CATEGORIES = "1: Identité et famille\n2: Administratif\n  3: Factures\n"
POLICY = AnalysisPolicy(max_keywords=10, json_naming_convention="snake_case", auto_confidence_threshold=0.9)

VALID_PAYLOAD = {
    "category_id": 3,
    "issuer_candidate": "EDF",
    "keywords": ["facture", "énergie"],
    "summary": "Facture EDF de mars 2026",
    "attributes": {"amount_eur": 123.45},
    "confidence": 0.95,
}


class _FakeClient:
    """Fake Mistral client: records the create() calls and returns a fixed JSON payload."""

    def __init__(self, payload):
        self.payload = payload
        self.calls = []

        def create(*, model, messages, response_format=None):
            self.calls.append({"model": model, "messages": messages, "response_format": response_format})
            content = payload if isinstance(payload, str) else json.dumps(payload)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])

        self.chat = SimpleNamespace(completions=SimpleNamespace(create=create))


def test_analyze_happy_path():
    """TU-28: valid JSON payload -> complete AnalysisRecord."""
    record = analyze("Facture EDF mars 2026, montant 123,45 EUR", CATEGORIES, POLICY, client=_FakeClient(VALID_PAYLOAD))
    assert record.category_id == 3
    assert record.issuer_candidate == "EDF"
    assert record.keywords == ["facture", "énergie"]
    assert record.summary == "Facture EDF de mars 2026"
    assert record.attributes == {"amount_eur": 123.45}
    assert record.confidence == 0.95


def test_analyze_too_many_keywords_rejected():
    """TU-29: more keywords than policy.max_keywords -> ValueError."""
    payload = {**VALID_PAYLOAD, "keywords": [f"k{i}" for i in range(11)]}
    with pytest.raises(ValueError, match="keywords"):
        analyze("texte", CATEGORIES, POLICY, client=_FakeClient(payload))


def test_analyze_unknown_category_rejected():
    """TU-30: category_id outside the tree export -> ValueError (constrained choice)."""
    payload = {**VALID_PAYLOAD, "category_id": 99}
    with pytest.raises(ValueError, match="not in the classification tree"):
        analyze("texte", CATEGORIES, POLICY, client=_FakeClient(payload))


def test_analyze_non_snake_case_attribute_rejected():
    """TU-31: attribute key not in snake_case -> ValueError."""
    payload = {**VALID_PAYLOAD, "attributes": {"Montant": 123.45}}
    with pytest.raises(ValueError, match="snake_case"):
        analyze("texte", CATEGORIES, POLICY, client=_FakeClient(payload))


def test_analyze_prompt_contains_tree_and_policy():
    """TU-32: the prompt sent to the model contains the flat tree, max_keywords and the convention."""
    client = _FakeClient(VALID_PAYLOAD)
    analyze("texte", CATEGORIES, POLICY, client=client)
    call = client.calls[0]
    assert call["model"] == "mistral-large-latest"
    assert call["response_format"] == {"type": "json_object"}
    system_msg, user_msg = call["messages"]
    assert system_msg["role"] == "system"
    assert "category_id" in system_msg["content"]
    assert user_msg["role"] == "user"
    assert "3: Factures" in user_msg["content"]
    assert "at most 10 keywords" in user_msg["content"]
    assert "snake_case" in user_msg["content"]


def test_analyze_bad_confidence_or_invalid_json_rejected():
    """TU-33: confidence out of [0,1] or invalid JSON -> ValueError."""
    with pytest.raises(ValueError, match="confidence"):
        analyze("texte", CATEGORIES, POLICY, client=_FakeClient({**VALID_PAYLOAD, "confidence": 1.5}))
    with pytest.raises(ValueError, match="Analysis completion failed"):
        analyze("texte", CATEGORIES, POLICY, client=_FakeClient("not json at all"))


def test_category_ids_from_export_and_active_check(tmp_path):
    """T4.2 helpers: export parsing and active-category check against the DB."""
    assert category_ids_from_export(CATEGORIES) == {1, 2, 3}
    init_db(tmp_path / "test.db")
    conn = connect(tmp_path / "test.db")
    try:
        conn.execute("INSERT INTO category (label, depth, active) VALUES ('Test', 1, 1)")
        conn.commit()
        assert is_active_category(conn, 1) is True
        assert is_active_category(conn, 42) is False
    finally:
        conn.close()
