# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : pipeline.py
# Version      : 0.5.0
# Date         : 2026-11-12
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Deterministic orchestration of the pipeline (steps 0-2: acquisition, persistence, analysis)."""

import sqlite3
import sys
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from .acquisition import ocr
from .acquisition.direct_read import read_direct
from .analysis import analyze
from .classification import export_flat, load_tree
from .config import Config, load_config
from .contracts import AcquisitionResult, AnalysisRecord, WriteResult
from .db.connection import connect, init_db
from .issuers import match_issuer, resolve_issuer
from .perimeter import DEFAULT_REJECTION_LOG, iter_allowed_files, log_rejection
from .routing import run_step0_checks

DEFAULT_CHUNK_CHARS = 8000

_MIME_BY_EXT = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".html": "text/html",
    ".htm": "text/html",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".webp": "image/webp",
}


def persist(conn: sqlite3.Connection, result: AcquisitionResult) -> WriteResult:
    """Step 1: persist the formal record of an acquired document (idempotent on source_file)."""
    source_file = result.source_file
    existing = conn.execute(
        "SELECT doc_id FROM document WHERE source_file = ?", (source_file,)
    ).fetchone()
    if existing:
        return WriteResult(doc_id=existing[0], written=False, reason="duplicate")
    suffix = Path(source_file).suffix.lower()
    try:
        cursor = conn.execute(
            "INSERT INTO document (source_file, date_added, status, dc_format) VALUES (?, ?, 'active', ?)",
            (
                source_file,
                datetime.now(timezone.utc).isoformat(),
                _MIME_BY_EXT.get(suffix, "application/octet-stream"),
            ),
        )
        doc_id = cursor.lastrowid
        ocr.save_conversion(conn, doc_id, replace(result, model=result.model or result.route))
        return WriteResult(doc_id=doc_id, written=True)
    except sqlite3.IntegrityError:
        conn.rollback()
        row = conn.execute(
            "SELECT doc_id FROM document WHERE source_file = ?", (source_file,)
        ).fetchone()
        return WriteResult(doc_id=row[0] if row else -1, written=False, reason="duplicate")


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


def analyze_base(
    config_dir: Path, base: Path, client=None, with_issuers: bool = False
) -> list[AnalysisRecord]:
    """Step 2: analyze every persisted document text (first chunk) into AnalysisRecords.

    With with_issuers=True, also resolve the issuer of each record (match + confidence rule)
    and set document.issuer_id when known.
    """
    config = load_config(Path(config_dir))
    init_db(base)
    conn = connect(base)
    try:
        if conn.execute("SELECT COUNT(*) FROM category").fetchone()[0] == 0:
            load_tree(conn, Path(config_dir) / "classification.yaml")
        categories = export_flat(conn)
        rows = conn.execute(
            """
            SELECT d.doc_id, c.extracted_text FROM document d
            JOIN conversion c ON c.doc_id = d.doc_id
            WHERE c.conversion_date = (
                SELECT MAX(conversion_date) FROM conversion WHERE doc_id = d.doc_id
            )
            ORDER BY d.doc_id
            """
        ).fetchall()
        records = []
        for row in rows:
            segments = chunk_text(row["extracted_text"])
            try:
                record = analyze(segments[0] if segments else "", categories, config.policy, client)
                if with_issuers and record.issuer_candidate:
                    match = match_issuer(conn, record.issuer_candidate)
                    resolved = resolve_issuer(
                        conn, match, record.issuer_candidate, record.confidence, config.policy
                    )
                    if resolved.status == "known" and resolved.issuer_id is not None:
                        conn.execute(
                            "UPDATE document SET issuer_id = ? WHERE doc_id = ?",
                            (resolved.issuer_id, row["doc_id"]),
                        )
                        conn.commit()
                records.append(record)
            except ValueError as exc:
                print(f"Step 2 analysis: doc_id={row['doc_id']} skipped ({exc})", file=sys.stderr)
    finally:
        conn.close()
    return records


def run(config_dir: Path, base: Path) -> list[WriteResult]:
    """Run steps 0-1 (acquisition + formal persistence) over every allowed root of the configuration."""
    config = load_config(Path(config_dir))
    init_db(base)
    conn = connect(base)
    try:
        results = []
        for root in config.perimeter.allowed_roots:
            for acquired in acquire(config, Path(root), conn):
                results.append(persist(conn, acquired))
    finally:
        conn.close()
    return results
