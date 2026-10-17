#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Compact, Elsevier-compliant replacements for the figures of the 20-page KBS
build (``paper-kbs/tex/journal_20p``).

Why this file exists
--------------------
The two hand-authored diagrams that shipped in the 20-page build were exported
from the archify HTML sources as Chromium print output.  Measured against the
build log by ``tex/journal_20p/_audit_artwork_20p.py`` they failed three
Elsevier artwork rules:

    fig1_architecture   scale 0.599   effective min text  5.29 pt   (floor 7)
    fig2_lanes          scale 0.571   effective min text  4.15 pt   (floor 7)

    both: Type3 (bitmap) fonts and 30 raster PNG xobjects each, i.e. line art
    delivered as a bitmap.  Neither the 7 pt floor nor "vector line art with
    fonts from the Elsevier list" can be met by shrinking a browser export.

Both were also ~35 % empty canvas at the foot, which is why they measured
10.13 in tall on the page.

Every figure below is drawn under the *same* typography contract as the rest
of the artwork in ``figures.py`` -- Arial, Type-42 (TrueType) embedding, pure
vector, nothing under 8 pt -- and at the width the 20-page build places it, so
the LaTeX scale factor is 1.00 and the 8 pt set here is the 8 pt the reader
sees:

    fig1_architecture   width=\textwidth      = 7.25 in   (drawn on 6.96 in)
    fig2_lanes          width=\textwidth      = 7.25 in   (drawn on 6.96 in)
    fig3_retrieval      width=\columnwidth    = 3.50 in
    fig10_mode_matrix   width=0.86\textwidth  = 0.86 x 7.25 = 6.24 in

fig1 and fig2 are drawn on 6.96 in canvases, i.e. slightly narrower than the
7.25 in they are placed at; the resulting 1.038 scale lifts their 8 pt to
8.30 pt effective, comfortably above the 7 pt floor, so they are left alone.
The two figures that were NOT above the floor -- fig3_retrieval and
fig10_mode_matrix -- are the ones re-laid out below.

``fig3_retrieval`` had been drawn on a 5.38 in canvas and was being scaled down
to 0.648 (5.19 pt effective); ``fig10_mode_matrix`` had no generator in the
repository at all, embedded DejaVuSans instead of Arial, and was being scaled
to 0.570 (4.56 pt effective).

Run:  uv run --with pymupdf --with matplotlib python -B figs_20p.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mticker  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

HERE = Path(__file__).resolve().parent
TARGET = HERE.parent / "tex" / "journal_20p" / "figs"

# reuse the audited typography helpers instead of restating the contract
_spec = importlib.util.spec_from_file_location("figmod", HERE / "figures.py")
figmod = importlib.util.module_from_spec(_spec)
sys.modules["figmod"] = figmod
_spec.loader.exec_module(figmod)

box = figmod.box
arrow = figmod.arrow
save = figmod.save
hide_top_right = figmod.hide_top_right
C = figmod.C
RESULTS = figmod.RESULTS

W = 6.96          # inches == 501.12 pt == \textwidth of the 20-page build
FS = 8.0

BAND_FC = "#F5F7F9"
ACQ_FC, ACQ_EC = "#E4F0E8", "#4F8A63"
RET_FC, RET_EC = "#E6EEF7", "#4A6E9B"
STORE_FC, STORE_EC = "#F2ECF6", "#7A5C93"
GATE_FC, GATE_EC = "#FBE9E7", "#B3563F"
TERM_FC, TERM_EC = "#EDF3EC", "#4F8A63"
GREY_FC, GREY_EC = "#F2F2F2", "#666666"

INK = "#111111"
SUB = "#3C3C3C"


def band(ax, x, y, w, h, title, ec):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.008,rounding_size=0.06",
                                fc=BAND_FC, ec=ec, lw=0.8,
                                ls=(0, (4, 2)), zorder=1))
    ax.text(x + w / 2, y + h - 0.15, title, ha="center", va="center",
            fontsize=FS, color=ec, fontweight="bold", zorder=2)


