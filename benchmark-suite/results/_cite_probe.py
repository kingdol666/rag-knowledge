#!/usr/bin/env python3
"""TEMP probe: calibrate the citation-marker regex against the 3ec2174 run
(paper claims cited = 9 / 6 / 1 for a2 / b / c). Read-only."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
RUN = SUITE / "results" / "runs" / "run-20260930T150453Z-3ec2174"

TARGET = {"a2": 9, "b": 6, "c": 1}

CANDIDATES = {
    "Q1 marker": r"(?:\bpart\s+\d+\s+of\s+\d+|\bchunk[_ ]?(?:index|id)?\s*\d+"
                r"|\bsections?\s+[0-9]|\btables?\s+[0-9]|\bfigures?\s+[0-9]"
                r"|\bappendi(?:x|ces)\s+[A-Z0-9]|§\s*\d)",
    "Q2 +dotted": r"(?:\bpart\s+\d+\s+of\s+\d+|\bchunk[_ ]?(?:index|id)?\s*\d+"
                  r"|\bsections?\s+[0-9]+(?:\.[0-9]+)*|§\s*\d+(?:\.[0-9]+)*"
                  r"|\btables?\s+[0-9]+|\bfigures?\s+[0-9]+|\bappendi(?:x|ces)\s+[A-Z0-9])",
    "Q3 no-sections": r"(?:\bpart\s+\d+\s+of\s+\d+|\bchunk[_ ]?(?:index|id)?\s*\d+"
                      r"|\btables?\s+[0-9]+|\bfigures?\s+[0-9]+|§\s*\d+(?:\.[0-9]+)*"
                      r"|\bappendi(?:x|ces)\s+[A-Z0-9])",
    "Q4 part only": r"(?:\bpart\s+\d+\s+of\s+\d+)",
}


def run(qid: str, q: dict) -> dict:
    gid = str(q.get("arxiv_id") or "")
    alt = gid.replace("-", "/")
    slug = re.sub(r"[^a-z0-9]+", "", str(q.get("paper") or "").lower())[:24]
    out = {}
    for t in ("a2", "b", "c"):
        p = RUN / f"track_{t}_{qid}.json"
        if not p.exists():
            continue
        r = json.loads(p.read_text(encoding="utf-8"))
        ans = str(r.get("answer") or "")
        nlow = re.sub(r"[^a-z0-9]+", "", ans.lower())
        grounded = bool(gid and (gid in ans or alt in ans)) or (slug in nlow)
        out[t] = {"ans": ans, "grounded": grounded,
                  "tools": r.get("tool_call_count"),
                  "err": r.get("error"), "is_error": r.get("is_error")}
    return out


def main() -> int:
    qs = json.loads((SUITE / "data" / "papers" / "qa_questions.json")
                    .read_text(encoding="utf-8"))["questions"]
    per_track_cells: dict[str, list[tuple[str, str, str]]] = {}
    for q in qs:
        qid = q.get("qid")
        cells = run(qid, q)
        for t, c in cells.items():
            per_track_cells.setdefault(t, []).append((qid, c["ans"], c["grounded"]))

    print(f"run: {RUN.name}\npaper target: {TARGET}\n")
    for name, pat in CANDIDATES.items():
        rx = re.compile(pat, re.I)
        counts = {}
        for t, cells in per_track_cells.items():
            n = sum(1 for _, a, _ in cells if rx.search(a))
            counts[t] = f"{n}/{len(cells)}"
        print(f"{name:<16} " + "  ".join(f"{t}={counts.get(t)}" for t in ("a2", "b", "c")))

    print("\n--- per-question winner (Q2) + markers seen ---")
    rx = re.compile(CANDIDATES["Q2 +dotted"], re.I)
    for t, cells in per_track_cells.items():
        print(f"\n[{t}]")
        for qid, a, grounded in sorted(cells):
            ms = sorted({m.group(0).strip() for m in rx.finditer(a)})
            print(f"  {qid} g={int(grounded)} n={len(ms)} {ms[:6]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
