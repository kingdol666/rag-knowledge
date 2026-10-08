#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Publication figures for the KBS submission (QDCVR platform).

Style: Okabe-Ito colorblind-safe palette, Helvetica-like sans, single-column
90 mm / double-column 190 mm, 300 dpi PNG + vector PDF.
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
    "font.size": 7.5,
    "axes.linewidth": 0.6,
    "axes.edgecolor": "#444444",
    "savefig.dpi": 300,
    "figure.dpi": 150,
})

C = {"blue": "#0072B2", "orange": "#E69F00", "green": "#009E73",
     "verm": "#D55E00", "pink": "#CC79A7", "sky": "#56B4E9",
     "yellow": "#F0E442", "black": "#000000", "grey": "#8C8C8C",
     "lgrey": "#E8E8E8", "dgrey": "#555555"}

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "experiments" / "results"
OUT = HERE
MM = 1 / 25.4


def save(fig, name):
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.png", bbox_inches="tight")
    plt.close(fig)
    print(f"saved {name}.pdf/.png")


def box(ax, x, y, w, h, text, fc="#FFFFFF", ec="#444444", fs=7.5,
        lw=0.7, bold=False, style="round,pad=0.02,rounding_size=0.8",
        tc="#111111", zorder=3):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=style,
                                fc=fc, ec=ec, lw=lw, zorder=zorder))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color=tc, zorder=zorder + 1,
            fontweight="bold" if bold else "normal", linespacing=1.25)


def arrow(ax, x1, y1, x2, y2, color="#555555", lw=0.9, style="-|>",
          ms=6, zorder=2, ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                                 mutation_scale=ms, color=color, lw=lw,
                                 linestyle=ls, zorder=zorder,
                                 shrinkA=1, shrinkB=1))


