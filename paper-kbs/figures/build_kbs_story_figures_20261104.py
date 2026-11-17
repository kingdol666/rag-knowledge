#!/usr/bin/env python3
"""Rebuild the three KBS story figures from editable vector primitives.

Outputs the architecture, end-to-end workflow, and the paired routing audit as
PDF (vector) plus 300-dpi PNG previews.  Figure text uses the audited KBS
typography helper and is designed at the placed two-column width.
"""
from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

HERE = Path(__file__).resolve().parent
OUT = HERE / "kbs_revision_20261104"
TARGET = HERE.parent / "tex" / "journal_20p" / "figs"
W = 6.96  # text width used by the camera-ready KBS build; 8 pt scales to 8.3 pt
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
VERM = "#D55E00"
PURPLE = "#7A5C93"
GREY = "#68737D"
LIGHT_BLUE = "#E8F1F8"
LIGHT_GREEN = "#EAF4EF"
LIGHT_ORANGE = "#FBF2DF"
LIGHT_RED = "#FAECE8"
LIGHT_PURPLE = "#F2EDF5"
LIGHT_GREY = "#F3F5F6"
LINE = "#53606B"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "Liberation Sans", "DejaVu Sans"],
    "font.size": FS,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "figure.dpi": 160,
    "savefig.dpi": 300,
    "savefig.bbox": None,
})


def rounded(ax, x, y, w, h, title, body="", *, fc="white", ec=LINE,
            title_color=INK, body_color=SUB, lw=0.8, title_fs=8.2,
            body_fs=8.0, radius=0.06, z=3):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.018,rounding_size={radius}",
        facecolor=fc, edgecolor=ec, linewidth=lw, zorder=z))
    if body:
        ax.text(x + w / 2, y + h * 0.68, title, ha="center", va="center",
                color=title_color, fontsize=title_fs, fontweight="bold", zorder=z + 2)
        ax.text(x + w / 2, y + h * 0.30, body, ha="center", va="center",
                color=body_color, fontsize=body_fs, linespacing=1.18, zorder=z + 2)
    else:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center",
                color=title_color, fontsize=title_fs, fontweight="bold", zorder=z + 2)


def arrow(ax, p1, p2, *, color=LINE, lw=0.85, style="-|>", ls="-",
          connection="arc3,rad=0", z=2, ms=8):
    ax.add_patch(FancyArrowPatch(
        p1, p2, arrowstyle=style, mutation_scale=ms, linewidth=lw,
        color=color, linestyle=ls, connectionstyle=connection, zorder=z))


def setup_axes(fig, h, xlim=(0, W)):
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(*xlim)
    ax.set_ylim(0, h)
    ax.axis("off")
    return ax


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    helper.OUT = OUT
    helper.save(fig, name)
    TARGET.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        shutil.copy2(OUT / f"{name}.{ext}", TARGET / f"{name}.{ext}")


def fig1_architecture():
    """Layered system architecture: access, domain services, and shared state."""
    h = 3.50
    fig = plt.figure(figsize=(W, h))
    ax = setup_axes(fig, h)

    ax.add_patch(FancyBboxPatch(
        (0.08, 0.08), W - 0.16, h - 0.16,
        boxstyle="round,pad=0.012,rounding_size=0.06",
        facecolor="#FFFFFF", edgecolor="#7C8791", linewidth=0.75, zorder=0))
    ax.text(0.22, 3.25, "HMRS self-hosted knowledge-base platform",
            ha="left", va="center", fontsize=9.0, fontweight="bold", color=INK)

    # Access layer
    ax.text(0.22, 2.89, "ACCESS", ha="left", va="center",
            fontsize=8.0, fontweight="bold", color=BLUE)
    rounded(ax, 1.06, 2.68, 2.48, 0.44, "Web interface", "Nuxt 3 · server-side proxy",
            fc=LIGHT_BLUE, ec=BLUE)
    rounded(ax, 3.76, 2.68, 2.90, 0.44, "Agent and CLI interface", "MCP server · 95 registered tools",
            fc=LIGHT_PURPLE, ec=PURPLE)
    arrow(ax, (2.30, 2.66), (2.30, 2.37), color=BLUE)
    arrow(ax, (5.20, 2.66), (5.20, 2.37), color=PURPLE)
    ax.text(3.74, 2.49, "HTTP / MCP calls", ha="center", va="center",
            fontsize=8.0, color=SUB, bbox=dict(fc="white", ec="none", pad=1.0), zorder=4)

    # Domain services
    ax.text(0.22, 2.28, "CORE SERVICES", ha="left", va="center",
            fontsize=8.0, fontweight="bold", color=GREEN)
    boxes = [
        (0.36, "Quality-gated acquisition", "MinerU parse/OCR · quality checks\nsplit · descriptions · tags", LIGHT_GREEN, GREEN),
        (2.54, "Organization and lifecycle", "catalog/tree · tags · dedup\nlifecycle · graph · experience", LIGHT_ORANGE, ORANGE),
        (4.72, "Retrieval and evidence", "BM25 · vector · catalog · graph\nlane policy · invoked evidence gate", LIGHT_BLUE, BLUE),
    ]
    for x, title, body, fc, ec in boxes:
        rounded(ax, x, 1.46, 1.88, 0.68, title, body, fc=fc, ec=ec,
                title_fs=7.9, body_fs=7.6)

    # Shared state boundary with three explicit stores.
    ax.text(0.22, 1.13, "SHARED DATA", ha="left", va="center",
            fontsize=8.0, fontweight="bold", color=PURPLE)
    stores = [
        (0.36, "Document store", "Markdown + extracted assets"),
        (2.54, "Registries", ".tree-fs.json + per-KB YAML"),
        (4.72, "Search and graph indices", "Chroma · BM25 · Neo4j"),
    ]
    for x, title, body in stores:
        rounded(ax, x, 0.43, 1.88, 0.48, title, body,
                fc=LIGHT_PURPLE, ec=PURPLE, title_fs=7.9, body_fs=7.5)

    # Each service reads or writes the shared stores; retrieval is explicitly bidirectional.
    for x in (1.30, 3.48, 5.66):
        arrow(ax, (x, 1.44), (x, 0.94), color=GREEN, style="<|-|>", lw=0.75, ms=7)
    ax.text(3.76, 0.22,
            "Files, registries and indices are audited after writes; retrieval reads the same state.",
            ha="center", va="center", fontsize=8.0, color=SUB)
    save(fig, "fig1_architecture")


