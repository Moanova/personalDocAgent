# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : acquisition/ocr.py
# Version      : 0.2.0
# Date         : 2026-11-12
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""OCR route: handoff to mistral-ocr-latest, persisted in the conversion table."""

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from ..contracts import AcquisitionResult

OCR_MODEL = "mistral-ocr-latest"
API_KEY_ENV = "MISTRAL_API_KEY"


def _client():
    """Build a Mistral client from the MISTRAL_API_KEY environment variable (lazy, no network call here)."""
    from mistralai.client import Mistral

    api_key = os.environ.get(API_KEY_ENV)
    if not api_key:
        raise RuntimeError(f"{API_KEY_ENV} is not set: cannot call the Mistral OCR API")
    return Mistral(api_key=api_key)


def convert(path: Path, client=None) -> AcquisitionResult:
    """Convert a PDF or image to structured Markdown via the Mistral OCR API."""
    path = Path(path)
    if client is None:
        client = _client()
    try:
        uploaded = client.files.upload(
            file={"file_name": path.name, "content": path.read_bytes()},
            purpose="ocr",
        )
        response = client.ocr.process(
            model=OCR_MODEL,
            document={"type": "file", "file_id": uploaded.id},
        )
        pages = sorted(response.pages, key=lambda page: page.index)
        text = "\n\n".join(page.markdown for page in pages)
    except Exception as exc:
        raise ValueError(f"OCR conversion failed for {path}: {exc}") from exc
    return AcquisitionResult(
        source_file=str(path.resolve()),
        route="ocr",
        text=text,
        model=OCR_MODEL,
        conversion_date=datetime.now(timezone.utc).isoformat(),
    )


def save_conversion(conn: sqlite3.Connection, doc_id: int, result: AcquisitionResult) -> bool:
    """Persist an extracted text in conversion (idempotent on doc_id+model); True if a row was inserted."""
    cursor = conn.execute(
        "INSERT OR IGNORE INTO conversion (doc_id, extracted_text, model, conversion_date) VALUES (?, ?, ?, ?)",
        (doc_id, result.text, result.model, result.conversion_date),
    )
    conn.commit()
    return cursor.rowcount > 0


def load_conversion(conn: sqlite3.Connection, doc_id: int, model: str) -> str | None:
    """Read a persisted conversion text, or None if absent (never re-pay a conversion)."""
    row = conn.execute(
        "SELECT extracted_text FROM conversion WHERE doc_id = ? AND model = ?",
        (doc_id, model),
    ).fetchone()
    return row[0] if row else None
