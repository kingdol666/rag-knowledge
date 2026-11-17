#!/usr/bin/env python3
"""Reference-style case anatomy figure for the E5 retrieval comparison.

The figure uses the visual grammar of the supplied clinical flowchart:
question/source card -> alternative retrieval paths -> evidence card ->
terminal verdict. The displayed values and excerpts are derived from the archived frozen
response records; this script changes only their visual arrangement.
"""
from __future__ import annotations

from pathlib import Path
import json
import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, Polygon, Rectangle

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figs"
PROVENANCE = ROOT / "experiment_data" / "case-anatomy-provenance.json"

INK = "#24384A"
NAVY = "#294765"
BLUE = "#2F9ED1"
PALE_BLUE = "#EAF5FB"
OCHRE = "#C88A2C"
PALE_OCHRE = "#FBF3E4"
BRICK = "#B65737"
PALE_BRICK = "#F9ECE7"
GREEN = "#36A866"
PALE_GREEN = "#EAF7EE"
SLATE = "#75818C"
GRID = "#D9E2E8"
LINE = "#9EADB8"
WHITE = "#FFFFFF"

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Liberation Sans", "DejaVu Sans"],
        "font.size": 8.2,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "savefig.facecolor": WHITE,
        "figure.facecolor": WHITE,
        "savefig.dpi": 300,
    }
)


def wrap(text: str, width: int) -> str:
    return "\n".join(textwrap.wrap(text, width=width, break_long_words=False))


def load_provenance() -> dict:
    data = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    science = data["cases"]["A-science-en-roberta.pdf"]
    literature = data["cases"]["F-pp-1"]
    assert science["arms"]["A0"]["gold_hit"] is False
    assert science["arms"]["A0h"]["gold_hit"] is True
    assert literature["arms"]["A0"]["gold_hit"] is False
    assert literature["arms"]["A0f"]["gold_hit"] is False
    assert literature["arms"]["A0h"]["gold_hit"] is True
    return data


def rounded_box(ax, x, y, w, h, face=WHITE, edge=LINE, lw=0.8,
                radius=0.010, linestyle="-"):
    ax.add_patch(
        FancyBboxPatch(
            (x, y), w, h,
            boxstyle=f"round,pad=0,rounding_size={radius}",
            facecolor=face,
            edgecolor=edge,
            linewidth=lw,
            linestyle=linestyle,
            zorder=1,
        )
    )


def panel(ax, x, y, w, h):
    rounded_box(ax, x, y, w, h, face=WHITE, edge=INK, lw=0.85,
                radius=0.006, linestyle=(0, (4.2, 3.0)))


def document_icon(ax, x, y, w=0.028, h=0.046, color="#8DB5E5"):
    """Small source-document glyph used inside the question card."""
    ax.add_patch(
        FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.0015,rounding_size=0.004",
            facecolor=WHITE, edgecolor=color, linewidth=0.9, zorder=5,
        )
    )
    ax.add_patch(
        Polygon(
            [[x + w * 0.65, y + h], [x + w, y + h * 0.65],
             [x + w * 0.65, y + h * 0.65]],
            closed=True, facecolor=PALE_BLUE, edgecolor=color,
            linewidth=0.65, zorder=6,
        )
    )
    for frac in (0.42, 0.29, 0.16):
        ax.plot([x + w * 0.18, x + w * 0.80],
                [y + h * frac, y + h * frac],
                color=color, linewidth=0.55, zorder=6)


def arrow(ax, x1, y1, x2, y2, color=INK, label=None, label_dy=0.014,
          lw=0.95, ms=9):
    """Draw an edge-to-edge flow arrow and an unobtrusive label."""
    ax.annotate(
        "", xy=(x2, y2), xytext=(x1, y1),
        arrowprops={
            "arrowstyle": "-|>",
            "mutation_scale": ms,
            "linewidth": lw,
            "color": color,
            "shrinkA": 0,
            "shrinkB": 0,
        },
        zorder=6,
    )
    if label:
        ax.text(
            (x1 + x2) / 2, (y1 + y2) / 2 + label_dy, label,
            fontsize=6.55, color=INK, ha="center", va="bottom", zorder=8,
            bbox={"facecolor": WHITE, "edgecolor": "none", "pad": 0.45},
        )


