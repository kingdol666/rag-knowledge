#!/usr/bin/env python3
"""Recompute and plot the v3 external-baseline blind comparison.

The script derives all scores from judgments-unified.jsonl, cross-checks the
published summary, and writes a compact JSON manifest plus a vector PDF/PNG.
It intentionally reports the corpus-scope asymmetry rather than presenting a
ranked leaderboard as a causal or fair comparison.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / "experiment_data" / "external_baselines_v3"
FIG = ROOT / "figs"
JUDGMENTS = DATA / "judgments-unified.jsonl"
SUMMARY = DATA / "summary-unified.json"

ARMS = [
    "hmrs-agent", "bm25", "dense", "rrf", "raptor", "lightrag",
    "deepread-native", "graphrag",
]
LABELS = {
    "hmrs-agent": "HMRS",
    "bm25": "BM25",
    "dense": "Dense",
    "rrf": "RRF",
    "raptor": "RAPTOR†",
    "lightrag": "LightRAG",
    "deepread-native": "DeepRead‡",
    "graphrag": "GraphRAG†",
}
SCOPE = {
    "hmrs-agent": "full 328 parts",
    "bm25": "full 328 parts",
    "dense": "full 328 parts",
    "rrf": "full 328 parts",
    "raptor": "30 gold parts",
    "lightrag": "full 328 parts",
    "deepread-native": "23/96 documents",
    "graphrag": "30 gold parts",
}
DIMS = ["factual", "completeness", "groundedness", "sources"]
DIM_LABELS = ["Factual", "Completeness", "Groundedness", "Attribution"]
VERDICTS = ["correct", "partial", "incorrect"]
EXPECTED = {
    "hmrs-agent": {"overall": 5.0, "correct": 10},
    "bm25": {"overall": 4.95, "correct": 9},
    "dense": {"overall": 4.9, "correct": 8},
    "rrf": {"overall": 4.83, "correct": 8},
    "raptor": {"overall": 4.8, "correct": 7},
    "lightrag": {"overall": 4.75, "correct": 7},
    "deepread-native": {"overall": 4.7, "correct": 10},
    "graphrag": {"overall": 4.28, "correct": 4},
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    rows = [json.loads(line) for line in JUDGMENTS.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_arm = defaultdict(list)
    for row in rows:
        by_arm[row["arm"]].append(row)
    assert set(by_arm) == set(ARMS), sorted(by_arm)
    assert all(len(by_arm[arm]) == 10 for arm in ARMS)

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    derived = {"arms": {}, "per_question": {}, "head_to_head": {}, "scope": SCOPE}
    for arm in ARMS:
        rs = by_arm[arm]
        dims = {dim: round(mean(r[dim] for r in rs), 3) for dim in DIMS}
        overall_values = [sum(r[dim] for dim in DIMS) / len(DIMS) for r in rs]
        verdicts = Counter(r["verdict"] for r in rs)
        overall = round(mean(overall_values), 3)
        derived["arms"][arm] = {
            "n": len(rs), "dimensions": dims, "overall": overall,
            "verdicts": {v: verdicts.get(v, 0) for v in VERDICTS},
            "question_overall": {r["qid"]: round(sum(r[d] for d in DIMS) / 4, 3) for r in rs},
        }
        # Fail closed against the unified summary's primary numbers.
        assert abs(overall - summary["primary"][arm]["overall"]) < 0.011, (arm, overall)
        assert verdicts.get("correct", 0) == EXPECTED[arm]["correct"], arm
    qids = sorted(derived["arms"][ARMS[0]]["question_overall"])
    for qid in qids:
        vals = {arm: derived["arms"][arm]["question_overall"][qid] for arm in ARMS}
        best = max(vals.values())
        derived["per_question"][qid] = {"scores": vals, "best": best, "best_arms": [a for a, v in vals.items() if v == best]}
    hmrs = derived["arms"]["hmrs-agent"]["question_overall"]
    for arm in ARMS:
        if arm == "hmrs-agent":
            continue
        diffs = [hmrs[q] - derived["arms"][arm]["question_overall"][q] for q in qids]
        derived["head_to_head"][arm] = {
            "hmrs_better": sum(d > 0 for d in diffs),
            "ties": sum(d == 0 for d in diffs),
            "baseline_better": sum(d < 0 for d in diffs),
            "mean_diff": round(mean(diffs), 3),
        }
    derived["sources_sha256"] = {p.name: sha256(p) for p in (JUDGMENTS, SUMMARY)}
    (DATA / "external-baselines-v3-derived.json").write_text(json.dumps(derived, indent=2, ensure_ascii=False), encoding="utf-8")

    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 8.2,
        "axes.titlesize": 9.2,
        "axes.labelsize": 8.2,
        "xtick.labelsize": 7.5,
        "ytick.labelsize": 7.5,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })
    fig, axes = plt.subplots(1, 2, figsize=(7.1, 3.2), gridspec_kw={"width_ratios": [1.05, 1.15]})
    fig.subplots_adjust(left=0.16, right=0.99, bottom=0.24, top=0.84, wspace=0.48)

    # Panel A: dimension heatmap, with full vs restricted scope separated by a line.
    ax = axes[0]
    mat = np.array([[derived["arms"][arm]["dimensions"][d] for d in DIMS] for arm in ARMS])
    im = ax.imshow(mat, cmap="YlGnBu", vmin=3.0, vmax=5.0, aspect="auto")
    ax.set_xticks(np.arange(4), DIM_LABELS, rotation=30, ha="right")
    ax.set_yticks(np.arange(len(ARMS)), [LABELS[a] for a in ARMS])
    ax.set_title("Unified blind judge: dimensions")
    ax.set_xlabel("Mean score (1–5)")
    ax.set_yticklabels([LABELS[a] for a in ARMS])
    ax.axhline(3.5, color="#5b6570", lw=0.8)
    for i, arm in enumerate(ARMS):
        for j, d in enumerate(DIMS):
            ax.text(j, i, f"{mat[i, j]:.1f}", ha="center", va="center", color="#132a3a" if mat[i, j] < 4.6 else "white", fontsize=7.1)
    for spine in ax.spines.values(): spine.set_visible(False)

    # Panel B: verdict composition; no ordering claim is made by the plot.
    ax = axes[1]
    y = np.arange(len(ARMS))
    left = np.zeros(len(ARMS))
    colors = {"correct": "#4477AA", "partial": "#DDAA33", "incorrect": "#BB5566"}
    for verdict in VERDICTS:
        counts = np.array([derived["arms"][arm]["verdicts"][verdict] for arm in ARMS])
        ax.barh(y, counts, left=left, height=0.64, color=colors[verdict], label=verdict.capitalize())
        for idx, count in enumerate(counts):
            if count:
                ax.text(left[idx] + count / 2, idx, str(int(count)), ha="center", va="center", fontsize=7.1, color="white" if verdict != "partial" else "#3b2f0b", fontweight="bold")
        left += counts
    ax.set_yticks(y, [LABELS[a] for a in ARMS])
    ax.invert_yaxis()
    ax.set_xlim(0, 10.8)
    ax.set_xlabel("Questions (n = 10)")
    ax.set_title("Verdict composition and mean overall score", pad=14)
    for idx, arm in enumerate(ARMS):
        ax.text(10.25, idx, f"{derived['arms'][arm]['overall']:.2f}", ha="left", va="center", fontsize=7.2)
    ax.text(10.25, -0.62, "overall", ha="left", va="bottom", fontsize=7.2, color="#4c5863")
    ax.legend(loc="upper center", bbox_to_anchor=(0.56, -0.22), frameon=False, ncol=3, fontsize=7.1, handlelength=1.1, columnspacing=0.8)
    ax.grid(axis="x", color="#d9e1e8", lw=0.6)
    ax.set_axisbelow(True)
    for spine in ["top", "right", "left"]: ax.spines[spine].set_visible(False)

    pdf_path = FIG / "fig_external_baselines.pdf"
    png_path = FIG / "fig_external_baselines.png"
    fig.savefig(pdf_path, bbox_inches="tight")
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(json.dumps({"overall": {a: derived["arms"][a]["overall"] for a in ARMS}, "pdf": str(pdf_path), "png": str(png_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

