# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : acquisition/ocr.py
# Version      : 0.1.0
# Date         : 2026-11-11
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""OCR route: handoff to mistral-ocr-latest, persisted in the conversion table."""

from pathlib import Path

from ..contracts import AcquisitionResult


def convert(path: Path) -> AcquisitionResult:
    """Convert a PDF or image to structured Markdown via the Mistral OCR API."""
    raise NotImplementedError
