# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : interrogation/agent.py
# Version      : 0.1.0
# Date         : 2026-11-11
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Query agent: chat.completions loop with function calling, history kept locally."""


def ask(question: str, history: list | None = None) -> str:
    """Answer a question about the collection by orchestrating the read-only tools."""
    raise NotImplementedError
