"""Build a complete figure index for all 29 KBS reference PDFs.

For every PDF we record:
  - every figure-caption line and the page it appears on,
  - how many raster images / vector drawings each page actually contains
    (a caption without any image content means the PDF lost its figures).

Output: paper-kbs/notes/kbs_all_figure_index.json
No rendering happens here; rendering is done by render_selected_kbs_figures.py.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "paper-kbs" / "reference" / "kbs"
OUT = ROOT / "paper-kbs" / "notes" / "kbs_all_figure_index.json"

CAPLINE = re.compile(r"^\s*(?:Figure|Fig)\.?\s*(\d+)\s*[.:)\-]", re.I)
WANT = re.compile(
    r"architect|framework|overview|workflow|pipeline|system|methodolog|"
    r"flow|schematic|process|diagram|structure|pipeline|schema|module|"
    r"comparison of|illustrat", re.I)

index = []
for pdf in sorted(REF.glob("*.pdf")):
    doc = pymupdf.open(str(pdf))
    pages = []
    captions = []
    for i, page in enumerate(doc):
        text = page.get_text()
        n_img = len(page.get_image_info())
        n_draw = len(page.get_drawings())
        lines = [ln.strip() for ln in text.splitlines()]
        for ln in lines:
            m = CAPLINE.match(ln)
            if m and len(ln) > 20:
                captions.append({"page": i + 1, "num": int(m.group(1)),
                                 "caption": ln[:230],
                                 "want": bool(WANT.search(ln))})
        pages.append({"page": i + 1, "images": n_img, "drawings": n_draw,
                      "textlen": len(text)})
    rich = [p for p in pages if p["images"] > 0 or p["drawings"] > 20]
    index.append({
        "file": pdf.name,
        "pages": len(doc),
        "bytes": pdf.stat().st_size,
        "has_graphics": bool(rich),
        "graphic_pages": [p["page"] for p in rich],
        "n_captions": len(captions),
        "captions": captions,
        "page_stats": pages,
    })
    wanted = sum(1 for c in captions if c["want"])
    print(f"{pdf.name[:58]:58s} pages={len(doc):3d} "
          f"graphics={'Y' if rich else 'N':1s} caps={len(captions):3d} "
          f"arch/flow-caps={wanted:2d}")
    doc.close()

OUT.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"\n[done] {len(index)} PDFs -> {OUT}")