def step(ax, x, y, w, h, head, sub, fc, ec):
    """Box with a bold head line and a smaller explanatory sub-line."""
    box(ax, x, y, w, h, "", fc=fc, ec=ec, lw=0.7, zorder=3)
    ax.text(x + w / 2, y + h * 0.67, head, ha="center", va="center",
            fontsize=FS, fontweight="bold", color=INK, zorder=5)
    ax.text(x + w / 2, y + h * 0.27, sub, ha="center", va="center",
            fontsize=FS, color=SUB, zorder=5, linespacing=1.2)


def note(ax, x, y, text, color, ha="center", va="center"):
    ax.text(x, y, text, ha=ha, va=va, fontsize=FS, color=color, zorder=6)


# ===========================================================================
# Fig. 1 --- two-path architecture over two authoritative stores
# ===========================================================================
def fig1():
    H = 3.98
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    bh, gap = 0.42, 0.20
    lx, lw = 0.17, 2.28
    mx, mw = 2.74, 1.48
    rx, rw = 4.56, 2.23

    band(ax, 0.05, 0.64, 2.47, 3.28, "Content-governed acquisition", ACQ_EC)
    band(ax, 4.44, 0.64, 2.47, 3.28,
         "Agent retrieval and evidence enforcement", RET_EC)

    # acquisition column: 4 steps, centred against the 5-step retrieval column
    rtop = 3.62
    rys = [rtop - i * (bh + gap) for i in range(5)]
    ltop = rtop - 0.31
    lys = [ltop - i * (bh + gap) for i in range(4)]

    acq = [
        ("Enterprise documents", "PDF · Office · scans"),
        ("Parse + quality gate", "MinerU · task-polled"),
        ("Content-derived routing (C1)", "description · tags · placement"),
        ("Index + post-check", "vector · BM25 · graph"),
    ]
    for y, (h1, h2) in zip(lys, acq):
        step(ax, lx, y - bh, lw, bh, h1, h2, ACQ_FC, ACQ_EC)
    for i in range(3):
        arrow(ax, lx + lw / 2, lys[i] - bh, lx + lw / 2, lys[i + 1] + 0.005)

    ret = [
        ("Clients and harnesses", "shared chat interface"),
        ("MCP + lane policy", "95 tools, twelve groups"),
        ("Candidate retrieval", "search · librarian · hybrid"),
        ("Content-verification gate (C2)", "reads fetched text · fail-closed"),
        ("Answer or not-found (C3)", "cited evidence · searched scope"),
    ]
    for y, (h1, h2) in zip(rys, ret):
        if h1.startswith("Content-ver"):
            fc, ec = GATE_FC, GATE_EC
        elif h1.startswith("Answer"):
            fc, ec = TERM_FC, TERM_EC
        else:
            fc, ec = RET_FC, RET_EC
        step(ax, rx, y - bh, rw, bh, h1, h2, fc, ec)
    for i in range(4):
        arrow(ax, rx + rw / 2, rys[i] - bh, rx + rw / 2, rys[i + 1] + 0.005)

    # the two authoritative stores, aligned with the retrieval steps they feed
    store_y = (rys[2] - bh / 2, rys[3] - bh / 2)
    step(ax, mx, store_y[0] - 0.24, mw, 0.48, "Knowledge-base records",
         "document files ·\ntree · YAML", STORE_FC, STORE_EC)
    step(ax, mx, store_y[1] - 0.24, mw, 0.48, "Search indices",
         "Chroma · BM25 ·\nNeo4j", STORE_FC, STORE_EC)

    arrow(ax, lx + lw + 0.01, lys[2] - bh / 2, mx - 0.01, store_y[0])
    arrow(ax, lx + lw + 0.01, lys[3] - bh / 2, mx - 0.01, store_y[1])
    arrow(ax, mx + mw + 0.01, store_y[0], rx - 0.01, rys[2] - bh / 2)
    arrow(ax, mx + mw + 0.01, store_y[1], rx - 0.01, rys[3] - bh / 2)

    note(ax, mx + mw / 2, store_y[0] + 0.36, "candidate sources", C["dgrey"])
    note(ax, mx + mw / 2, store_y[1] - 0.38, "fetched content", C["dgrey"])

    ax.text(0.05, 0.31,
            "Contracts.  C1 placement — the parsed body, not the filename, decides\n"
            "the library, its description and its tags.  C2 admission — a candidate\n"
            "becomes evidence only after the server fetches and scores its text.\n"
            "C3 absence — an explicit not-found report naming the scope searched.",
            ha="left", va="center", fontsize=FS, color="#222222", zorder=6,
            linespacing=1.35)

    figmod.OUT = TARGET
    save(fig, "fig1_architecture")