def question_card(ax, x, y, w, h, meta, question, target):
    """Input card with a separate evaluation strip below the question."""
    rounded_box(ax, x, y, w, h, face="#F3F5F6", edge=INK, lw=0.8,
                radius=0.006)
    document_icon(ax, x + 0.014, y + 0.024, w=0.027, h=0.044)
    tx = x + 0.055
    ax.text(tx, y + h - 0.015, meta, fontsize=6.55, color=SLATE,
            style="italic", ha="left", va="top", zorder=5)
    # These questions fit on one line at the full-width figure size; keeping
    # them single-line gives the target strip a stable, non-overlapping home.
    ax.text(tx, y + h - 0.037, "Q: " + question,
            fontsize=8.0, color=INK, fontweight="bold", ha="left", va="top",
            zorder=5)
    ax.plot([tx, x + w - 0.014], [y + 0.026, y + 0.026],
            color=GRID, linewidth=0.55, zorder=3)
    ax.text(tx, y + 0.008, "evaluation target: " + target, fontsize=6.45,
            color=OCHRE, fontweight="bold", ha="left", va="bottom", zorder=5)


def group_label(ax, x, y, number, title, color, note=None,
                text_x=None, rule_start=0.31):
    ax.add_patch(Circle((x, y), 0.013, facecolor=WHITE, edgecolor=color,
                        linewidth=0.95, zorder=5))
    ax.text(x, y - 0.001, str(number), fontsize=7.0, color=color,
            fontweight="bold", ha="center", va="center", zorder=6)
    if text_x is None:
        text_x = x + 0.022
    ax.text(text_x, y, title, fontsize=8.1, color=color,
            fontweight="bold", ha="left", va="center", zorder=6)
    if note:
        ax.text(0.944, y, note, fontsize=6.5, color=SLATE,
                style="italic", ha="right", va="center", zorder=6)
    ax.plot([rule_start, 0.944], [y - 0.018, y - 0.018],
            color=GRID, linewidth=0.65, zorder=2)


def process_card(ax, x, y, w, h, title, lines, accent=BLUE, face=PALE_BLUE,
                 body_size=6.9):
    """Process node with a compact dark title strip."""
    rounded_box(ax, x, y, w, h, face=face, edge=accent, lw=0.9,
                radius=0.008)
    band_h = min(0.024, h * 0.34)
    ax.add_patch(
        Rectangle((x, y + h - band_h), w, band_h,
                  facecolor=accent, edgecolor=accent, linewidth=0, zorder=2)
    )
    ax.text(x + 0.010, y + h - band_h / 2, title, fontsize=6.95,
            color=WHITE, fontweight="bold", ha="left", va="center", zorder=5)
    ax.text(x + 0.010, y + h - band_h - 0.010, "\n".join(lines),
            fontsize=body_size, color=INK, ha="left", va="top",
            linespacing=1.20, zorder=5)


def evidence_card(ax, x, y, w, h, title, excerpt, accent=OCHRE,
                  body_size=6.75):
    """Evidence/provenance node; deliberately distinct from process cards."""
    rounded_box(ax, x, y, w, h, face="#F7F8F8", edge=accent, lw=0.9,
                radius=0.008)
    band_h = min(0.024, h * 0.34)
    ax.add_patch(
        Rectangle((x, y + h - band_h), w, band_h,
                  facecolor=accent, edgecolor=accent, linewidth=0, zorder=2)
    )
    ax.text(x + 0.010, y + h - band_h / 2, "EVIDENCE · " + title,
            fontsize=6.85, color=WHITE, fontweight="bold",
            ha="left", va="center", zorder=5)
    ax.text(x + 0.010, y + h - band_h - 0.010, excerpt,
            fontsize=body_size, color=INK, ha="left", va="top",
            linespacing=1.18, zorder=5)


def verdict_card(ax, x, y, w, h, hit, note):
    """Uniform terminal node for lexical containment verdicts."""
    edge = GREEN if hit else BRICK
    face = PALE_GREEN if hit else PALE_BRICK
    rounded_box(ax, x, y, w, h, face=face, edge=edge, lw=1.0,
                radius=0.008)
    badge_w = 0.044
    ax.add_patch(
        Rectangle((x, y), badge_w, h, facecolor=edge, edgecolor=edge,
                  linewidth=0, zorder=2)
    )
    ax.text(x + badge_w / 2, y + h / 2, "HIT" if hit else "MISS",
            fontsize=7.0, color=WHITE, fontweight="bold",
            ha="center", va="center", zorder=6)
    ax.text(x + badge_w + 0.010, y + h / 2, note, fontsize=6.65,
            color=INK, ha="left", va="center", zorder=6)


