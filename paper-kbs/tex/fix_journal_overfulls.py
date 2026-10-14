"""Iteratively widen over-wide floats in the generated journal variant.

Compiles paper-kbs/tex/journal/main2.tex, reads Overfull \\hbox reports that come
from tabular boxes, locates the enclosing float in the journal sources, switches
\\begin{table} -> \\begin{table*} (or figure -> figure*), and repeats.
Operates only on the generated copies under tex/journal/.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

TEXBIN = Path(r"C:\texlive\2025\bin\windows")
JOURNAL = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge\paper-kbs\tex\journal")
LOG = JOURNAL / "main2.log"
MAX_ROUNDS = 5

FLOAT_RE = re.compile(
    r"\\begin\{(table|figure)\}(\*?)(\[[^\]]*\])?", re.M
)
OVERFULL_RE = re.compile(r"Overfull \\hbox \(([0-9.]+)pt too wide\) in paragraph at lines (\d+)--(\d+)")


def float_blocks(path: Path) -> list[dict[str, object]]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    out: list[dict[str, object]] = []
    open_at: dict[str, int] = {}
    open_kind = ""
    for i, ln in enumerate(lines, start=1):
        m = FLOAT_RE.search(ln)
        if m and not open_at:
            open_at = {"start": i, "col": ln.index("\\begin")}
            open_kind = m.group(1)
            starred = m.group(2) == "*"
        if f"\\end{{{open_kind}}}" in ln and open_at:
            out.append(
                {
                    "kind": open_kind,
                    "start": open_at["start"],
                    "end": i,
                    "starred": starred,
                }
            )
            open_at = {}
    return out


def compile_once() -> str:
    for f in ("main2.aux",):
        pass
    subprocess.run(
        [str(TEXBIN / "pdflatex.exe"), "-interaction=nonstopmode", "main2.tex"],
        cwd=JOURNAL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    raw = LOG.read_bytes()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16", errors="replace")
    return raw.decode("utf-8", errors="replace")


def widen(path: Path, block: dict[str, object]) -> bool:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    kind = block["kind"]
    s, e = int(block["start"]), int(block["end"])
    if block["starred"]:
        return False
    lines[s - 1] = lines[s - 1].replace(f"\\begin{{{kind}}}", f"\\begin{{{kind}*}}", 1)
    lines[e - 1] = lines[e - 1].replace(f"\\end{{{kind}}}", f"\\end{{{kind}*}}", 1)
    path.write_text("".join(lines), encoding="utf-8")
    return True


def main() -> int:
    files = sorted(JOURNAL.glob("*.tex"))
    for rnd in range(1, MAX_ROUNDS + 1):
        log = compile_once()
        hits = [
            (float(m.group(1)), int(m.group(2)), int(m.group(3)))
            for m in OVERFULL_RE.finditer(log)
        ]
        if not hits:
            print(f"round {rnd}: no overfull tabular boxes remain")
            return 0
        candidates: list[tuple[Path, dict[str, object], float, int, int]] = []
        for path in files:
            for blk in float_blocks(path):
                for width, a, b in hits:
                    if int(blk["start"]) - 3 <= a and b <= int(blk["end"]) + 3:
                        candidates.append((path, blk, width, a, b))
        changed = 0
        seen: set[tuple[str, int]] = set()
        for path, blk, width, a, b in sorted(candidates, key=lambda t: -t[2]):
            key = (path.name, int(blk["start"]))
            if key in seen:
                continue
            seen.add(key)
            if widen(path, blk):
                changed += 1
                print(f"  round {rnd}: widest the {blk['kind']} at {path.name}:{blk['start']} "
                      f"({width:.1f}pt overfull, lines {a}--{b})")
        if not changed:
            print(f"round {rnd}: {len(hits)} overfull box(es) could not be attributed to a float:")
            for width, a, b in hits:
                print(f"    {width:.1f}pt at lines {a}--{b}")
            return 1
    print("round limit reached")
    return 1


if __name__ == "__main__":
    sys.exit(main())
