#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Publication figures for the KBS submission (QDCVR platform).

Typography contract (Elsevier artwork requirement)
--------------------------------------------------
Every figure is drawn at EXACTLY the width at which the manuscript places it,
so the LaTeX ``\\includegraphics`` scale factor is 1.0 and the point size set
here is the point size the reader sees:

    full width (``width=\\textwidth``, 13.67 cm)...... 5.38 in
    fig4_inflation (``width=0.5\\textwidth``).......... 2.69 in
    fig7_ood (``width=0.62\\textwidth``)............... 3.34 in

No text is drawn below ``_MIN_FS`` = 8.0 pt.  Everything stays vector: no
``rasterized=True``, no images, Type-42 (TrueType) fonts only.

Because the canvases are now much smaller than the old ones, the layouts were
re-tuned rather than merely re-fonted: shorter axis labels, fewer tick labels,
legends moved inside the axes, tighter ``constrained_layout`` spacing and, for
the two box-and-arrow diagrams (fig1, fig2), a rebuilt internal grid.

Style: Okabe-Ito colorblind-safe palette, sans-serif, 300 dpi PNG + vector PDF.
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Patch
from matplotlib.textpath import TextPath

# ---------------------------------------------------------------------------
# Global typography / line-art settings
# ---------------------------------------------------------------------------
FONT = "Arial"           # Elsevier's artwork list; single family everywhere
_MIN_FS = 8.0            # hard floor for every text object in every figure
_FS = 8.0                # standard body size

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": [FONT, "Helvetica", "Liberation Sans", "DejaVu Sans"],
    "font.size": _FS,
    "axes.labelsize": _FS,
    "axes.titlesize": _FS,
    "xtick.labelsize": _FS,
    "ytick.labelsize": _FS,
    "legend.fontsize": _FS,
    "axes.linewidth": 0.6,
    "axes.edgecolor": "#444444",
    "lines.linewidth": 1.0,
    "lines.markersize": 3.0,
    "patch.linewidth": 0.6,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "xtick.major.size": 2.0,
    "ytick.major.size": 2.0,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.0,       # no 0.1 in shim: the PDF page WIDTH is
                                     # what the audit scales against, so a
                                     # padded page would shrink every glyph
    "savefig.dpi": 300,
    "figure.dpi": 150,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "pdf.compression": 6,
    # math is only used by log-axis minor ticks and unit labels: keep it in the
    # same Arial face so the PDF embeds exactly one family (Elsevier list).
    "mathtext.fontset": "custom",
    "mathtext.default": "regular",
    "mathtext.rm": FONT,
    "mathtext.it": FONT + ":italic",
    "mathtext.bf": FONT + ":bold",
    "mathtext.sf": FONT,
    "mathtext.tt": FONT,
})

C = {"blue": "#0072B2", "orange": "#E69F00", "green": "#009E73",
     "verm": "#D55E00", "pink": "#CC79A7", "sky": "#56B4E9",
     "yellow": "#F0E442", "black": "#000000", "grey": "#8C8C8C",
     "lgrey": "#E8E8E8", "dgrey": "#555555"}

# ---------------------------------------------------------------------------
# Shared data-figure grammar (SCI style)
# ---------------------------------------------------------------------------
# Colour encodes a role, never a method's identity, and the same role keeps the
# same colour in every figure: the system's promoted behaviour is blue, a
# failure is vermillion, a baseline or context series is grey. Metric triples use
# one hue as a light-to-dark ramp so that a legend can be read without a colour
# key. Bars carry direct value labels and no frame; there is no top/right spine
# and no grid, because every plotted value is labelled or countable.
SEM = {"system": C["blue"], "failure": C["verm"], "recovered": C["green"],
       "baseline": "#B8B8B8", "secondary": C["orange"], "context": "#D9D9D9"}
RAMP = ["#A6CEE3", "#4A90C2", "#08519C"]      # light -> dark for metric triples

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "experiments" / "results"
OUT = HERE

# placed widths (inches), taken from the \includegraphics calls in paper-kbs/tex
W_FULL = 5.38            # 13.67 cm  (\textwidth)
W_COL = 3.50             #  8.89 cm  (\columnwidth)
W_HALF = 2.69            #  6.83 cm  (0.5\textwidth)
W_OOD = 3.34             #  8.47 cm  (0.62\textwidth)

# DejaVu Sans average advance width per point of font size.  ``tw`` measures
# the real outline; _CPT is only the first-pass estimate used while laying out.
_CPT = 0.63


def tw(s: str, fs: float = _FS) -> float:
    """Rendered width of the widest line of *s*, in inches, at font size *fs*.

    Measured from the actual font outlines (``TextPath``) so that the
    hand-placed diagrams can be laid out against the true advance widths
    instead of a guess; the longest line wins because these labels are centred.
    """
    if fs <= 0 or not s.strip():
        return 0.0
    tp = TextPath((0, 0), s, size=fs, prop=FontProperties(family=FONT))
    return tp.get_extents().width / 72.0


def _enforce_min_fonts(fig):
    """Raise every text object below ``_MIN_FS`` up to the floor.

    Matplotlib itself draws a few labels smaller than the configured size —
    log-axis minor tick labels come out at 0.7 x ``ytick.labelsize`` (5.6 pt at
    our 8 pt base), which silently broke the Elsevier 8 pt rule on the
    latency panel of fig 3.  Rather than hunt each case, the floor is enforced
    on the finished figure, right before it is drawn and measured.
    """
    for t in fig.findobj(matplotlib.text.Text):
        if not t.get_text().strip():
            continue
        if t.get_fontsize() < _MIN_FS - 1e-9:
            t.set_fontsize(_MIN_FS)


def save(fig, name):
    """Write vector PDF + 300 dpi PNG at exactly the designed canvas size.

    The page is pinned to the designed canvas: with ``savefig.bbox = "tight"``
    matplotlib would crop the page to the drawn ink, so the exported page is
    never the size the figure was designed at -- the LaTeX placement then
    scales it by an unknown factor (that is exactly how the original artwork
    ended up at 5.3 pt).  ``bbox_inches`` must be given explicitly because
    ``None`` falls back to the "tight" rcParam.  ``_check_overflow`` and
    ``_assert_page_size`` prove nothing was clipped by giving up the crop.
    """
    _enforce_min_fonts(fig)
    fig.canvas.draw()
    # Tick Text objects are (re)created inside the draw, so a second pass is
    # needed: without it a log-axis minor label stayed at 5.6 pt and the
    # audit read exactly that on fig 3.
    _enforce_min_fonts(fig)
    fig.canvas.draw()
    _check_overflow(fig, name)
    _BOX_GUARDS.clear()
    box = fig.bbox_inches            # the full canvas, in inches
    fig.savefig(OUT / f"{name}.pdf", bbox_inches=box)
    fig.savefig(OUT / f"{name}.png", dpi=300, bbox_inches=box)
    _assert_page_size(fig, name)
    plt.close(fig)
    print(f"saved {name}.pdf/.png")


