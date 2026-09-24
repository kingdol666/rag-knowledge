#!/usr/bin/env python3
"""Map each part -> chapters present (illustration-heading form 'Chapter X.]')."""
import re
from pathlib import Path

PARTS = Path("D:/codes/ClaudeGPT/rag_project/rag-knowledge/benchmark-suite/data/novels/parts")
STORE = Path("D:/codes/ClaudeGPT/rag_project/rag-knowledge/storage/tree-file-system/Novel-PridePrejudice")

CH = re.compile(r"Chapter\s+([IVXL]+)\s*\.?\s*\]")


def roman_to_int(s):
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
    total = prev = 0
    for ch in reversed(s):
        v = vals[ch]
        if v < prev:
            total -= v
        else:
            total += v
            prev = v
    return total


def scan(fp):
    txt = fp.read_text(encoding="utf-8", errors="replace")
    hits = [(roman_to_int(m.group(1)), m.group(1)) for m in CH.finditer(txt)]
    return txt, hits


def key(p):
    m = re.search(r"part (\d+) of", p.name)
    return int(m.group(1)) if m else 0


files = sorted(PARTS.glob("pride_and_prejudice (part *.md"), key=key)
print("=== PART FILES ===")
for fp in files:
    txt, hits = scan(fp)
    nums = sorted({n for n, _ in hits})
    rng = f"{min(nums)}-{max(nums)}" if nums else "NONE"
    print(f"part {key(fp):>2}  chars={len(txt):>6}  chapters={len(hits):>2}  range={rng:<8} "
          f"list={[r for _, r in hits]}")

print("\n=== STORE FILES ===")
for fp in sorted(STORE.glob("pride_and_prejudice*.md")):
    txt, hits = scan(fp)
    nums = sorted({n for n, _ in hits})
    rng = f"{min(nums)}-{max(nums)}" if nums else "NONE"
    print(f"{fp.name:<55} chars={len(txt):>6} n={len(hits):>2} range={rng:<8} list={[r for _, r in hits]}")
