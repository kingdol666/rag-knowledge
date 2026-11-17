#!/usr/bin/env python3
"""Build the management-model figure for the HMRS KBS manuscript.

The figure carries the paper's central claim: documents are managed at three
levels (collection, document, segment) and a query is served tier by tier
(catalogue, shelf, document, segment).  The visual direction was drafted as a
generated concept image and rebuilt here as editable vector primitives, under
the same contract as the rest of the artwork in this directory: Arial only,
8 pt floor, vector PDF plus a 300 dpi PNG preview, drawn at the placed width so
that the LaTeX placement does not scale the type down.

Run from this directory:
    uv run --with matplotlib --with numpy --with pymupdf python -B build_fig_management_model.py
"""
from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE = Path(__file__).resolve().parent
OUT = HERE / "kbs_revision_20261111"
TARGET = HERE.parent / "tex" / "journal_20p" / "figs"

# Placed width of a \includegraphics[width=\textwidth] figure in the 5p
# two-column build (7.22 in).  Drawing at 6.96 in leaves the 8 pt type at
# 8.3 pt after placement.
W = 6.96
H = 3.80
FS = 8.0

spec = importlib.util.spec_from_file_location("kbs_fig_helpers", HERE / "figures.py")
if spec is None or spec.loader is None:
    raise RuntimeError("Cannot load paper-kbs/figures/figures.py")
helper = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = helper
spec.loader.exec_module(helper)

INK = "#20262E"
SUB = "#46515C"
BLUE = "#0072B2"
GREEN = "#009E73"
ORANGE = "#E69F00"
PURPLE = "#7A5C93"
LIGHT_BLUE = "#E8F1F8"
LIGHT_GREEN = "#EAF4EF"
LIGHT_ORANGE = "#FBF2DF"
LIGHT_PURPLE = "#F2EDF5"
LINE = "#53606B"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": [helper.FONT, "Helvetica", "Liberation Sans", "DejaVu Sans"],
    "font.size": FS,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "savefig.facecolor": "white",
})


def band(ax, x, y, w, h, edge, fill, title, chips, chip_w):
    """One management level: a tinted band with a coloured left edge."""
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.012,rounding_size=0.05",
        facecolor=fill, edgecolor=LINE, linewidth=0.7, zorder=1))
    ax.add_patch(FancyBboxPatch(
        (x + 0.012, y + 0.012), 0.05, h - 0.024,
        boxstyle="round,pad=0.0,rounding_size=0.024",
        facecolor=edge, edgecolor=edge, linewidth=0, zorder=2))
    ax.text(x + 0.105, y + h - 0.135, title, ha="left", va="center",
            fontsize=FS + 0.3, fontweight="bold", color=INK, zorder=3)
    cx = x + 0.105
    cy = y + 0.035
    widths = chip_w if isinstance(chip_w, (list, tuple)) else [chip_w] * len(chips)
    for label, cw in zip(chips, widths):
        for line in label.split(chr(10)):
            need = helper.tw(line, FS - 0.2)
            if need > cw - 0.04:
                raise SystemExit(
                    "chip label does not fit: %r needs %.3f in, chip is %.3f in"
                    % (line, need, cw))
        ax.add_patch(FancyBboxPatch(
            (cx, cy), cw, 0.275,
            boxstyle="round,pad=0.008,rounding_size=0.032",
            facecolor="white", edgecolor=edge, linewidth=0.6, zorder=2))
        ax.text(cx + cw / 2, cy + 0.137, label, ha="center", va="center",
                fontsize=FS - 0.2, color=INK, zorder=3, linespacing=1.15)
        cx += cw + 0.055


def tier_box(ax, x, y, w, h, name, sub):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.010,rounding_size=0.05",
        facecolor=LIGHT_BLUE, edgecolor=BLUE, linewidth=0.7, zorder=2))
    ax.text(x + w / 2, y + h * 0.62, name, ha="center", va="center",
            fontsize=FS + 0.2, fontweight="bold", color=INK, zorder=3)
    ax.text(x + w / 2, y + h * 0.27, sub, ha="center", va="center",
            fontsize=FS - 0.4, color=SUB, zorder=3)