def _assert_page_size(fig, name, tol=0.012):
    """The exported page must be exactly the designed canvas.

    ``savefig.bbox = "tight"`` crops to the drawn ink, so a stray label pushes
    the page off the designed size -- and the placement scale the Elsevier rule
    depends on silently changes with it.  Measuring the PDF itself is the only
    check that sees the real page.
    """
    import pymupdf

    W, H = fig.get_size_inches()
    with pymupdf.open(OUT / f"{name}.pdf") as doc:
        r = doc[0].rect
    w, h = r.width / 72.0, r.height / 72.0
    if abs(w - W) > tol or abs(h - H) > tol:
        raise AssertionError(
            f"{name}: page {w:.3f}x{h:.3f} in != designed {W:.3f}x{H:.3f} in")


def _check_overflow(fig, name):
    """Fail loudly if any text leaves the canvas (it would be clipped).

    Everything drawn here is placed by hand or by ``constrained_layout``, and
    a clipped label is unrecoverable in print, so a hard assert is cheaper than
    spotting it in a thumbnail.  Runs at figure-dpi, i.e. on the same geometry
    that goes to the PDF.

    Tick labels whose tick lies outside the view interval are exempt: they keep
    a position (extrapolated by the transform) but are never drawn, and
    matplotlib's own layout pass ignores them too.
    """
    r = fig.canvas.get_renderer()
    W, H = fig.get_size_inches()
    undrawn = set()
    for ax in fig.axes:
        labels = (list(ax.get_xticklabels()) + list(ax.get_yticklabels())
                  + list(ax.get_xticklabels(minor=True))
                  + list(ax.get_yticklabels(minor=True))
                  + [ax.xaxis.get_offset_text(), ax.yaxis.get_offset_text()])
        tb = ax.get_tightbbox(r)
        for t in labels:
            if tb is None:
                continue
            bb = t.get_window_extent(r)
            if not (tb.x0 - 1 <= bb.x0 and bb.x1 <= tb.x1 + 1
                    and tb.y0 - 1 <= bb.y0 and bb.y1 <= tb.y1 + 1):
                undrawn.add(id(t))
    bad = []
    for a in fig.findobj(matplotlib.text.Text):
        if not a.get_text().strip() or not a.get_visible():
            continue
        if id(a) in undrawn:
            continue
        bb = a.get_window_extent(r)
        x0, x1 = bb.x0 / fig.dpi, bb.x1 / fig.dpi
        y0, y1 = bb.y0 / fig.dpi, bb.y1 / fig.dpi
        if x0 < -0.01 or x1 > W + 0.01 or y0 < -0.01 or y1 > H + 0.01:
            bad.append(("outside canvas: " + a.get_text()[:40].replace("\n", "|"),
                        x0, x1, y0, y1))
    for artist, ax, x, y, w, h in _BOX_GUARDS:
        if artist.figure is not fig:
            continue
        bb = artist.get_window_extent(r)
        p = ax.transData.transform
        px0, py0 = p((x, y))
        px1, py1 = p((x + w, y + h))
        if bb.x0 < min(px0, px1) - 0.5 or bb.x1 > max(px0, px1) + 0.5 \
                or bb.y0 < min(py0, py1) - 0.5 or bb.y1 > max(py0, py1) + 0.5:
            bad.append(("overflows its box: "
                        + artist.get_text()[:40].replace("\n", "|"),
                        bb.x0 / fig.dpi, bb.x1 / fig.dpi,
                        bb.y0 / fig.dpi, bb.y1 / fig.dpi))
            if _DEBUG_FIT:
                print(f"     box x[{min(px0, px1):.1f},{max(px0, px1):.1f}] "
                      f"y[{min(py0, py1):.1f},{max(py0, py1):.1f}]")
    if bad:
        for t, x0, x1, y0, y1 in bad:
            print(f"  !! {name}: {t}  bbox x[{x0:.3f},{x1:.3f}] "
                  f"y[{y0:.3f},{y1:.3f}]  canvas {W:.2f}x{H:.2f}")
        raise AssertionError(f"{name}: {len(bad)} text object(s) do not fit "
                             f"their {W:.2f}x{H:.2f} in canvas")


def box(ax, x, y, w, h, text, fc="#FFFFFF", ec="#444444", fs=_FS,
        lw=0.6, bold=False, style=None, tc="#111111", zorder=3):
    if style is None:
        r = min(0.05, 0.125 * min(w, h))
        style = f"round,pad=0.02,rounding_size={r:.4f}"
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=style,
                                fc=fc, ec=ec, lw=lw, zorder=zorder))
    t = ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
                fontsize=fs, color=tc, zorder=zorder + 1,
                fontweight="bold" if bold else "normal", linespacing=1.18)
    _guard(ax, t, x, y, w, h)
    return (x + w / 2, y + h / 2)


_BOX_GUARDS = []
_DEBUG_FIT = False


def _guard(ax, artist, x, y, w, h, pad=0.006):
    """Record an artist that must stay inside the box it was drawn for.

    The canvases here are drawn at their final size, so a label that is one
    character too wide is silently clipped by the axes at save time.  The
    overflow check in ``save()`` turns that into a hard error instead of a
    mangled figure.  ``pad`` is a hair of slack for the ink extents.
    """
    _BOX_GUARDS.append((artist, ax, x + pad, y + pad, w - 2 * pad, h - 2 * pad))


def arrow(ax, x1, y1, x2, y2, color="#555555", lw=0.8, style="-|>",
          ms=5, zorder=2, ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                                 mutation_scale=ms, color=color, lw=lw,
                                 linestyle=ls, zorder=zorder,
                                 shrinkA=1, shrinkB=1))


def hide_top_right(ax, left=False):
    for sp in (("top", "right") if not left else ("top", "right", "left")):
        ax.spines[sp].set_visible(False)


def origin_axes(ax, minor=True):
    """Origin-style data frame: all four spines, inward major and minor ticks.

    Origin's default 2D graph has a closed box and ticks that point into the
    plotting area on every side; labels stay on the left and bottom. The KBS
    artwork rule is unaffected because no text size changes.
    """
    for sp in ax.spines.values():
        sp.set_visible(True)
        sp.set_linewidth(0.8)
        sp.set_color("#222222")
    ax.tick_params(axis="both", which="major", direction="in", top=True,
                   right=True, length=3.0, width=0.8, pad=2.0)
    if minor:
        ax.minorticks_on()
        ax.tick_params(axis="both", which="minor", direction="in", top=True,
                       right=True, length=1.6, width=0.6)


