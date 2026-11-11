# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : acquisition/direct_read.py
# Version      : 0.1.0
# Date         : 2026-11-11
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Direct read route: TXT, MD, cleaned HTML, DOCX, ODT."""

from pathlib import Path

from ..contracts import AcquisitionResult


def read_direct(path: Path) -> AcquisitionResult:
    """Read a document directly and return the acquisition result (raw text)."""
    raise NotImplementedError
