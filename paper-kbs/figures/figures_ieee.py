#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IEEE TII figures for the QDCVR paper.

Sizes: single column 3.5 in (89 mm), double column 7.16 in (181 mm).
Style: Okabe-Ito palette, sans, thin frames — IEEE two-column layout.
All quantitative figures read the released experiment JSONs.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 7.0,
    "axes.linewidth": 0.5,
    "axes.edgecolor": "#444444",
    "savefig.dpi": 300,
})

C = {"blue": "#0072B2", "orange": "#E69F00", "green": "#009E73",
     "verm": "#D55E00", "pink": "#CC79A7", "sky": "#56B4E9",
     "yellow": "#F0E442", "grey": "#8C8C8C", "dgrey": "#555555"}

HERE = Path(__file__).resolve().parent
RES = HERE.parent / "experiments" / "results"
OUT = HERE / "ieee"
MM = 1 / 25.4
SC = 89 * MM      # single column width
DC = 181 * MM     # double column width


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.png", bbox_inches="tight")
    plt.close(fig)
    print(f"saved {name}")


def box(ax, x, y, w, h, text, fc="#FFFFFF", ec="#444444", fs=6.0,
        lw=0.6, tc="#111111"):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.02,rounding_size=0.6",
                                fc=fc, ec=ec, lw=lw, zorder=3))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color=tc, zorder=4, linespacing=1.2)


def arrow(ax, x1, y1, x2, y2, color="#555555", lw=0.7, ms=5, ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                 mutation_scale=ms, color=color, lw=lw,
                                 linestyle=ls, zorder=2, shrinkA=1, shrinkB=1))


# ---------------------------------------------------------------- fig1 arch
def fig_arch():
    fig, ax = plt.subplots(figsize=(DC, 84 * MM))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 46)
    ax.axis("off")

    def layer(y, h, label):
        ax.add_patch(FancyBboxPatch((16.5, y), 82.5, h,
                     boxstyle="round,pad=0.02,rounding_size=0.8",
                     fc="#F7F7F7", ec="#BBBBBB", lw=0.5, zorder=1))
        ax.text(17.3, y + h - 0.7, label, fontsize=5.4, color="#777777",
                style="italic", va="top")

    layer(37.2, 8.2, "Clients / agentic orchestration (chat API)")
    for i, t in enumerate(["Web UI\nNuxt 3", "HTTP API\nREST+SSE",
                           "CLI", "MCP\nclients"]):
        box(ax, 18 + i * 11.6, 38.0, 10.6, 4.6, t, fc="#EDF3FA",
            ec=C["blue"], fs=5.6)
    box(ax, 66, 38.0, 15, 4.6, "14 chat engines\n(omp, Claude, ACP ...)",
        fc="#FFF4E6", ec=C["orange"], fs=5.6)
    box(ax, 83, 38.0, 14.6, 4.6, "Lane gating\n+ sub-agent budget",
        fc="#FFF4E6", ec=C["orange"], fs=5.6)

    layer(25.4, 10.6, "Retrieval lanes (Sec. IV)")
    box(ax, 18, 26.1, 24.5, 7.0,
        "Lane A Search\nquery rewrite -> dense top-30\n-> judging gate",
        fc="#E8F5F1", ec=C["green"], fs=5.6)
    box(ax, 45.5, 26.1, 24.5, 7.0,
        "Lane B Librarian\ncatalog -> scan -> judge\n(batch<=6) -> read",
        fc="#E8F5F1", ec=C["green"], fs=5.6)
    box(ax, 73, 26.1, 24.5, 7.0,
        "Lane C Hybrid\nmerge -> judge -> cut\n-> top-5 read (one call)",
        fc="#E8F5F1", ec=C["green"], fs=5.6)
    arrow(ax, 42.6, 29.6, 45.4, 29.6, color=C["verm"], lw=0.8, ms=4)
    ax.text(44.0, 30.6, "fallback", fontsize=5.0, color=C["verm"],
            ha="center")

    layer(12.2, 12.0, "MCP tool layer (97 tools, 8 groups) / domain services")
    groups = ["search\n(4)", "graph\n(11)", "judge\n(1)", "exp.\n(25)",
              "SOUL\n(22)", "ingest\n(9)", "lifecycle\n(12)", "fs\n(13)"]
    for i, t in enumerate(groups):
        box(ax, 18 + i * 10.2, 18.0, 9.3, 4.2, t, fc="#F3EEF8",
            ec="#7A6FA0", fs=5.2)
    svc = ["Vector svc\nChroma+HNSW", "Two-stage\nBM25+graph",
           "Graph svc\nNeo4j 5", "Experience\ncases", "Laya judge\nworker"]
    for i, t in enumerate(svc):
        box(ax, 18 + i * 16.3, 12.8, 15.2, 4.6, t, fc="#FDF1EC",
            ec=C["verm"], fs=5.2)

    stores = ["Tree FS\nmd+registry", "ChromaDB\nBGE-M3 1024-d",
              "Neo4j 5.20\nDoc/KB/Tag", "BM25\njieba invert",
              "Model cache\nBGE-M3+Laya"]
    for i, t in enumerate(stores):
        box(ax, 18 + i * 16.3, 3.2, 15.2, 5.6, t, fc="#F2F2F2",
            ec=C["dgrey"], fs=5.2)
    ax.text(17.3, 9.4, "Storage", fontsize=5.4, color="#777777",
            style="italic")

    for x in (50,):
        arrow(ax, x, 37.1, x, 36.2, lw=0.9)
        arrow(ax, x, 25.3, x, 24.4, lw=0.9)
        arrow(ax, x, 12.1, x, 9.2, lw=0.9)

    # ingestion column
    ax.add_patch(FancyBboxPatch((0.5, 3.2), 14.6, 42.2,
                 boxstyle="round,pad=0.02,rounding_size=0.8",
                 fc="#FBFBFB", ec="#BBBBBB", lw=0.5, zorder=1))
    ax.text(7.8, 44.6, "Ingestion", fontsize=5.4, color="#777777",
            style="italic", ha="center")
    steps = ["Upload\nPDF/Office/scan", "Parse\nMinerU OCR",
             "Semantic split\n>30 k chars", "Tags+desc\ncontent-derived",
             "Index\nvec+graph+BM25", "Post-check\nretrievable"]
    y = 39.4
    for i, t in enumerate(steps):
        box(ax, 1.6, y, 12.4, 4.6, t, fc="#FFFFFF", ec=C["blue"], fs=5.2)
        if i < len(steps) - 1:
            arrow(ax, 7.8, y - 0.05, 7.8, y - 1.7, lw=0.7)
        y -= 6.5
    arrow(ax, 15.2, 6.0, 17.9, 6.0, color=C["blue"], lw=0.8)
    save(fig, "fig1_architecture")