# ===========================================================================
# Fig 1 —platform architecture (full width, 13.67 cm = 5.38 in)
# ---------------------------------------------------------------------------
# Canvas coordinates are INCHES (xlim 0..5.38, ylim 0..6.90).  Every box was
# laid out against the measured DejaVu ink widths (``tw``): the widest label on
# the canvas is ".knowledge-base.yml" at 1.16 in, so the 4-up bands run at
# 4 x 1.24 + 3 x 0.185 = 5.02 in (0.495 in in from each edge) and the 3-up
# bands at 3 x 1.56 + 2 x 0.17 = 5.02 in.  That measurement is what fixed the
# column pitch and forced the longest labels onto their short forms (the
# caption spells out "svc" = service, "Doc files" = the parsed markdown plus
# its extracted images, "Lib metadata" = the per-library index).
# Nothing on this canvas is smaller than 8 pt.
# ===========================================================================
def fig_architecture():
    """Four stacked layers + acquisition, organization/life-cycle and the
    pollable-task / content-verification side flows (paper-kbs §3.3)."""
    H = 7.35
    fig = plt.figure(figsize=(W_FULL, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_FULL)
    ax.set_ylim(0, H)
    ax.axis("off")

    def panel(x, y, w, h, title, detail=None, fc="#FFFFFF", ec=C["dgrey"],
              tt="#111111", dt="#333333", bold=False, lw=0.6, z=3, fs=_FS,
              dfs=_FS):
        """Thin-edged rectangle: title line plus an optional detail line."""
        ax.add_patch(FancyBboxPatch(
            (x, y), w, h, boxstyle="square,pad=0.0",
            fc=fc, ec=ec, lw=lw, zorder=z))
        if detail:
            lh = 0.066
            a = ax.text(x + w / 2, y + h / 2 + lh, title, ha="center",
                        va="center", fontsize=fs, color=tt, zorder=z + 1,
                        fontweight="bold" if bold else "normal")
            b = ax.text(x + w / 2, y + h / 2 - lh, detail, ha="center",
                        va="center", fontsize=dfs, color=dt, zorder=z + 1)
            _guard(ax, a, x, y, w, h)
            _guard(ax, b, x, y, w, h)
        else:
            a = ax.text(x + w / 2, y + h / 2, title, ha="center", va="center",
                        fontsize=fs, color=tt, zorder=z + 1,
                        fontweight="bold" if bold else "normal",
                        linespacing=1.15)
            _guard(ax, a, x, y, w, h)

    def cband(y, h, title, fc="#F7F7F7", ec="#BBBBBB", tfs=_FS):
        """Grouping container with the heading inside the top-left corner."""
        ax.add_patch(FancyBboxPatch(
            (0.30, y), W_FULL - 0.34, h, boxstyle="square,pad=0.0",
            fc=fc, ec=ec, lw=0.6, zorder=1))
        a = ax.text(0.36, y + h - 0.05, title, fontsize=tfs, color="#5F5F5F",
                    style="italic", ha="left", va="top", zorder=5)
        _guard(ax, a, 0.33, y, W_FULL - 0.66, h)

    # column grids, measured rather than guessed --------------------------
    # both grids start at x = 0.36 and end at 5.28, i.e. inside the 0.30-5.34
    # container bands, so the outermost boxes never overrun a band edge.
    W4 = (5.28 - 0.36 - 3 * 0.2325) / 4          # 4-up: 4 x 1.0556 + 3 gaps
    X4 = tuple(0.36 + i * (W4 + 0.2325) for i in range(4))
    W3 = (5.28 - 0.36 - 2 * 0.17) / 3            # 3-up: 3 x 1.5267 + 2 gaps
    X3 = tuple(0.36 + i * (W3 + 0.17) for i in range(3))
    XC3 = [x + W3 / 2 for x in X3]

    # ---- client and agent layer (top) ------------------------------------
    cband(6.63, 0.66, "Client and agent layer")
    cli = [("Web interface", "Nuxt 3 UI"),
           ("Chat harness", "endpoint adapter"),
           ("Lane policy", "attached server-side")]
    for x, (t, d) in zip(X3, cli):
        panel(x, 6.73, W3, 0.34, t, d, fc="#EDF3FA", ec=C["blue"])

    # ---- tool layer (one MCP server, 95 tools in eight groups) -----------
    cband(4.54, 1.96, "Tool layer")
    ax.add_patch(FancyBboxPatch(
        (0.36, 6.06), W_FULL - 0.54, 0.22, boxstyle="square,pad=0.0",
        fc="#F3EEF8", ec="#7A6FA0", lw=0.6, zorder=3))
    a = ax.text(W_FULL / 2, 6.17,
                "MCP server (kb-mcp) \u2014 95 tools in eight groups",
                ha="center", va="center", fontsize=_FS, color="#111111",
                fontweight="bold", zorder=4)
    _guard(ax, a, 0.36, 6.06, W_FULL - 0.54, 0.22)
    tools = [("Knowledge base", "CRUD and catalog"),
             ("Document read", "/ write"),
             ("File system", "tree and images"),
             ("Parsing", "task status"),
             ("Search", "vector index"),
             ("Tags", "registry"),
             ("Knowledge graph", "documents"),
             ("Experience", "persona")]
    for i, (t, d) in enumerate(tools):
        r, c = divmod(i, 4)
        panel(X4[c], 5.56 - r * 0.48, W4, 0.36, t, d,
              fc="#F3EEF8", ec="#7A6FA0")
    panel(X4[0], 4.64, W4, 0.28, "Lane policy", "server-side filter",
          fc="#FAF7FC", ec="#7A6FA0")
    panel(X4[2], 4.64, W4, 0.28, "Long-running work", "pollable tasks",
          fc="#FAF7FC", ec="#7A6FA0")
    for x in XC3:                                 # client -> tool layer
        arrow(ax, x, 6.73, x, 6.52, lw=0.8)

    # ---- domain service layer -------------------------------------------
    cband(3.23, 1.18, "Domain service layer")
    svc = [("Tree registry", "tree and catalog"),
           ("Parse scheduler", "supervises OCR"),
           ("Vector service", "chunk vectors"),
           ("Candidates", "two-stage search"),
           ("Experience svc", "cases and ratings"),
           ("Graph service", "document links"),
           ("Judging worker", "resident, cached"),
           ("Content checks", "quotes and units")]
    for i, (t, d) in enumerate(svc):
        r, c = divmod(i, 4)
        panel(X4[c], 3.83 - r * 0.50, W4, 0.36, t, d,
              fc="#FDF1EC", ec=C["verm"])

    # ---- storage layer ---------------------------------------------------
    cband(2.42, 0.68, "Storage layer")
    stores = [("Document tree", ".tree-fs.json"),
              ("Vector store", "1024-d HNSW"),
              ("Graph database", "libraries, tags"),
              ("Work DBs", "parse, index, chat")]
    for x, (t, d) in zip(X4, stores):
        panel(x, 2.52, W4, 0.36, t, d, fc="#F2F2F2", ec=C["dgrey"])

    # ---------- runtime call path: tools -> services -> storage -----------
    for y1, y2 in ((4.54, 4.52), (3.23, 3.20)):
        arrow(ax, W_FULL / 2, y1, W_FULL / 2, y2, lw=0.8)

    # =====================================================================
    # (a) Acquisition pipeline —feeds the storage layer from below
    # =====================================================================
    cband(1.03, 1.26, "Acquisition pipeline")
    y1, y2 = 1.73, 1.13                          # top row, wrap-around row
    steps = [("Raw documents", "Office, PDF"), ("Parse", "MinerU OCR"),
             ("Quality gate", "post-checks"), ("Split", "structure-aware"),
             ("Describe, tag", "content-derived"), ("Index", "retrievability")]
    for i, (t, d) in enumerate(steps):
        panel(X4[i % 4], y1 if i < 4 else y2, W4, 0.34, t, d,
              fc="#FFFFFF", ec=C["blue"])
    for i in range(3):
        arrow(ax, X4[i] + W4, y1 + 0.17, X4[i + 1], y1 + 0.17, lw=0.8)
    arrow(ax, X4[3] + W4 / 2, y1, X4[3] + W4 / 2, 1.60, lw=0.8)
    arrow(ax, X4[3] + W4 / 2, 1.60, X4[0] + W4 / 2, 1.60, lw=0.8)
    arrow(ax, X4[0] + W4 / 2, 1.60, X4[0] + W4 / 2, y2, lw=0.8)
    arrow(ax, X4[0] + W4, y2 + 0.17, X4[1], y2 + 0.17, lw=0.8)
    arrow(ax, X4[1] + W4, y2 + 0.17, X4[2], y2 + 0.17, lw=0.8)
    # failure branch: the quality gate rejects visibly instead of storing
    panel(X4[3], y2, W4, 0.34, "Reject visibly", "not stored",
          fc="#FBEDEA", ec=C["verm"])
    arrow(ax, X4[2] + W4 / 2, y1, X4[2] + W4 / 2, y2 + 0.34, lw=0.8,
          color=C["verm"])
    ax.text(X4[2] + W4 / 2 + 0.04, y2 + 0.215, "fails", fontsize=_FS,
            color=C["verm"], ha="left", va="center", zorder=6,
            bbox=dict(fc="white", ec="none", alpha=0.9, pad=0.15))
    # the pipeline hands its documents to the storage layer
    ax.text(0.10, 1.62, "documents", fontsize=_FS, color=C["grey"],
            ha="center", va="center", rotation=90, zorder=6,
            fontweight="bold")
    arrow(ax, 0.20, 1.46, 0.20, 2.70, lw=0.8, color=C["grey"])
    # =====================================================================
    # (b) Organization and life-cycle management —three-source agreement
    # =====================================================================
    cband(0.00, 0.96, "Organization and life-cycle management")
    org = [("Tree registry", ".tree-fs.json"),
           ("Doc files", "markdown, images"),
           ("Lib metadata", ".knowledge-base.yml")]
    for i, (t, d) in enumerate(org):
        panel(X3[i], 0.32, W3, 0.28, t, d, fc="#FFFFFF", ec=C["dgrey"])
        if i < 2:
            arrow(ax, X3[i] + W3 + 0.04, 0.46, X3[i + 1] - 0.04, 0.46,
                  lw=0.7, style="<|-|>", ms=4)
    a = ax.text(XC3[1], 0.13, "three-source agreement", fontsize=_FS,
                color=C["grey"], ha="center", va="center", zorder=6)
    _guard(ax, a, X3[1], 0.03, W3, 0.20)

    # Full-bleed canvas saved as-is: bbox_inches="tight" would crop to the
    # drawn ink and stretch it back, pushing the outermost band corners onto
    # the page edge.  Saving without the tight bbox keeps the designed
    # 5.38 x 7.35 in canvas and its intended margins (and its 1.0 scale).
    save(fig, "fig1_architecture")


# ===========================================================================
# Fig 2 —three-lane retrieval flow (full width, 13.67 cm = 5.38 in)
# ===========================================================================
def fig_lanes():
    """Three parallel retrieval lanes plus the fallback / not-found edges.

    Canvas coordinates are INCHES.  At 8 pt the 1.60 in lane columns hold at
    most ~27 characters per line, so each step label is hand-wrapped to four
    short lines (``|`` line breaks are explicit, never automatic: matplotlib
    would happily run a long line straight through the box edge).  The box
    rows are 0.56 in tall to carry those four lines, which is why the canvas
    is 3.87 in rather than the 3.6 in of the 6 pt original.
    """
    H = 3.87
    fig = plt.figure(figsize=(W_FULL, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_FULL)
    ax.set_ylim(0, H)
    ax.axis("off")

    COLW = 1.60
    CXS = [0.11, 1.89, 3.67]          # left edge of each lane column
    CTR = [x + COLW / 2 for x in CXS]

    box(ax, 1.88, 3.58, 1.62, 0.24, "User query (natural language)",
        fc="#EDF3FA", ec=C["blue"], bold=True, style="round,pad=0.0")

    heads = ["Lane A: Search", "Lane B: Librarian", "Lane C: Hybrid"]
    for x, h in zip(CXS, heads):
        box(ax, x, 3.24, COLW, 0.24, h, fc="#E8F5F1", ec=C["green"],
            style="round,pad=0.0")
    # fan-out from the query box
    ax.plot([2.69, 2.69], [3.58, 3.50], color="#555555", lw=0.8, zorder=2)
    ax.plot([CTR[0], CTR[2]], [3.50, 3.50], color="#555555", lw=0.8, zorder=2)
    for c in CTR:
        arrow(ax, c, 3.50, c, 3.26, lw=0.8)

    a_steps = [
        "A0  Query rewrite\nsubject \u00d7 attribute \u00d7\n"
        "constraints; experience-\nfirst for incidents",
        "A1  Dense wide net\ntop-30 chunks, thresh\n"
        "0.35, dedupe per doc,\ncross-KB balance",
        "A2  Judging gate\nbatches \u2264 6 refs; server\n"
        "fetches text; the verdict\nbeats the score",
        "A3  Evidence pack\nonly verified passages\n"
        "returned; confidence\nP0/P1/P2 per citation",
    ]
    b_steps = [
        "B0\u2013B1  Catalog scan\nKB list \u2192 per-shelf\nlisting; descriptions\n"
        "are claims, not facts",
        "B2  Query-shape routing\nliteral \u2192 machine\nenumeration; semantic\n"
        "\u2192 the judging path",
        "B3  Judging gate\nbatches \u2264 6 refs; 0.5\nsemantic and 0.3\n"
        "enumeration; fail-closed",
        "B4\u2013B5  Read + report\nfull text \u2265 500 chars;\nfive-part report incl.\n"
        "blind spots",
    ]
    c_steps = [
        "C1  Dual-lane candidates\nvector top-30 plus\nkeyword rank (one\n"
        "server-side call)",
        "C2  Merge and cap\ndedupe by (KB, doc);\nagreed first;\n"
        "candidate cap 12",
        "C3  Judge + relative cut\nverdicts kept \u2265 best \u221215\nwith a top-5 floor;\n"
        "anchor guard",
        "C4  Read top-5 in full\n\u2265 500 chars each \u2192\ngrounded answer with\n"
        "lane and score",
    ]
    ROWH, ROWSTEP, Y0 = 0.56, 0.66, 2.56
    for col_x, steps in zip(CXS, (a_steps, b_steps, c_steps)):
        y = Y0
        for i, s in enumerate(steps):
            box(ax, col_x, y, COLW, ROWH, s, fc="#FFFFFF", ec=C["green"],
                style="round,pad=0.0")
            if i < len(steps) - 1:
                arrow(ax, col_x + COLW / 2, y - 0.005,
                      col_x + COLW / 2, y - ROWSTEP + ROWH + 0.005, lw=0.8)
            y -= ROWSTEP
    ybot = Y0 - 3 * ROWSTEP                          # bottom row of boxes

    # A -> B fallback (zero survivors): dashed edge along the bottom
    axe = CTR[0]
    arrow(ax, axe, ybot, axe, 0.42, lw=0.9, color=C["verm"], ls=(0, (4, 2)))
    arrow(ax, axe, 0.42, CTR[1], 0.42, lw=0.9, color=C["verm"], ls=(0, (4, 2)))
    arrow(ax, CTR[1], 0.42, CTR[1], ybot - 0.005, lw=0.9, color=C["verm"],
          ls=(0, (4, 2)))
    ax.text(CTR[0] + 0.02, 0.34, "zero survivors", fontsize=_FS,
            color=C["verm"], ha="left", va="top", zorder=6)
    # B and C -> not-found
    arrow(ax, CTR[1], ybot, CTR[1], 0.20, lw=0.9, color=C["verm"])
    ax.text(CTR[1] + 0.06, 0.20, "not-found", fontsize=_FS, color=C["verm"],
            ha="left", va="center", zorder=6)
    arrow(ax, CTR[2], ybot, CTR[2], 0.20, lw=0.9, color=C["verm"])
    arrow(ax, CTR[2], 0.20, CTR[1] + 0.90, 0.20, lw=0.9, color=C["verm"])
    ax.text(CTR[2] + 0.06, 0.31, "still empty", fontsize=_FS, color=C["verm"],
            ha="left", va="center", zorder=6)
    save(fig, "fig2_lanes")


# ===========================================================================
# Fig 3 —Exp1 retrieval-layer results (full width)
# ===========================================================================
def fig_retrieval():
    summary = json.loads((RESULTS / "exp1_summary.json").read_text(encoding="utf-8"))
    s = summary["summary"]
    order = ["bm25", "dense", "rrf", "graph", "twostage", "fusion_only", "qdcvr_hybrid"]
    # short tick labels: the method names live in the caption instead
    labels = ["BM25", "Dense", "RRF", "Graph", "2-stage", "Fusion", "QDCVR-H"]

    # Effectiveness only, drawn at the column width the manuscript places it
    # at. Latency is reported in the table and the text; a second panel
    # repeating it would weight the platform's weakest property as heavily as
    # the retrieval quality it is meant to support.
    fig, ax = plt.subplots(figsize=(W_COL, 2.15), layout="constrained")
    x = list(range(len(order)))
    w = 0.26
    for k, (metric, mname) in enumerate([("hit@5", "Hit@5"),
                                         ("recall@5", "Recall@5"),
                                         ("mrr", "MRR")]):
        vals = [s[m][metric] for m in order]
        ax.bar([i + (k - 1) * w for i in x], vals, width=w, label=mname,
               color=RAMP[k], edgecolor="white", linewidth=0.4)
    ax.set_xticks(x)
    ax.set_xticklabels(["BM25", "Dense", "RRF", "Graph", "2-stg", "Fusion",
                        "QDCVR-H"], rotation=24, ha="right",
                       rotation_mode="anchor")
    ax.set_ylabel("Score (16 questions)")
    ax.set_ylim(0, 1.55)
    ax.set_yticks([0.0, 0.25, 0.5, 0.75, 1.0])
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.0),
              ncol=3, columnspacing=0.7, handlelength=1.0,
              handletextpad=0.35, borderaxespad=0.25, borderpad=0.0)
    origin_axes(ax)
    # mark the two configurations the paper's argument turns on
    ax.annotate("fusion", xy=(5, s["fusion_only"]["hit@5"]),
                xytext=(5, s["fusion_only"]["hit@5"] + 0.19), ha="center",
                color=C["dgrey"])
    ax.annotate("verdict", xy=(6, s["qdcvr_hybrid"]["hit@5"]),
                xytext=(6, s["qdcvr_hybrid"]["hit@5"] + 0.19), ha="center",
                color=SEM["failure"])
    save(fig, "fig3_retrieval")


