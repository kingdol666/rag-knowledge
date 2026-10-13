#!/usr/bin/env python3
"""Stability suite runner — 3 tasks × 3 lanes × N rounds against the live platform.

This is the canonical, re-runnable entry point for the suite whose results live in
`review/stability-multiround-20261013/results/` (27 cells, 27/27 lane-compliant,
median 52 s). The original implementation was written under
`review/stability-multiround-20260930/`; the 2026-10-13 cleanup archived that
directory, so this launcher delegates to the archived implementation when present
and otherwise tells you the one command that restores it.

Behaviour (unchanged):
  * one real `POST /api/claude/chat` per cell (non-stream, `mcpMount=stdio`);
  * lane A = vector-first, lane B = librarian / catalog-only (no vector calls),
    lane C = platform hybrid (`kbEnhanced` + `kbIds`);
  * tasks: attention formula (answerable) · seismic-wave classes (not covered by
    the corpus) · Sichuan pickles (out of corpus) — the last two must be refused.

Usage:
    python review/stability-multiround-20261013/run_stability.py r1 r2 r3
    python review/stability-multiround-20261013/run_stability.py r1 \
        --out review/stability-multiround-20261013/results

Cost: roughly $0.35-0.85 per cell (~$17 for 27 cells), ~30-40 min wall clock.
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARCHIVED = HERE.parent / "archive-superseded" / "stability-multiround-20260930" / "run_stability.py"

if not ARCHIVED.is_file():
    sys.exit(
        "stability runner implementation not found.\n"
        f"  expected: {ARCHIVED}\n"
        "  restore it with (run from the repo root; the archive stores paths as "
        "review/<dir>):\n"
        "    mkdir -p review && tar -xzf "
        "review/archive-superseded/review-superseded-20261013.tar.gz -C . "
        "review/stability-multiround-20260930\n"
        "  (the archived 27-cell results stay valid either way)"
    )

sys.argv[0] = str(ARCHIVED)
runpy.run_path(str(ARCHIVED), run_name="__main__")
