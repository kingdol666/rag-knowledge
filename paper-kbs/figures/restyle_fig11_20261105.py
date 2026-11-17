#!/usr/bin/env python3
"""Restyle fig11_three_arms to the kbs_revision_20261104 house look (Okabe-Ito,
open spines, direct labels). Data re-derived from exp_r2_grade_corrected.json
with assertions against the printed figure values."""
from __future__ import annotations

import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
GRADE = REPO / "benchmark-suite/results/exp_r2_grade_corrected.json"
OUT_PDF = HERE.parent / "tex/journal_20p/figs/fig11_three_arms.pdf"
OUT_PNG = HERE.parent / "tex/journal_20p/figs/fig11_three_arms.png"

TEAL = "#009E73"
BLUE = "#0072B2"
VERM = "#D55E00"
GREY = "#8A99A3"
INK = "#20262E"

ARMS = [("a2", "Platform"), ("b", "Bare agent"), ("c", "Dense")]
METRICS = [("gold_hit", "gold-ID"), ("kw_ok", "keywords"), ("cited", "markers")]
EXPECTED = {("a2", "gold_hit"): 10, ("a2", "kw_ok"): 9, ("a2", "cited"): 9,
            ("b", "gold_hit"): 10, ("b", "kw_ok"): 9, ("b", "cited"): 7,
            ("c", "gold_hit"): 10, ("c", "kw_ok"): 9, ("c", "cited"): 2}

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

grade = json.loads(GRADE.read_text(encoding="utf-8"))["grades"]
counts = {}
for arm_key, _ in ARMS:
    g = grade[arm_key]
    assert g["n"] == 10, "n!=10 for %s" % arm_key
    for field, _ in METRICS:
        counts[(arm_key, field)] = g[field]

for k, v in EXPECTED.items():
    got = counts[k]
    assert got == v, "data drift at %s: graded %d, figure %d" % (k, got, v)

plt.rcParams.update({
    "font.family": "Arial", "font.size": 8,
    "axes.edgecolor": INK, "axes.labelcolor": INK,
    "xtick.color": INK, "ytick.color": INK, "text.color": INK,
    "axes.spines.top": False, "axes.spines.right": False,
    "pdf.fonttype": 42,
})
fig, ax = plt.subplots(figsize=(3.35, 2.05), layout="constrained")
x = range(len(ARMS))
w = 0.26
series_colors = [BLUE, GREY, VERM]
for mi, (field, label) in enumerate(METRICS):
    vals = [counts[(k, field)] for k, _ in ARMS]
    xs = [i + (mi - 1) * w for i in x]
    ax.bar(xs, vals, width=w * 0.92, color=series_colors[mi],
           edgecolor="white", linewidth=0.4, label=label, zorder=3)
    for xi, v in zip(xs, vals):
        ax.text(xi, v + 0.25, str(v), ha="center", va="bottom",
                fontsize=7.2, color=INK, zorder=5)
ax.axhline(10, ls=(0, (4, 3)), lw=0.8, color=GREY, zorder=1)
ax.set_xticks(list(x), [lbl for _, lbl in ARMS], fontsize=8)
ax.set_ylim(0, 11.8)
ax.set_yticks([0, 2, 4, 6, 8, 10])
ax.set_ylabel("questions (of 10)", fontsize=8)
ax.legend(frameon=False, fontsize=7.2, loc="lower left", ncols=3,
          bbox_to_anchor=(0.0, 1.02, 1.0, 0.12), handletextpad=0.4,
          columnspacing=0.9)
fig.savefig(OUT_PDF)
fig.savefig(OUT_PNG, dpi=300)
print("fig11 restyled ->", OUT_PDF)