# ===========================================================================
# Fig 4 —judge score inflation (0.5\textwidth = 2.69 in)
# ===========================================================================
def fig_inflation():
    data = json.loads((RESULTS / "exp1_retrieval.json").read_text(encoding="utf-8"))
    gold_scores, nongold_scores = [], []
    for row in data["rows"]:
        if row.get("method") != "qdcvr_hybrid" or "judge_scores" not in row:
            continue
        gold_scores += row["judge_scores"]["gold"]
        for p, sc in row["judge_scores"]["all"].items():
            if not any(g.lower() in p.lower()
                       for g in _gold_of(row["qid"])):
                nongold_scores.append(sc)

    rng = np.random.default_rng(7)
    fig, ax = plt.subplots(figsize=(W_HALF, 2.05), layout="constrained")
    for i, (vals, col, name) in enumerate([
            (gold_scores, SEM["system"], "Gold"),
            (nongold_scores, SEM["baseline"], "Non-gold")]):
        xs = rng.normal(i, 0.055, size=len(vals))
        ax.scatter(xs, vals, s=6, color=col, alpha=0.65, edgecolors="none",
                   label=name, zorder=3)
        ax.hlines(np.median(vals), i - 0.22, i + 0.22, color=col, lw=1.4,
                  zorder=4)
    ax.axhline(0.5, color=C["dgrey"], lw=0.8, ls="--")
    ax.text(1.80, 0.508, "accept 0.5", color=C["dgrey"], ha="right",
            va="bottom", zorder=5)
    ax.set_xticks([0, 1])
    ax.set_xticklabels([f"Gold docs\n(n = {len(gold_scores)})",
                        f"Non-gold\n(n = {len(nongold_scores)})"])
    ax.set_ylabel("Laya evidence score")
    ax.set_yticks([0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
    ax.set_ylim(0.42, 1.05)
    # A closed Origin frame clips anything drawn past the axes: reserve the
    # right margin for the two median labels and the threshold annotation.
    ax.set_xlim(-0.45, 1.85)
    ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(0.02, 0.99),
              markerscale=0.9, handletextpad=0.4, borderaxespad=0.15,
              borderpad=0.0, labelspacing=0.2)
    origin_axes(ax)
    med_n = float(np.median(nongold_scores))
    med_g = float(np.median(gold_scores))
    ax.annotate(f"{med_g:.2f}", (0.24, med_g), fontsize=_FS, color=SEM["system"],
                va="center", ha="left")
    ax.annotate(f"{med_n:.2f}", (1.24, med_n), fontsize=_FS,
                color=C["dgrey"], va="center", ha="left")
    ax.annotate("Mann-Whitney $p$ = 0.26", (0.5, 0.458), ha="center",
                va="bottom", color=C["dgrey"])
    save(fig, "fig4_inflation")


_GOLD_CACHE = None
def _gold_of(qid):
    global _GOLD_CACHE
    if _GOLD_CACHE is None:
        sys.path.insert(0, str(HERE.parent / "experiments"))
        from kbcommon import QUESTIONS
        _GOLD_CACHE = {q["qid"]: q["gold_doc_substrings"] for q in QUESTIONS}
    return _GOLD_CACHE[qid]


# ===========================================================================
# Fig 5 —Exp2 agentic end-to-end results (full width)
# ===========================================================================
def fig_e2e():
    outdir = RESULTS / "exp2_lanes"
    runs = []
    for f in sorted(outdir.glob("run_*.json")):
        runs.append(json.loads(f.read_text(encoding="utf-8"))["run"])
    if not runs:
        print("exp2 data not ready; skip fig5")
        return
    arms = ["search", "librarian", "hybrid", "bare"]
    arm_labels = ["Search (A)", "Librarian (B)", "Hybrid (C)", "Bare agent"]
    colors = [C["blue"], C["green"], C["orange"], C["grey"]]
    qids = sorted({r["qid"] for r in runs})

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(W_FULL, 2.30),
                                 gridspec_kw={"width_ratios": [1.5, 1]},
                                 layout="constrained")
    w = 0.19
    for k, arm in enumerate(arms):
        rs = [next((r for r in runs if r["arm"] == arm and r["qid"] == q), None)
              for q in qids]
        vals = [r["wall_s"] if r else 0 for r in rs]
        xs = [i + (k - 1.5) * w for i in range(len(qids))]
        a1.bar(xs, vals, width=w, color=colors[k], edgecolor="white",
               linewidth=0.4, label=arm_labels[k])
        for xi, r in zip(xs, rs):
            if r and r.get("turns"):
                a1.text(xi, r["wall_s"] + 2, str(r["turns"]), ha="center",
                        color="#333333")
    a1.set_xticks(range(len(qids)))
    a1.set_xticklabels([f"{q}\n{_short(q)}" for q in qids])
    a1.set_ylabel("End-to-end wall time (s)")
    a1.legend(frameon=False, loc="upper left", ncol=2, columnspacing=0.7,
              handlelength=1.0, handletextpad=0.4, borderaxespad=0.1,
              borderpad=0.0, labelspacing=0.25)
    a1.set_ylim(0, max(r["wall_s"] for r in runs) * 1.48)
    a1.set_yticks([0, 50, 100, 150])
    hide_top_right(a1, left=True)
    a1.tick_params(length=2, pad=1.5)
    a1.set_title("(a) Wall time per run (numbers = agent turns)", loc="left")

    for k, arm in enumerate(arms):
        rs = [r for r in runs if r["arm"] == arm]
        if not rs:
            continue
        hit = sum(1 for r in rs if r["doc_citation_hit"]) / len(rs)
        turns = sum((r["turns"] or 0) for r in rs) / len(rs)
        xd = (k - 1.5) * 0.7  # dodge overlapping (turns, hit) points
        a2.scatter([turns + xd], [hit], s=22, color=colors[k], zorder=3,
                   label=arm_labels[k], edgecolors="white", linewidths=0.4)
        # labels fanned out to the left / below / right: the three grounding
        # arms sit within 0.11 in of each other at 8 pt, so stacked labels
        # collided ("HybridSearch").
        offs = {0: (-5, 1), 1: (0, -13), 2: (5, 1), 3: (6, -11)}
        ha = {0: "right", 1: "center", 2: "left", 3: "left"}
        a2.annotate(arm_labels[k].split(" ")[0], (turns + xd, hit),
                    textcoords="offset points", xytext=offs[k], ha=ha[k])
    a2.set_xlabel("Mean agent turns per run")
    a2.set_ylabel("Citation gold-hit rate")
    a2.set_ylim(-0.12, 1.20)
    a2.set_yticks([0.0, 0.5, 1.0])
    a2.set_xlim(0, max((r["turns"] or 0) for r in runs) * 1.30 + 2)
    a2.grid(True, lw=0.3, color="#E5E5E5")
    a2.tick_params(length=2, pad=1.5)
    hide_top_right(a2, left=True)
    a2.set_title("(b) Cost vs. groundedness", loc="left")
    save(fig, "fig5_e2e")


