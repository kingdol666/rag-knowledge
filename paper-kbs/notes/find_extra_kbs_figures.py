"""Find figure-caption pages missed by the first keyword-ranked scan.

Prints every caption line of the requested PDFs and renders pages whose caption
mentions an architecture / framework / overview / workflow / pipeline / system.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "paper-kbs" / "reference" / "kbs"
OUT = REF / "figures"
OUT.mkdir(parents=True, exist_ok=True)

TARGETS = [
    "A_LLM_IR_System_BankSupervisors_2024.pdf",
    "A_KG_Orchestra_OpenSource_MultiAgent_Framework_2026.pdf",
    "B_InformationTheoretic_DualMemory_System_2025.pdf",
    "B_RAG_EngineeringDesignKnowledge_2024.pdf",
]
CAPLINE = re.compile(r"^\s*(?:Figure|Fig)\.?\s*\d+[.:)]", re.I)
WANT = re.compile(r"architect|framework|overview|workflow|pipeline|system|"
                  r"methodolog|flow|schematic|process|diagram|structure", re.I)

all_caps = {}
for name in TARGETS:
    doc = pymupdf.open(str(REF / name))
    caps = []
    for i, page in enumerate(doc):
        for line in page.get_text().splitlines():
            if CAPLINE.match(line) and len(line.strip()) > 18:
                caps.append({"page": i + 1, "caption": line.strip()[:190]})
    all_caps[name] = caps
    print(f"\n### {name[:64]}")
    for c in caps:
        flag = " <== RENDER" if WANT.search(c["caption"]) else ""
        print(f"  p{c['page']:02d} {c['caption'][:130]}{flag}")
    # render up to 3 extra pages with architecture-ish captions, skipping
    # pages already rendered in the first pass
    already = {int(m.group(1)) for f in OUT.glob(name.replace(".pdf", "") + "__p*.png")
               if (m := re.search(r"__p(\d+)\.png$", f.name))}
    pick = [c for c in caps if WANT.search(c["caption"]) and c["page"] not in already][:3]
    for c in pick:
        pix = doc[c["page"] - 1].get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
        fn = f"{name.replace('.pdf','')}__p{c['page']:02d}.png"
        pix.save(str(OUT / fn))
        print(f"    [rendered] {fn}")
    doc.close()

(ROOT / "paper-kbs" / "notes" / "kbs_all_figure_captions.json").write_text(
    json.dumps(all_caps, ensure_ascii=False, indent=1), encoding="utf-8")
print("\n[done] captions -> paper-kbs/notes/kbs_all_figure_captions.json")
