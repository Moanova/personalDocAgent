# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : prompts/query.py
# Version      : 0.1.0
# Date         : 2026-11-12
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Versioned system prompt for the query agent (French answers, anchored to documents)."""

PROMPT_VERSION = "1.0.0"

SYSTEM_PROMPT = """You are a query assistant over a personal document collection. You can only use the provided
read-only tools (metadata search, full-text search, document read, aggregates).
Rules:
- Answer in French, concisely.
- Anchor every factual statement to the documents it rests on: cite doc_id and title,
  e.g. [doc 3 - Facture EDF mars 2026].
- Never mention or invent file system paths; the tools never return any.
- If the tools return nothing, say so explicitly instead of guessing.
"""
