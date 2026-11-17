# -*- coding: utf-8 -*-
"""Build three KBS figure redesign candidates in two native-vector styles.

This staging builder never edits the canonical manuscript figures. It writes six
PDF+PNG candidates into figure-redesign-20261112/vectors/{style}/.
All exact labels/data are authored here; GPT Image boards are visual direction only.
"""
from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = HERE / "vectors"
FB = ROOT / "review" / "experiment-redesign-20261101" / "artifacts" / "final_bench"
STATS = json.loads((FB / "s6_stats.json").read_text(encoding="utf-8"))
TRACES = json.loads((FB / "s4_traces_final.json").read_text(encoding="utf-8"))

# KBS / Elsevier two-column full-width staging canvas: 6.96 x ~3.8 in.
W = 6.96
INK = "#20262E"
SUB = "#46515C"
LINE = "#53606B"
BLUE = "#0072B2"
GREEN = "#009E73"
ORANGE = "#E69F00"
VERM = "#D55E00"
PURPLE = "#7A5C93"
GREY = "#68737D"
LIGHT_BLUE = "#E8F1F8"
LIGHT_GREEN = "#EAF4EF"
LIGHT_ORANGE = "#FBF2DF"
LIGHT_PURPLE = "#F2EDF5"
LIGHT_GREY = "#F3F5F6"

STYLES = {
    "style1": {
        "bg": "#FFFFFF", "ink": INK, "sub": SUB, "line": LINE,
        "blue": BLUE, "green": GREEN, "orange": ORANGE,
        "purple": PURPLE, "verm": VERM, "panel": "#F8FAFC",
        "state": "#F2EDF5", "state_edge": PURPLE,
    },
    "style2": {
        "bg": "#FCF8F0", "ink": "#18283D", "sub": "#465466", "line": "#64748B",
        "blue": "#234E70", "green": "#4C8C78", "orange": "#C8963E",
        "purple": "#786C8D", "verm": "#B86250", "panel": "#FFFDF8",
        "state": "#F1EBDD", "state_edge": "#786C8D",
    },
}

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 8.2, "axes.labelsize": 8.2, "xtick.labelsize": 8.0,
    "ytick.labelsize": 8.0, "legend.fontsize": 8.0, "pdf.fonttype": 42,
    "ps.fonttype": 42, "svg.fonttype": "none", "savefig.facecolor": "white", "figure.dpi": 150,
})


def setup(name: str, style: str, h: float):
    spec = STYLES[style]
    fig = plt.figure(figsize=(W, h), facecolor=spec["bg"])
    ax = fig.add_axes([0, 0, 1, 1], facecolor=spec["bg"])
    ax.set_xlim(0, W)
    ax.set_ylim(0, h)
    ax.axis("off")
    return fig, ax, spec


def box(ax, x, y, w, h, title, body="", *, fc="white", ec=LINE, spec=None,
        title_fs=8.4, body_fs=7.6, lw=.75, radius=.05, title_color=None,
        body_color=None, z=2):
    spec = spec or STYLES["style1"]
    title_color = title_color or spec["ink"]
    body_color = body_color or spec["sub"]
    ax.add_patch(FancyBboxPatch((x, y), w, h,
        boxstyle=f"round,pad=.012,rounding_size={radius}",
        facecolor=fc, edgecolor=ec, linewidth=lw, zorder=z))
    if body:
        ax.text(x + w/2, y + h*.66, title, ha="center", va="center",
                fontsize=title_fs, fontweight="bold", color=title_color, zorder=z+1)
        ax.text(x + w/2, y + h*.28, body, ha="center", va="center",
                fontsize=body_fs, color=body_color, linespacing=1.1, zorder=z+1)
    else:
        ax.text(x + w/2, y + h/2, title, ha="center", va="center",
                fontsize=title_fs, fontweight="bold", color=title_color, zorder=z+1)


def arrow(ax, p1, p2, *, color=LINE, lw=.85, ls="-", style="-|>", ms=7, z=3,
          connection="arc3,rad=0"):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle=style,
        mutation_scale=ms, linewidth=lw, color=color, linestyle=ls,
        connectionstyle=connection, zorder=z))


