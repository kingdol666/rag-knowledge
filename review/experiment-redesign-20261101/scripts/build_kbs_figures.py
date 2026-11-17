# -*- coding: utf-8 -*-
"""Generate publication figures for the management and R3 content-layer evidence.

The plots use the frozen final and 2026-11-12 R3 JSON summaries directly. The
figures are deliberately non-pooled: management panels retain their original
denominators, while the R3 panel contains only the six complete content-layer
arms. PDFs are the manuscript assets; PNGs are review previews.
"""
from __future__ import annotations

import json
from math import sqrt
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge")
BASE = ROOT / "review" / "experiment-redesign-20261101" / "artifacts"
JOURNAL = ROOT / "paper-kbs" / "tex" / "journal_20p" / "figs"
FINAL = BASE / "final_bench"
R3 = BASE / "replication_bench_20261112"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 8.5,
    "axes.titlesize": 9.5,
    "axes.labelsize": 8.5,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 7.5,
    "axes.linewidth": 0.8,
    "xtick.major.width": 0.7,
    "ytick.major.width": 0.7,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})
BLUE = "#1f5aa6"
ORANGE = "#d77a22"
TEAL = "#17807a"
SLATE = "#5d6b7a"
RED = "#b23a48"
GRID = "#d9e1ea"


def save(fig, stem):
    fig.savefig(JOURNAL / f"{stem}.pdf", bbox_inches="tight", pad_inches=0.04)
    fig.savefig(JOURNAL / f"{stem}.png", dpi=320, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)


def wilson(k, n, z=1.96):
    p = k / n
    den = 1 + z * z / n
    ctr = (p + z * z / (2 * n)) / den
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0, ctr - half), min(1, ctr + half)


def management_figure():
    fig, axes = plt.subplots(1, 3, figsize=(8.35, 2.70), gridspec_kw={"wspace": 0.82})
    fig.subplots_adjust(bottom=.28, top=.80)

    # Panel a: no pooled denominator; each bar is a named campaign.
    ax = axes[0]
    labels = ["arXiv", "Wiki EN", "Wiki ZH", "Wiki JA"]
    vals = [79/100, .875, 1.0, 1.0]
    colors = [BLUE, TEAL, TEAL, TEAL]
    ax.bar(np.arange(4), vals, color=colors, width=.66, edgecolor="white", linewidth=.6)
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("Observed proportion")
    ax.set_xticks(np.arange(4), labels)
    ax.tick_params(axis="x", labelsize=6.5, pad=2, rotation=22)
    ax.set_title("(a) Acquisition / assignment")
    ax.grid(axis="y", color=GRID, linewidth=.55)
    ax.set_axisbelow(True)
    for i, v in enumerate(vals):
        if v >= .99:
            ax.text(i, v + .045, "100%", ha="center", va="bottom", fontsize=5.8, color=SLATE, fontweight="bold")
        else:
            ax.text(i, v + .035, f"{v*100:.1f}%", ha="center", va="bottom", fontsize=6.1)
    ax.text(.5, -.29, "arXiv n=100; Wiki n=400/language", transform=ax.transAxes, fontsize=6.1, color=SLATE, ha="center")

    # Panel b: selected operational checks retain their denominators.
    ax = axes[1]
    labels = ["content", "storage", "life pass", "life fail"]
    vals = [322/322, 33/33, 4/16, 2/16]
    colors = [TEAL, TEAL, BLUE, RED]
    ax.bar(np.arange(4), vals, color=colors, width=.66, edgecolor="white", linewidth=.6)
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("Observed proportion")
    ax.set_xticks(np.arange(4), labels)
    ax.tick_params(axis="x", labelsize=6.5, pad=2, rotation=22)
    ax.set_title("(b) State / lifecycle checks")
    ax.grid(axis="y", color=GRID, linewidth=.55)
    ax.set_axisbelow(True)
    texts = ["322/322", "33/33", "4/16", "2/16"]
    for i, (v, t) in enumerate(zip(vals, texts)):
        if v >= .99:
            ax.text(i, v + .045, t, ha="center", va="bottom", fontsize=5.8, color=SLATE, fontweight="bold")
        else:
            ax.text(i, v + .035, t, ha="center", va="bottom", fontsize=6.1)
    ax.text(.5, -.29, "Selected checks; not exhaustive", transform=ax.transAxes, fontsize=6.1, color=SLATE, ha="center")

    # Panel c: operational experience is shown as a small evidence profile.
    ax = axes[2]
    labels = ["drafts", "lessons", "approval"]
    vals = [13, 1, 0]
    colors = [ORANGE, TEAL, RED]
    ax.bar(np.arange(3), vals, color=colors, width=.66, edgecolor="white", linewidth=.6)
    ax.set_ylim(0, 14.5)
    ax.set_ylabel("Observed count")
    ax.set_xticks(np.arange(3), labels)
    ax.tick_params(axis="x", labelsize=6.5, pad=2)
    ax.set_title("(c) Operational experience")
    ax.grid(axis="y", color=GRID, linewidth=.55)
    ax.set_axisbelow(True)
    for i, v in enumerate(vals):
        ax.text(i, v + .35, str(v), ha="center", va="bottom", fontsize=6.8)
    ax.text(.5, -.29, "One small KB; approval/decay untested", transform=ax.transAxes, fontsize=6.1, color=SLATE, ha="center")

    fig.suptitle("HMRS management evidence, reported per campaign", x=.02, ha="left", y=.98, fontsize=10.5, fontweight="bold")
    save(fig, "fig_management_evidence")


