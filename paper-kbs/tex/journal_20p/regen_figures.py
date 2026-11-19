#!/usr/bin/env python3
"""Regenerate two data figures from frozen artefacts (revision 2026-11-11).

- fig_retrieval_comparison: panel (b) now shows only the seven LOGGED configs
  (derived Judge-as-filter removed) so it no longer contradicts the caption.
- fig_ladder_optimization: adds panel (b) per-question cost (calls + KB, log)
  and annotates the significant tiered-vs-flat contrast.

Outputs vector PDF + 300 dpi PNG into figs/. Colour-blind-safe palette.
"""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import NullFormatter, NullLocator
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "..", "experiments", "results")
FB = os.path.join(HERE, "..", "..", "..", "review", "experiment-redesign-20261101",
                  "artifacts", "final_bench")
FIG = os.path.join(HERE, "figs")

# Okabe-Ito colour-blind-safe palette
BLUE, ORANGE, SKY, GREEN, VERM, GREY = ("#0072B2", "#E69F00", "#56B4E9",
                                       "#009E73", "#D55E00", "#999999")
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9,
    # Origin-style: full box frame, inward ticks, clean white canvas
    "axes.spines.top": True, "axes.spines.right": True,
    "axes.linewidth": 0.9, "xtick.major.width": 0.9, "ytick.major.width": 0.9,
    "xtick.direction": "in", "ytick.direction": "in",
    "xtick.top": True, "ytick.right": True,
    "axes.facecolor": "white", "figure.facecolor": "white",
    "figure.dpi": 300, "savefig.dpi": 300,
})

def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def save(fig, name):
    fig.savefig(os.path.join(FIG, name + ".pdf"), bbox_inches="tight")
    fig.savefig(os.path.join(FIG, name + ".png"), bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)

# ---------------- fig_retrieval_comparison ----------------
s1 = load(os.path.join(RES, "exp1_summary.json"))["summary"]
s10 = load(os.path.join(RES, "exp10_papers_toollayer.json"))["summary"]
order = ["bm25", "dense", "rrf", "graph", "twostage", "fusion_only", "qdcvr_hybrid"]
labels = ["BM25", "Dense", "RRF", "Graph", "Two-stage", "Fusion-only", "HMRS-Hybrid"]
fig, (a, b) = plt.subplots(1, 2, figsize=(7, 2.5),
                           gridspec_kw={"width_ratios": [2.1, 1]})
x = np.arange(len(order)); w = 0.26
for i, (met, c) in enumerate([("hit@5", BLUE), ("recall@5", GREEN), ("mrr", ORANGE)]):
    vals = [s1[k][met] for k in order]
    a.bar(x + (i - 1) * w, vals, w, color=c, label=met.upper().replace("@5", "@5"))
    for xx, v in zip(x + (i - 1) * w, vals):
        a.text(xx, v + 0.02, f"{v:.2f}", ha="center", va="bottom", fontsize=7, rotation=90)
a.set_xticks(x); a.set_xticklabels(labels, rotation=30, ha="right")
a.set_ylim(0, 1.18); a.set_ylabel("Score (top-5 document lists)")
a.set_title("(a) Industrial corpus: 42 documents, 16 questions", loc="left", fontsize=10)
a.legend(ncol=3, frameon=False, fontsize=8, loc="lower center", bbox_to_anchor=(0.5, 1.16))
a.grid(axis="y", lw=0.4, alpha=0.5); a.set_axisbelow(True)

order_b = ["bm25", "dense", "rrf", "graph", "twostage", "fusion_only", "judged"]
lab_b = ["BM25", "Dense", "RRF", "Graph", "Two-stage", "Fusion-only", "HMRS-Hybrid"]
vals = [s10[k]["hit@5"] for k in order_b]
b.bar(np.arange(len(order_b)), vals, 0.62, color=BLUE)
for xx, v in zip(np.arange(len(order_b)), vals):
    b.text(xx, v + 0.02, f"{v:.2f}", ha="center", va="bottom", fontsize=7)
