"""Filesystem helpers shared by the API routes and storage."""

from __future__ import annotations

from pathlib import Path


def safe_child(root: Path, relative_path: str) -> Path | None:
    """Resolve ``relative_path`` under ``root``, refusing path traversal."""
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate
