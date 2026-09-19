#!/usr/bin/env python3
"""编译产物 main.pdf -> 逐页 PNG (page-1.png, ...) 供视检."""
import sys
from pathlib import Path
import fitz

TEX = Path(__file__).resolve().parent / "tex"
OUT = TEX / "pages"
OUT.mkdir(exist_ok=True)

def main() -> int:
    pdf = TEX / "main.pdf"
    doc = fitz.open(pdf)
    for old in OUT.glob("page-*.png"):
        old.unlink()
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=110)
        pix.save(OUT / f"page-{i+1}.png")
    print(f"[done] {len(doc)} pages -> {OUT}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
