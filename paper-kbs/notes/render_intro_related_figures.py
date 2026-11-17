"""Render the curated Introduction / Related Work figures.

Output naming deliberately differs from the previous methodology-figure pass:
  <slug>__pNN_intro.png        full page  (144 dpi)
  <slug>__pNN_intro_crop.png   figure crop (216 dpi)

Crop logic: prefer the largest raster-image bbox; otherwise union vector
drawings. Always stop at the first figure-caption block so body text is not
included.
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

SELECTED = {
    "B_FinBloom_KnowledgeGrounding_RealtimeData_2026.pdf": [3, 4],
    "A_FineGrained_StatefulKnowledgeExploration_2025.pdf": [3, 4],
    "A_Building_KnowledgeGrounded_Dialogue_2024.pdf": [2, 3],
    "B_LGMT_ReasoningReliability_Testing_2026.pdf": [3, 4],
    "B_PrivateLibrary_CodeGeneration_LLM_2025.pdf": [3],
    "B_XAI_MetaSurvey_2023.pdf": [2, 6],
    "B_Survey_LLM_KnowledgeBasedMethods_2025.pdf": [2, 3],
    "B_LLM_Understand_KnowledgeGraphs_2025.pdf": [2],
    "A_MSDiagnosis_Benchmark_Framework_MultiStepClinical_2025.pdf": [1],
    "A_LLM_IR_System_BankSupervisors_2024.pdf": [4],
    "B_QueryExpansion_SemanticRelations_RetrievalSystems_2023.pdf": [2, 3],
    "B_RAG_EngineeringDesignKnowledge_2024.pdf": [2],
    "A_SoftwareRefArch_JournalisticKnowledgePlatforms_2023.pdf": [3],
}

CAP = re.compile(r"(?i)^\s*(?:fig(?:ure)?\.?\s*)\d+\s*[.:)\-]")
report = []

for name, pages in SELECTED.items():
    pdf = REF / name
    if not pdf.exists():
        print("[missing]", name)
        continue
    doc = pymupdf.open(str(pdf))
    slug = name.replace(".pdf", "")
    for pno in pages:
        if pno > len(doc):
            continue
        page = doc[pno - 1]
        full_fn = f"{slug}__p{pno:02d}_intro.png"
        page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False).save(str(OUT / full_fn))

        cap_y = None
        for b in page.get_text("blocks"):
            first = b[4].strip().splitlines()[0] if b[4].strip() else ""
            if CAP.match(first):
                cap_y = b[1] if cap_y is None else min(cap_y, b[1])

        imgs = [pymupdf.Rect(i["bbox"]) for i in page.get_image_info() if i.get("bbox")]
        big = max(imgs, key=lambda r: r.get_area()) if imgs else None
        boxes = [r for r in imgs if r.get_area() > 1500]
        for dr in page.get_drawings():
            r = dr.get("rect")
            if r and r.width > 4 and r.height > 4:
                boxes.append(pymupdf.Rect(r))

        if big and big.get_area() > 3000:
            chosen = big
        elif boxes:
            chosen = boxes[0]
            for b in boxes[1:]:
                chosen |= b
        else:
            chosen = None

        crop_fn = None
        if chosen is not None:
            pad = 9
            clip = pymupdf.Rect(max(0, chosen.x0 - pad), max(0, chosen.y0 - pad),
                                min(page.rect.width, chosen.x1 + pad),
                                min(page.rect.height, chosen.y1 + pad))
            if cap_y is not None:
                clip.y1 = min(clip.y1, cap_y - 3)
            if clip.width > 70 and clip.height > 70:
                crop_fn = f"{slug}__p{pno:02d}_intro_crop.png"
                page.get_pixmap(matrix=pymupdf.Matrix(3, 3), clip=clip,
                                alpha=False).save(str(OUT / crop_fn))
        report.append({"file": name, "page": pno, "full": full_fn,
                       "crop": crop_fn, "caption_y": cap_y})
        print(f"[ok] {slug[:50]:50s} p{pno:02d} cap_y="
              f"{('%.0f' % cap_y) if cap_y else 'NA':>4s} crop={'Y' if crop_fn else 'N'}")
    doc.close()

(ROOT / "paper-kbs/notes/kbs_intro_related_render.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"\n[done] {len(report)} pages rendered")