def _short(qid):
    m = {"Q2": "EL delam.", "Q4": "POE barrier",
         "Q6": "weight alarm", "Q7": "TC0 root"}
    return m.get(qid, qid)


# ===========================================================================
# Fig 6 —cut-margin replay + ordering-vs-filter (full width)
# ===========================================================================
def fig_margin_variants():
    d = json.loads((RESULTS / "exp3_abstention.json").read_text(encoding="utf-8"))
    rp = d["cut_replay"]
    margins = sorted(float(k) for k in rp)
    golds = [rp[str(m)]["gold_kept"] if str(m) in rp else rp[m]["gold_kept"]
             for m in margins]
    kept = [rp[str(m)]["mean_kept"] if str(m) in rp else rp[m]["mean_kept"]
            for m in margins]
    e5 = json.loads((RESULTS / "exp5_judge_filter.json").read_text(
        encoding="utf-8"))["summary"]

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(W_FULL, 2.15),
                                 gridspec_kw={"width_ratios": [1.10, 1]},
                                 layout="constrained")
    ax = a1
    ax.plot(margins, golds, "-o", color=SEM["system"], lw=1.0, ms=2.6,
            label="golds kept (of 17)")
    ax.set_xlabel("cut margin (best $-$ m)")
    ax.set_ylabel("golds kept", color=SEM["system"])
    ax.set_ylim(6, 18.6)
    ax.set_yticks([8, 10, 12, 14, 16])
    ax.set_xticks([0.0, 0.1, 0.2, 0.3])
    ax.tick_params(length=2, pad=1.0)
    ax2 = ax.twinx()
    ax2.plot(margins, kept, "-s", color=C["dgrey"], lw=1.0, ms=2.4,
             label="mean kept set")
    ax2.set_ylabel("mean kept (of 12)", color=C["dgrey"])
    ax2.set_ylim(6, 12.6)
    ax2.set_yticks([7, 9, 11])
    ax2.tick_params(length=2, pad=1.0)
    ax.axvline(0.15, color=C["dgrey"], lw=0.6, ls="--")
    ax.text(0.155, 6.5, "0.15", color=C["dgrey"], va="bottom", ha="left")
    ax.axvline(0.20, color=SEM["system"], lw=0.6, ls="--")
    ax.text(0.205, 6.5, "0.20", color=SEM["system"], va="bottom", ha="left")
    # Origin-style frame on both the left axis and its twin.
    for a in (ax, ax2):
        for sp in a.spines.values():
            sp.set_visible(True)
            sp.set_linewidth(0.8)
            sp.set_color("#222222")
    ax.tick_params(axis="both", direction="in", top=True, right=False,
                   length=3.0, width=0.8, pad=2.0)
    ax2.tick_params(axis="both", direction="in", right=True, left=False,
                    top=False, bottom=False, length=3.0, width=0.8, pad=2.0)
    ax.minorticks_on()
    ax.tick_params(which="minor", direction="in", top=True, right=False,
                   length=1.6, width=0.6)
    ax.set_title("(a) cut-margin replay", loc="left")

    ax = a2
    names = ["Fusion", "Judged", "Filter", "RRF"]
    vals = [0.94, e5["judged"]["hit@5"], e5["filter_only"]["hit@5"],
            e5["rrf_fuse"]["hit@5"]]
    cols = [SEM["baseline"], SEM["failure"], SEM["system"], SEM["context"]]
    ax.bar(range(4), vals, color=cols, edgecolor="white", linewidth=0.4,
           width=0.62)
    # No reference line here: two bars sit exactly on the fusion value, so a
    # dashed line would print through their own labels. The caption carries the
    # comparison.
    for i, v in enumerate(vals):
        ax.text(i, v + 0.03, f"{v:.2f}", ha="center")
    ax.set_xticks(range(4))
    ax.set_xticklabels(names)
    ax.set_ylabel("Hit@5")
    ax.set_ylim(0, 1.24)
    ax.set_yticks([0.0, 0.5, 1.0])
    origin_axes(ax)
    ax.set_title("(b) verdict roles, same pools", loc="left")
    save(fig, "fig6_margin_variants")