# ===========================================================================
# Fig 1 — platform architecture (double column)
# ===========================================================================
def fig_architecture():
    fig, ax = plt.subplots(figsize=(190 * MM, 132 * MM))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 70)
    ax.axis("off")

    def layer(y, h, label, fc="#F7F7F7"):
        ax.add_patch(FancyBboxPatch((17.5, y), 81.5, h,
                                    boxstyle="round,pad=0.02,rounding_size=1.0",
                                    fc=fc, ec="#BBBBBB", lw=0.6, zorder=1))
        ax.text(18.4, y + h - 1.1, label, fontsize=6.2, color="#777777",
                style="italic", va="top", zorder=4)

    # ---- clients layer
    layer(60.0, 9.0, "Clients")
    for i, t in enumerate(["Web UI\n(Nuxt 3)", "HTTP API\n(REST + SSE)",
                           "CLI\n(ragctl)", "MCP clients\n(Claude & agents)"]):
        box(ax, 20 + i * 20, 60.6, 18, 5.6, t, fc="#EDF3FA", ec=C["blue"], fs=7)

    # ---- agentic orchestration layer
    layer(47.0, 11.5, "Agentic orchestration (chat API)")
    box(ax, 20, 47.6, 22, 6.6, "Chat engines\n14 harness adapters\n(omp, Claude, ACP, ...)",
        fc="#FFF4E6", ec=C["orange"], fs=6.8)
    box(ax, 45, 47.6, 24, 6.6, "Lane gating\nper-lane tool whitelists,\nturn budget 600 s",
        fc="#FFF4E6", ec=C["orange"], fs=6.8)
    box(ax, 72, 47.6, 25, 6.6, "Retrieval sub-agent\none delegated retriever,\n≤12 MCP calls per task",
        fc="#FFF4E6", ec=C["orange"], fs=6.8)

    # ---- retrieval lanes layer
    layer(33.0, 12.5, "Retrieval lanes (Section 4)")
    box(ax, 20, 33.6, 25, 7.6,
        "Lane A  Search\nquery rewrite → dense top-30\n→ citation-only judging gate",
        fc="#E8F5F1", ec=C["green"], fs=6.6)
    box(ax, 47.5, 33.6, 25, 7.6,
        "Lane B  Librarian\ncatalog → scan → route → judge\n(≤6 refs/batch) → read survivors",
        fc="#E8F5F1", ec=C["green"], fs=6.6)
    box(ax, 75, 33.6, 22, 7.6,
        "Lane C  Hybrid\nsingle server-side call:\nmerge → judge → cut → read",
        fc="#E8F5F1", ec=C["green"], fs=6.6)
    arrow(ax, 45.1, 37.4, 47.4, 37.4, color=C["verm"], lw=1.0, ms=5)
    ax.text(46.25, 38.5, "fallback", fontsize=5.6, color=C["verm"], ha="center")

    # ---- MCP tool layer
    layer(21.5, 10.0, "MCP tool layer — kb-mcp server (97 tools in 8 groups)")
    groups = ["search\n(4)", "graph\n(11)", "judging\n(1)", "experience\n(25)",
              "SOUL\n(22)", "ingest &\nparse (9)", "KB life-\ncycle (12)",
              "fs / tags\n(13)"]
    for i, t in enumerate(groups):
        box(ax, 19.5 + i * 10.05, 22.2, 9.2, 5.6, t, fc="#F3EEF8",
            ec="#7A6FA0", fs=6.0)

    # ---- services layer
    layer(10.5, 9.5, "Domain services (FastAPI)")
    svc = ["Vector service\nChromaDB per-KB\nHNSW cosine", "Two-stage\nBM25 + graph\n→ dense refine",
           "Graph service\nNeo4j 5\nDoc/KB/Tag", "Experience\nversioned cases\n+ auto-summary",
           "Laya judge\nresident worker,\nrubric protocol"]
    for i, t in enumerate(svc):
        box(ax, 19 + i * 16.1, 11.2, 15, 6.6, t, fc="#FDF1EC",
            ec=C["verm"], fs=6.0)

    # ---- storage layer
    stores = ["Tree file system\nMarkdown +\nmetadata registry",
              "ChromaDB\nper-KB collection\nBGE-M3 1024-d",
              "Neo4j 5.20\nBELONGS_TO /\nRELATED_TO",
              "BM25 index\njieba inverted,\nincremental",
              "Model cache\nBGE-M3 +\nLaya checkpoint"]
    for i, t in enumerate(stores):
        box(ax, 19 + i * 16.1, 2.0, 15, 6.2, t, fc="#F2F2F2",
            ec=C["dgrey"], fs=5.9)

    # vertical arrows between layers
    x = 50
    arrow(ax, x, 59.9, x, 54.4, lw=1.1)
    arrow(ax, x, 46.9, x, 41.4, lw=1.1)
    arrow(ax, x, 32.9, x, 31.7, lw=1.1)
    arrow(ax, x, 21.4, x, 20.2, lw=1.1)
    arrow(ax, x, 10.4, x, 8.4, lw=1.1)

    # ---- ingestion pipeline (left column)
    ax.add_patch(FancyBboxPatch((1.0, 2.0), 14.5, 67.0,
                                boxstyle="round,pad=0.02,rounding_size=1.0",
                                fc="#FBFBFB", ec="#BBBBBB", lw=0.6, zorder=1))
    ax.text(8.2, 66.6, "Ingestion pipeline", fontsize=6.2, color="#777777",
            style="italic", ha="center")
    steps = ["Upload\n(PDF/Office/scan)", "Parse\nMinerU OCR engine",
             "Semantic split\n>30 k chars, agent plan",
             "Content-derived tags\n+ descriptions",
             "Index\nvector + graph + BM25",
             "Post-condition check\nretrievability gate"]
    y = 60.5
    for i, s in enumerate(steps):
        box(ax, 2.2, y, 12.1, 6.6, s, fc="#FFFFFF", ec=C["blue"], fs=6.1)
        if i < len(steps) - 1:
            arrow(ax, 8.2, y - 0.1, 8.2, y - 2.4, lw=0.9)
        y -= 9.2
    arrow(ax, 15.6, 5.1, 18.9, 5.1, lw=1.0, color=C["blue"])
    ax.text(99, 0.3, "Solid arrows: runtime call path; the ingestion pipeline feeds all four stores.",
            fontsize=5.8, color="#777777", ha="right")
    save(fig, "fig1_architecture")


