"""Tighten the crop for the five pages whose auto-union also captured body text.

Coordinates come from the measured raster-image bbox / caption positions
(documented in the console diagnostics), not from guesswork.
"""
from __future__ import annotations

from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "paper-kbs" / "reference" / "kbs"
OUT = REF / "figures"

FIX = {
    "A_Coordinated_LLM_MultiAgent_QA_2025__p10_crop.png":
        ("A_Coordinated_LLM_MultiAgent_QA_2025.pdf", 10, (100, 115, 510, 260)),
    "B_InformationTheoretic_DualMemory_System_2025__p09_crop.png":
        ("B_InformationTheoretic_DualMemory_System_2025.pdf", 9, (0, 45, 612, 219)),
    "A_SoftwareRefArch_JournalisticKnowledgePlatforms_2023__p11_crop.png":
        ("A_SoftwareRefArch_JournalisticKnowledgePlatforms_2023.pdf", 11, (30, 430, 280, 592)),
    "A_SoftwareRefArch_JournalisticKnowledgePlatforms_2023__p07_crop.png":
        ("A_SoftwareRefArch_JournalisticKnowledgePlatforms_2023.pdf", 7, (355, 548, 510, 700)),
    "A_HELIOT_LLM_CDSS_2025__p07_crop.png":
        ("A_HELIOT_LLM_CDSS_2025.pdf", 7, (65, 65, 547, 360)),
}

for fn, (pdf, pno, box) in FIX.items():
    doc = pymupdf.open(str(REF / pdf))
    page = doc[pno - 1]
    clip = pymupdf.Rect(*box)
    page.get_pixmap(matrix=pymupdf.Matrix(3, 3), clip=clip,
                    alpha=False).save(str(OUT / fn))
    print(f"[refined] {fn} clip={box}")
    doc.close()
