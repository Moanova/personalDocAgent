# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : perimeter.py
# Version      : 0.3.0
# Date         : 2026-11-12
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""File-system access perimeter evaluation (deny by default).

Evaluation order (design §3bis): explicit exclusion > explicit allowance > denied.
Canonical resolution (realpath) happens before any evaluation. The application is read-only on the file system.
"""

import os
import re
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

from .config import PerimeterConfig

DEFAULT_REJECTION_LOG = Path("data") / "rejections.log"


def _glob_to_regex(pattern: str) -> re.Pattern:
    """Convert a glob pattern to a regex: ** crosses directories, * and ? stay within one segment.

    A leading **/ also matches the leading / of absolute POSIX paths. Backslashes are normalized
    to forward slashes so Windows-style patterns match on every OS.
    """
    pattern = pattern.replace("\\", "/")
    parts = []
    i = 0
    if pattern.startswith("**/"):
        parts.append("/?(?:[^/]+/)*")
        i = 3
    while i < len(pattern):
        if pattern.startswith("**/", i):
            parts.append("(?:[^/]+/)*")
            i += 3
        elif pattern.startswith("**", i):
            parts.append(".*")
            i += 2
        elif pattern[i] == "*":
            parts.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            parts.append("[^/]")
            i += 1
        else:
            parts.append(re.escape(pattern[i]))
            i += 1
    return re.compile("^" + "".join(parts) + "$")


def _is_excluded(canonical: Path, exclusions: list[str]) -> bool:
    text = canonical.as_posix()
    return any(_glob_to_regex(pattern).match(text) for pattern in exclusions)


def _is_under_root(canonical: Path, root: str) -> bool:
    try:
        canonical.relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False


def is_allowed(path: Path, perimeter: PerimeterConfig) -> bool:
    """Evaluate a path against exclusions then allowed roots (path resolved canonically first)."""
    canonical = Path(path).resolve()
    if _is_excluded(canonical, perimeter.exclusions):
        return False
    return any(_is_under_root(canonical, root) for root in perimeter.allowed_roots)


def iter_allowed_files(root: Path, perimeter: PerimeterConfig) -> Iterator[Path]:
    """Recursively walk an allowed root: stops inside excluded directories, yields only allowed files."""
    root = Path(root).resolve()
    if not is_allowed(root, perimeter):
        return
    for dirpath, dirnames, filenames in os.walk(root, followlinks=perimeter.follow_symlinks):
        dirnames[:] = [d for d in dirnames if not _is_excluded(Path(dirpath) / d, perimeter.exclusions)]
        for name in filenames:
            path = Path(dirpath) / name
            if is_allowed(path, perimeter):
                yield path


def log_rejection(path: Path, reason: str, journal: Path = DEFAULT_REJECTION_LOG) -> None:
    """Append a timestamped line to the rejection log (the rejected file is never read)."""
    journal = Path(journal)
    journal.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with journal.open("a", encoding="utf-8") as f:
        f.write(f"{timestamp} | {reason} | {Path(path).resolve()}\n")