# ===========================================================================
# Fig 2 — three-lane retrieval flow (double column)
# ===========================================================================
def fig_lanes():
    fig, ax = plt.subplots(figsize=(190 * MM, 112 * MM))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 58)
    ax.axis("off")

    box(ax, 36, 52.5, 28, 4.8, "User query (natural language)", fc="#EDF3FA",
        ec=C["blue"], fs=8, bold=True)

    heads = [("Lane A — Search\nfast vector + verification gate", 1.5),
             ("Lane B — Librarian\nhierarchical navigation", 34.5),
             ("Lane C — Hybrid\nserver-side orchestration", 67.5)]
    for title, x in heads:
        box(ax, x, 45.2, 31, 5.4, title, fc="#E8F5F1", ec=C["green"],
            fs=7.0, bold=False)
        arrow(ax, 46 + (x / 67.5) * 8, 52.4, x + 15.5, 50.8, lw=1.0)

    a_steps = [
        "A0  Query rewrite\nsubject × attribute × constraints;\nexperience-first for incident queries",
        "A1  Dense wide-net\nkb_search_vector top-30, thr 0.35,\nper-doc dedupe, cross-KB balance",
        "A2  Judging gate (cite-only refs)\nkb_laya_judge batch ≤6; server fetches\ntext; score never overrules verdict",
        "A3  Evidence pack\nonly verified passages returned;\nconfidence P0/P1/P2 per citation",
    ]
    b_steps = [
        "B0–B1  Catalog + description scan\nkb_list → per-shelf document listing;\ndescriptions are claims, not facts",
        "B2  Query-shape routing\nliteral/enumeration → machine scan;\nsemantic → judging path",
        "B3  Judging gate\nbatch ≤6 refs; threshold 0.5 semantic /\n0.3 enumeration; fail-closed on errors",
        "B4–B5  Read survivors + report\nkb_doc_read ≤2000 chars; five-part report\n(sources, confidence, blind spots)",
    ]
    c_steps = [
        "C1  Dual-lane candidates\nvector top-30 ∥ catalog keyword rank\n(one MCP call, all server-side)",
        "C2  Merge + cap\n(kb, doc) dedupe; agreed docs first;\ncandidate_cap = 12",
        "C3  Judge + relative cut\nLaya verdicts; keep ≥ best−0.15 with\ntop-5 floor; cross-domain anchor guard",
        "C4  Full-text read top-5\n≤2000 chars each → grounded answer\nwith per-citation lane + score",
    ]
    for col_x, steps in ((1.5, a_steps), (34.5, b_steps), (67.5, c_steps)):
        y = 36.4
        for i, s in enumerate(steps):
            box(ax, col_x, y, 31, 7.0, s, fc="#FFFFFF", ec=C["green"], fs=6.3)
            if i < len(steps) - 1:
                arrow(ax, col_x + 15.5, y - 0.05, col_x + 15.5, y - 1.75, lw=0.9)
            y -= 9.0
    # bottom row: not-found box
    box(ax, 39, 1.2, 24, 4.6, "Honest not-found report\n(terminal state)",
        fc="#FBEDEA", ec=C["verm"], fs=6.8)
    # A -> B fallback (zero survivors)
    arrow(ax, 17, 8.4, 17, 3.5, lw=1.0, color=C["verm"], ls=(0, (4, 2)))
    arrow(ax, 17, 3.5, 34.4, 3.5, lw=1.0, color=C["verm"], ls=(0, (4, 2)))
    arrow(ax, 34.4, 3.5, 34.4, 8.3, lw=1.0, color=C["verm"], ls=(0, (4, 2)))
    ax.text(25.7, 2.0, "zero survivors → escalate to Lane B", fontsize=6.0,
            color=C["verm"], ha="center")
    # B / C -> not-found
    arrow(ax, 50, 8.4, 50, 6.0, lw=1.0, color=C["verm"])
    arrow(ax, 83, 8.4, 83, 3.5, lw=1.0, color=C["verm"])
    arrow(ax, 83, 3.5, 63.2, 3.5, lw=1.0, color=C["verm"])
    ax.text(73, 2.0, "still empty → not-found", fontsize=6.0,
            color=C["verm"], ha="center")
    ax.text(50, 56.6, "", fontsize=1)
    save(fig, "fig2_lanes")


