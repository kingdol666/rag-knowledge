"""Audit figure artwork against Elsevier journal artwork requirements.

Read-only. Reports, per figure: natural size, vector-vs-raster content,
embedded font names, text size range, and the effective (post-scaling)
minimum text size when the figure is placed at the width used in the manuscript.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import fitz  # PyMuPDF

FIGS = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge\paper-kbs\tex\figs")
PDF = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge\paper-kbs\tex\main2.pdf")

# width factor applied by \includegraphics in the v2 chapter files
WIDTH_FACTOR = {
    "fig1_architecture": 1.0,
    "fig2_lanes": 1.0,
    "fig3_retrieval": 1.0,
    "fig4_inflation": 0.5,
    "fig5_e2e": 1.0,
    "fig6_margin_variants": 1.0,
    "fig7_ood": 0.62,
    "fig8_anatomy": 1.0,
    "fig9_robustness": 1.0,
}


def text_width_pt(pdf: Path) -> float:
    doc = fitz.open(pdf)
    best = 0.0
    for page in doc:
        for blk in page.get_text("dict")["blocks"]:
            if blk.get("type") != 0:
                continue
            x0 = min(s["bbox"][0] for l in blk["lines"] for s in l["spans"])
            x1 = max(s["bbox"][2] for l in blk["lines"] for s in l["spans"])
            best = max(best, x1 - x0)
    doc.close()
    return best


def audit(path: Path) -> dict:
    doc = fitz.open(path)
    page = doc[0]
    rect = page.rect
    raster = []
    for xref in range(1, doc.xref_length()):
        try:
            if doc.xref_is_image(xref):
                info = doc.extract_image(xref)
                raster.append((info.get("width"), info.get("height"), info.get("ext")))
        except Exception:  # noqa: BLE001
            pass
    drawings = len(page.get_drawings())
    sizes: list[float] = []
    fonts: set[str] = set()
    nchars = 0
    for blk in page.get_text("dict")["blocks"]:
        if blk.get("type") != 0:
            continue
        for line in blk["lines"]:
            for span in line["spans"]:
                sizes.append(round(span["size"], 2))
                fonts.add(span["font"])
                nchars += len(span["text"])
    doc.close()
    sizes.sort()
    return {
        "natural_pt": (round(rect.width, 1), round(rect.height, 1)),
        "natural_in": (round(rect.width / 72, 2), round(rect.height / 72, 2)),
        "raster_images": raster,
        "vector_ops": drawings,
        "text_chars": nchars,
        "text_size_min": sizes[0] if sizes else None,
        "text_size_med": sizes[len(sizes) // 2] if sizes else None,
        "text_size_max": sizes[-1] if sizes else None,
        "fonts": sorted(fonts),
    }


def main() -> int:
    tw = text_width_pt(PDF)
    print(f"manuscript textwidth measured from main2.pdf: {tw:.1f} pt = {tw/28.4527:.2f} cm\n")
    out = {}
    for name, factor in WIDTH_FACTOR.items():
        pdf = FIGS / f"{name}.pdf"
        if not pdf.exists():
            print(f"MISSING {pdf}")
            continue
        info = audit(pdf)
        info["width_factor"] = factor
        target_w = tw * factor
        info["placed_width_pt"] = round(target_w, 1)
        nat_w = info["natural_pt"][0]
        scale = target_w / nat_w
        info["scale"] = round(scale, 3)
        if info["text_size_min"]:
            info["effective_min_pt"] = round(info["text_size_min"] * scale, 2)
            info["effective_med_pt"] = round(info["text_size_med"] * scale, 2)
        out[name] = info
        raster = info["raster_images"]
        print(f"--- {name}")
        print(f"    natural {info['natural_in'][0]}x{info['natural_in'][1]} in   scale {scale:.3f}"
              f"   placed width {target_w/28.4527:.2f} cm")
        print(f"    text sizes pt: min {info['text_size_min']} med {info['text_size_med']}"
              f" max {info['text_size_max']}  ->  effective min {info.get('effective_min_pt')} pt"
              f"  (chars {info['text_chars']}, vector ops {info['vector_ops']})")
        print(f"    raster xobjects: {raster if raster else 'none (pure vector)'}")
        print(f"    fonts: {', '.join(info['fonts'])}")
    (FIGS.parent / "notes").mkdir(exist_ok=True)
    dump = FIGS.parent / "notes" / "artwork-audit.json"
    dump.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nwrote {dump}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
