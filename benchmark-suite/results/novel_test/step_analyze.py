#!/usr/bin/env python3
"""Map chapters -> parts, and summarise the retrieval trace."""
from __future__ import annotations
import json, re, sys
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent.parent
OUT = Path(__file__).resolve().parent
PARTS = SUITE / "data" / "novels" / "parts"

CH = re.compile(r"(?im)^chapter\s+([IVXL]+)\.?\]?\s*$")
ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def rn(s):
    v = 0
    for i, c in enumerate(s):
        if i + 1 < len(s) and ROMAN[c] < ROMAN[s[i + 1]]:
            v -= ROMAN[c]
        else:
            v += ROMAN[c]
    return v


def part_num(name):
    m = re.search(r"part (\d+) of", name)
    return int(m.group(1)) if m else 0


mapping = {}
for f in sorted(PARTS.glob("*.md"), key=lambda p: part_num(p.name)):
    nums = [rn(x) for x in CH.findall(f.read_text(encoding="utf-8"))]
    mapping[f"part {part_num(f.name)}"] = nums
print("chapter -> part map:")
for k, v in mapping.items():
    print(f"  {k}: {v}")

trace = json.loads((OUT / "retrieval_trace.json").read_text(encoding="utf-8"))
print("\n=== Phase 1b sub-query top-5 hits ===")
for name, hits in trace["phases"]["phase1b_subqueries"].items():
    print(f"\n[{name}]")
    for h in hits:
        print(f"  {h['score']:.4f} {str(h['doc_path']).split('/')[-1]} "
              f"c{h['chunk_index']} :: {h['content'][:110]!r}")

print("\n=== candidate docs (dedup) ===")
for c in trace["candidates"]:
    print(f"  {c['score']:.4f} {str(c['doc_path']).split('/')[-1]}")