def main() -> None:
    helper.OUT = OUT
    OUT.mkdir(parents=True, exist_ok=True)
    TARGET.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    left_x, left_w = 0.10, 3.52
    chip_w = 1.02

    ax.text(left_x, H - 0.18, "Management levels", ha="left", va="center",
            fontsize=FS + 0.6, fontweight="bold", color=BLUE)
    band(ax, left_x, 2.66, left_w, 0.62, BLUE, LIGHT_BLUE, "Collection level",
         ["Library and sub-library\ncatalogue", "Content-derived\nplacement",
          "Descriptions\nand tags"], [1.16, 1.02, 1.02])
    band(ax, left_x, 1.94, left_w, 0.62, GREEN, LIGHT_GREEN, "Document level",
         ["Duplicate review", "Move, rename,\ndelete", "Forced re-index"], chip_w)
    band(ax, left_x, 1.22, left_w, 0.62, ORANGE, LIGHT_ORANGE, "Segment level",
         ["Structural split", "Dense and lexical\nindices", "Evidence gate"], chip_w)

    # Shared state: the three stores that the levels write to and read from.
    ax.add_patch(FancyBboxPatch(
        (left_x, 0.60), left_w, 0.46,
        boxstyle="round,pad=0.010,rounding_size=0.05",
        facecolor=LIGHT_PURPLE, edgecolor=PURPLE, linewidth=0.7, zorder=1))
    ax.text(left_x + 0.105, 0.99, "Shared state", ha="left", va="center",
            fontsize=FS, fontweight="bold", color=PURPLE, zorder=3)
    sx = left_x + 0.105
    shared = [("Document files", 0.95), ("Tree registry\nand per-KB YAML", 1.15),
              ("Search indices", 0.95)]
    for label, cw in shared:
        for line in label.split("\n"):
            need = helper.tw(line, FS)   # helper.save() enforces an 8 pt floor
            if need > cw - 0.05:
                raise SystemExit("shared-state label too wide: %r %.3f > %.3f"
                                 % (line, need, cw - 0.05))
        ax.add_patch(FancyBboxPatch(
            (sx, 0.655), cw, 0.27,
            boxstyle="round,pad=0.008,rounding_size=0.032",
            facecolor="white", edgecolor=PURPLE, linewidth=0.6, zorder=2))
        ax.text(sx + cw / 2, 0.79, label, ha="center", va="center",
                fontsize=FS, color=INK, zorder=3, linespacing=1.05)
        sx += cw + 0.06

    ax.plot([3.92, 3.92], [0.55, H - 0.05], color=LINE, lw=0.7, zorder=1)

    ax.text(4.14, H - 0.18, "Tiered query path", ha="left", va="center",
            fontsize=FS + 0.6, fontweight="bold", color=ORANGE)
    ax.text(4.14, H - 0.40, "each tier narrows the next", ha="left",
            va="center", fontsize=FS - 0.5, color=SUB)

    tx, tw_ = 4.14, 1.70
    tiers = [
        ("Catalogue", "collections and descriptions", 2.66),
        ("Shelf", "documents in one collection", 1.94),
        ("Document", "open a body", 1.22),
        ("Segment", "score and admit", 0.50),
    ]
    for name, sub, ty in tiers:
        tier_box(ax, tx, ty, tw_, 0.56, name, sub)
    for i in range(len(tiers) - 1):
        helper.arrow(ax, tx + tw_ / 2, tiers[i][2], tx + tw_ / 2,
                     tiers[i + 1][2] + 0.56, color=LINE, lw=0.85,
                     style="-|>", ms=6, zorder=3)

    ax.text(W / 2, 0.20,
            "Management state is written and reconciled; the query path reads it tier by tier.",
            ha="center", va="center", fontsize=FS - 0.2, color=SUB)

    helper.save(fig, "fig_management_model")

    for ext in ("pdf", "png"):
        shutil.copy2(OUT / f"fig_management_model.{ext}",
                     TARGET / f"fig_management_model.{ext}")
    print(f"wrote {TARGET}/fig_management_model.pdf/.png")


if __name__ == "__main__":
    main()