# ===========================================================================
# Fig 7 —OOD probes (0.62\textwidth = 3.34 in)
# ===========================================================================
def fig_ood_kbs():
    d = json.loads((RESULTS / "exp3_abstention.json").read_text(encoding="utf-8"))
    pr = d["probes"]
    topics = ["Li thermal\nrunaway", "Vaccination\nschedule",
              "Python\nconcurrency", "Mold vent\ndesign"]
    kept = [p["kept_n"] for p in pr]
    over = [p["vector_above_0.35"] for p in pr]
    x = range(len(pr))
    w = 0.36
    fig, ax = plt.subplots(figsize=(W_OOD, 2.05), layout="constrained")
    ax.bar([i - w / 2 for i in x], kept, width=w, color=SEM["failure"],
           label="kept by judge (of 12)", edgecolor="white", linewidth=0.3)
    ax.bar([i + w / 2 for i in x], over, width=w, color=SEM["baseline"],
           label="chunks above 0.35", edgecolor="white", linewidth=0.3)
    for xi, v in zip(x, kept):
        ax.text(xi - w / 2, v + 0.45, str(v), ha="center")
    for xi, v in zip(x, over):
        ax.text(xi + w / 2, v + 0.45, str(v), ha="center")
    ax.set_xticks(list(x))
    ax.set_xticklabels(topics)
    ax.set_ylabel("count")
    ax.set_ylim(0, 22)
    ax.set_yticks([0, 5, 10, 15])
    ax.legend(frameon=False, loc="upper center", ncol=1,
              handlelength=1.0, handletextpad=0.4, borderaxespad=0.1,
              borderpad=0.0, labelspacing=0.25)
    origin_axes(ax)
    save(fig, "fig7_ood")


