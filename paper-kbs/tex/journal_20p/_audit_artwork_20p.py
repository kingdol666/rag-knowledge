"""Audit the journal_20p artwork against Elsevier/KBS artwork requirements.

Read-only. Derives each figure's ACTUAL scale from the LaTeX log of the real
build (native PDF box vs requested box), then reports the effective
post-scaling minimum text size, raster content, fonts and colour usage.

Elsevier minimum finished text size is 7 pt (6 pt for sub/superscripts).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import fitz  # PyMuPDF

HERE = Path(__file__).resolve().parent
LOG = HERE / "qdcvr_kbs.log"
FIGS = HERE / "figs"

NATIVE_RE = re.compile(
    r"<(figs/[A-Za-z0-9_]+\.pdf),\s*id=\d+,\s*([\d.]+)pt x ([\d.]+)pt>"
)
REQ_RE = re.compile(
    r"<use (figs/[A-Za-z0-9_]+\.pdf)>\s*\nPackage pdftex\.def Info:.*?\n"
    r"(?:.*?\n)*?\(pdftex\.def\)\s+Requested size:\s*([\d.]+)pt x ([\d.]+)pt",
    re.M,
)


def parse_log() -> dict[str, dict[str, float]]:
    text = LOG.read_text(encoding="utf-8", errors="replace")
    native: dict[str, tuple[float, float]] = {}
    for m in NATIVE_RE.finditer(text):
        native[m.group(1)] = (float(m.group(2)), float(m.group(3)))
    req: dict[str, tuple[float, float]] = {}
    for m in REQ_RE.finditer(text):
        req[m.group(1)] = (float(m.group(2)), float(m.group(3)))
    out = {}
    for key, (nw, nh) in native.items():
        if key not in req:
            continue
        rw, rh = req[key]
        out[Path(key).stem] = {
            "native_w": nw,
            "native_h": nh,
            "req_w": rw,
            "req_h": rh,
            "scale": rw / nw,
        }
    return out


def audit_pdf(path: Path) -> dict:
    doc = fitz.open(path)
    page = doc[0]
    raster = []
    for xref in range(1, doc.xref_length()):
        try:
            if doc.xref_is_image(xref):
                info = doc.extract_image(xref)
                raster.append((info.get("width"), info.get("height"), info.get("ext")))
        except Exception:  # noqa: BLE001
            pass
    sizes: list[float] = []
    fonts: set[str] = set()
    colors: set[int] = set()
    for blk in page.get_text("dict")["blocks"]:
        if blk.get("type") != 0:
            continue
        for line in blk["lines"]:
            for span in line["spans"]:
                sizes.append(round(span["size"], 2))
                fonts.add(span["font"])
                colors.add(span["color"])
    rect = page.rect
    doc.close()
    sizes.sort()
    return {
        "box": (round(rect.width, 1), round(rect.height, 1)),
        "raster": raster,
        "n_text": len(sizes),
        "min": sizes[0] if sizes else None,
        "med": sizes[len(sizes) // 2] if sizes else None,
        "max": sizes[-1] if sizes else None,
        "fonts": sorted(fonts),
        "colors": sorted(colors),
    }


def main() -> int:
    scales = parse_log()
    if not scales:
        print("no figure inclusions found in", LOG)
        return 1
    print(f"build log: {LOG.name}")
    print(f"{'figure':<22}{'scale':>7}{'nat_min':>9}{'eff_min':>9}"
          f"{'eff_med':>9}{'raster':>8}  status")
    worst = 99.0
    bad: list[str] = []
    for name in sorted(scales):
        pdf = FIGS / f"{name}.pdf"
        if not pdf.exists():
            print(f"{name:<22}{'--':>7}  MISSING {pdf}")
            continue
        s = scales[name]
        info = audit_pdf(pdf)
        eff_min = info["min"] * s["scale"] if info["min"] else None
        eff_med = info["med"] * s["scale"] if info["med"] else None
        status = "ok"
        if eff_min is not None:
            worst = min(worst, eff_min)
            if eff_min < 7.0:
                status = "BELOW 7pt"
                bad.append(f"{name} ({eff_min:.2f} pt)")
        print(f"{name:<22}{s['scale']:>7.3f}{info['min'] or 0:>9.2f}"
              f"{eff_min or 0:>9.2f}{eff_med or 0:>9.2f}"
              f"{(len(info['raster']) if info['raster'] else 0):>8}  {status}")
        print(f"    natural {s['native_w'] / 72:.2f}x{s['native_h'] / 72:.2f} in"
              f"   placed {s['req_w'] / 72:.2f}x{s['req_h'] / 72:.2f} in"
              f"   fonts: {', '.join(info['fonts'])}")
        if info["raster"]:
            print(f"    RASTER XOBJECTS: {info['raster']}")
    print()
    print(f"minimum effective text size across all figures: {worst:.2f} pt"
          f"  (Elsevier floor 7 pt)")
    if bad:
        print("FIGURES BELOW FLOOR: " + "; ".join(bad))
    return 0


if __name__ == "__main__":
    sys.exit(main())