def fig2_workflow():
    """Two swimlanes connect knowledge creation to evidence-grounded answers."""
    h = 3.78
    fig = plt.figure(figsize=(W, h))
    ax = setup_axes(fig, h)

    # Lane labels and backgrounds
    ax.add_patch(FancyBboxPatch((0.08, 2.73), W - 0.16, 0.88,
                               boxstyle="round,pad=0.012,rounding_size=0.05",
                               facecolor="#F7FAF8", edgecolor="#96B7A3", linewidth=0.7, zorder=0))
    ax.add_patch(FancyBboxPatch((0.08, 0.23), W - 0.16, 1.16,
                               boxstyle="round,pad=0.012,rounding_size=0.05",
                               facecolor="#F7F9FB", edgecolor="#9CB2C7", linewidth=0.7, zorder=0))
    ax.text(0.20, 3.47, "A  KNOWLEDGE CREATION AND MAINTENANCE",
            ha="left", va="center", fontsize=8.2, fontweight="bold", color=GREEN)
    ax.text(0.20, 1.22, "B  QUESTION-TO-EVIDENCE WORKFLOW",
            ha="left", va="center", fontsize=8.2, fontweight="bold", color=BLUE)

    # Ingestion lifecycle: five steps, with a visible post-index repair loop.
    top_y, bw, bh, gap = 2.89, 1.12, 0.43, 0.22
    xs = [0.22 + i * (bw + gap) for i in range(5)]
    stages = [
        ("Source files", "PDF · Office · scans"),
        ("Parse + QC", "MinerU · OCR · structure"),
        ("Split + enrich", "descriptions · tags"),
        ("Route to KB", "parsed content selects"),
        ("Index + post-check", "probe · audit · repair"),
    ]
    for i, (x, (title, body)) in enumerate(zip(xs, stages)):
        fc, ec = (LIGHT_GREEN, GREEN) if i < 4 else (LIGHT_ORANGE, ORANGE)
        rounded(ax, x, top_y, bw, bh, title, body, fc=fc, ec=ec,
                title_fs=7.8, body_fs=7.6, radius=0.045)
        if i < len(xs) - 1:
            arrow(ax, (x + bw + 0.015, top_y + bh / 2),
                  (xs[i + 1] - 0.015, top_y + bh / 2), color=GREEN, lw=0.8, ms=7)
    # Online workflow
    by, bh2 = 0.50, 0.55
    bx = [0.23, 1.47, 2.91, 4.30]
    bws = [1.05, 1.25, 1.20, 1.15]
    bottom = [
        ("Question", "request + scope"),
        ("Select lane", "Search / Librarian /\nHybrid"),
        ("Retrieve", "catalog · BM25\nvector · graph"),
        ("Verify evidence", "fetch text · Laya\nsegment verdict"),
    ]
    for i, (x, width, (title, body)) in enumerate(zip(bx, bws, bottom)):
        fc, ec = (LIGHT_BLUE, BLUE) if i < 3 else (LIGHT_RED, VERM)
        rounded(ax, x, by, width, bh2, title, body, fc=fc, ec=ec,
                title_fs=7.8, body_fs=7.4, radius=0.045)
        if i < len(bx) - 1:
            arrow(ax, (x + width + 0.015, by + bh2 / 2),
                  (bx[i + 1] - 0.015, by + bh2 / 2), color=BLUE, lw=0.8, ms=7)

    # Terminal outcomes after verification
    ox, ow = 5.68, 1.08
    rounded(ax, ox, 0.72, ow, 0.36, "Verified", "answer + cite sources",
            fc=LIGHT_GREEN, ec=GREEN, title_fs=7.8, body_fs=7.5, radius=0.04)
    rounded(ax, ox, 0.28, ow, 0.36, "None survives", "not-found + scope",
            fc=LIGHT_GREY, ec=GREY, title_fs=7.8, body_fs=7.5, radius=0.04)
    arrow(ax, (bx[3] + bws[3] + 0.015, by + bh2 * 0.75), (ox - 0.015, 0.90),
          color=GREEN, lw=0.8, ms=7)
    arrow(ax, (bx[3] + bws[3] + 0.015, by + bh2 * 0.25), (ox - 0.015, 0.46),
          color=GREY, lw=0.8, ms=7)

    # Cross-lane knowledge state: ingestion writes; query retrieves from it.
    arrow(ax, (3.47, 2.70), (3.47, 1.88), color=PURPLE, style="-|>", lw=0.8, ms=7)
    rounded(ax, 1.55, 1.63, 3.86, 0.45, "Shared knowledge base",
            "files and assets · tree registry · per-KB YAML\nChroma vector · BM25 lexical · Neo4j graph",
            fc=LIGHT_PURPLE, ec=PURPLE, title_fs=8.0, body_fs=7.8, radius=0.05)
    arrow(ax, (3.47, 1.61), (3.47, 1.04), color=PURPLE, style="-|>", lw=0.8, ms=7)
    save(fig, "fig2_workflow")