def title(ax, text, subtitle, h, spec):
    ax.text(.16, h-.18, text, ha="left", va="center", fontsize=10.2,
            fontweight="bold", color=spec["ink"])
    ax.text(.16, h-.40, subtitle, ha="left", va="center", fontsize=8.0,
            color=spec["sub"])


def save(fig, style, name):
    path = OUT / style
    path.mkdir(parents=True, exist_ok=True)
    fig.savefig(path / f"{name}.pdf", bbox_inches=None, dpi=300)
    fig.savefig(path / f"{name}.png", bbox_inches=None, dpi=300)
    fig.savefig(path / f"{name}.svg", bbox_inches=None, dpi=300)
    plt.close(fig)


def build_design(style):
    fig, ax, s = setup("design", style, 3.86)
    h = 3.86
    title(ax, "HMRS system design overview",
          "managed state, service boundaries, and an optional catalogue-first access path", h, s)
    # Three semantic columns: management objects, services, and query path.
    ax.text(.16, 3.18, "MANAGEMENT OBJECTS", color=s["blue"], fontsize=8.4, fontweight="bold")
    layers = [
        ("Collection", "KB / sub-KB · content-informed placement\ndescriptions + tags", s["blue"], "#E8F1F8"),
        ("Document", "parts · duplicate review · move / rename / delete\nexplicit re-index", s["green"], "#EAF4EF"),
        ("Segment", "structural split · dense + BM25 indices\noptional Laya gate", s["orange"], "#FBF2DF"),
    ]
    for i, (lab, body, ec, fc) in enumerate(layers):
        y = 2.48 - i*.59
        box(ax, .16, y, 2.10, .47, lab, body, fc=fc, ec=ec, spec=s,
            title_fs=8.0, body_fs=6.6, title_color=ec)

    ax.text(2.48, 3.18, "SERVICE BOUNDARIES", color=s["green"], fontsize=8.4, fontweight="bold")
    box(ax, 2.48, 2.48, .94, .47, "Browser / Web", "Nuxt proxy", fc="#E8F1F8", ec=s["blue"], spec=s, title_fs=7.0, body_fs=6.3)
    box(ax, 3.54, 2.48, .94, .47, "Agent / CLI", "MCP stdio", fc="#F2EDF5", ec=s["purple"], spec=s, title_fs=7.0, body_fs=6.3)
    box(ax, 2.88, 1.83, 1.20, .47, "FastAPI", "parse · search · graph", fc="#EAF4EF", ec=s["green"], spec=s, title_fs=7.7, body_fs=6.4)
    box(ax, 2.88, 1.20, 1.20, .47, "MinerU", "OCR / structure", fc="#EAF4EF", ec=s["green"], spec=s, title_fs=7.5, body_fs=6.4)
    arrow(ax, (2.95, 2.47), (3.20, 2.32), color=s["blue"], lw=.75)
    arrow(ax, (4.00, 2.47), (3.76, 2.32), color=s["purple"], lw=.75)
    arrow(ax, (3.48, 1.82), (3.48, 1.69), color=s["green"], lw=.75)

    ax.text(4.56, 3.18, "OPTIONAL QUERY PATH", color=s["orange"], fontsize=8.4, fontweight="bold")
    tiers = [("Catalogue", "collections + descriptions"), ("Shelf", "documents in one KB"),
             ("Document", "open body"), ("Segment", "score / admit")]
    for i, (lab, body) in enumerate(tiers):
        y = 2.52 - i*.50
        box(ax, 4.56, y, 2.20, .36, lab, body, fc="#E8F1F8", ec=s["blue"], spec=s,
            title_fs=7.5, body_fs=6.2)
        if i:
            arrow(ax, (5.66, y+.48), (5.66, y+.37), color=s["line"], lw=.75, ms=6)

    ax.text(.16, .95, "SHARED AUDITABLE STATE", color=s["purple"], fontsize=8.4,
            fontweight="bold", zorder=12,
            bbox=dict(facecolor=s["bg"], edgecolor="none", pad=1.8))
    state = [("Files", "Markdown + assets"), ("Registries", ".tree-fs.json + YAML"),
             ("Indices", "Chroma / BGE-M3 + BM25"), ("Graph", "Neo4j navigation; not evidence")]
    for i, (lab, body) in enumerate(state):
        x = .16 + i*1.68
        box(ax, x, .48, 1.52, .34, lab, body, fc=s["state"], ec=s["state_edge"], spec=s,
            title_fs=7.2, body_fs=5.8)
    for x, target in [(3.12, .92), (3.48, 2.60), (3.48, 4.28)]:
        # Route the dashed state links below the section header, then enter each
        # store vertically; this keeps the header and arrowheads unambiguous.
        ax.plot([x, x], [1.17, .88], color=s["state_edge"], ls="--", lw=.7, zorder=3)
        ax.plot([x, target], [.88, .88], color=s["state_edge"], ls="--", lw=.7, zorder=3)
        arrow(ax, (target, .88), (target, .82), color=s["state_edge"], ls="--", lw=.7, ms=6, z=4)
    ax.text(3.46, .15, "Indexing and graph build are separate operations; Laya is optional and its score is not proof.",
            ha="center", va="center", fontsize=6.9, color=s["sub"])
    save(fig, style, "figureA_design_overview")