# ===========================================================================
# Fig 3 — Exp1 retrieval-layer results
# ===========================================================================
def fig_retrieval():
    summary = json.loads((RESULTS / "exp1_summary.json").read_text(encoding="utf-8"))
    s = summary["summary"]
    order = ["bm25", "dense", "rrf", "graph", "twostage", "fusion_only", "qdcvr_hybrid"]
    labels = ["BM25", "Dense", "RRF", "Graph", "Two-\nstage", "Fusion",
              "QDCVR-\nH"]
    colors = [C["grey"], C["sky"], C["blue"], C["pink"], C["yellow"],
              C["orange"], C["green"]]

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(190 * MM, 62 * MM),
                                 gridspec_kw={"width_ratios": [1.45, 1]})
    x = range(len(order))
    w = 0.27
    for k, (metric, mname) in enumerate([("hit@5", "Hit@5"),
                                         ("recall@5", "Recall@5"),
                                         ("mrr", "MRR")]):
        vals = [s[m][metric] for m in order]
        a1.bar([i + (k - 1) * w for i in x], vals, width=w, label=mname,
               color=[C["blue"], C["sky"], C["green"]][k], edgecolor="white",
               linewidth=0.4)
    a1.set_xticks(list(x))
    a1.set_xticklabels(labels, fontsize=6.6)
    a1.set_ylabel("Score (mean over 16 questions)")
    a1.set_ylim(0, 1.08)
    a1.legend(frameon=False, fontsize=6.8, loc="lower left", ncol=3,
              columnspacing=0.9, handlelength=1.2)
    a1.tick_params(length=2)
    for sp in ("top", "right"):
        a1.spines[sp].set_visible(False)

    lats = [max(s[m]["latency_mean"], 0.001) for m in order]
    a2.bar(list(x), lats, color=colors, edgecolor="white", linewidth=0.4)
    a2.set_yscale("log")
    a2.set_xticks(list(x))
    a2.set_xticklabels(labels, fontsize=6.6)
    a2.set_ylabel("Mean latency per query (s, log scale)")
    a2.tick_params(length=2)
    for xi, v in zip(x, lats):
        lbl = f"{v*1000:.1f} ms" if v < 0.05 else (
            f"{v*1000:.0f} ms" if v < 0.5 else f"{v:.2f} s")
        a2.text(xi, v * 1.25, lbl, ha="center", fontsize=6.0, color="#333333")
    a2.set_ylim(0.0005, 3)
    for sp in ("top", "right"):
        a2.spines[sp].set_visible(False)
    a1.set_title("(a) Effectiveness", fontsize=7.5, loc="left")
    a2.set_title("(b) Latency (42 docs, 5 KBs)", fontsize=7.5, loc="left")
    fig.tight_layout(w_pad=1.5)
    save(fig, "fig3_retrieval")