b.set_xticks(np.arange(len(order_b))); b.set_xticklabels(lab_b, rotation=30, ha="right")
b.set_ylim(0, 1.12); b.set_ylabel("Hit@5")
b.set_title("(b) arXiv corpus: 79 papers, 10 questions", loc="left", fontsize=10)
b.grid(axis="y", lw=0.4, alpha=0.5); b.set_axisbelow(True)
fig.tight_layout()
save(fig, "fig_retrieval_comparison")

# ---------------- fig_ladder_optimization ----------------
s6 = load(os.path.join(FB, "s6_stats.json"))["per_arm"]
tr = load(os.path.join(FB, "s4_traces_final.json"))
arms = ["A0", "A0f", "A0h", "PD", "A1b", "A2", "A3", "A1-readall"]
lab = ["A0\ntiered", "A0f\n+full-win", "A0h\n+chunk", "PD\nprecise", "A1b\nflat", "A2\nno-gate", "A3\nname-only", "read-all\nbound"]
rate = [s6[a]["gold_rate"] for a in arms]
ci = [s6[a]["gold_ci95"] for a in arms]
calls = []
for a in arms:
    rows = tr[a]
    ck = "calls" if "calls" in rows[0] else None
    calls.append(sum(r.get(ck, 0) for r in rows) / len(rows) if ck else np.nan)
kb = [s6[a]["avg_bytes_gold"] / 1000.0 for a in arms]

fig, (a, b) = plt.subplots(1, 2, figsize=(7, 2.5),
                           gridspec_kw={"width_ratios": [1.5, 1]})
cols = [GREY, SKY, BLUE, VERM, ORANGE, GREY, GREY, GREEN]
xx = np.arange(len(arms))
err = np.array([[r - c[0], c[1] - r] for r, c in zip(rate, ci)]).T
a.bar(xx, rate, 0.66, color=cols, yerr=err, capsize=3, error_kw={"lw": 0.9})
a.axhline(rate[0], ls="--", lw=0.9, color=GREY)
for i, (r, c) in enumerate(zip(rate, ci)):
    a.text(i, c[1] + 0.02, f"{r*100:.1f}", ha="center", va="bottom", fontsize=7)
a.set_xticks(xx); a.set_xticklabels(lab, fontsize=7.5)
a.set_ylim(0, 1.12); a.set_ylabel("Gold-string containment (72 q)")
a.set_title("(a) Containment, Wilson 95% CI", loc="left", fontsize=10)
a.annotate("A0h vs A1b: 13-0, p=0.00024", xy=(2, rate[2]), xytext=(2.4, 0.98),
           fontsize=7.5, color=BLUE, arrowprops=dict(arrowstyle="->", lw=0.7, color=BLUE))
a.grid(axis="y", lw=0.4, alpha=0.5); a.set_axisbelow(True)

w = 0.38
b.bar(xx - w/2, calls, w, color=BLUE, label="search calls / q")
b.set_yscale("log")
b.yaxis.set_minor_formatter(NullFormatter())
b.yaxis.set_minor_locator(NullLocator())
b.set_yticks([10, 100, 1000])
b.set_ylabel("calls / question (log)", color=BLUE)
b.tick_params(axis="y", labelcolor=BLUE)
b2 = b.twinx()
b2.bar(xx + w/2, kb, w, color=ORANGE, label="KB read / q")
b2.set_yscale("log")
b2.yaxis.set_minor_formatter(NullFormatter())
b2.yaxis.set_minor_locator(NullLocator())
b2.set_yticks([10, 100, 1000, 10000])
b2.set_ylabel("KB read / question (log)", color=ORANGE)
b2.tick_params(axis="y", labelcolor=ORANGE)
b2.spines["right"].set_visible(True)
b.set_xticks(xx); b.set_xticklabels([l.split("\n")[0] for l in lab], fontsize=7.5)
b.set_title("(b) Per-question cost (both dimensions)", loc="left", fontsize=10)
h1, l1 = b.get_legend_handles_labels(); h2, l2 = b2.get_legend_handles_labels()
b.legend(h1 + h2, l1 + l2, frameon=False, fontsize=7.5, loc="upper left")
fig.tight_layout()
save(fig, "fig_ladder_optimization")
print("done")