def build_lifecycle(style):
    fig, ax, s = setup("lifecycle", style, 3.92)
    h = 3.92
    title(ax, "HMRS ingest-to-evidence lifecycle",
          "content-informed placement, entry-dependent indexing, and explicit terminal states", h, s)
    # swimlanes
    ax.add_patch(FancyBboxPatch((.10, 2.35), 6.76, .94,
        boxstyle="round,pad=.012,rounding_size=.05", facecolor=s["panel"],
        edgecolor=s["green"], linewidth=.65))
    ax.add_patch(FancyBboxPatch((.10, .35), 6.76, 1.52,
        boxstyle="round,pad=.012,rounding_size=.05", facecolor=s["panel"],
        edgecolor=s["blue"], linewidth=.65))
    ax.text(.22, 3.13, "A  KNOWLEDGE CREATION + MAINTENANCE", color=s["green"], fontsize=8.0, fontweight="bold")
    ax.text(.22, 1.70, "B  QUESTION → EVIDENCE", color=s["blue"], fontsize=8.0, fontweight="bold")
    top = [("Source", "PDF / Office / scan"), ("Parse + QC", "MinerU · OCR · structure"),
           ("Split + enrich", "descriptions · tags"), ("Route", "agent selects KB"),
           ("Save state", "files + registries"), ("Index / probe", "entry-dependent")]
    xs = np.linspace(.23, 5.48, len(top))
    for i, (lab, body) in enumerate(top):
        ec = s["green"] if i < 4 else s["orange"]
        box(ax, xs[i], 2.57, 1.00, .39, lab, body, fc="#EAF4EF" if i < 4 else "#FBF2DF",
            ec=ec, spec=s, title_fs=7.0, body_fs=5.7)
        if i < len(top)-1:
            arrow(ax, (xs[i]+1.02, 2.76), (xs[i+1]-.02, 2.76), color=s["green"], lw=.75, ms=6)
    # State ribbon
    box(ax, 1.30, 1.98, 4.32, .26, "Shared state", "files · registries · vector/BM25 · graph",
        fc=s["state"], ec=s["state_edge"], spec=s, title_fs=7.3, body_fs=6.2)
    arrow(ax, (3.45, 2.55), (3.45, 2.26), color=s["state_edge"], ls="--")
    arrow(ax, (3.45, 1.97), (3.45, 1.72), color=s["state_edge"], ls="--")
    # Query flow
    bottom = [("Question", "scope"), ("Select", "pinned / all-library"),
              ("Gather", "catalogue / BM25 / vector / graph"), ("Judge", "optional Laya")]
    bx = [.23, 1.46, 2.86, 4.44]
    bw = [1.02, 1.18, 1.36, 1.10]
    for i, (x, w, (lab, body)) in enumerate(zip(bx, bw, bottom)):
        ec = s["blue"] if i < 3 else s["orange"]
        box(ax, x, 1.05, w, .42, lab, body, fc="#E8F1F8" if i < 3 else "#FBF2DF",
            ec=ec, spec=s, title_fs=7.2, body_fs=6.0)
        if i < len(bottom)-1:
            arrow(ax, (x+w+.02, 1.26), (bx[i+1]-.02, 1.26), color=s["blue"], lw=.8, ms=6)
    # terminal branches
    box(ax, 5.82, 1.40, .88, .38, "Evidence", "+ sources", fc="#EAF4EF", ec=s["green"], spec=s, title_fs=6.9, body_fs=5.8)
    box(ax, 5.82, .92, .88, .38, "Not found", "scoped", fc="#F3F5F6", ec=GREY, spec=s, title_fs=6.9, body_fs=5.8)
    box(ax, 5.82, .44, .88, .38, "Failure", "execution", fc="#FBF2DF", ec=s["verm"], spec=s, title_fs=6.9, body_fs=5.8)
    arrow(ax, (5.56, 1.32), (5.80, 1.58), color=s["green"], lw=.75, ms=6)
    arrow(ax, (5.56, 1.18), (5.80, 1.10), color=GREY, lw=.75, ms=6)
    arrow(ax, (5.56, 1.05), (5.80, .62), color=s["orange"], lw=.75, ms=6)
    ax.text(3.46, .18, "A threshold score is not proof of support · execution failure ≠ semantic absence",
            ha="center", va="center", fontsize=7.1, color=s["sub"])
    save(fig, style, "figureB_ingest_to_evidence")


