# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : classification.py
# Version      : 0.1.0
# Date         : 2026-11-11
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Classification tree: YAML seed loading and flat export."""

import sqlite3
from pathlib import Path

import yaml


def load_tree(conn: sqlite3.Connection, seed: Path) -> int:
    """Load the YAML seed into the category table (idempotent). Return the number of active categories."""
    with Path(seed).open("r", encoding="utf-8") as f:
        roots = yaml.safe_load(f)
    if not isinstance(roots, list):
        raise ValueError(f"Invalid seed (list of nodes expected): {seed}")
    total = 0
    for node in roots:
        total += _load_node(conn, node, parent_id=None, depth=1)
    conn.commit()
    return total


def _load_node(conn: sqlite3.Connection, node: dict, parent_id: int | None, depth: int) -> int:
    category_id = _find_or_create(conn, parent_id, node["label"], depth)
    total = 1
    for child in node.get("children") or []:
        total += _load_node(conn, child, category_id, depth + 1)
    return total


def _find_or_create(conn: sqlite3.Connection, parent_id: int | None, label: str, depth: int) -> int:
    if parent_id is None:
        row = conn.execute(
            "SELECT category_id FROM category WHERE parent_id IS NULL AND label = ?",
            (label,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT category_id FROM category WHERE parent_id = ? AND label = ?",
            (parent_id, label),
        ).fetchone()
    if row is not None:
        conn.execute(
            "UPDATE category SET depth = ?, active = 1 WHERE category_id = ?",
            (depth, row[0]),
        )
        return row[0]
    cur = conn.execute(
        "INSERT INTO category (parent_id, label, depth, active) VALUES (?, ?, ?, 1)",
        (parent_id, label, depth),
    )
    return cur.lastrowid


def export_flat(conn: sqlite3.Connection) -> str:
    """Flat export of active categories (id: label, indented by depth) for the analysis agent context."""
    lines = []
    for row in conn.execute(
        "SELECT category_id, label, depth FROM category WHERE active = 1 ORDER BY category_id"
    ):
        lines.append(f"{'  ' * (row['depth'] - 1)}{row['category_id']}: {row['label']}")
    return "\n".join(lines)
