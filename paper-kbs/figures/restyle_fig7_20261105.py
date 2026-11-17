#!/usr/bin/env python3
"""Restyle fig7_ood to match the revision set: open top/right spines, Okabe-Ito
semantic colors, direct labels. Data asserted against exp3_abstention.json."""
from __future__ import annotations

import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
SRC = HERE.parent / "experiments/results/exp3_abstention.json"
OUT_PDF = HERE.parent / "tex/journal_20p/figs/fig7_ood.pdf"
OUT_PNG = HERE.parent / "tex/journal_20p/figs/fig7_ood.png"

VERM = "#D55E00"
GREY = "#8A99A3"
INK = "#20262E"
TOPICS = ["Li thermal\nrunaway", "Vaccination\nschedule",
          "Python\nconcurrency", "Mold vent\ndesign"]
EXPECTED = [(11, 4), (11, 8), (9, 10), (11, 7)]

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

d = json.loads(SRC.read_text(encoding="utf-8"))
pr = d["probes"]
kept = [p["kept_n"] for p in pr]
over = [p["vector_above_0.35"] for p in pr]
got = list(zip(kept, over))
assert got == EXPECTED, "data drift: %s" % got
assert len(pr) == 4

plt.rcParams.update({
    "font.family": "Arial", "font.size": 8,
    "axes.edgecolor": INK, "axes.labelcolor": INK,
    "xtick.color": INK, "ytick.color": INK, "text.color": INK,
    "axes.spines.top": False, "axes.spines.right": False,
    "pdf.fonttype": 42,
})
fig, ax = plt.subplots(figsize=(3.35, 2.05), layout="constrained")
x = range(len(pr))
w = 0.36
b1 = ax.bar([i - w / 2 for i in x], kept, width=w, color=VERM,
            edgecolor="white", linewidth=0.4, label="kept by judge (of 12)", zorder=3)
b2 = ax.bar([i + w / 2 for i in x], over, width=w, color=GREY,
            edgecolor="white", linewidth=0.4, label="chunks above 0.35", zorder=3)
for bars in (b1, b2):
    for b in bars:
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.35,
                str(int(b.get_height())), ha="center", va="bottom",
                fontsize=7.2, color=INK, zorder=5)
ax.set_xticks(list(x))
ax.set_xticklabels(TOPICS, fontsize=7.4)
ax.set_ylabel("count", fontsize=8)
ax.set_ylim(0, 13.5)
ax.set_yticks([0, 2, 4, 6, 8, 10, 12])
ax.legend(frameon=False, fontsize=7.2, loc="lower left", ncols=2,
          bbox_to_anchor=(0.0, 1.02, 1.0, 0.12), handletextpad=0.4,
          columnspacing=0.9)
fig.savefig(OUT_PDF)
fig.savefig(OUT_PNG, dpi=300)
print("fig7 restyled ->", OUT_PDF)