def branch_spine(ax, x, y_top, row_ys, color, y_bottom=None):
    """Shared query spine with explicit alternative branch points."""
    if y_bottom is None:
        y_bottom = min(row_ys)
    ax.plot([x, x], [y_top, y_bottom], color=color, linewidth=0.9,
            zorder=4)
    ax.annotate("", xy=(x, y_top), xytext=(x, y_top + 0.018),
                arrowprops={"arrowstyle": "-|>", "mutation_scale": 8,
                            "linewidth": 0.9, "color": color}, zorder=6)
    for row_y in row_ys:
        ax.add_patch(Circle((x, row_y), 0.0065, facecolor=WHITE,
                            edgecolor=color, linewidth=0.9, zorder=6))


def case_a(ax, data):
    science = data["cases"]["A-science-en-roberta.pdf"]
    x0, y0, w0, h0 = 0.025, 0.535, 0.95, 0.440
    panel(ax, x0, y0, w0, h0)
    ax.text(0.040, 0.953, "(a)  A-science-en-roberta · two evidence paths",
            fontsize=9.1, fontweight="bold", color=INK, ha="left", va="center")
    question_card(
        ax, 0.060, 0.850, 0.880, 0.078,
        science["meta"], science["question"], '“' + science["target"] + '”',
    )
    group_label(ax, 0.060, 0.823, 1, "Alternative retrieval arms",
                NAVY, "same question · different evidence admission",
                rule_start=0.340)

    row1, row2 = 0.766, 0.640
    branch_spine(ax, 0.060, 0.850, [row1, row2], NAVY, y_bottom=row2)
    arrow(ax, 0.0665, row1, 0.150, row1, NAVY)
    process_card(ax, 0.150, row1 - 0.038, 0.190, 0.076,
                 "A0 · BASELINE", ("tiered judged pack", f"{science['arms']['A0']['survivor_count']} survivors"),
                 accent=OCHRE, face=PALE_OCHRE)
    arrow(ax, 0.340, row1, 0.370, row1, OCHRE, "read")
    evidence_card(ax, 0.370, row1 - 0.032, 0.255, 0.064,
                  "retrieved passage",
                  "RoBERTa string not admitted",
                  accent=OCHRE, body_size=6.8)
    arrow(ax, 0.625, row1, 0.665, row1, OCHRE)
    verdict_card(ax, 0.665, row1 - 0.032, 0.275, 0.064, False,
                 "target string absent")

    arrow(ax, 0.0665, row2, 0.150, row2, NAVY)
    process_card(ax, 0.150, row2 - 0.040, 0.190, 0.080,
                 "A0h · ENHANCED", ("tiered pack + top-8 chunks", f"{science['arms']['A0h']['survivor_count']} survivors"),
                 accent=BLUE, face=PALE_BLUE)
    arrow(ax, 0.340, row2, 0.370, row2, BLUE, "add")
    evidence_card(ax, 0.370, row2 - 0.040, 0.255, 0.080,
                  "archived passage · #70",
                  science["excerpt"].split(" ... ", 1)[-1][:46] + "...",
                  accent=BLUE, body_size=6.8)
    arrow(ax, 0.625, row2, 0.665, row2, BLUE)
    verdict_card(ax, 0.665, row2 - 0.040, 0.275, 0.080, True,
                 "target string present")

    ax.text(0.500, 0.560,
            "The displayed excerpt is from the frozen A0h response capture; verdicts are target-string proxies.",
            fontsize=6.65, color=SLATE, ha="center", va="center")


