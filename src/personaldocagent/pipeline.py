# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : pipeline.py
# Version      : 0.2.0
# Date         : 2026-11-12
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Deterministic orchestration of the pipeline (step 0 acquisition for now)."""

import sqlite3
from collections.abc import Callable
from pathlib import Path

from .acquisition import ocr
from .acquisition.direct_read import read_direct
from .config import Config, load_config
from .contracts import AcquisitionResult, WriteResult
from .db.connection import connect, init_db
from .perimeter import DEFAULT_REJECTION_LOG, iter_allowed_files, log_rejection
from .routing import run_step0_checks

DEFAULT_CHUNK_CHARS = 8000


def chunk_text(text: str, max_chars: int = DEFAULT_CHUNK_CHARS) -> list[str]:
    """Split a long text into segments of at most max_chars, preferring paragraph boundaries."""
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]
    chunks = []
    current = ""
    for paragraph in text.split("\n\n"):
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            for start in range(0, len(paragraph), max_chars):
                chunks.append(paragraph[start : start + max_chars])
        elif current and len(current) + 2 + len(paragraph) > max_chars:
            chunks.append(current)
            current = paragraph
        else:
            current = f"{current}\n\n{paragraph}" if current else paragraph
    if current:
        chunks.append(current)
    return chunks


def acquire(
    config: Config,
    root: Path,
    conn: sqlite3.Connection,
    journal: Path = DEFAULT_REJECTION_LOG,
    ocr_convert: Callable[[Path], AcquisitionResult] | None = None,
) -> list[AcquisitionResult]:
    """Step 0 acquisition over an allowed root: checks, route dispatch, rejections journalled."""
    if ocr_convert is None:
        ocr_convert = ocr.convert
    results = []
    for path in iter_allowed_files(root, config.perimeter):
        step0 = run_step0_checks(path, config, conn, journal)
        if not step0.accepted:
            continue
        try:
            if step0.route == "direct_read":
                results.append(read_direct(path))
            elif step0.route == "ocr":
                results.append(ocr_convert(path))
            else:
                log_rejection(path, f"unknown_route:{step0.route}", journal)
        except ValueError:
            log_rejection(path, "conversion_failed", journal)
    return results


def run_step0(config_dir: Path, base: Path) -> list[AcquisitionResult]:
    """Run step 0 acquisition over every allowed root of the configuration."""
    config = load_config(Path(config_dir))
    init_db(base)
    conn = connect(base)
    try:
        results = []
        for root in config.perimeter.allowed_roots:
            results.extend(acquire(config, Path(root), conn))
    finally:
        conn.close()
    return results


def run(config_dir: Path, root: Path) -> list[WriteResult]:
    """Run the full pipeline (steps 0-7) over the files of an allowed root (later EPICs)."""
    raise NotImplementedError
