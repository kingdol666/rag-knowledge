"""Render the curated architecture / workflow figure pages from the KBS pack.

For each (PDF, page) pair we write two files into reference/kbs/figures/:
  <slug>__pNN.png        full page at 144 dpi (shows the two-column layout)
  <slug>__pNN_crop.png   tight crop around the graphical content (shows the drawing)

The crop is the union of all raster-image and vector-drawing bounding boxes on
that page, padded slightly; if a page has no detectable graphics we skip the
crop and report it.
"""
from __future__ import annotations

import json
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "paper-kbs" / "reference" / "kbs"
OUT = REF / "figures"
OUT.mkdir(parents=True, exist_ok=True)

SELECTED = {
    "A_SoftwareRefArch_JournalisticKnowledgePlatforms_2023.pdf": [3, 7, 8, 11],
    "A_COMPANION_Developing_SoftwareRefArch_JKP_CEUR2021.pdf": [4, 6],
    "A_Automating_EngineeringModeling_LLM_Agents_2026.pdf": [6, 9, 12, 21],
    "A_HELIOT_LLM_CDSS_2025.pdf": [6, 7],
    "A_GOFAI_Meets_GenerativeAI_ExpertSystems_2026.pdf": [9],
    "A_Coordinated_LLM_MultiAgent_QA_2025.pdf": [10],
    "A_FineGrained_StatefulKnowledgeExploration_2025.pdf": [4],
    "A_LLM_IR_System_BankSupervisors_2024.pdf": [16],
    "A_KG_Orchestra_OpenSource_MultiAgent_Framework_2026.pdf": [31],
    "B_KnowledgeRetrieval_InContextLearning_SemanticSearch_2025.pdf": [4, 5],
    "B_FinBloom_KnowledgeGrounding_RealtimeData_2026.pdf": [6, 19],
    "B_LGMT_ReasoningReliability_Testing_2026.pdf": [5],
    "B_PrivateLibrary_CodeGeneration_LLM_2025.pdf": [5],
    "B_QueryExpansion_SemanticRelations_RetrievalSystems_2023.pdf": [10],
    "B_RAG_EngineeringDesignKnowledge_2024.pdf": [2, 9],
    "B_InformationTheoretic_DualMemory_System_2025.pdf": [9],
    "B_Survey_LLM_KnowledgeBasedMethods_2025.pdf": [2],
}

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
        full_fn = f"{slug}__p{pno:02d}.png"
        pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
        pix.save(str(OUT / full_fn))

        # union of graphical bounding boxes
        boxes = []
        for im in page.get_image_info():
            b = im.get("bbox")
            if b:
                boxes.append(pymupdf.Rect(b))
        for dr in page.get_drawings():
            r = dr.get("rect")
            if r and r.width > 3 and r.height > 3:
                boxes.append(pymupdf.Rect(r))
        crop_fn = None
        if boxes:
            u = boxes[0]
            for b in boxes[1:]:
                u |= b
            pad = 8
            clip = pymupdf.Rect(max(0, u.x0 - pad), max(0, u.y0 - pad),
                                min(page.rect.width, u.x1 + pad),
                                min(page.rect.height, u.y1 + pad))
            if clip.width > 60 and clip.height > 60:
                crop_fn = f"{slug}__p{pno:02d}_crop.png"
                page.get_pixmap(matrix=pymupdf.Matrix(3, 3), clip=clip,
                                alpha=False).save(str(OUT / crop_fn))
        report.append({"file": name, "page": pno, "full": full_fn,
                       "crop": crop_fn, "n_graphics": len(boxes)})
        print(f"[ok] {slug[:52]:52s} p{pno:02d} graphics={len(boxes):4d} "
              f"crop={'Y' if crop_fn else 'N'}")
    doc.close()

(ROOT / "paper-kbs" / "notes" / "kbs_selected_figures.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"\n[done] {len(report)} pages -> {OUT}")
