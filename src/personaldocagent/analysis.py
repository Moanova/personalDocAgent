# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : analysis.py
# Version      : 0.2.0
# Date         : 2026-11-12
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Agent-driven step 2: content analysis via a Mistral completion (strict JSON output)."""

import json
import os
import re
import sqlite3
from functools import lru_cache

from .config import AnalysisPolicy
from .contracts import AnalysisRecord
from .prompts.analysis import SYSTEM_PROMPT, build_user_prompt

ANALYSIS_MODEL = "mistral-large-latest"
API_KEY_ENV = "MISTRAL_API_KEY"

_SNAKE_CASE_KEY = re.compile(r"^[a-z][a-z0-9_]*$")
_EXPORT_ID = re.compile(r"^\s*(\d+): ", re.MULTILINE)


@lru_cache(maxsize=None)
def _client():
    """Build the Mistral client lazily from MISTRAL_API_KEY (memoized: built once per process)."""
    from mistralai.client import Mistral

    api_key = os.environ.get(API_KEY_ENV)
    if not api_key:
        raise RuntimeError(f"{API_KEY_ENV} is not set: cannot call the Mistral API")
    return Mistral(api_key=api_key)


def category_ids_from_export(categories: str) -> set[int]:
    """Parse the flat export lines 'id: label' into the set of allowed category ids."""
    return {int(match) for match in _EXPORT_ID.findall(categories)}


def is_active_category(conn: sqlite3.Connection, category_id: int) -> bool:
    """Is the category id present and active in the category table?"""
    row = conn.execute(
        "SELECT 1 FROM category WHERE category_id = ? AND active = 1", (category_id,)
    ).fetchone()
    return row is not None


def _parse_record(payload: dict, categories: str, policy: AnalysisPolicy) -> AnalysisRecord:
    """Validate a raw JSON payload into an AnalysisRecord (deterministic checks)."""
    try:
        category_id = int(payload["category_id"])
        issuer_candidate = payload.get("issuer_candidate")
        keywords = list(payload["keywords"])
        summary = str(payload["summary"])
        attributes = dict(payload.get("attributes") or {})
        confidence = float(payload["confidence"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid analysis JSON payload: {exc}") from exc
    if category_id not in category_ids_from_export(categories):
        raise ValueError(f"category_id {category_id} is not in the classification tree")
    record = AnalysisRecord(
        category_id=category_id,
        issuer_candidate=issuer_candidate,
        keywords=keywords,
        summary=summary,
        attributes=attributes,
        confidence=confidence,
    )
    record.validate(policy.max_keywords)
    for key in attributes:
        if not _SNAKE_CASE_KEY.match(key):
            raise ValueError(f"attribute key {key!r} is not {policy.json_naming_convention}")
    if not 0.0 <= confidence <= 1.0:
        raise ValueError(f"confidence {confidence} out of range [0, 1]")
    return record


def analyze(text: str, categories: str, policy: AnalysisPolicy, client=None) -> AnalysisRecord:
    """Analyze an extracted text: category, issuer candidate, keywords, summary, JSON attributes."""
    if client is None:
        client = _client()
    user_prompt = build_user_prompt(categories, policy, text)
    try:
        response = client.chat.completions.create(
            model=ANALYSIS_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        payload = json.loads(response.choices[0].message.content)
    except Exception as exc:
        raise ValueError(f"Analysis completion failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Analysis payload is not a JSON object")
    return _parse_record(payload, categories, policy)
