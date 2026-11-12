# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : interrogation/agent.py
# Version      : 0.2.1
# Date         : 2026-11-12
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Query agent: chat.completions loop with function calling, history kept locally."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from ..analysis import ANALYSIS_MODEL, _client
from ..prompts.query import SYSTEM_PROMPT
from . import tools as query_tools

MAX_TURNS = 10
DEFAULT_HISTORY_PATH = Path("data") / "query_history.json"
DEFAULT_QUERY_LOG = Path("data") / "query.log"

TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "Search documents on metadata: category, issuer, dates, type, status, keyword.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filters": {
                        "type": "object",
                        "properties": {
                            key: {"type": "string"}
                            for key in (
                                "category_id",
                                "issuer_id",
                                "date_from",
                                "date_to",
                                "dc_type",
                                "status",
                                "keyword",
                            )
                        },
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_fulltext",
            "description": "Full-text (FTS5) search in the extracted document texts; returns doc_id, title, excerpt.",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_document",
            "description": "Read one document: extracted text (truncated if long) and description.",
            "parameters": {
                "type": "object",
                "properties": {"doc_id": {"type": "integer"}},
                "required": ["doc_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "aggregate",
            "description": "Count or sum over documents (optionally filtered); sums read a JSON attribute (e.g. amount_eur).",
            "parameters": {
                "type": "object",
                "properties": {
                    "restricted_query": {
                        "type": "object",
                        "properties": {
                            "op": {"type": "string", "enum": ["count", "sum"]},
                            "attribute": {"type": "string"},
                            "filters": {"type": "object"},
                        },
                        "required": ["op"],
                    }
                },
            },
        },
    },
]

_TOOLS = {
    "search_documents": query_tools.search_documents,
    "search_fulltext": query_tools.search_fulltext,
    "read_document": query_tools.read_document,
    "aggregate": query_tools.aggregate,
}


def _content_to_text(content) -> str:
    """Normalize a message content (str, None or list of chunks) to plain text.

    The SDK may return a list of chunks (TextChunk, ThinkChunk, ...): only the textual
    parts are kept, so the history stays JSON-serializable and valid as an API payload.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(c.text for c in content if isinstance(getattr(c, "text", None), str))
    return str(content)


def save_history(path: Path, history: list) -> None:
    """Persist the message history as JSON."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def load_history(path: Path) -> list:
    """Load a persisted message history (empty list if absent)."""
    path = Path(path)
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _log_query(question: str, answer: str, journal: Path = DEFAULT_QUERY_LOG) -> None:
    """Append the question/answer pair to the query journal."""
    journal = Path(journal)
    journal.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with journal.open("a", encoding="utf-8") as f:
        f.write(f"{stamp} | Q: {question}\n{stamp} | A: {answer}\n\n")


def ask(question: str, history: list | None = None, conn: sqlite3.Connection | None = None, client=None) -> str:
    """Answer a question about the collection by orchestrating the read-only tools.

    The message history (list of dicts) is updated in place when provided; persist it with
    save_history(). Returns the final assistant answer (anchored to doc_id + title).
    """
    if conn is None:
        raise ValueError("ask() requires an open database connection (conn)")
    if client is None:
        client = _client()
    messages = history if history is not None else []
    if not messages or messages[0].get("role") != "system":
        messages.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
    messages.append({"role": "user", "content": question})
    for _ in range(MAX_TURNS):
        response = client.chat.complete(model=ANALYSIS_MODEL, messages=messages, tools=TOOL_SPECS)
        message = response.choices[0].message
        tool_calls = getattr(message, "tool_calls", None)
        messages.append(
            {
                "role": "assistant",
                "content": _content_to_text(message.content),
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in (tool_calls or [])
                ],
            }
        )
        if not tool_calls:
            answer = _content_to_text(message.content)
            _log_query(question, answer)
            return answer
        for tc in tool_calls:
            name = tc.function.name
            if name not in _TOOLS:
                raise ValueError(f"unknown tool: {name}")
            args = json.loads(tc.function.arguments or "{}")
            try:
                result = _TOOLS[name](conn, **args)
            except (ValueError, TypeError) as exc:
                result = {"error": str(exc)}
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                }
            )
    raise ValueError(f"query did not converge in {MAX_TURNS} turns")
