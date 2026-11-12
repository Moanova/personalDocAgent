# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : prompts/analysis.py
# Version      : 0.1.0
# Date         : 2026-11-12
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Versioned prompts for the step 2 analysis agent (English, model-facing)."""

from ..config import AnalysisPolicy

PROMPT_VERSION = "1.0.0"

SYSTEM_PROMPT = """You are a document analysis agent for a personal document collection.
Analyze the document text and answer with a single strict JSON object (no markdown, no extra text) with exactly these keys:
- category_id: integer, MUST be one of the category ids listed in the user message (classification tree)
- issuer_candidate: string or null (the issuer/emitter of the document, e.g. a company name)
- keywords: list of strings, at most the maximum given in the user message
- summary: string, a short free-text summary containing the essential values (amounts, dates, parties)
- attributes: object with keys in the naming convention given in the user message (e.g. snake_case), holding any value of interest (amounts, references)
- confidence: float between 0 and 1, your confidence in the analysis
"""


def build_user_prompt(categories: str, policy: AnalysisPolicy, text: str) -> str:
    """Build the user prompt: flat classification tree (id: label), analysis policy, document text."""
    return (
        "Classification tree (id: label, indented by depth). "
        "category_id MUST be one of these ids:\n"
        f"{categories}\n\n"
        f"Constraints: at most {policy.max_keywords} keywords; "
        f"attributes keys in {policy.json_naming_convention}; confidence between 0 and 1.\n\n"
        f"Document text:\n{text}"
    )
