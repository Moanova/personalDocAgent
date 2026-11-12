# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : analysis.py
# Version      : 0.2.3
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


_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)
_SKIP_CHUNK_TYPES = ("thinking", "reasoning")


def _content_to_str(content) -> str:
    """Normalize message content to plain text: str as-is; chunk list joined over text chunks only.

    Thinking/reasoning chunks (ThinkChunk, type='thinking') carry no .text and are skipped.
    """
    if isinstance(content, str):
        return content
    parts = []
    for chunk in content or []:
        if isinstance(chunk, str):
            parts.append(chunk)
        elif isinstance(chunk, dict):
            if chunk.get("type") in _SKIP_CHUNK_TYPES:
                continue
            parts.append(str(chunk.get("text", "")))
        else:
            if getattr(chunk, "type", None) in _SKIP_CHUNK_TYPES:
                continue
            text = getattr(chunk, "text", None)
            if text is not None:
                parts.append(str(text))
    return "".join(parts)


def _extract_json(raw: str):
    """Parse raw text as JSON; fallback: the first {...} block (model may wrap JSON in prose)."""
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        match = _JSON_BLOCK.search(raw)
        if match:
            return json.loads(match.group(0))
        raise


def analyze(text: str, categories: str, policy: AnalysisPolicy, client=None) -> AnalysisRecord:
    """Analyze an extracted text: category, issuer candidate, keywords, summary, JSON attributes."""
    if client is None:
        client = _client()
    user_prompt = build_user_prompt(categories, policy, text)
    try:
        response = client.chat.complete(
            model=ANALYSIS_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
    except Exception as exc:
        raise ValueError(f"Analysis completion failed: {exc}") from exc
    raw = _content_to_str(response.choices[0].message.content)
    try:
        payload = _extract_json(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Analysis completion failed: invalid JSON ({exc}); content preview: {raw[:200]!r}"
        ) from exc
    if not isinstance(payload, dict):
        raise ValueError("Analysis payload is not a JSON object")
    return _parse_record(payload, categories, policy)