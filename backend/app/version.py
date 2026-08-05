"""
Project version resolution for the backend.

The single source of truth is the ``VERSION`` file at the repository root
(next to ``backend/``). ragctl and kb-mcp read the same file, so the backend
never drifts from the shipped release number.
"""
from __future__ import annotations

from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_ROOT_VERSION_FILE = _BACKEND_DIR.parent / "VERSION"


def get_version() -> str:
    """Return the project version from the root VERSION file.

    Falls back to ``0.0.0`` only when the file is missing (e.g. the backend
    is vendored standalone without the repo root).
    """
    try:
        v = _ROOT_VERSION_FILE.read_text(encoding="utf-8").strip()
        if v:
            return v
    except OSError:
        pass
    return "0.0.0"