# ===========================================================================
# Fig. 2 --- three lanes over one verification gate
# ===========================================================================
def fig2():
    H = 3.52
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    bh, gap = 0.40, 0.16
    qx, qw = 2.63, 1.70
    qc = qx + qw / 2                       # 3.48 -- the column centre of the page

    # query sits 0.03 higher than it needs so the fan-out arrows keep a
    # visible shaft before they stop on the band top edges (3.04 + 0.005)
    step(ax, qx, 3.13, qw, 0.36, "User query", "natural language",
         GREY_FC, GREY_EC)

    lanes = [
        (0.05, "Lane A — Search", RET_FC, RET_EC, [
            ("1  Rewrite", "subject · attribute · constraints"),
            ("2  Wide dense net", "top-30, threshold 0.35"),
            ("3  Judge", "batches of 6, server-fetched"),
        ]),
        (2.38, "Lane B — Librarian", ACQ_FC, ACQ_EC, [
            ("1  Catalog ladder", "root, sub-KBs, budgeted pages"),
            ("2  Query-shape routing", "literal: scanner; semantic: judge"),
            ("3  Judge", "batches of 6, fail-closed"),
        ]),
        (4.71, "Lane C — Hybrid", STORE_FC, STORE_EC, [
            # lane steps are numbered, not lettered: C1-C3 are the
            # manuscript's design-contract IDs and must stay unambiguous.
            ("1  Server call", "vector top-30 + catalog"),
            ("2  Merge and cap", "agreed-by-both first; cap 12"),
            ("3  Judge and cut", "0.5 threshold; top-5 read"),
        ]),
    ]
    for x, title, fc, ec, steps in lanes:
        band(ax, x, 1.16, 2.20, 1.88, title, ec)
        for i, (h1, h2) in enumerate(steps):
            y = 2.74 - i * (bh + gap)
            step(ax, x + 0.09, y - bh, 2.02, bh, h1, h2, fc, ec)
            if i:
                arrow(ax, x + 1.10, y + gap, x + 1.10, y + 0.005)
        # stop on the band top edge: an endpoint inside the band drives the
        # shaft through the title row (the "Lane B — Librarian" collision)
        arrow(ax, qc, 3.13, x + 1.10, 3.04 + 0.005)

    # gate
    step(ax, qx, 0.62, qw, 0.40, "Content-verification gate",
         "reads content, votes; fail-closed", GATE_FC, GATE_EC)
    for x in (0.05, 2.38, 4.71):
        arrow(ax, x + 1.10, 1.14, qc, 1.04)

    # terminals
    step(ax, 0.05, 0.06, 2.20, 0.40, "Not-found report",
         "searched scope + blind spots", GREY_FC, GREY_EC)
    step(ax, 4.71, 0.06, 2.20, 0.40, "Grounded answer",
         "reads top-5 in full; cites P0–P2", TERM_FC, TERM_EC)
    arrow(ax, 2.90, 0.62, 1.30, 0.47, color=GATE_EC, ls=(0, (3, 2)))
    arrow(ax, 4.06, 0.62, 5.70, 0.47, color=TERM_EC)

    note(ax, 1.55, 0.70, "zero verified evidence", GATE_EC, ha="left")
    note(ax, 6.10, 0.74, "survivors", TERM_EC, ha="left")

    figmod.OUT = TARGET
    save(fig, "fig2_lanes")


