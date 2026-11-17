"""Locate and render architecture / workflow figure pages from the KBS PDF pack.

Uses PyMuPDF (only available in D:/anaconda3/python.exe on this machine).
Two outputs:
  kbs_figure_candidates.json  : per-page caption hits (evidence of where figures are)
  paper-kbs/reference/kbs/figures/*.png : rendered candidate pages at 144 dpi

No figure interpretation is done here; the PNGs are visually inspected afterwards.
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

# Papers closest to a RAG / knowledge-management SYSTEM (architecture + flow first).
TARGETS = [
    "A_SoftwareRefArch_JournalisticKnowledgePlatforms_2023.pdf",
    "B_RAG_EngineeringDesignKnowledge_2024.pdf",
    "B_KnowledgeRetrieval_InContextLearning_SemanticSearch_2025.pdf",
    "A_LLM_IR_System_BankSupervisors_2024.pdf",
    "A_KG_Orchestra_OpenSource_MultiAgent_Framework_2026.pdf",
    "A_FineGrained_StatefulKnowledgeExploration_2025.pdf",
    "B_InformationTheoretic_DualMemory_System_2025.pdf",
    "B_Survey_LLM_KnowledgeBasedMethods_2025.pdf",
    "A_Coordinated_LLM_MultiAgent_QA_2025.pdf",
    "A_GOFAI_Meets_GenerativeAI_ExpertSystems_2026.pdf",
]

CAP = re.compile(r"\b(?:Fig|Figure)\.?\s*(\d+)\b", re.I)
KEYS = re.compile(
    r"\b(architecture|framework|workflow|pipeline|overview|system design|"
    r"proposed (?:method|system|model)|schematic|flowchart|process)\b", re.I)

results = []
for name in TARGETS:
    p = REF / name
    if not p.exists():
        print("[missing]", name)
        continue
    doc = pymupdf.open(str(p))
    hits = []
    for i, page in enumerate(doc):
        text = page.get_text()
        caps = [m.group(0) for m in CAP.finditer(text)]
        keys = sorted({m.group(0).lower() for m in KEYS.finditer(text)})
        # a caption line is stronger evidence than a bare keyword
        score = 3 * len(caps) + len(keys)
        if caps or (keys and score >= 2):
            # keep the caption sentence for human checking
            cap_line = ""
            for line in text.splitlines():
                if CAP.search(line):
                    cap_line = line.strip()[:180]
                    break
            hits.append({"page": i + 1, "captions": caps[:6], "keywords": keys[:8],
                         "score": score, "caption_line": cap_line})
    hits.sort(key=lambda h: -h["score"])
    # render at most 4 candidate pages per paper, but keep the full hit list
    chosen = hits[:4]
    for h in chosen:
        page = doc[h["page"] - 1]
        pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
        slug = name.replace(".pdf", "")
        fn = f"{slug}__p{h['page']:02d}.png"
        pix.save(str(OUT / fn))
        h["png"] = fn
    results.append({"file": name, "pages": len(doc), "hits": hits,
                    "rendered": [h["png"] for h in chosen]})
    print(f"[scan] {name[:62]:62s} pages={len(doc):3d} hits={len(hits):3d} "
          f"rendered={len(chosen)}")
    doc.close()

(ROOT / "paper-kbs" / "notes" / "kbs_figure_candidates.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"\n[done] {sum(len(r['rendered']) for r in results)} PNGs -> {OUT}")
