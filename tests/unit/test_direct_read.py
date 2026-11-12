# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : tests/unit/test_direct_read.py
# Version      : 0.1.0
# Date         : 2026-11-12
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Unit tests for the direct read route (task T2.1, TU-01 to TU-08 in tests/plan_tests.md)."""

from datetime import datetime
from pathlib import Path

import pytest
from docx import Document
from odf.opendocument import OpenDocumentText
from odf.text import P

from personaldocagent.acquisition.direct_read import read_direct


def _write_docx(path: Path) -> None:
    doc = Document()
    doc.add_paragraph("Facture du 12 novembre 2026")
    table = doc.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Désignation"
    table.cell(0, 1).text = "Montant"
    doc.save(str(path))


def _write_odt(path: Path) -> None:
    doc = OpenDocumentText()
    doc.text.addElement(P(text="Relevé bancaire janvier"))
    doc.save(str(path))


def test_read_txt_utf8(tmp_path):
    """TU-01: TXT read as UTF-8, accents preserved."""
    f = tmp_path / "notes.txt"
    f.write_text("Été à l'île — accents çéàü", encoding="utf-8")
    assert read_direct(f).text == "Été à l'île — accents çéàü"


def test_read_markdown_verbatim(tmp_path):
    """TU-02: Markdown read verbatim."""
    f = tmp_path / "readme.md"
    f.write_text("# Titre\n\nCorps du texte.\n", encoding="utf-8")
    assert read_direct(f).text == "# Titre\n\nCorps du texte.\n"


def test_read_html_cleaned(tmp_path):
    """TU-03: HTML text only, script and style contents excluded."""
    f = tmp_path / "page.html"
    f.write_text(
        "<html><head><style>body { color: red; }</style></head>"
        "<body><h1>Titre</h1><p>Paragraphe</p><script>alert('x')</script></body></html>",
        encoding="utf-8",
    )
    text = read_direct(f).text
    assert "Titre" in text
    assert "Paragraphe" in text
    assert "alert" not in text
    assert "color" not in text


def test_read_docx_paragraphs_and_tables(tmp_path):
    """TU-04: DOCX paragraphs and table cells extracted."""
    f = tmp_path / "doc.docx"
    _write_docx(f)
    text = read_direct(f).text
    assert "Facture du 12 novembre 2026" in text
    assert "Désignation" in text
    assert "Montant" in text


def test_read_odt(tmp_path):
    """TU-05: ODT text extracted via odfpy."""
    f = tmp_path / "doc.odt"
    _write_odt(f)
    assert "Relevé bancaire janvier" in read_direct(f).text


def test_acquisition_result_contract(tmp_path):
    """TU-06: AcquisitionResult fields (route, model=None, canonical source, ISO date)."""
    f = tmp_path / "a.txt"
    f.write_text("contenu", encoding="utf-8")
    result = read_direct(f)
    assert result.route == "direct_read"
    assert result.model is None
    assert result.source_file == str(f.resolve())
    assert result.text == "contenu"
    datetime.fromisoformat(result.conversion_date)


def test_unsupported_extension_rejected(tmp_path):
    """TU-07: extension outside the direct_read route raises a contextual ValueError."""
    f = tmp_path / "a.pdf"
    f.write_bytes(b"%PDF-1.4")
    with pytest.raises(ValueError, match="Unsupported extension"):
        read_direct(f)


def test_corrupt_file_rejected(tmp_path):
    """TU-07: unreadable/corrupt file raises a contextual ValueError, no partial read."""
    f = tmp_path / "broken.docx"
    f.write_bytes(b"not a docx")
    with pytest.raises(ValueError, match="Direct read failed"):
        read_direct(f)


def test_dispatch_case_insensitive(tmp_path):
    """TU-08: dispatch on the lowercased extension (.TXT, .HTML routed correctly)."""
    f = tmp_path / "A.TXT"
    f.write_text("maj", encoding="utf-8")
    assert read_direct(f).text == "maj"
    h = tmp_path / "B.HTML"
    h.write_text("<p>Salut</p>", encoding="utf-8")
    assert "Salut" in read_direct(h).text
