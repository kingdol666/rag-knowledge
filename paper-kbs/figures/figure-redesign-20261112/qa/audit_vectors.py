# -*- coding: utf-8 -*-
"""Audit staged KBS figure candidates without touching canonical figures."""
from __future__ import annotations
import json, re
from pathlib import Path
import pymupdf

HERE = Path(__file__).resolve().parent.parent
V = HERE / "vectors"
FB = Path(r"D:/codes/ClaudeGPT/rag_project/rag-knowledge/review/experiment-redesign-20261101/artifacts/final_bench")
STATS = json.loads((FB / "s6_stats.json").read_text(encoding="utf-8"))
TRACES = json.loads((FB / "s4_traces_final.json").read_text(encoding="utf-8"))
rows = []
expected = [37,45,52,46,39,25,33,72]
keys = ["A0","A0f","A0h","PD","A1b","A2","A3","A1-readall"]
for k, e in zip(keys, expected):
    assert STATS["per_arm"][k]["gold_hits"] == e
    assert STATS["per_arm"][k]["n_gold"] == 72
    tr = [r for r in TRACES[k] if not r.get("is_refusal")]
    assert len(tr) == 72

for style in ("style1", "style2"):
    for name in ("figureA_design_overview", "figureB_ingest_to_evidence", "figureC_latest_results"):
        pdf = V / style / f"{name}.pdf"
        png = V / style / f"{name}.png"
        svg = V / style / f"{name}.svg"
        assert pdf.exists() and png.exists() and svg.exists()
        doc = pymupdf.open(pdf)
        assert len(doc) == 1
        page = doc[0]
        rect = page.rect
        text = page.get_text()
        images = page.get_images(full=True)
        drawings = page.get_drawings()
        fonts = page.get_fonts(full=True)
        # Final-size canvas is intentionally bounded to a full-width figure.
        assert 480 <= rect.width <= 530, (style, name, rect.width)
        assert rect.height > 180, (style, name, rect.height)
        assert not images, (style, name, "raster image object")
        assert len(drawings) > 20, (style, name, "too few vector drawings")
        assert text.strip(), (style, name, "no selectable text")
        assert "Arial" in repr(fonts) or "Liberation" in repr(fonts) or "Helvetica" in repr(fonts), (style, name, fonts)
        svg_text = svg.read_text(encoding="utf-8")
        assert "<text" in svg_text
        assert "<image" not in svg_text
        rows.append({
            "style": style, "figure": name,
            "pdf_width_pt": rect.width, "pdf_height_pt": rect.height,
            "drawings": len(drawings), "images": len(images),
            "fonts": [f[3] for f in fonts], "text_chars": len(text),
            "svg_text": svg_text.count("<text"),
        })

out = HERE / "qa" / "vector_audit.json"
out.write_text(json.dumps({"status":"PASS", "figures":rows}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"PASS: audited {len(rows)} candidates; no raster objects; selectable text and vector drawings present")
