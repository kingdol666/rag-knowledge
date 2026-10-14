"""Report box size, text-size range, fonts and raster content of figure PDFs."""
from __future__ import annotations

import sys
from pathlib import Path

import pymupdf


def probe(p: str) -> None:
    d = pymupdf.open(p)
    pg = d[0]
    r = pg.rect
    sizes: list[float] = []
    fonts: set[str] = set()
    for b in pg.get_text("dict")["blocks"]:
        if b.get("type") != 0:
            continue
        for line in b["lines"]:
            for s in line["spans"]:
                sizes.append(round(s["size"], 2))
                fonts.add(s["font"])
    rast = 0
    for x in range(1, d.xref_length()):
        try:
            if d.xref_is_image(x):
                rast += 1
        except Exception:  # noqa: BLE001
            pass
    sizes.sort()
    print(f"{Path(p).name:<44} box {r.width:7.1f} x {r.height:6.1f} pt"
          f"  ({r.width / 72:.2f} x {r.height / 72:.2f} in)")
    if sizes:
        print(f"    text min {sizes[0]:6.2f}  med {sizes[len(sizes) // 2]:6.2f}"
              f"  max {sizes[-1]:6.2f}  spans {len(sizes)}")
        scale = 501.12 / r.width
        print(f"    placed at 501.1pt wide -> scale {scale:.3f}"
              f"  effective min {sizes[0] * scale:.2f} pt")
    print(f"    fonts: {sorted(fonts)}")
    print(f"    raster xobjects: {rast}")
    d.close()


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        probe(arg)
        print()
