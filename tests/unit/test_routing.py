# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : tests/unit/test_routing.py
# Version      : 0.1.0
# Date         : 2026-11-11
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Unit tests for the routing table and the step 0 checks."""

from pathlib import Path

import pytest

from personaldocagent.config import AnalysisPolicy, Config, PerimeterConfig, RoutingConfig
from personaldocagent.db.connection import connect, init_db
from personaldocagent.routing import is_duplicate, route_for, run_step0_checks


def _config(root: Path, exclusions=()) -> Config:
    return Config(
        perimeter=PerimeterConfig(allowed_roots=[str(root)], exclusions=list(exclusions)),
        routing=RoutingConfig(
            default_route="reject",
            formats={"direct_read": [".txt", ".md"], "ocr": [".pdf"]},
        ),
        policy=AnalysisPolicy(),
    )


@pytest.fixture
def conn(tmp_path):
    init_db(tmp_path / "test.db")
    c = connect(tmp_path / "test.db")
    yield c
    c.close()


@pytest.fixture
def root(tmp_path):
    r = tmp_path / "collection"
    r.mkdir()
    return r


def test_route_by_extension_case_insensitive(root):
    routing = _config(root).routing
    assert route_for(Path("a.pdf"), routing) == "ocr"
    assert route_for(Path("B.PDF"), routing) == "ocr"
    assert route_for(Path("notes.MD"), routing) == "direct_read"
    assert route_for(Path("a.xyz"), routing) == "reject"


def test_is_duplicate_on_canonical_source_file(conn, root):
    target = root / "a.pdf"
    target.write_text("x", encoding="utf-8")
    assert is_duplicate(target, conn) is False
    conn.execute(
        "INSERT INTO document (source_file, date_added) VALUES (?, '2026-11-01')",
        (str(target.resolve()),),
    )
    conn.commit()
    assert is_duplicate(target, conn) is True


def test_checks_outside_perimeter(conn, root, tmp_path):
    target = tmp_path / "outside.pdf"
    target.write_text("x", encoding="utf-8")
    journal = tmp_path / "rejections.log"
    res = run_step0_checks(target, _config(root), conn, journal)
    assert res.accepted is False and res.reason == "outside_perimeter"
    assert "outside_perimeter" in journal.read_text(encoding="utf-8")


def test_checks_unsupported_format(conn, root, tmp_path):
    target = root / "a.xyz"
    target.write_text("x", encoding="utf-8")
    journal = tmp_path / "rejections.log"
    res = run_step0_checks(target, _config(root), conn, journal)
    assert res.accepted is False and res.reason == "unsupported_format"
    assert "unsupported_format" in journal.read_text(encoding="utf-8")


def test_checks_duplicate(conn, root, tmp_path):
    target = root / "a.pdf"
    target.write_text("x", encoding="utf-8")
    conn.execute(
        "INSERT INTO document (source_file, date_added) VALUES (?, '2026-11-01')",
        (str(target.resolve()),),
    )
    conn.commit()
    journal = tmp_path / "rejections.log"
    res = run_step0_checks(target, _config(root), conn, journal)
    assert res.accepted is False and res.reason == "duplicate" and res.route == "ocr"
    assert "duplicate" in journal.read_text(encoding="utf-8")


def test_checks_ok_ocr_route_no_rejection(conn, root, tmp_path):
    target = root / "a.pdf"
    target.write_text("x", encoding="utf-8")
    journal = tmp_path / "rejections.log"
    res = run_step0_checks(target, _config(root), conn, journal)
    assert res.accepted is True and res.route == "ocr" and res.reason is None
    assert not journal.exists()
