# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : __main__.py
# Version      : 0.1.0
# Date         : 2026-11-11
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Module entry point: python -m personaldocagent."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