# ===========================================================================
# Fig. 3 --- tool-layer retrieval over the industrial corpus
# ---------------------------------------------------------------------------
# Placed at ``width=\columnwidth`` = 252.0 pt = 3.50 in, so the canvas IS
# 3.50 in and the LaTeX scale factor is 1.00.  The previous version was drawn
# on a 5.38 in canvas and scaled by 0.648, which put its 8 pt labels on the
# page at 5.19 pt.
#
# The two panels are STACKED rather than set side by side.  At 3.50 in total a
# side-by-side split leaves the panels about 2.1 in and 1.3 in wide, and seven
# method labels collide in either of those even rotated -- the original source
# recorded exactly that ("7 method names at 8 pt collide in a 3 in panel"):
# it rotated instead of thinning them out so every bar keeps its method label.
# Stacking gives each panel the full column width and preserves that choice.
# ===========================================================================
W3, H3 = 3.50, 4.90


def fig3():
    summary = json.loads(
        (RESULTS / "exp1_summary.json").read_text(encoding="utf-8"))
    s = summary["summary"]
    order = ["bm25", "dense", "rrf", "graph", "twostage", "fusion_only",
             "qdcvr_hybrid"]
    # short tick labels: the method names live in the caption instead
    labels = ["BM25", "Dense", "RRF", "Graph", "2-stg", "Fusion", "QDCVR-H"]
    colors = [C["grey"], C["sky"], C["blue"], C["pink"], C["yellow"],
              C["orange"], C["green"]]
    x = list(range(len(order)))

    fig, (a1, a2) = plt.subplots(2, 1, figsize=(W3, H3), layout="constrained")

    w = 0.26
    for k, (metric, mname) in enumerate([("hit@5", "Hit@5"),
                                         ("recall@5", "Recall@5"),
                                         ("mrr", "MRR")]):
        vals = [s[m][metric] for m in order]
        a1.bar([i + (k - 1) * w for i in x], vals, width=w, label=mname,
               color=[C["blue"], C["sky"], C["green"]][k],
               edgecolor="white", linewidth=0.4)
    a1.set_xticks(x)
    a1.set_xticklabels(labels, rotation=32, ha="right", rotation_mode="anchor")
    a1.set_ylabel("Score (mean over 16 questions)")
    a1.set_ylim(0, 1.34)
    a1.set_yticks([0.0, 0.5, 1.0])
    a1.legend(frameon=False, loc="upper left", ncol=3,
              columnspacing=0.8, handlelength=1.0, handletextpad=0.4,
              borderaxespad=0.1, borderpad=0.0)
    a1.tick_params(length=2, pad=1.5)
    hide_top_right(a1, left=True)
    a1.set_title("(a) Effectiveness", loc="left")

    lats = [max(s[m]["latency_mean"], 0.001) for m in order]
    a2.bar(x, lats, color=colors, edgecolor="white", linewidth=0.4)
    a2.set_yscale("log")
    # The decade labels are plain decimals ("0.001", "0.1", "1"): the 10^k
    # mathtext form renders the exponent at 0.7 x the base size, i.e. a 5.6 pt
    # superscript in the PDF, which is exactly what the artwork audit rejects.
    # The minor labels are dropped for the same reason plus a layout one:
    # constrained_layout reserves no room for minor tick labels.
    a2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:g}"))
    a2.yaxis.set_minor_formatter(mticker.NullFormatter())
    a2.set_xticks(x)
    a2.set_xticklabels(labels, rotation=32, ha="right", rotation_mode="anchor")
    a2.set_ylabel("Latency (log scale)")
    a2.set_ylim(0.0005, 6.0)
    for xi, v in zip(x, lats):
        # every bar is labelled in milliseconds -- a seconds label on the
        # slowest bar next to millisecond siblings read as a 0.5-vs-62 gap.
        lbl = f"{v * 1000:.0f}"
        a2.text(xi, v * 1.45, lbl, ha="center", color="#333333")
    a2.tick_params(length=2, pad=1.5)
    hide_top_right(a2, left=True)
    a2.set_title("(b) Latency per call (ms)", loc="left")

    figmod.OUT = TARGET
    save(fig, "fig3_retrieval")


