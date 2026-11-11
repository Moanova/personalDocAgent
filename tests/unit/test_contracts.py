# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : tests/unit/test_contracts.py
# Version      : 0.1.0
# Date         : 2026-11-11
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Unit tests for the interface contracts (dataclasses)."""

import inspect
import json
from dataclasses import asdict

import pytest

from personaldocagent import analysis, issuers, pipeline
from personaldocagent.acquisition import direct_read, ocr
from personaldocagent.contracts import (
    AcquisitionResult,
    AnalysisRecord,
    DocumentRecord,
    IssuerMatch,
    SearchFilters,
    WriteResult,
)
from personaldocagent.interrogation import tools


def test_acquisition_result_json_serializable():
    r = AcquisitionResult(
        source_file="/collection/a.pdf",
        route="ocr",
        text="# Invoice",
        model="mistral-ocr-latest",
        conversion_date="2026-11-11",
    )
    d = asdict(r)
    assert json.loads(json.dumps(d)) == d
    assert d["route"] == "ocr"


def test_analysis_record_validate_keyword_limit():
    record = AnalysisRecord(
        category_id=15,
        issuer_candidate="EDF",
        keywords=["word"] * 11,
        summary="summary",
        attributes={"amount_eur": 87.4},
        confidence=0.95,
    )
    with pytest.raises(ValueError):
        record.validate(max_keywords=10)
    record.keywords = record.keywords[:10]
    record.validate(max_keywords=10)


def test_analysis_record_attributes_json_roundtrip():
    record = AnalysisRecord(1, None, [], "s", {"amount_eur": 87.4}, 0.9)
    assert json.loads(json.dumps(asdict(record)["attributes"])) == {"amount_eur": 87.4}


def test_document_record_defaults_and_json():
    r = DocumentRecord(source_file="/x.pdf", date_added="2026-11-11")
    assert r.status == "active"
    assert r.attributes == "{}"
    assert r.agents == [] and r.subjects == [] and r.categories == []
    json.dumps(asdict(r))


def test_issuer_match_and_write_result():
    m = IssuerMatch(status="known", issuer_id=3)
    assert asdict(m)["status"] == "known"
    w = WriteResult(doc_id=1, written=True)
    assert w.reason is None


def test_search_filters_all_optional():
    f = SearchFilters(status="active", keyword="invoice")
    assert f.category_id is None and f.issuer_id is None
    json.dumps(asdict(f))


def test_stub_signatures_reference_the_contracts():
    assert "AcquisitionResult" in str(inspect.signature(direct_read.read_direct).return_annotation)
    assert "AcquisitionResult" in str(inspect.signature(ocr.convert).return_annotation)
    assert "AnalysisRecord" in str(inspect.signature(analysis.analyze).return_annotation)
    assert "IssuerMatch" in str(inspect.signature(issuers.match_issuer).return_annotation)
    assert "WriteResult" in str(inspect.signature(pipeline.run).return_annotation)
    param = inspect.signature(tools.search_documents).parameters["filters"]
    assert "SearchFilters" in str(param.annotation)
