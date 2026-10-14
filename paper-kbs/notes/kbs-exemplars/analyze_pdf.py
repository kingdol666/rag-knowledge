"""Structural fingerprint of a paper PDF: pages, words, sections, floats, references.

Usage: python analyze_pdf.py <pdf> [<pdf> ...]
Prints one compact block per file so several papers can be compared side by side.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from pypdf import PdfReader

SEC_NUM = re.compile(r"^\s*(\d{1,2})(?:\.(\d{1,2}))?(?:\.(\d{1,2}))?\s+([A-Z][^\n]{2,70})$")
FIG = re.compile(r"^\s*(?:Fig\.?|Figure)\s*(\d{1,2})\s*[.:]")
TAB = re.compile(r"^\s*Table\s*(\d{1,2})\s*[.:]")
REF_ENTRY = re.compile(r"^\s*\[\d{1,3}\]")


def analyze(path: Path) -> None:
    reader = PdfReader(str(path))
    pages = len(reader.pages)
    page_text: list[str] = []
    for p in reader.pages:
        try:
            page_text.append(p.extract_text() or "")
        except Exception:
            page_text.append("")
    full = "\n".join(page_text)
    lines = [ln.rstrip() for ln in full.splitlines()]

    words = len(re.findall(r"\b[\w'-]+\b", full))

    sections: list[str] = []
    for ln in lines:
        m = SEC_NUM.match(ln.strip())
        if m and len(m.group(4).split()) <= 9:
            sections.append(ln.strip())
    # keep first occurrence, drop obvious table/figure numbering noise
    seen: set[str] = set()
    secs: list[str] = []
    for s in sections:
        key = re.sub(r"\s+", " ", s).lower()
        if key in seen:
            continue
        seen.add(key)
        secs.append(re.sub(r"\s+", " ", s))

    figs = sorted({int(m.group(1)) for ln in lines if (m := FIG.match(ln))})
    tabs = sorted({int(m.group(1)) for ln in lines if (m := TAB.match(ln))})

    # references: last occurrence of a 'References' heading, then count [n] entries
    ref_idx = None
    for i, ln in enumerate(lines):
        if re.match(r"^\s*References\s*$", ln.strip(), re.I):
            ref_idx = i
    refs = 0
    if ref_idx is not None:
        refs = sum(1 for ln in lines[ref_idx:] if REF_ENTRY.match(ln))
    if refs == 0:
        refs = len({int(m.group(1)) for ln in lines if (m := REF_ENTRY.match(ln))})

    # first page head (title + author block)
    head = " | ".join(x.strip() for x in page_text[0].splitlines()[:6] if x.strip())

    print(f"== {path.name}")
    print(f"   pages           : {pages}")
    print(f"   words (extracted): {words}  (~{words // max(pages,1)}/page)")
    print(f"   sections found  : {len(secs)}")
    for s in secs[:28]:
        print(f"        {s}")
    print(f"   figures         : {len(figs)} {figs}")
    print(f"   tables          : {len(tabs)} {tabs}")
    print(f"   reference entries: {refs}")
    print(f"   first page head : {head[:220]}")
    print()


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        analyze(Path(arg))