def fig3_routing():
    """Paired route accuracy and its discordance table for A0 versus A3."""
    h = 2.70
    fig = plt.figure(figsize=(W, h))
    ax1 = fig.add_axes([0.22, 0.23, 0.37, 0.63])
    ax2 = fig.add_axes([0.66, 0.22, 0.30, 0.64])

    # Panel A: route accuracy with Wilson intervals; categories remain explicit.
    labels = ["Descriptions enabled (A0)", "Descriptions removed (A3)"]
    vals = np.array([100.0, 37 / 72 * 100])
    lo = np.array([94.9, 40.1])
    hi = np.array([100.0, 62.6])
    y = np.array([1, 0])
    colors = [BLUE, GREY]
    for yi, value, low, high, color, label in zip(y, vals, lo, hi, colors, labels):
        ax1.errorbar(value, yi, xerr=[[value - low], [high - value]], fmt="o",
                     markersize=5.4, color=color, ecolor=color, capsize=3,
                     elinewidth=1.25, markeredgecolor="white", markeredgewidth=0.7,
                     zorder=3)
        result_label = "72/72 (100%)" if value == 100 else f"37/72 ({value:.1f}%)"
        label_x = 96.0 if value == 100 else 66.0
        ax1.text(label_x, yi + 0.22, result_label, ha="right" if value == 100 else "left",
                 va="center",
                 fontsize=8.0, color=INK)
    ax1.set_yticks(y, labels)
    ax1.set_xlim(0, 110)
    ax1.set_ylim(-0.55, 1.55)
    ax1.set_xticks([0, 25, 50, 75, 100])
    ax1.set_xlabel("Correct KB routing (%)")
    ax1.set_title("(a) Matched routing accuracy", loc="left", pad=7, fontsize=8.2, fontweight="bold")
    ax1.grid(axis="x", color="#DDE2E6", linewidth=0.55, zorder=0)
    ax1.tick_params(axis="both", length=2.5, pad=3)
    helper.hide_top_right(ax1, left=True)

    # Panel B: paired 2x2 outcomes (rows A0; columns A3).
    matrix = np.array([[37, 35], [0, 0]])
    ax2.set_xlim(0, 2)
    ax2.set_ylim(0, 2)
    ax2.set_xticks([0.5, 1.5], ["Correct", "Wrong"])
    ax2.set_yticks([1.5, 0.5], ["Correct", "Wrong"])
    ax2.set_xlabel("Descriptions removed (A3)")
    ax2.set_title("(b) Paired route outcomes", loc="left", pad=7,
                  fontsize=8.2, fontweight="bold")
    fills = [["#DDEBF6", "#DCEFE7"], ["#F2F4F5", "#F2F4F5"]]
    for r in range(2):
        for c in range(2):
            y0 = 1 - r
            ax2.add_patch(Rectangle((c, y0), 1, 1, facecolor=fills[r][c],
                                    edgecolor="white", linewidth=1.2))
            ax2.text(c + 0.5, y0 + 0.53, str(matrix[r, c]), ha="center", va="center",
                     fontsize=10.0, fontweight="bold", color=INK)
            desc = [["both correct", "A0 only"], ["A3 only", "both wrong"]][r][c]
            ax2.text(c + 0.5, y0 + 0.24, desc, ha="center", va="center",
                     fontsize=7.8, color=SUB)
    for spine in ax2.spines.values():
        spine.set_visible(False)
    ax2.tick_params(length=0, pad=3)
    ax2.text(1.0, -0.46, "Exact McNemar p = 5.82e-11",
             ha="center", va="center", fontsize=8.0, color=INK)

    save(fig, "fig3_routing")


def main():
    fig1_architecture()
    fig2_workflow()
    fig3_routing()
    print(f"PDF and PNG outputs: {OUT}")
    print(f"Manuscript figure copies: {TARGET}")


if __name__ == "__main__":
    main()
