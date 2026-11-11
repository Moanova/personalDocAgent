# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : tests/unit/test_perimeter.py
# Version      : 0.1.0
# Date         : 2026-11-11
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Unit tests for the file-system access perimeter."""

from pathlib import Path

import pytest

from personaldocagent.config import PerimeterConfig
from personaldocagent.perimeter import is_allowed, iter_allowed_files, log_rejection


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / "collection"
    (root / "statements" / "2026").mkdir(parents=True)
    (root / "statements" / "2026" / "jan.pdf").write_text("x", encoding="utf-8")
    (root / "statements" / "draft.txt").write_text("x", encoding="utf-8")
    (root / "archive").mkdir()
    (root / "archive" / "old.pdf").write_text("x", encoding="utf-8")
    (root / "notes.md").write_text("x", encoding="utf-8")
    outside = tmp_path / "secret.pdf"
    outside.write_text("x", encoding="utf-8")
    (root / "internal_link.pdf").symlink_to(root / "notes.md")
    (root / "external_link.pdf").symlink_to(outside)
    return root, outside


def perimeter(root: Path, exclusions=(), follow=False) -> PerimeterConfig:
    return PerimeterConfig(
        allowed_roots=[str(root)],
        exclusions=list(exclusions),
        follow_symlinks=follow,
    )


def test_deny_by_default_with_empty_roots(tree):
    root, outside = tree
    p = PerimeterConfig()
    assert is_allowed(root / "notes.md", p) is False
    assert is_allowed(outside, p) is False


def test_file_inside_root_allowed(tree):
    root, _ = tree
    assert is_allowed(root / "notes.md", perimeter(root)) is True
    assert is_allowed(root / "statements" / "2026" / "jan.pdf", perimeter(root)) is True


def test_outside_root_denied(tree):
    root, outside = tree
    assert is_allowed(outside, perimeter(root)) is False


def test_exclusion_takes_priority_over_allowance(tree):
    root, _ = tree
    p = perimeter(root, exclusions=[f"{root}/archive/**"])
    assert is_allowed(root / "archive" / "old.pdf", p) is False
    assert is_allowed(root / "notes.md", p) is True


def test_exclusion_glob_star_within_segment(tree):
    root, _ = tree
    p = perimeter(root, exclusions=[f"{root}/*.md"])
    assert is_allowed(root / "notes.md", p) is False
    assert is_allowed(root / "statements" / "draft.txt", p) is True


def test_realpath_internal_link_allowed_external_link_denied(tree):
    root, _ = tree
    p = perimeter(root)
    assert is_allowed(root / "internal_link.pdf", p) is True
    assert is_allowed(root / "external_link.pdf", p) is False


def test_walk_stops_inside_excluded_directory(tree):
    root, _ = tree
    p = perimeter(root, exclusions=[f"{root}/archive/**"])
    found = {f.name for f in iter_allowed_files(root, p)}
    assert found == {"jan.pdf", "draft.txt", "notes.md", "internal_link.pdf"}


def test_walk_of_disallowed_root_yields_nothing(tree):
    root, outside = tree
    assert list(iter_allowed_files(outside, perimeter(root))) == []


def test_log_rejection_writes_timestamped_line(tree, tmp_path):
    root, outside = tree
    journal = tmp_path / "data" / "rejections.log"
    log_rejection(outside, "outside_perimeter", journal)
    content = journal.read_text(encoding="utf-8")
    assert "outside_perimeter" in content
    assert str(outside.resolve()) in content