# ---------------------------------------------------------------- fig2 lanes
def fig_lanes():
    fig, ax = plt.subplots(figsize=(SC, 92 * MM))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    box(ax, 28, 92.5, 44, 5.2, "User query (natural language)",
        fc="#EDF3FA", ec=C["blue"], fs=6.6)

    rows = [
        ("Lane A - Search (pinned, fast)", 71.0,
         ["A0\nrewrite", "A1\ndense top-30", "A2\njudge gate",
          "A3\nevidence pack"]),
        ("Lane B - Librarian (all libraries)", 47.0,
         ["B0-1\ncatalog+scan", "B2\nroute", "B3\njudge batch<=6",
          "B4-5\nread+report"]),
        ("Lane C - Hybrid (one server call)", 23.0,
         ["C1\nvector||catalog", "C2\nmerge cap 12", "C3\njudge+rel.cut",
          "C4\nread top-5"]),
    ]
    for title, y, chips in rows:
        arrow(ax, 40, 92.4, 8, y + 12.6, lw=0.6, color=C["dgrey"])
        ax.text(2, y + 9.8, title, fontsize=6.2, color=C["green"],
                fontweight="bold", va="bottom")
        for i, c in enumerate(chips):
            box(ax, 2 + i * 24.7, y + 0.8, 22.7, 8.2, c, fc="#FFFFFF",
                ec=C["green"], fs=5.4)
            if i < 3:
                arrow(ax, 24.7 + i * 24.7, y + 4.9, 26.7 + i * 24.7,
                      y + 4.9, lw=0.7)

    box(ax, 30, 9.0, 40, 6.4,
        "Verification gate (Laya judge)\nfetched text, fail-closed",
        fc="#F3EEF8", ec="#7A6FA0", fs=6.0)
    for x in (14.0, 50.0, 86.0):
        arrow(ax, x, 23.8, x, 15.6, lw=0.7, color=C["dgrey"])
    box(ax, 22, 0.2, 56, 5.4,
        "zero survivors -> explicit not-found report\n(terminal state; escalate Lane A -> B once)",
        fc="#FBEDEA", ec=C["verm"], fs=5.8)
    arrow(ax, 50, 8.9, 50, 5.8, color=C["verm"], lw=0.8)
    arrow(ax, 8.5, 71.8, 8.5, 3.0, color=C["verm"], lw=0.7, ls=(0, (3, 2)))
    arrow(ax, 8.5, 3.0, 21.9, 3.0, color=C["verm"], lw=0.7, ls=(0, (3, 2)))
    ax.text(6.6, 36.0, "escalate", fontsize=5.2, color=C["verm"],
            rotation=90, va="center")
    save(fig, "fig2_lanes")