def case_b(ax, data):
    literature = data["cases"]["F-pp-1"]
    x0, y0, w0, h0 = 0.025, 0.035, 0.95, 0.475
    panel(ax, x0, y0, w0, h0)
    ax.text(0.040, 0.492, "(b)  F-pp-1 · controls versus chunk-window union",
            fontsize=9.1, fontweight="bold", color=INK, ha="left", va="center")
    question_card(
        ax, 0.060, 0.389, 0.880, 0.078,
        literature["meta"], literature["question"],
        '“' + literature["target"] + '”',
    )
    group_label(ax, 0.060, 0.374, 1, "Parallel control arms",
                OCHRE, "A0 and A0f are alternatives", rule_start=0.330)

    # Two independent control lanes.  Each terminates in its own aligned MISS node.
    row_a0, row_a0f = 0.331, 0.265
    branch_spine(ax, 0.060, 0.390, [row_a0, row_a0f], OCHRE,
                 y_bottom=row_a0f)
    arrow(ax, 0.0665, row_a0, 0.150, row_a0, OCHRE)
    process_card(ax, 0.150, row_a0 - 0.028, 0.185, 0.056,
                 "A0 · PACK", (f"{literature['arms']['A0']['survivor_count']} survivor · P&P part 2",),
                 accent=OCHRE, face=PALE_OCHRE, body_size=6.65)
    arrow(ax, 0.335, row_a0, 0.365, row_a0, OCHRE)
    evidence_card(ax, 0.365, row_a0 - 0.028, 0.235, 0.056,
                  "headers only", "dialogue not admitted", accent=OCHRE,
                  body_size=6.65)
    arrow(ax, 0.600, row_a0, 0.635, row_a0, OCHRE)
    verdict_card(ax, 0.635, row_a0 - 0.028, 0.305, 0.056, False,
                 "gold string absent")

    arrow(ax, 0.0665, row_a0f, 0.150, row_a0f, OCHRE)
    process_card(ax, 0.150, row_a0f - 0.028, 0.185, 0.056,
                 "A0f · WINDOW", (f"full window · {literature['arms']['A0f']['survivor_count']} survivors",),
                 accent=OCHRE, face=PALE_OCHRE, body_size=6.65)
    arrow(ax, 0.335, row_a0f, 0.365, row_a0f, OCHRE)
    evidence_card(ax, 0.365, row_a0f - 0.028, 0.235, 0.056,
                  "window boundary", "ends before dialogue", accent=OCHRE,
                  body_size=6.65)
    arrow(ax, 0.600, row_a0f, 0.635, row_a0f, OCHRE)
    verdict_card(ax, 0.635, row_a0f - 0.028, 0.305, 0.056, False,
                 "gold string absent")

    group_label(ax, 0.060, 0.204, 2, "Enhanced arm",
                BLUE, "chunk-window union", rule_start=0.245)
    row_h = 0.135
    # The enhanced lane has its own explicit source-to-row connector; this
    # prevents the left arrow from appearing as a detached stub.
    branch_spine(ax, 0.060, 0.190, [row_h], BLUE, y_bottom=row_h)
    arrow(ax, 0.0665, row_h, 0.150, row_h, BLUE)
    process_card(ax, 0.150, row_h - 0.034, 0.205, 0.068,
                 "A0h · ENHANCED", ("windows + top-8 chunks", f"{literature['arms']['A0h']['survivor_count']} survivors"),
                 accent=BLUE, face=PALE_BLUE, body_size=6.65)
    arrow(ax, 0.355, row_h, 0.385, row_h, BLUE, "add")
    evidence_card(ax, 0.385, row_h - 0.034, 0.310, 0.068,
                  "original English excerpt",
                  wrap(literature["excerpt"], 52),
                  accent=BLUE, body_size=6.15)
    arrow(ax, 0.695, row_h, 0.730, row_h, BLUE)
    verdict_card(ax, 0.730, row_h - 0.034, 0.210, 0.068, True,
                 "gold present")

    ax.text(0.500, 0.060,
            "Frozen response records; verdicts are target-string containment proxies, not answer correctness.",
            fontsize=6.55, color=SLATE, ha="center", va="center")


def main() -> None:
    fig = plt.figure(figsize=(7.15, 5.45))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    data = load_provenance()
    case_a(ax, data)
    case_b(ax, data)

    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / "fig_opt_case.pdf", format="pdf", facecolor=WHITE)
    fig.savefig(FIG / "fig_opt_case.png", dpi=300, format="png", facecolor=WHITE)
    plt.close(fig)
    print(f"wrote {FIG / 'fig_opt_case.pdf'} and {FIG / 'fig_opt_case.png'}")


if __name__ == "__main__":
    main()
