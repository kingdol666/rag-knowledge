#!/usr/bin/env python3
"""TEMP probe 2: split the citation marker families to see which definition
reproduces the paper's 9/6/1. Read-only."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
RUN = SUITE / "results" / "runs" / "run-20260930T150453Z-3ec2174"

PART = r"\bpart\s+\d+\s+of\s+\d+"
CHUNK = r"\bchunk[_ ]?(?:index|id)?\s*\d+"
STRUCT = (r"(?:\bsections?\s+[0-9]+(?:\.[0-9]+)*|\btables?\s+[0-9]+"
          r"|\bfigures?\s+[0-9]+|§\s*\d+(?:\.[0-9]+)*|\bappendi(?:x|ces)\s+[A-Z0-9])")

FAMILIES = {
    "part": PART, "chunk": CHUNK, "struct": STRUCT,
    "part+struct": f"(?:{PART}|{STRUCT})",
    "part+chunk": f"(?:{PART}|{CHUNK})",
    "all": f"(?:{PART}|{CHUNK}|{STRUCT})",
}


def main() -> int:
    qs = json.loads((SUITE / "data" / "papers" / "qa_questions.json")
                    .read_text(encoding="utf-8"))["questions"]
    data: dict[str, dict[str, str]] = {}
    for q in qs:
        for t in ("a2", "b", "c"):
            p = RUN / f"track_{t}_{q['qid']}.json"
            if p.exists():
                data.setdefault(t, {})[q["qid"]] = str(
                    json.loads(p.read_text(encoding="utf-8")).get("answer") or "")

    print(f"{'definition':<16} " + "  ".join(f"{t:>8}" for t in ("a2", "b", "c"))
          + "   paper: a2=9 b=6 c=1")
    for name, pat in FAMILIES.items():
        rx = re.compile(pat, re.I)
        cells = []
        for t in ("a2", "b", "c"):
            n = sum(1 for a in data[t].values() if rx.search(a))
            cells.append(f"{n}/{len(data[t])}")
        print(f"{name:<16} " + "  ".join(f"{c:>8}" for c in cells))

    print("\nper-question family hits (a2 / b / c):")
    rxs = {k: re.compile(v, re.I) for k, v in FAMILIES.items()}
    for q in qs:
        qid = q["qid"]
        line = [qid]
        for t in ("a2", "b", "c"):
            a = data[t].get(qid, "")
            fams = "+".join(k for k in ("part", "chunk", "struct") if rxs[k].search(a))
            line.append(f"{t}:{fams or '-'}")
        print("  " + "  ".join(line))
    return 0


if __name__ == "__main__":
    sys.exit(main())