# ===========================================================================
# Fig 4 — judge score inflation (verifier analysis)
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

    import numpy as np
    rng = np.random.default_rng(7)
    fig, ax = plt.subplots(figsize=(90 * MM, 62 * MM))
    for i, (vals, col, name) in enumerate([
            (gold_scores, C["green"], "Gold documents"),
            (nongold_scores, C["verm"], "Non-gold survivors")]):
        xs = rng.normal(i, 0.055, size=len(vals))
        ax.scatter(xs, vals, s=11, color=col, alpha=0.65, edgecolors="none",
                   label=name, zorder=3)
        ax.hlines(np.median(vals), i - 0.22, i + 0.22, color=col, lw=1.6, zorder=4)
    ax.axhline(0.5, color=C["dgrey"], lw=0.9, ls="--")
    ax.text(1.42, 0.508, "accept threshold 0.5", fontsize=6.2,
            color=C["dgrey"], ha="right", zorder=5)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Gold documents", "Non-gold\nsurvivors"], fontsize=7)
    ax.set_ylabel("Laya evidence-criterion score")
    ax.set_ylim(0.42, 1.03)
    ax.legend(frameon=False, fontsize=6.4, loc="upper left",
              bbox_to_anchor=(0.02, 0.72), markerscale=0.8)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.tick_params(length=2)
    med_n = float(np.median(nongold_scores))
    med_g = float(np.median(gold_scores))
    ax.annotate(f"median {med_g:.2f}", (0.24, med_g + 0.008), fontsize=6.2,
                color=C["green"], va="bottom")
    ax.annotate(f"median {med_n:.2f}", (0.28, 0.965), fontsize=6.2,
                color=C["verm"], va="top")
    fig.tight_layout()
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
# Fig 5 — Exp2 agentic end-to-end results
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
    arm_labels = ["Search\n(Lane A)", "Librarian\n(Lane B)", "Hybrid\n(Lane C)",
                  "Bare agent\n(no KB)"]
    colors = [C["blue"], C["green"], C["orange"], C["grey"]]
    qids = sorted({r["qid"] for r in runs})
    qcolors = dict(zip(qids, [C["sky"], C["yellow"], C["pink"], C["lgrey"]]))

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(190 * MM, 64 * MM),
                                 gridspec_kw={"width_ratios": [1.5, 1]})
    w = 0.19
    import numpy as np
    for k, arm in enumerate(arms):
        rs = [next((r for r in runs if r["arm"] == arm and r["qid"] == q), None)
              for q in qids]
        vals = [r["wall_s"] if r else 0 for r in rs]
        xs = [i + (k - 1.5) * w for i in range(len(qids))]
        a1.bar(xs, vals, width=w, color=colors[k], edgecolor="white",
               linewidth=0.4, label=arm_labels[k].replace("\n", " "))
        for xi, r in zip(xs, rs):
            if r and r.get("turns"):
                a1.text(xi, r["wall_s"] + 4, str(r["turns"]), ha="center",
                        fontsize=5.6, color="#333333")
    a1.set_xticks(range(len(qids)))
    a1.set_xticklabels([f"{q}\n{_short(q)}" for q in qids], fontsize=6.4)
    a1.set_ylabel("End-to-end wall time (s)")
    a1.legend(frameon=False, fontsize=6.2, loc="upper right", ncol=2)
    a1.set_ylim(0, max(r["wall_s"] for r in runs) * 1.22)
    for sp in ("top", "right"):
        a1.spines[sp].set_visible(False)
    a1.tick_params(length=2)
    a1.set_title("(a) Wall time per run (numbers = agent turns)",
                 fontsize=7.5, loc="left")

    for k, arm in enumerate(arms):
        rs = [r for r in runs if r["arm"] == arm]
        if not rs:
            continue
        hit = sum(1 for r in rs if r["doc_citation_hit"]) / len(rs)
        turns = sum((r["turns"] or 0) for r in rs) / len(rs)
        xd = (k - 1.5) * 0.7  # dodge overlapping (turns, hit) points
        a2.scatter([turns + xd], [hit], s=46, color=colors[k], zorder=3,
                   label=arm_labels[k].replace("\n", " "), edgecolors="white",
                   linewidths=0.5)
        offs = {0: (9, 7), 1: (-9, -15), 2: (9, -15), 3: (9, 7)}
        ha = {0: "left", 1: "right", 2: "left", 3: "left"}
        a2.annotate(arm_labels[k].split("\n")[0], (turns + xd, hit),
                    textcoords="offset points", xytext=offs[k], ha=ha[k],
                    fontsize=6.2)
    a2.set_xlabel("Mean agent turns per run")
    a2.set_ylabel("Citation gold-hit rate")
    a2.set_ylim(-0.08, 1.12)
    a2.set_xlim(0, max((r["turns"] or 0) for r in runs) * 1.25 + 1)
    a2.grid(True, lw=0.3, color="#E5E5E5")
    a2.tick_params(length=2)
    for sp in ("top", "right"):
        a2.spines[sp].set_visible(False)
    a2.set_title("(b) Cost vs. groundedness", fontsize=7.5, loc="left")
    fig.tight_layout(w_pad=1.6)
    save(fig, "fig5_e2e")


def _short(qid):
    m = {"Q2": "EL delamination", "Q4": "POE barrier",
         "Q6": "weight alarm", "Q7": "TC0 root cause"}
    return m.get(qid, qid)


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