# ===========================================================================
# Fig 9 —robustness overview (full width, 2x2)
# ===========================================================================
def fig_robustness():
    R = RESULTS

    # ---- (a) paraphrase grid: per-method Hit@5, original vs paraphrase
    e1s = json.loads((R / "exp1_summary.json").read_text(
        encoding="utf-8"))["summary"]
    e6s = json.loads((R / "exp6_paraphrase.json").read_text(
        encoding="utf-8"))["summary"]
    methods = [("bm25", "BM25"), ("dense", "Dense"), ("rrf", "RRF"),
               ("twostage", "2-stage"), ("fusion_only", "Fusion"),
               ("judged", "Judged"), ("filter_only", "Filter")]
    fig, axes = plt.subplots(2, 2, figsize=(W_FULL, 6.10),
                             layout="constrained")
    ax = axes[0][0]
    y = list(range(len(methods)))[::-1]
    for yi, (m, label) in zip(y, methods):
        o = e1s[m]["hit@5"] if m in e1s else e1s.get(m, {}).get("hit@5", 0)
        pa = e6s[m]["hit@5"]
        ax.plot([o, pa], [yi, yi], "-", color="#BBBBBB", lw=0.9, zorder=1)
        ax.plot(o, yi, "o", color=C["blue"], ms=3.2, zorder=3)
        ax.plot(pa, yi, "o", color=C["verm"], ms=3.2, zorder=3)
        if abs(o - pa) > 0.001:
            # Put the paraphrase number on the far side of its own dot: the
            # two dots of a row are only ~0.04 in apart, so a centred label
            # landed on the original marker.
            if pa >= o:
                off, al = (5, -4), "left"
            else:
                off, al = (-5, -4), "right"
            ax.annotate(f"{pa:.2f}", (pa, yi), textcoords="offset points",
                        xytext=off, color=C["verm"], va="top",
                        ha=al, fontsize=_FS)
    ax.set_yticks(y)
    ax.set_yticklabels([l for _, l in methods])
    ax.set_xlabel("Hit@5")
    ax.set_xlim(0.42, 1.18)
    ax.set_xticks([0.5, 0.7, 0.9, 1.1])
    ax.plot([], [], "o", color=C["blue"], ms=3.2, label="original (16 q)")
    ax.plot([], [], "o", color=C["verm"], ms=3.2, label="paraphrase (16 q)")
    ax.legend(frameon=False, loc="lower left", handlelength=1.0,
              handletextpad=0.4, borderaxespad=0.1, borderpad=0.0,
              labelspacing=0.25)
    ax.tick_params(length=2, pad=1.5)
    hide_top_right(ax)
    ax.set_title("(a) paraphrase grid", loc="left")

    # ---- (b) NLI separation: gold vs non-gold, doc-head and span-max
    e7 = json.loads((R / "exp7_second_signal.json").read_text(
        encoding="utf-8"))
    e9 = json.loads((R / "exp9_span_nli.json").read_text(encoding="utf-8"))
    ax = axes[0][1]
    data = {"head\ngold": [p["nli"] for p in e7["pairs"] if p["gold"]],
            "head\nnon-gold": [p["nli"] for p in e7["pairs"]
                               if not p["gold"]],
            "span\ngold": [p["nli_span"] for p in e9["pairs"] if p["gold"]],
            "span\nnon-gold": [p["nli_span"] for p in e9["pairs"]
                               if not p["gold"]]}
    keys = list(data)
    rng = np.random.default_rng(7)
    for i, k in enumerate(keys):
        vals = data[k]
        x = i + rng.uniform(-0.13, 0.13, size=len(vals))
        ax.scatter(x, vals, s=2, color=C["blue"] if "gold" in k else C["verm"],
                   alpha=0.45, edgecolors="none", zorder=2)
        med = statistics.median(vals)
        ax.hlines(med, i - 0.28, i + 0.28, color="#222222", lw=1.2, zorder=3)
        ax.text(i + 0.32, med, f"{med:.2f}", va="center", color="#222222")
    ax.set_xticks(range(len(keys)))
    ax.set_xticklabels(keys)
    ax.set_ylabel("NLI entailment score")
    ax.set_ylim(-0.04, 1.04)
    ax.set_yticks([0.0, 0.5, 1.0])
    ax.tick_params(length=2, pad=1.5)
    hide_top_right(ax)
    ax.set_title("(b) NLI anti-separation (medians)", loc="left")

    # ---- (c) second corpus: judged collapse disappears without confusers
    e10 = json.loads((R / "exp10_papers_toollayer.json").read_text(
        encoding="utf-8"))["summary"]
    ax = axes[1][0]
    arms = [("bm25", "BM25"), ("fusion_only", "Fusion"),
            ("judged", "Judged"), ("filter_only", "Filter")]
    orig = [1.00, e1s["fusion_only"]["hit@5"], e1s["qdcvr_hybrid"]["hit@5"],
            0.9375]
    papers = [e10[a]["hit@5"] for a, _ in arms]
    x = np.arange(len(arms))
    w = 0.36
    ax.bar(x - w / 2, orig, width=w, color=C["blue"], label="PV (42 docs)",
           edgecolor="white", linewidth=0.3)
    ax.bar(x + w / 2, papers, width=w, color=C["orange"],
           label="arXiv (79 docs)", edgecolor="white", linewidth=0.3)
    for xi, v in zip(x, orig):
        ax.text(xi - w / 2, v + 0.03, f"{v:.2f}", ha="center")
    for xi, v in zip(x, papers):
        ax.text(xi + w / 2, v + 0.03, f"{v:.2f}", ha="center")
    ax.set_xticks(x)
    ax.set_xticklabels([l for _, l in arms])
    ax.set_ylabel("Hit@5")
    ax.set_ylim(0, 1.46)
    ax.set_yticks([0.0, 0.5, 1.0])
    ax.legend(frameon=False, loc="upper left", ncol=2, columnspacing=0.7,
              handlelength=1.0, handletextpad=0.4, borderaxespad=0.1,
              borderpad=0.0, labelspacing=0.25)
    ax.tick_params(length=2, pad=1.5)
    hide_top_right(ax, left=True)
    ax.set_title("(c) second corpus: judged = fusion = filter", loc="left")

    # ---- (d) graded probes: kept counts by tier
    e8 = json.loads((R / "exp8_graded_probes.json").read_text(
        encoding="utf-8"))
    ax = axes[1][1]
    tiers = e8["tool_layer"]
    cols = {"partial": C["orange"], "absent": C["grey"]}
    for i, t in enumerate(tiers):
        ax.bar(i, t["kept_n"], color=cols[t["tier"]], edgecolor="white",
               linewidth=0.3)
        ax.text(i, t["kept_n"] + 0.45, str(t["kept_n"]), ha="center")
    ax.axhline(12, color=C["dgrey"], lw=0.6, ls="--")
    # right-hand end of the pool line: at the left it collided with the two
    # "12" bar labels and the dashed line itself
    ax.text(len(tiers) - 0.55, 12.45, "pool 12", ha="right", va="bottom",
            color=C["dgrey"])
    ax.set_xticks(range(len(tiers)))
    ax.set_xticklabels([t["qid"] for t in tiers])
    ax.set_ylabel("candidates kept")
    ax.set_ylim(0, 18.5)
    ax.set_yticks([0, 5, 10, 15])
    ax.legend(handles=[Patch(fc=cols["partial"], label="partial"),
                       Patch(fc=cols["absent"], label="absent")],
              frameon=False, loc="upper left", ncol=1, handlelength=1.0,
              handletextpad=0.4, borderaxespad=0.1, borderpad=0.0,
              labelspacing=0.25)
    ax.tick_params(length=2, pad=1.5)
    hide_top_right(ax, left=True)
    ax.set_title("(d) graded probes: threshold keeps everything", loc="left")

    save(fig, "fig9_robustness")


