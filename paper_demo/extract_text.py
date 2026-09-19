#!/usr/bin/env python3
"""提取范文 PDF 文本 -> reference/*.txt, 供风格研读."""
from pathlib import Path
import sys

REF = Path(__file__).resolve().parent / "reference"

def main() -> int:
    pdfs = sorted(REF.glob("*.pdf"))
    if not pdfs:
        print("no pdfs"); return 1
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("fitz missing"); return 1
    for p in pdfs:
        doc = fitz.open(p)
        parts = [f"=== {p.name} | pages={len(doc)} ==="]
        for i, page in enumerate(doc):
            parts.append(f"\n----- page {i+1} -----\n" + page.get_text("text"))
        out = p.with_suffix(".txt")
        out.write_text("".join(parts), encoding="utf-8")
        print(f"[txt] {out.name} ({len(doc)}p)")
        doc.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())
