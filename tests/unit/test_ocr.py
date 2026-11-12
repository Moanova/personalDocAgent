# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : tests/unit/test_ocr.py
# Version      : 0.1.0
# Date         : 2026-11-12
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Unit tests for the OCR route and the conversion persistence (task T2.2, TU-09 to TU-14)."""

from datetime import datetime
from types import SimpleNamespace

import pytest

from personaldocagent.acquisition.ocr import OCR_MODEL, convert, load_conversion, save_conversion
from personaldocagent.contracts import AcquisitionResult
from personaldocagent.db.connection import connect, init_db


class _FakeClient:
    """Fake Mistral client: records calls, returns two out-of-order OCR pages."""

    def __init__(self):
        self.calls = []
        self.raise_exc = None

        def upload(*, file, purpose=None):
            self.calls.append(("upload", file, purpose))
            return SimpleNamespace(id="file-123")

        def process(*, model, document):
            self.calls.append(("process", model, document))
            if self.raise_exc is not None:
                raise self.raise_exc
            pages = [
                SimpleNamespace(index=1, markdown="page deux"),
                SimpleNamespace(index=0, markdown="page un"),
            ]
            return SimpleNamespace(pages=pages)

        self.files = SimpleNamespace(upload=upload)
        self.ocr = SimpleNamespace(process=process)


@pytest.fixture
def pdf(tmp_path):
    f = tmp_path / "scan.pdf"
    f.write_bytes(b"%PDF-1.4 fake")
    return f


@pytest.fixture
def conn(tmp_path):
    init_db(tmp_path / "test.db")
    c = connect(tmp_path / "test.db")
    c.execute(
        "INSERT INTO document (source_file, date_added) VALUES ('/collection/scan.pdf', '2026-11-12')"
    )
    c.commit()
    yield c
    c.close()


def _result(text="Facture EDF mars 2026"):
    return AcquisitionResult(
        source_file="/collection/scan.pdf",
        route="ocr",
        text=text,
        model=OCR_MODEL,
        conversion_date="2026-11-12T10:00:00+00:00",
    )


def test_convert_contract(pdf):
    """TU-09: AcquisitionResult fields, pages joined in index order."""
    result = convert(pdf, client=_FakeClient())
    assert result.route == "ocr"
    assert result.model == "mistral-ocr-latest"
    assert result.text == "page un\n\npage deux"
    assert result.source_file == str(pdf.resolve())
    datetime.fromisoformat(result.conversion_date)


def test_convert_uploads_then_processes(pdf):
    """TU-10: files.upload(purpose="ocr") before ocr.process with the file_id and model."""
    client = _FakeClient()
    convert(pdf, client=client)
    assert [call[0] for call in client.calls] == ["upload", "process"]
    _, upload_file, purpose = client.calls[0]
    assert purpose == "ocr"
    assert upload_file["file_name"] == "scan.pdf"
    assert upload_file["content"] == b"%PDF-1.4 fake"
    _, model, document = client.calls[1]
    assert model == "mistral-ocr-latest"
    assert document == {"type": "file", "file_id": "file-123"}


def test_convert_api_error_wrapped(pdf):
    """TU-11: API error raised as a contextual ValueError."""
    client = _FakeClient()
    client.raise_exc = RuntimeError("API down")
    with pytest.raises(ValueError, match="OCR conversion failed"):
        convert(pdf, client=client)


def test_save_and_load_conversion_idempotent(conn):
    """TU-12: save_conversion inserts once (True), then ignores (False); load roundtrip."""
    assert save_conversion(conn, 1, _result()) is True
    assert save_conversion(conn, 1, _result("autre texte")) is False
    assert load_conversion(conn, 1, OCR_MODEL) == "Facture EDF mars 2026"
    assert load_conversion(conn, 1, "autre-modele") is None
    count = conn.execute("SELECT COUNT(*) FROM conversion").fetchone()[0]
    assert count == 1


def test_save_conversion_feeds_fts(conn):
    """TU-13: the FTS trigger indexes the saved text in conversion_fts."""
    save_conversion(conn, 1, _result())
    row = conn.execute(
        "SELECT rowid FROM conversion_fts WHERE conversion_fts MATCH 'EDF'"
    ).fetchone()
    assert row is not None


def test_missing_api_key_raises_without_network(pdf, monkeypatch):
    """TU-14: MISTRAL_API_KEY unset -> explicit RuntimeError, no client built."""
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="MISTRAL_API_KEY"):
        convert(pdf)