# ===========================================================================
# Fig. 10 --- ten-question six-method matrix (tab:e4-matrix)
# ---------------------------------------------------------------------------
# Placed at ``width=0.86\textwidth`` = 0.86 x 7.25 = 6.24 in, so the canvas is
# 6.24 in.  This figure had NO generator anywhere in the repository; it is
# rebuilt here from the six rows of ``tab:e4-matrix``.  Two of its defects are
# fixed by rebuilding rather than scaling:
#
#   * it embedded DejaVuSans, which is not on the Elsevier artwork font list
#     (Arial/Helvetica/Courier/Symbol/Times/Times New Roman); it is drawn here
#     under figures.py's Arial + Type-42 contract;
#   * it was scaled by 0.570, putting its 8 pt labels on the page at 4.56 pt.
#
# The BM25, Dense and RRF wall clocks are 0.05-0.1 s, i.e. invisible beside
# 33.1 s, so their values are written out instead of being read off bar height
# (the previous figure did the same); the bars themselves are kept so the
# three baselines stay in the comparison.
# ===========================================================================
W10, H10 = 6.24, 2.55

MODE_LABELS = ["Mode\nA", "Mode\nB", "Mode\nC", "BM25", "Dense", "RRF"]
MODE_RECALL = [10, 7, 9, 10, 10, 10]                  # gold docs of ten
MODE_LATENCY = [19.8, 14.0, 33.1, 0.05, 0.1, 0.05]    # s, mean per question


def fig10():
    fig, (a1, a2) = plt.subplots(
        1, 2, figsize=(W10, H10),
        gridspec_kw={"width_ratios": [1.0, 1.08]}, layout="constrained")
    x = list(range(len(MODE_LABELS)))
    # the three tool-layer modes carry the accent colours, the three lexical /
    # dense baselines stay grey -- the same split fig3_retrieval uses.
    cols = [C["green"], C["verm"], C["blue"], C["grey"], C["grey"], C["grey"]]

    a1.bar(x, MODE_RECALL, width=0.66, color=cols, edgecolor="white",
           linewidth=0.4)
    for xi, v in zip(x, MODE_RECALL):
        a1.text(xi, v + 0.30, f"{v}/10", ha="center", color="#333333")
    a1.set_xticks(x)
    a1.set_xticklabels(MODE_LABELS)
    a1.set_ylabel("Gold recall (of 10)")
    a1.set_ylim(0, 12.4)
    a1.set_yticks([0, 2, 4, 6, 8, 10])
    a1.tick_params(length=2, pad=1.5)
    hide_top_right(a1, left=True)
    a1.set_title("(a) Document-level gold recall", loc="left")

    a2.bar(x, MODE_LATENCY, width=0.66, color=cols, edgecolor="white",
           linewidth=0.4)
    for xi, v in zip(x, MODE_LATENCY):
        a2.text(xi, v + 1.45, f"{v}s", ha="center", color="#333333")
    a2.set_xticks(x)
    a2.set_xticklabels(MODE_LABELS)
    a2.set_ylabel("Latency (s)")
    a2.set_ylim(0, 38.0)
    a2.set_yticks([0, 10, 20, 30])
    a2.tick_params(length=2, pad=1.5)
    hide_top_right(a2, left=True)
    a2.set_title("(b) Mean wall clock per question", loc="left")

    figmod.OUT = TARGET
    save(fig, "fig10_mode_matrix")


if __name__ == "__main__":
    TARGET.mkdir(parents=True, exist_ok=True)
    fig1()
    fig2()
    # fig3_retrieval moved to figures.py:fig_retrieval (single effectiveness
    # panel at column width) on 2026-10-16; fig10_mode_matrix was dropped from
    # the manuscript because Table tab:e4-matrix carries the same six methods.
    print(f"wrote to {TARGET}")
