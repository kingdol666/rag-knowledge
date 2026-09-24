"""Compatibility wrapper for the shared structure-aware splitter.

The public service API remains stable for existing routes while the actual
boundary logic lives in ``semantic_splitter``. Agent plans are optional and
must pass the same source-backed validation used by the ingest script.
"""
from __future__ import annotations

from .semantic_splitter import (
    DEFAULT_DESC_CHARS,
    DEFAULT_OVERLAP_CHARS,
    MIN_MAX_CHARS,
    SplitPart,
    StructuralUnit,
    clamp_max_chars,
    content_description,
    plan_split,
    scan_structural_units,
    should_split,
    source_sha256,
    split_document,
)

# Effective default is configured by config.yml; keep this symbol for clients
# that imported the old wrapper constant.
DEFAULT_MAX_CHARS = 30_000

__all__ = [
    "DEFAULT_DESC_CHARS", "DEFAULT_MAX_CHARS", "DEFAULT_OVERLAP_CHARS",
    "MIN_MAX_CHARS", "SplitPart", "StructuralUnit", "clamp_max_chars",
    "content_description", "plan_split", "scan_structural_units",
    "should_split", "source_sha256", "split_document",
]
