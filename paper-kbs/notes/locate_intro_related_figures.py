"""Find figures that sit inside Introduction / Related Work sections of the KBS pack.

Method:
  1. page-level section detection from heading-like lines;
  2. caption pages from the already-built kbs_all_figure_index.json;
  3. a figure is "intro/related" when its page lies in
     [intro_page, first_method_page) or in the Related Work block.

Output: paper-kbs/notes/kbs_intro_related_figures.json
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "paper-kbs" / "reference" / "kbs"
IDX = json.loads((ROOT / "paper-kbs/notes/kbs_all_figure_index.json").read_text(encoding="utf-8"))
OUT = ROOT / "paper-kbs/notes/kbs_intro_related_figures.json"

HEAD_INTRO = re.compile(r"(?i)^\s*(?:1\.?\s*|I\.\s*)?introduction\b")
HEAD_REL = re.compile(
    r"(?i)^\s*(?:\d+(?:\.\d+)*\.?\s*)?"
    r"(related work|related works|background|state[- ]of[- ]the[- ]art|"
    r"literature review|related studies|prior work)\b")
HEAD_NEXT = re.compile(
    r"(?i)^\s*(?:\d+(?:\.\d+)*\.?\s*)?"
    r"(method|methods|methodology|proposed|system model|system design|"
    r"framework|architecture|preliminar|materials?|approach|model|"
    r"technique|design|implementation|evaluation|experiment|results|"
    r"study design|problem formulation|problem statement)\b")
CAPTION_FIG = re.compile(r"(?i)^\s*(?:fig(?:ure)?\.?\s*)(\d+)\s*[.:)\-]")

WANT = re.compile(
    r"compared to|comparison|overview|illustrat|example|scenario|"
    r"taxonom|classif|framework|architecture|challenge|issue|gap|"
    r"motivat|approach|process|workflow|structure|paradigm|static|dynamic", re.I)

results = []
for entry in IDX:
    name = entry["file"]
    pdf = REF / name
    if not pdf.exists():
        continue

    # --- page-level heading scan -------------------------------------------
    # using PyMuPDF here only to get text; no rendering
    import pymupdf
    doc = pymupdf.open(str(pdf))
    intro_page = rel_page = None
    next_page = None
    heading_log = []
    for i, page in enumerate(doc):
        pno = i + 1
        for line in page.get_text().splitlines():
            s = line.strip()
            if len(s) > 95 or len(s) < 4:
                continue
            if HEAD_INTRO.match(s) and intro_page is None:
                intro_page = pno
                heading_log.append({"page": pno, "kind": "intro", "text": s[:90]})
            elif HEAD_REL.match(s) and rel_page is None:
                rel_page = pno
                heading_log.append({"page": pno, "kind": "related", "text": s[:90]})
            elif HEAD_NEXT.match(s):
                if intro_page and pno > intro_page and (rel_page is None or pno > rel_page):
                    if next_page is None:
                        next_page = pno
                        heading_log.append({"page": pno, "kind": "next", "text": s[:90]})
    doc.close()

    # --- decide the intro/related window ----------------------------------
    start = intro_page or 1
    end = next_page or (rel_page + 3 if rel_page else min(6, entry["pages"]))
    if rel_page:
        end = max(end, rel_page + 2)

    figs = []
    for c in entry["captions"]:
        if start <= c["page"] < end:
            figs.append({
                "page": c["page"],
                "num": c["num"],
                "caption": c["caption"],
                "template_candidate": bool(WANT.search(c["caption"])),
            })

    results.append({
        "file": name,
        "pages": entry["pages"],
        "intro_page": intro_page,
        "related_page": rel_page,
        "next_page": next_page,
        "window": [start, end],
        "headings": heading_log,
        "intro_related_figures": figs,
    })
    print(f"{name[:54]:54s} intro={str(intro_page):>4s} rel={str(rel_page):>4s} "
          f"next={str(next_page):>4s} window={start}-{end-1} figs={len(figs)}")

OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
n = sum(len(r["intro_related_figures"]) for r in results)
print(f"\n[done] {n} intro/related figures -> {OUT}")