# ===========================================================================
# Fig 8 —anatomy of one real query (Q2, logged QDCVR-Hybrid traces)
# ===========================================================================
def fig_anatomy():
    d = json.loads((RESULTS / "exp5_q2_anatomy.json").read_text(
        encoding="utf-8"))
    r = d["response"]
    fusion = [p.replace("\\", "/") for p in r["merge"]["judged_candidates"]]
    kept = {p.replace("\\", "/"): float(k["score"])
            for k in r["cut"]["kept"] for p in [k["doc_path"]]}
    judged = sorted(kept, key=lambda p: -kept[p])

    def cls(p):
        if "EL-2025-0317" in p:
            return "gold"
        if "aw-industrial/【演示线1" in p:
            return "plc"
        return "other"

    col = {"gold": C["blue"], "plc": C["verm"], "other": "#C8C8C8"}
    lw = {"gold": 1.5, "plc": 0.9, "other": 0.7}
    ms = {"gold": 3.0, "plc": 2.2, "other": 2.0}

    fig, axes = plt.subplots(1, 2, figsize=(W_FULL, 2.95), sharey=True,
                             layout="constrained")
    panels = [
        (axes[0], judged, "(a) Judge as re-ranker (shipped ordering)",
         "score order"),
        (axes[1], fusion, "(b) Judge as filter (verdicts only)",
         "fusion order"),
    ]
    for ax, order, title, xright in panels:
        pos = {p: i + 1 for i, p in enumerate(order)}
        ax.axhspan(0.5, 5.5, color="#EDF6EA", zorder=0)
        ax.text(-0.36, 5.05, "top-5 read window", color=C["green"],
                va="center", zorder=4,
                bbox=dict(fc="white", ec="none", alpha=0.85, pad=0.8))
        for p in fusion:
            k = cls(p)
            ax.plot([0, 1], [fusion.index(p) + 1, pos[p]], "-",
                    color=col[k], lw=lw[k], zorder=3 if k == "gold" else 2,
                    marker="o", ms=ms[k], mfc=col[k], mec="white", mew=0.4,
                    solid_capstyle="round")
        ax.set_xlim(-0.55, 1.62)
        ax.set_ylim(12.8, 0.3)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["fusion rank", xright])
        ax.tick_params(length=0, pad=1.5)
        ax.set_yticks(range(1, 13))
        for sp in ax.spines.values():
            sp.set_visible(False)
        ax.set_title(title, loc="left")
    axes[0].set_yticklabels([str(i) for i in range(1, 13)])
    axes[0].set_ylabel("rank", labelpad=1)

    # score annotations (real logged scores)
    axes[0].annotate("PLC telemetry 0.926", xy=(1, 1), xytext=(4, 2),
                     textcoords="offset points", color=C["verm"],
                     va="center")
    axes[0].annotate("gold 0.846 \u2192 not read", xy=(1, 8),
                     xytext=(4, 0), textcoords="offset points",
                     color=C["blue"], va="center")
    axes[1].annotate("gold read first (0.846)", xy=(1, 1),
                     xytext=(4, 0), textcoords="offset points",
                     color=C["blue"], va="center")

    from matplotlib.lines import Line2D
    handles = [
        Line2D([], [], color=col["gold"], lw=1.5, marker="o", ms=3.0,
               label="gold: EL-2025-0317 delamination RCA report"),
        Line2D([], [], color=col["plc"], lw=0.9, marker="o", ms=2.2,
               label="extruder-PLC demo telemetry reports (5)"),
        Line2D([], [], color=col["other"], lw=0.7, marker="o", ms=2.0,
               label="other corpus documents (6)"),
    ]
    fig.legend(handles=handles, frameon=False, loc="outside lower center",
               ncol=1, handlelength=1.4, handletextpad=0.5,
               labelspacing=0.25, borderpad=0.0)
    save(fig, "fig8_anatomy")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "1"):
        fig_architecture()
    if which in ("all", "2"):
        fig_lanes()
    if which in ("all", "3"):
        fig_retrieval()
    if which in ("all", "4"):
        fig_inflation()
    if which in ("all", "5"):
        fig_e2e()
    if which in ("all", "6"):
        fig_margin_variants()
    if which in ("all", "7"):
        fig_ood_kbs()
    if which in ("all", "8"):
        fig_anatomy()
    if which in ("all", "9"):
        fig_robustness()