# ------------------------------------------------------- fig3 tool layer
def fig_tool():
    s = json.loads((RES / "exp1_summary.json").read_text(encoding="utf-8"))["summary"]
    order = ["bm25", "dense", "rrf", "graph", "twostage", "fusion_only",
             "qdcvr_hybrid"]
    labels = ["BM25", "Dense", "RRF", "Graph", "2-stage", "Fusion",
              "QDCVR"]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(SC, 96 * MM),
                                 sharex=True)
    x = range(len(order))
    w = 0.27
    for k, (metric, mname) in enumerate([("hit@5", "Hit@5"),
                                         ("recall@5", "Recall@5"),
                                         ("mrr", "MRR")]):
        a1.bar([i + (k - 1) * w for i in x],
               [s[m][metric] for m in order], width=w,
               color=[C["blue"], C["sky"], C["green"]][k],
               edgecolor="white", linewidth=0.3, label=mname)
    a1.set_ylim(0, 1.08)
    a1.set_ylabel("Score")
    a1.legend(frameon=False, fontsize=6, ncol=3, loc="lower left",
              columnspacing=0.8, handlelength=1.0)
    a1.tick_params(length=2, labelsize=6.5)
    for sp in ("top", "right"):
        a1.spines[sp].set_visible(False)

    lats = [max(s[m]["latency_mean"], 0.001) for m in order]
    a2.bar(list(x), lats, color=[C["grey"], C["sky"], C["blue"], C["pink"],
                                 C["yellow"], C["orange"], C["green"]],
           edgecolor="white", linewidth=0.3)
    a2.set_yscale("log")
    a2.set_ylabel("Mean latency (s)")
    for xi, v in zip(x, lats):
        lbl = f"{v*1000:.0f}" if v >= 0.005 else f"{v*1000:.1f}"
        a2.text(xi, v * 1.3, lbl, ha="center", fontsize=5.6, color="#333333")
    a2.set_ylim(0.0005, 3)
    a2.set_xticks(list(x))
    a2.set_xticklabels(labels, fontsize=6.5)
    a2.tick_params(length=2, labelsize=6.5)
    a2.set_xlabel("method (ms labels in (b) are milliseconds)", fontsize=6)
    for sp in ("top", "right"):
        a2.spines[sp].set_visible(False)
    fig.tight_layout(h_pad=0.7)
    save(fig, "fig3_tool")