def build_results(style):
    spec = STYLES[style]
    fig = plt.figure(figsize=(W, 3.72), facecolor=spec["bg"])
    gs = fig.add_gridspec(1, 3, width_ratios=[1.55, .90, .90],
                          left=.12, right=.98, bottom=.19, top=.82, wspace=.36)
    ax = fig.add_subplot(gs[0, 0], facecolor=spec["bg"])
    calls = fig.add_subplot(gs[0, 1], facecolor=spec["bg"], sharey=ax)
    kb = fig.add_subplot(gs[0, 2], facecolor=spec["bg"], sharey=ax)
    fig.text(.12, .94, "Latest content-layer results", fontsize=10.2, fontweight="bold", color=spec["ink"], ha="left")
    fig.text(.12, .885, "Frozen 11 Nov aggregate · gold-string containment over 72 questions · trace-recorded costs", fontsize=8.0, color=spec["sub"], ha="left")
    arms = ["A0", "A0f", "A0h", "PD", "A1b", "A2", "A3", "Read-all"]
    keys = ["A0", "A0f", "A0h", "PD", "A1b", "A2", "A3", "A1-readall"]
    y = np.arange(len(arms))
    rates, lo, hi, count = [], [], [], []
    calls_v, kb_v = [], []
    for k in keys:
        st = STATS["per_arm"][k]
        assert st["n_gold"] == 72
        rates.append(st["gold_rate"] * 100)
        lo.append(st["gold_ci95"][0] * 100)
        hi.append(st["gold_ci95"][1] * 100)
        count.append(st["gold_hits"])
        rows = [r for r in TRACES[k] if not r.get("is_refusal")]
        assert len(rows) == 72
        calls_v.append(sum(r.get("calls", 0) for r in rows) / 72)
        kb_v.append(sum(r.get("bytes_ingested", 0) for r in rows) / 72 / 1000)
        assert abs(st["avg_bytes_gold"] - sum(r.get("bytes_ingested", 0) for r in rows) / 72) < 1.0
        assert abs(st["avg_tool_s_gold"] - sum(r.get("tool_seconds", 0) for r in rows) / 72) < .06
    assert count == [37, 45, 52, 46, 39, 25, 33, 72]
    colors = [GREY, BLUE, BLUE, ORANGE, "#648DA8", VERM, GREY, "#9AA3AA"]
    for i, (r, l, h, c) in enumerate(zip(rates, lo, hi, count)):
        color = spec["blue"] if i == 2 else (spec["orange"] if i == 3 else colors[i])
        ax.errorbar(r, i, xerr=[[r-l], [h-r]], fmt="o", color=color, ecolor=spec["ink"],
                    capsize=2.5, elinewidth=.8, markersize=5.4, markeredgecolor="white", zorder=3)
        ax.text(min(108, r+3.0), i, f"{c}/72", va="center", ha="left", fontsize=7.3, color=spec["ink"],
                bbox=dict(facecolor=spec["bg"], edgecolor="none", pad=.5), zorder=5)
    ax.axvline(rates[0], color=spec["line"], ls=(0,(4,3)), lw=.75)
    ax.set_xlim(0, 116); ax.set_xticks([0, 25, 50, 75, 100]); ax.set_xlabel("Gold-string containment (%)")
    ax.set_yticks(y); ax.set_yticklabels(arms); ax.invert_yaxis(); ax.set_title("(a) quality", loc="left", fontsize=8.5, fontweight="bold", pad=8)
    # direct annotation: exact paired comparison
    ax.text(0.04, 0.23, "A0h vs PD: 7:1; p=0.0703\n(directionally higher; not significant)",
            transform=ax.transAxes, ha="left", va="top", fontsize=6.7, color=spec["sub"],
            bbox=dict(facecolor=spec["bg"], edgecolor=spec["line"], linewidth=.45, pad=2.0), zorder=6)
    for a in (ax, calls, kb):
        a.spines["top"].set_visible(False); a.spines["right"].set_visible(False)
        a.tick_params(length=3, width=.65); a.grid(axis="x", color="#D8DDE2", lw=.45); a.set_axisbelow(True)
    calls.scatter(calls_v, y, s=28, color=spec["blue"], marker="s", zorder=3)
    kb.scatter(kb_v, y, s=32, color=spec["orange"], marker="^", zorder=3)
    calls.set_xscale("log"); kb.set_xscale("log")
    calls.set_xlim(.7, 30); kb.set_xlim(.7, 30000)
    calls.set_xticks([1, 3, 10, 30], ["1", "3", "10", "30"])
    kb.set_xticks([1, 10, 100, 1000, 10000], ["1", "10", "100", "1k", "10k"])
    calls.set_xlabel("Tool calls / question\n(trace mean)"); kb.set_xlabel("Trace KB / question\n(may overlap)")
    calls.set_yticks(y); kb.set_yticks(y); calls.tick_params(labelleft=False); kb.tick_params(labelleft=False)
    calls.set_title("(b) calls", loc="left", fontsize=8.5, fontweight="bold", pad=8)
    kb.set_title("(c) text volume", loc="left", fontsize=8.5, fontweight="bold", pad=8)
    # key cost labels
    calls.text(calls_v[2], 2-.23, "10.7", ha="center", va="bottom", fontsize=7.0, color=spec["blue"])
    calls.text(calls_v[3], 3+.22, "17.0", ha="center", va="top", fontsize=7.0, color=spec["orange"])
    kb.text(kb_v[2], 2-.23, "309", ha="center", va="bottom", fontsize=7.0, color=spec["orange"])
    kb.text(kb_v[3], 3+.22, "308", ha="center", va="top", fontsize=7.0, color=spec["orange"])
    fig.text(.12, .025, "Containment is a retrieval proxy, not answer correctness. Trace bytes may include repeated text; not model-token counts.", fontsize=6.9, color=spec["sub"], ha="left")
    out = OUT / style; out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / "figureC_latest_results.pdf", bbox_inches=None, dpi=300)
    fig.savefig(out / "figureC_latest_results.png", bbox_inches=None, dpi=300)
    fig.savefig(out / "figureC_latest_results.svg", bbox_inches=None, dpi=300)
    plt.close(fig)


def main():
    for style in STYLES:
        build_design(style)
        build_lifecycle(style)
        build_results(style)
    print("built 6 vector candidates")


if __name__ == "__main__":
    main()
