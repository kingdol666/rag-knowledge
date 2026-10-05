#!/usr/bin/env python3
"""Map each part file -> chapter headings present + char counts."""
import re
from pathlib import Path

PARTS = Path("D:/codes/ClaudeGPT/rag_project/rag-knowledge/benchmark-suite/data/novels/parts")
STORE = Path("D:/codes/ClaudeGPT/rag_project/rag-knowledge/storage/tree-file-system/Novel-PridePrejudice")

ROMAN = re.compile(r"^\s*Chapter\s+([IVXL]+)\s*\.?\s*$", re.M)
# also inline heading forms
ROMAN_ANY = re.compile(r"Chapter\s+([IVXL]+)")


def roman_to_int(s: str) -> int:
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
    total = 0
    prev = 0
    for ch in reversed(s):
        v = vals[ch]
        if v < prev:
            total -= v
        else:
            total += v
            prev = v
    return total


def int_to_roman(n: int) -> str:
    table = [(100, "C"), (90, "XC"), (50, "L"), (40, "XL"), (10, "X"),
             (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    out = []
    for v, s in table:
        while n >= v:
            out.append(s)
            n -= v
    return "".join(out)


def scan(fp: Path) -> dict:
    txt = fp.read_text(encoding="utf-8", errors="replace")
    lines = txt.splitlines()
    # headings that are standalone lines
    standalone = []
    for i, ln in enumerate(lines):
        m = ROMAN.match(ln)
        if m:
            standalone.append((i, m.group(1), roman_to_int(m.group(1))))
    inline = [(i, m.group(1), roman_to_int(m.group(1)))
              for i, ln in enumerate(lines) for m in [ROMAN_ANY.search(ln)] if m]
    return {"path": str(fp), "chars": len(txt), "lines": len(lines),
            "standalone": standalone, "inline": inline, "text": txt}


def main():
    files = sorted(PARTS.glob("pride_and_prejudice (part *.md"))
    # natural sort by part number
    def key(p):
        m = re.search(r"part (\d+) of", p.name)
        return int(m.group(1)) if m else 0
    files = sorted(files, key=key)
    print(f"{'part':>4} {'chars':>7} {'#std':>4}  chapter headings (standalone, line#)")
    for fp in files:
        d = scan(fp)
        std = d["standalone"]
        nums = [n for _, _, n in std]
        rng = f"{min(nums)}-{max(nums)}" if nums else "NONE"
        heads = ", ".join(f"{r}@{i}" for i, r, _ in std[:8])
        print(f"{key(fp):>4} {d['chars']:>7} {len(std):>4}  {rng:<9} {heads}{' ...' if len(std) > 8 else ''}")
    # also list store files
    print("\n=== STORE FILES ===")
    sf = sorted(STORE.glob("pride_and_prejudice*.md"))
    for fp in sf:
        d = scan(fp)
        nums = [n for _, _, n in d["standalone"]]
        rng = f"{min(nums)}-{max(nums)}" if nums else "NONE"
        print(f"{fp.name:<60} chars={d['chars']:>7} std={len(d['standalone']):>3} range={rng}")


if __name__ == "__main__":
    main()
