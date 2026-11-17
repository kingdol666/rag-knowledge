#!/usr/bin/env python3
"""Plot frozen retrieval metrics for the two corpora; vector PDF and PNG."""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "experiments" / "results"
OUT = HERE / "kbs_revision_20261111"
TARGET = HERE.parent / "tex" / "journal_20p" / "figs"

spec = importlib.util.spec_from_file_location("kbs_fig_helpers", HERE / "figures.py")
helper = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = helper
spec.loader.exec_module(helper)

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": [helper.FONT, "Arial", "DejaVu Sans"],
    "font.size": 8.5, "axes.labelsize": 8.5, "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5, "legend.fontsize": 8.5, "axes.linewidth": .8,
    "xtick.direction": "in", "ytick.direction": "in", "pdf.fonttype": 42,
    "ps.fonttype": 42, "savefig.facecolor": "white",
})

# Only directly measured runs, as in the figure caption; derived replays
# are reported separately in the table.
CONFIGS = [
    ("bm25", "bm25", "BM25"), ("graph", "graph", "Graph"),
    ("twostage", "twostage", "Two-stage"),
    ("fusion_only", "fusion_only", "Fusion-only"),
    ("qdcvr_hybrid", "judged", "HMRS-Hybrid"),
]
METRICS = [("hit@5", "Hit@5", "#0072B2", "o"),
           ("recall@5", "Recall@5", "#009E73", "s"),
           ("mrr", "MRR@5", "#E69F00", "^")]


def main() -> None:
    helper.OUT = OUT
    OUT.mkdir(parents=True, exist_ok=True)
    TARGET.mkdir(parents=True, exist_ok=True)
    industrial = json.loads((RESULTS / "exp1_summary.json").read_text(encoding="utf-8"))["summary"]
    papers = json.loads((RESULTS / "exp10_papers_toollayer.json").read_text(encoding="utf-8"))["summary"]
    fig, (left, right) = plt.subplots(1, 2, figsize=(6.96, 3.65),
                                      gridspec_kw={"width_ratios": [1.15, 1]})
    fig.subplots_adjust(left=.18, right=.98, bottom=.15, top=.80, wspace=.28)
    y = np.arange(len(CONFIGS))
    for offset, (key, label, color, marker) in zip((-.19, 0, .19), METRICS):
        vals = [industrial[a][key] for a, _, _ in CONFIGS]
        left.scatter(vals, y + offset, s=30, marker=marker, c=color, label=label,
                     edgecolors="white", linewidths=.35, zorder=3)
    vals = [papers[b]["hit@5"] for _, b, _ in CONFIGS]
    right.scatter(vals, y, s=31, marker="o", c="#0072B2", edgecolors="white",
                  linewidths=.35, zorder=3)
    for yi, value in zip(y, vals):
        right.annotate(f"{value:.2f}", (value, yi), xytext=(6, 0),
                       textcoords="offset points", ha="left", va="center", fontsize=8.5)
    for ax in (left, right):
        ax.set_xlim(0, 1.16)
        ax.set_xticks([0, .2, .4, .6, .8, 1])
        ax.set_ylim(len(CONFIGS) - 1 + .65, -.65)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="x", color="#D8DDE2", linewidth=.5)
        ax.set_axisbelow(True)
        ax.tick_params(length=3, width=.8)
    left.set_yticks(y, [label for _, _, label in CONFIGS])
    right.set_yticks(y, [""] * len(y))
    left.set_xlabel("Score (top-5 document lists)")
    right.set_xlabel("Hit@5")
    left.text(0, 1.02, "(a)", transform=left.transAxes, fontsize=9, fontweight="bold")
    right.text(0, 1.02, "(b)", transform=right.transAxes, fontsize=9, fontweight="bold")
    left.legend(loc="lower left", bbox_to_anchor=(-.01, 1.08), ncol=3,
                frameon=False, handletextpad=.25, columnspacing=.8, borderaxespad=0)
    helper.save(fig, "fig_retrieval_comparison")
    for ext in ("pdf", "png"):
        shutil.copy2(OUT / f"fig_retrieval_comparison.{ext}", TARGET / f"fig_retrieval_comparison.{ext}")


if __name__ == "__main__":
    main()
