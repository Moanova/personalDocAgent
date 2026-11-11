# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : issuers.py
# Version      : 0.1.0
# Date         : 2026-11-11
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Issuer matching: exact then approximate SQL search (LIKE)."""

import sqlite3

from .contracts import IssuerMatch


def match_issuer(conn: sqlite3.Connection, candidate: str) -> IssuerMatch:
    """Match an issuer candidate: known, ambiguous or unknown."""
    raise NotImplementedError
