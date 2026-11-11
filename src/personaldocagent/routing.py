# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : routing.py
# Version      : 0.1.0
# Date         : 2026-11-11
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Routing table (extension to processing route) and deterministic step 0 checks."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .config import Config, RoutingConfig
from .perimeter import DEFAULT_REJECTION_LOG, is_allowed, log_rejection


@dataclass
class Step0Result:
    """Result of the three step 0 checks: path allowed, format accepted, not a duplicate."""

    accepted: bool
    route: str
    reason: str | None = None


def route_for(path: Path, routing: RoutingConfig) -> str:
    """Processing route of a file according to its extension (case-insensitive), else default_route."""
    ext = Path(path).suffix.lower()
    for route, extensions in routing.formats.items():
        if ext in {e.lower() for e in extensions}:
            return route
    return routing.default_route


def is_duplicate(path: Path, conn: sqlite3.Connection) -> bool:
    """Does a document already exist in the database for this source file (canonical path)?"""
    canonical = str(Path(path).resolve())
    return conn.execute("SELECT 1 FROM document WHERE source_file = ?", (canonical,)).fetchone() is not None


def run_step0_checks(
    path: Path,
    config: Config,
    conn: sqlite3.Connection,
    journal: Path = DEFAULT_REJECTION_LOG,
) -> Step0Result:
    """Chain the three checks before conversion; every rejection is logged without reading the file."""
    if not is_allowed(path, config.perimeter):
        log_rejection(path, "outside_perimeter", journal)
        return Step0Result(False, "reject", "outside_perimeter")
    route = route_for(path, config.routing)
    if route == "reject":
        log_rejection(path, "unsupported_format", journal)
        return Step0Result(False, route, "unsupported_format")
    if is_duplicate(path, conn):
        log_rejection(path, "duplicate", journal)
        return Step0Result(False, route, "duplicate")
    return Step0Result(True, route)
