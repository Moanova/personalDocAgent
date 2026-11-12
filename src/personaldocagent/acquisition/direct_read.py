# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : acquisition/direct_read.py
# Version      : 0.2.0
# Date         : 2026-11-12
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Direct read route: TXT, MD, cleaned HTML, DOCX, ODT (no API call)."""

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup
from docx import Document
from odf import teletype
from odf.opendocument import load
from odf.text import P

from ..contracts import AcquisitionResult


def _read_plain(path: Path) -> str:
    """Read a TXT or Markdown file as UTF-8 text."""
    return path.read_text(encoding="utf-8")


def _read_html(path: Path) -> str:
    """Read an HTML file as cleaned text (scripts and styles removed)."""
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text(separator="\n")


def _read_docx(path: Path) -> str:
    """Read a DOCX file: paragraphs then table rows (tab-separated cells)."""
    document = Document(str(path))
    parts = [paragraph.text for paragraph in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            parts.append("\t".join(cell.text for cell in row.cells))
    return "\n".join(part for part in parts if part)


def _read_odt(path: Path) -> str:
    """Read an ODT file: extracted text of every paragraph element."""
    document = load(str(path))
    return "\n".join(teletype.extractText(paragraph) for paragraph in document.getElementsByType(P))


_READERS: dict[str, Callable[[Path], str]] = {
    ".txt": _read_plain,
    ".md": _read_plain,
    ".html": _read_html,
    ".htm": _read_html,
    ".docx": _read_docx,
    ".odt": _read_odt,
}


def read_direct(path: Path) -> AcquisitionResult:
    """Read a document directly (no API call) and return the acquisition result (raw text)."""
    path = Path(path)
    reader = _READERS.get(path.suffix.lower())
    if reader is None:
        raise ValueError(f"Unsupported extension for the direct read route: {path}")
    try:
        text = reader(path)
    except Exception as exc:
        raise ValueError(f"Direct read failed for {path}: {exc}") from exc
    return AcquisitionResult(
        source_file=str(path.resolve()),
        route="direct_read",
        text=text,
        model=None,
        conversion_date=datetime.now(timezone.utc).isoformat(),
    )