def r3_content_figure():
    arms = ["A0", "A0f", "A0h", "PD", "A1b", "A2"]
    names = ["A0", "A0f", "A0h", "PD", "A1b", "A2"]
    frozen = np.array([37, 45, 52, 46, 39, 25]) / 72
    r3 = np.array([39, 44, 51, 45, 39, 25]) / 72
    lo_f, hi_f = zip(*[wilson(k, 72) for k in [37,45,52,46,39,25]])
    lo_r, hi_r = zip(*[wilson(k, 72) for k in [39,44,51,45,39,25]])
    yerr_f = np.vstack([frozen - np.array(lo_f), np.array(hi_f) - frozen])
    yerr_r = np.vstack([r3 - np.array(lo_r), np.array(hi_r) - r3])
    fig, axes = plt.subplots(1, 2, figsize=(7.9, 2.70), gridspec_kw={"wspace": .78})
    fig.subplots_adjust(bottom=.30, top=.82)
    ax = axes[0]
    x = np.arange(len(arms))
    ax.errorbar(x - .09, frozen, yerr=yerr_f, fmt="o", color=BLUE, markersize=5.5, capsize=2.5, linewidth=1.0, label="Frozen final")
    ax.errorbar(x + .09, r3, yerr=yerr_r, fmt="s", color=ORANGE, markersize=4.7, capsize=2.5, linewidth=1.0, label="R3 replication")
    ax.axhline(0, color="#64748b", linewidth=.6)
    ax.set_ylim(0, 1.04)
    ax.set_ylabel("Gold-string containment")
    ax.set_xticks(x, names)
    ax.set_title("(a) Evidence containment")
    ax.grid(axis="y", color=GRID, linewidth=.55)
    ax.set_axisbelow(True)
    ax.legend(frameon=True, facecolor="white", edgecolor="none", framealpha=.92, loc="upper right", fontsize=6.7)
    ax.annotate("A0h 51/72", xy=(2.09, r3[2]), xytext=(2.0, .83), arrowprops=dict(arrowstyle="-", color=ORANGE, lw=.8), fontsize=7.0, color=ORANGE, ha="center")

    # Cost panel: R3 values, two scales kept separate.
    ax = axes[1]
    bytes_k = np.array([38.321, 303.418, 309.106, 307.866, 38.464, 1.787])
    seconds = np.array([17.4, 12.0, 12.5, 12.9, 10.3, 1.0])
    width = .34
    ax.bar(x - width/2, bytes_k, width, color=SLATE, label="Bytes/q (KB)")
    ax2 = ax.twinx()
    ax2.plot(x + width/2, seconds, "o-", color=TEAL, linewidth=1.3, markersize=4.4, label="Tool time (s/q)")
    ax.set_ylabel("Trace bytes per gold question (KB)", color=SLATE)
    ax2.set_ylabel("Tool time per gold question (s)", color=TEAL)
    ax.set_xticks(x, names)
    ax.set_title("(b) R3 cost profile")
    ax.grid(axis="y", color=GRID, linewidth=.55)
    ax.set_axisbelow(True)
    ax.set_ylim(0, 360)
    ax2.set_ylim(0, 20)
    lines, labs = ax.get_legend_handles_labels()
    lines2, labs2 = ax2.get_legend_handles_labels()
    fig.legend(lines + lines2, labs + labs2, frameon=True, facecolor="white", edgecolor="none", framealpha=.95, loc="lower center", bbox_to_anchor=(.77, -.015), ncol=2, fontsize=6.2)

    fig.suptitle("Latest complete R3 content-layer comparison (gold n=72 per arm)", x=.02, ha="left", y=1.01, fontsize=10.5, fontweight="bold")
    fig.text(.5, .075, "Containment is a retrieval proxy; A0h is highest complete R3 arm. Configurations vary beyond navigation.", fontsize=6.4, color=SLATE, ha="center")
    save(fig, "fig_r3_content_comparison")


if __name__ == "__main__":
    JOURNAL.mkdir(parents=True, exist_ok=True)
    management_figure()
    r3_content_figure()
    print("generated", JOURNAL / "fig_management_evidence.pdf")
    print("generated", JOURNAL / "fig_r3_content_comparison.pdf")