# ------------------------------------------------------------ fig4 inflation
def fig_inflation():
    data = json.loads((RES / "exp1_retrieval.json").read_text(encoding="utf-8"))
    sys.path.insert(0, str(HERE.parent / "experiments"))
    from kbcommon import QUESTIONS
    qg = {q["qid"]: q["gold_doc_substrings"] for q in QUESTIONS}
    gold, nongold = [], []
    for row in data["rows"]:
        if row.get("method") != "qdcvr_hybrid" or "judge_scores" not in row:
            continue
        gold += row["judge_scores"]["gold"]
        for p, sc in row["judge_scores"]["all"].items():
            if not any(g.lower() in p.lower()
                       for g in qg[row["qid"]]):
                nongold.append(sc)
    import numpy as np
    rng = np.random.default_rng(7)
    fig, ax = plt.subplots(figsize=(SC, 56 * MM))
    for i, (vals, col) in enumerate([(gold, C["green"]),
                                     (nongold, C["verm"])]):
        xs = rng.normal(i, 0.05, size=len(vals))
        ax.scatter(xs, vals, s=8, color=col, alpha=0.65, edgecolors="none")
        ax.hlines(float(np.median(vals)), i - 0.2, i + 0.2, color=col,
                  lw=1.4)
    ax.axhline(0.5, color=C["dgrey"], lw=0.8, ls="--")
    ax.text(1.42, 0.508, "threshold 0.5", fontsize=5.8, color=C["dgrey"],
            ha="right")
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Gold\n(n=17)", "Non-gold\n(n=174)"], fontsize=6.5)
    ax.set_ylabel("Judge score", fontsize=7)
    ax.set_ylim(0.42, 1.03)
    med_n = float(np.median(nongold))
    med_g = float(np.median(gold))
    ax.annotate(f"med {med_g:.2f}", (0.22, med_g + 0.006), fontsize=5.8,
                color=C["green"], va="bottom")
    ax.annotate(f"med {med_n:.2f}", (0.30, 0.975), fontsize=5.8,
                color=C["verm"], va="top")
    ax.tick_params(length=2, labelsize=6.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    save(fig, "fig4_inflation")


# ------------------------------------------------------------- fig5 margin
def fig_margin():
    d = json.loads((RES / "exp3_abstention.json").read_text(encoding="utf-8"))
    rp = d["cut_replay"]
    margins = sorted(float(k) for k in rp)
    golds = [rp[str(m)]["gold_kept"] if str(m) in rp else rp[m]["gold_kept"]
             for m in margins]
    kept = [rp[str(m)]["mean_kept"] if str(m) in rp else rp[m]["mean_kept"]
            for m in margins]
    fig, ax = plt.subplots(figsize=(SC, 52 * MM))
    ax.plot(margins, golds, "-o", color=C["blue"], lw=1.1, ms=3.2,
            label="golds kept (of 17)")
    ax.set_xlabel("relative cut margin (best $-$ m)")
    ax.set_ylabel("golds kept", color=C["blue"])
    ax.set_ylim(6, 17.6)
    ax.tick_params(length=2, labelsize=6.5)
    ax2 = ax.twinx()
    ax2.plot(margins, kept, "-s", color=C["verm"], lw=1.1, ms=3.0,
             label="mean kept set size")
    ax2.set_ylabel("mean kept set size (of 12)", color=C["verm"])
    ax2.set_ylim(6, 12.4)
    ax2.tick_params(length=2, labelsize=6.5)
    ax.axvline(0.15, color=C["dgrey"], lw=0.7, ls="--")
    ax.text(0.152, 7.0, "shipped 0.15", fontsize=5.6, color=C["dgrey"],
            rotation=90, va="bottom")
    ax.axvline(0.20, color=C["green"], lw=0.7, ls="--")
    ax.text(0.205, 7.0, "0.20", fontsize=5.6, color=C["green"], rotation=90,
            va="bottom")
    for sp in ("top",):
        ax.spines[sp].set_visible(False)
        ax2.spines[sp].set_visible(False)
    fig.tight_layout()
    save(fig, "fig5_margin")


# --------------------------------------------------------------- fig6 ood
def fig_ood():
    d = json.loads((RES / "exp3_abstention.json").read_text(encoding="utf-8"))
    pr = d["probes"]
    topics = ["lithium\nthermal run.", "vaccination\nschedule",
              "Python\nconcurrency", "mold\nvent design"]
    kept = [p["kept_n"] for p in pr]
    over = [p["vector_above_0.35"] for p in pr]
    x = range(len(pr))
    w = 0.36
    fig, ax = plt.subplots(figsize=(SC, 50 * MM))
    ax.bar([i - w / 2 for i in x], kept, width=w, color=C["verm"],
           label="judged candidates kept (of 12)", edgecolor="white",
           linewidth=0.3)
    ax.bar([i + w / 2 for i in x], over, width=w, color=C["sky"],
           label="dense chunks above 0.35", edgecolor="white", linewidth=0.3)
    for xi, v in zip(x, kept):
        ax.text(xi - w / 2, v + 0.25, str(v), ha="center", fontsize=5.6)
    ax.set_xticks(list(x))
    ax.set_xticklabels(topics, fontsize=5.8)
    ax.set_ylabel("count")
    ax.set_ylim(0, 16)
    ax.legend(frameon=False, fontsize=5.8, loc="lower center",
              bbox_to_anchor=(0.5, 1.0), ncol=2,
              columnspacing=1.0, handlelength=1.2)
    ax.tick_params(length=2, labelsize=6.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    save(fig, "fig6_ood")


# ---------------------------------------------------------------- fig7 e2e
def fig_e2e():
    runs = []
    for f in sorted((RES / "exp2_lanes").glob("run_*.json")):
        runs.append(json.loads(f.read_text(encoding="utf-8"))["run"])
    arms = ["search", "librarian", "hybrid", "bare"]
    arm_lbl = ["Search", "Librarian", "Hybrid", "Bare"]
    colors = [C["blue"], C["green"], C["orange"], C["grey"]]
    qids = ["Q2", "Q4", "Q6", "Q7"]
    qlbl = ["EL delam.", "POE barrier", "weight alarm", "TC0 root"]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(SC, 96 * MM))
    w = 0.19
    for k, arm in enumerate(arms):
        vals, turs = [], []
        for q in qids:
            r = next((r for r in runs if r["arm"] == arm and r["qid"] == q),
                     None)
            vals.append(r["wall_s"] if r else 0)
            turs.append((r["turns"] if r and r.get("turns") else 0))
        xs = [i + (k - 1.5) * w for i in range(len(qids))]
        a1.bar(xs, vals, width=w, color=colors[k], edgecolor="white",
               linewidth=0.3, label=arm_lbl[k])
        for xi, v, t in zip(xs, vals, turs):
            if t:
                a1.text(xi, v + 3, str(t), ha="center", fontsize=4.8,
                        color="#333333")
    a1.set_ylabel("wall time (s)")
    a1.legend(frameon=False, fontsize=5.8, ncol=4, loc="upper right",
              columnspacing=0.8, handlelength=1.0)
    a1.set_ylim(0, 130)
    a1.set_xticks(range(len(qids)))
    a1.set_xticklabels([f"{q}" for q in qlbl], fontsize=6)
    a1.tick_params(length=2, labelsize=6.5)
    a1.set_title("(a) round-1 wall time (labels = turns)", fontsize=6.5,
                 loc="left")
    for sp in ("top", "right"):
        a1.spines[sp].set_visible(False)

    for k, arm in enumerate(arms):
        rs = [r for r in runs if r["arm"] == arm]
        if not rs:
            continue
        hit = sum(1 for r in rs if r["doc_citation_hit"]) / len(rs)
        turns = sum((r["turns"] or 0) for r in rs) / len(rs)
        xd = (k - 1.5) * 1.0
        a2.scatter([turns + xd], [hit], s=34, color=colors[k], zorder=3,
                   edgecolors="white", linewidths=0.5)
        offs = {0: (5, -13), 1: (-6, 8), 2: (1, -13), 3: (7, 6)}
        ha = {0: "left", 1: "right", 2: "center", 3: "left"}
        a2.annotate(arm_lbl[k], (turns + xd, hit), textcoords="offset points",
                    xytext=offs[k], ha=ha[k], fontsize=5.8)
    a2.set_xlabel("mean agent turns per run (round 1)")
    a2.set_ylabel("citation gold-hit rate")
    a2.set_ylim(-0.08, 1.12)
    a2.set_xlim(0, 7.4)
    a2.grid(True, lw=0.25, color="#E5E5E5")
    a2.tick_params(length=2, labelsize=6.5)
    a2.set_title("(b) groundedness vs. turns", fontsize=6.5, loc="left")
    for sp in ("top", "right"):
        a2.spines[sp].set_visible(False)
    fig.tight_layout(h_pad=0.7)
    save(fig, "fig7_e2e")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    todo = {"1": fig_arch, "2": fig_lanes, "3": fig_tool,
            "4": fig_inflation, "5": fig_margin, "6": fig_ood,
            "7": fig_e2e}
    for k, fn in todo.items():
        if which in ("all", k):
            fn()
