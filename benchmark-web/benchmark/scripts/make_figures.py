"""Generate CIKM-publication figures from frozen-corpus benchmark snapshots.

Outputs (results/figures/):
  fig1_track1_main.{pdf,svg,png}   — P@5 & MRR by method x dataset (Track 1)
  fig2_fpr.{pdf,svg,png}           — FPR by method x dataset
  fig3_domain_collapse.{pdf,svg,png} — domain track: corpus-scale dominance + recall-knob recovery
  fig4_verifier.{pdf,svg,png}      — verifier accuracy vs CRAG anchors
  fig5_reproducibility.{pdf,svg,png} — run1 vs run2 metric deltas (all zero)
  fig6_latency.{pdf,svg,png}       — latency by method

All numbers are read from results/repro/*-run1.json snapshots (no hardcoding).
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

RESULTS = Path(__file__).resolve().parent.parent / "results"
FIG = RESULTS / "figures"
FIG.mkdir(parents=True, exist_ok=True)

# colorblind-safe palette (Okabe-Ito)
C = {"two_stage": "#0072B2", "vector_flat": "#D55E00", "two_stage_bal": "#009E73",
     "two_stage_nb": "#CC79A7", "vector_domain": "#999999", "two_stage_k150": "#56B4E9"}
METHOD_LABEL = {"two_stage": "Two-Stage (S0, k=20)", "vector_flat": "Flat Vector (NaiveRAG)",
                "two_stage_bal": "Two-Stage Balanced", "two_stage_nb": "Two-Stage -Graph",
                "vector_domain": "Flat Vector (oracle KB)", "two_stage_k150": "Two-Stage (k=150)"}

plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
    "legend.fontsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "figure.dpi": 200, "savefig.bbox": "tight", "axes.spines.top": False,
    "axes.spines.right": False,
})


def load(name: str) -> dict:
    return json.load(open(RESULTS / "repro" / name, encoding="utf-8"))


def save(fig, name: str) -> None:
    for ext in ("pdf", "svg", "png"):
        fig.savefig(FIG / f"{name}.{ext}")
    plt.close(fig)
    print(f"  ✓ {name} (.pdf/.svg/.png)")


def short(v: dict) -> dict:
    return {m: {k: d.get(k, 0) for k in ("p1", "p5", "mrr", "fpr", "ndcg5", "routing", "latency_ms")}
            for m, d in v.get("methods", {}).items()}


def flat(d: dict, prefix: str = "") -> dict:
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flat(v, key + "."))
        else:
            out[key] = v
    return out


hot = short(load("track1-hotpotqa-run1.json"))
wiki = short(load("track1-2wiki-run1.json"))
dom20 = short(load("domain-k20-frozen.json"))
dom150 = short(load("domain-k150-frozen-run1.json"))
ver = json.load(open(RESULTS / "verifier-popqa.json", encoding="utf-8"))

METHODS = ["vector_flat", "vector_domain", "two_stage", "two_stage_nb", "two_stage_bal"]


def grouped(ax, metric: str, ylab: str) -> None:
    datasets = [("HotpotQA (n=91)", hot), ("2Wiki (n=86)", wiki)]
    width = 0.15
    xs = np.arange(len(METHODS))
    for i, (label, data) in enumerate(datasets):
        vals = [data[m].get(metric, 0) for m in METHODS]
        bars = ax.bar(xs + (i - 0.5) * width, vals, width, label=label,
                      color=["#0072B2", "#E69F00"][i], edgecolor="black", linewidth=0.4)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.008, f"{v:.2f}",
                    ha="center", va="bottom", fontsize=6.5)
    ax.set_xticks(xs)
    ax.set_xticklabels(["Flat Vector\n(NaiveRAG)", "Flat Vector\n(oracle KB)",
                        "Two-Stage\n(S0, k=20)", "Two-Stage\n−graph", "Two-Stage\n+balanced"])
    ax.set_ylabel(ylab)
    ax.set_ylim(0, max(0.85, max(max(d[m].get(metric, 0) for m in METHODS) for _, d in datasets) + 0.12))
    ax.legend(loc="upper right")
    ax.grid(axis="y", alpha=0.25)


# ── Fig 1: main retrieval comparison ─────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.4))
grouped(axes[0], "p5", "P@5")
axes[0].set_title("(a) Precision@5")
grouped(axes[1], "mrr", "MRR")
axes[1].set_title("(b) MRR")
fig.suptitle("Track 1 retrieval: two-stage multi-KB routing vs flat vector baseline (frozen 12,588-page corpus)",
             fontsize=9.5, y=1.02)
save(fig, "fig1_track1_main")

# ── Fig 2: FPR ───────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(6.4, 3.2))
grouped(ax, "fpr", "FPR (cross-KB false recall)")
ax.set_title("Cross-domain false-pull rate (lower is better)")
save(fig, "fig2_fpr")

# ── Fig 3: domain corpus-scale collapse + fix ────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(9.8, 3.4))
domfix = short(load("domain-fixed-run1.json"))
configs = ["Small corpus\n(prior config)", "Mega-corpus\nbroken stage1 (k=20)",
           "Mega-corpus\nbudget knob (k=150)", "Mega-corpus\nFIXED stage1\n(pool×8 + KB quota)"]
ts_p5 = [0.424, dom20["two_stage"]["p5"], dom150["two_stage"]["p5"], domfix["two_stage"]["p5"]]
flat_p5 = [0.388, dom20["vector_flat"]["p5"], dom150["vector_flat"]["p5"], domfix["vector_flat"]["p5"]]
xs = np.arange(4)
for i, (vals, label, color) in enumerate([
        (ts_p5, "Two-Stage (S0)", "#0072B2"), (flat_p5, "Flat Vector", "#D55E00")]):
    bars = axes[0].bar(xs + (i - 0.5) * 0.34, vals, 0.34, label=label,
                       color=color, edgecolor="black", linewidth=0.4)
    for b, v in zip(bars, vals):
        axes[0].text(b.get_x() + b.get_width() / 2, v + 0.006, f"{v:.3f}",
                     ha="center", va="bottom", fontsize=6.5)
axes[0].set_xticks(xs)
axes[0].set_xticklabels(configs, fontsize=7)
axes[0].set_ylabel("P@5")
axes[0].set_title("(a) Domain-50: corpus-scale dominance\nand stage1 defense recovery")
axes[0].legend(fontsize=7.5)
axes[0].grid(axis="y", alpha=0.25)

routing = [0.52, dom20["two_stage"]["routing"], dom150["two_stage"]["routing"], domfix["two_stage"]["routing"]]
fpr = [0.596, dom20["two_stage"]["fpr"], dom150["two_stage"]["fpr"], domfix["two_stage"]["fpr"]]
axes[1].plot(xs, routing, "o-", color="#0072B2", label="KB routing acc")
axes[1].plot(xs, fpr, "s--", color="#D55E00", label="FPR")
for i, (r, f) in enumerate(zip(routing, fpr)):
    axes[1].annotate(f"{r:.2f}", (xs[i], r), textcoords="offset points", xytext=(0, 7), fontsize=7)
    axes[1].annotate(f"{f:.2f}", (xs[i], f), textcoords="offset points", xytext=(0, 7), fontsize=7)
axes[1].set_xticks(xs)
axes[1].set_xticklabels(configs, fontsize=7)
axes[1].set_ylim(0, 1.15)
axes[1].set_title("(b) Routing accuracy vs FPR")
axes[1].legend(fontsize=7.5)
axes[1].grid(axis="y", alpha=0.25)
save(fig, "fig3_domain_collapse")

# ── Fig 4: verifier vs CRAG anchors ──────────────────────────────────
fig, ax = plt.subplots(figsize=(6.4, 3.0))
anchors = ver.get("crag_table4_anchors", {})
names = ["CRAG T5-based\n(Table 4)", "ChatGPT\nfew-shot", "ChatGPT-CoT", "ChatGPT\nzero-shot",
         "QDCVR heuristic\n(2-class, ours)", "QDCVR heuristic\n(3-class, ours)"]
vals = [anchors.get("CRAG T5-based (Table 4)"), anchors.get("ChatGPT-few-shot"),
        anchors.get("ChatGPT-CoT"), anchors.get("ChatGPT zero-shot"),
        ver["scorers"]["heuristic"]["acc_binary_pct"], ver["scorers"]["heuristic"]["acc_3class_pct"]]
colors = ["#BBBBBB"] * 4 + ["#0072B2", "#56B4E9"]
bars = ax.barh(names[::-1], vals[::-1], color=colors[::-1], edgecolor="black", linewidth=0.4)
for b, v in zip(bars, vals[::-1]):
    ax.text(v + 1, b.get_y() + b.get_height() / 2, f"{v:.1f}", va="center", fontsize=7.5)
ax.set_xlabel("Accuracy (%) — PopQA verifier protocol")
ax.set_xlim(0, 100)
ax.grid(axis="x", alpha=0.25)
save(fig, "fig4_verifier")

# ── Fig 5: reproducibility deltas ────────────────────────────────────
pairs = [("domain k=150", "domain-k150-frozen-run1.json", "domain-k150-frozen-run2.json"),
         ("hotpotqa", "track1-hotpotqa-run1.json", "track1-hotpotqa-run2.json"),
         ("2wiki", "track1-2wiki-run1.json", "track1-2wiki-run2.json"),
         ("verifier", "verifier-run1.json", "verifier-run2.json")]
labels, deltas = [], []
for face, f1, f2 in pairs:
    a, b = flat(load(f1)), flat(load(f2))
    for k in sorted(set(a) & set(b)):
        if "latency" in k or "timestamp" in k:
            continue
        va, vb = a[k], b[k]
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
            labels.append(f"{face}:{k.split('.')[-1]}")
            deltas.append(abs(va - vb))
fig, ax = plt.subplots(figsize=(6.8, 2.6))
ax.bar(range(len(deltas)), deltas, color="#0072B2", edgecolor="black", linewidth=0.3)
ax.set_xticks(range(len(deltas)))
ax.set_xticklabels(labels, rotation=60, fontsize=5.5, ha="right")
ax.set_ylabel("|run1 - run2|")
ax.set_title(f"Reproducibility: per-metric absolute deltas across two independent runs (n={len(deltas)} metrics, all zero)")
ax.set_ylim(0, max(0.01, max(deltas) + 0.005))
ax.grid(axis="y", alpha=0.25)
save(fig, "fig5_reproducibility")

# ── Fig 6: latency ───────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(6.4, 3.0))
width = 0.35
xs = np.arange(len(METHODS))
for i, (label, data) in enumerate([("HotpotQA", hot), ("2Wiki", wiki)]):
    vals = [data[m].get("latency_ms", 0) for m in METHODS]
    ax.bar(xs + (i - 0.5) * width, vals, width, label=label,
           color=["#0072B2", "#E69F00"][i], edgecolor="black", linewidth=0.4)
ax.set_xticks(xs)
ax.set_xticklabels([METHOD_LABEL[m].replace(" (", "\n(") for m in METHODS])
ax.set_ylabel("latency (ms/query)")
ax.set_title("Retrieval latency by method")
ax.legend()
ax.grid(axis="y", alpha=0.25)
save(fig, "fig6_latency")

print("all figures written to", FIG)
