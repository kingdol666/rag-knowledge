#!/usr/bin/env python3
"""Build the E3 baseline answer-quality figure for the journal_20p manuscript.

Source: the 2026-11-20 v2 blind-evaluation grid packaged under
experiment_data/baseline_quality_v2/ (answers, judgments, anonymisation map,
aggregate summary). The builder fails closed on any source-hash mismatch and
re-derives every plotted number from the raw rows; it also cross-checks the
re-derived aggregates against summary-v2.json. Outputs: vector PDF, 300-dpi
PNG preview, and a plotted-values manifest with input/output hashes.
"""
from __future__ import annotations

import hashlib
import json
import math
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

HERE = Path(__file__).resolve().parent
TARGET = HERE.parent
DATA = TARGET / "experiment_data" / "baseline_quality_v2"
FIG = TARGET / "figs"

EXPECTED_SHA256 = {
    "answers-v2.jsonl": "4254613b4e23ec9ea3d022a6bce95967ec7d1334bdcd7e46d61b99083ec11e42",
    "judgments-v2.jsonl": "1aea092f722962f029278fca6adec4664bb9fb9c7d47759aa7079d124fd66842",
    "mapping-v2.json": "0b42649c556a54197e0c19c2d706f68de228691194cb8d94b43efb634677a02d",
    "summary-v2.json": "1f206ae9b8450a7d0b77e34d1c91b16c213decefd069cae51dc2c705dd1fe3da",
}


def round_half_even(value: float | Decimal, places: int = 2) -> float:
    quantum = Decimal("1").scaleb(-places)
    return float(Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_EVEN))


ARMS = ["hmrs-agent", "bm25", "dense", "rrf"]
LABEL = {"hmrs-agent": "HMRS", "bm25": "BM25", "dense": "Dense", "rrf": "RRF-order"}
DIMS = ["factual", "completeness", "groundedness", "sources"]
DIM_LABEL = ["Factual", "Completeness", "Groundedness", "Attribution"]
QIDS = [f"BQ{i:02d}" for i in range(1, 11)]

INK = "#23394F"
STEEL = "#35689A"
LSTEEL = "#8FB3C9"
OCHRE = "#C58A2E"
LOCHRE = "#D9A45B"
BRICK = "#A9542F"
SLATE = "#8D98A4"
GRID = "#E3E8ED"
FILL = "#EDF2F6"
WHITE = "#FFFFFF"
ARM_COLOR = {"hmrs-agent": STEEL, "bm25": OCHRE, "dense": BRICK, "rrf": SLATE}
VERDICT_COLOR = {"correct": STEEL, "partial": LOCHRE, "incorrect": BRICK}

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Liberation Sans", "DejaVu Sans"],
        "font.size": 8.2,
        "axes.labelsize": 8.2,
        "axes.titlesize": 8.2,
        "xtick.labelsize": 8.0,
        "ytick.labelsize": 8.0,
        "legend.fontsize": 7.6,
        "axes.linewidth": 0.8,
        "axes.edgecolor": INK,
        "text.color": INK,
        "axes.labelcolor": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "xtick.direction": "in",
        "ytick.direction": "in",
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "savefig.facecolor": WHITE,
        "figure.facecolor": WHITE,
        "axes.facecolor": WHITE,
        "savefig.dpi": 300,
    }
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_sources() -> tuple[dict, dict, dict]:
    hashes = {name: sha256(DATA / name) for name in EXPECTED_SHA256}
    for name, expected in EXPECTED_SHA256.items():
        if hashes[name] != expected:
            raise ValueError(f"Source hash changed for {name}")
    answers = {}
    for line in (DATA / "answers-v2.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        answers[(row["qid"], row["arm"])] = row
    judgments = {}
    for line in (DATA / "judgments-v2.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        judgments[(row["qid"], row["arm"])] = row
    summary = json.loads((DATA / "summary-v2.json").read_text(encoding="utf-8"))
    if len(answers) != 40 or len(judgments) != 40:
        raise ValueError("Expected a complete 4 x 10 grid")
    for key, row in judgments.items():
        if not row.get("ok"):
            raise ValueError(f"Judgment failed for {key}")
    return answers, judgments, summary


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    p = k / n
    denominator = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return max(0.0, centre - half), min(1.0, centre + half)


def sign_test(diff: list[float]) -> tuple[float, int, int]:
    nonzero = [d for d in diff if d != 0]
    pos = sum(d > 0 for d in nonzero)
    n = len(nonzero)
    k = min(pos, n - pos)
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2**n) if n else 1.0
    return p, n, pos


def mcnemar(hmrs: list[bool], base: list[bool]) -> tuple[int, int, float]:
    first = sum(a and not b for a, b in zip(hmrs, base))
    second = sum(b and not a for a, b in zip(hmrs, base))
    n = first + second
    k = min(first, second)
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2**n) if n else 1.0
    return first, second, p


def derive(answers: dict, judgments: dict, summary: dict) -> dict:
    scores = {a: {d: [judgments[(q, a)][d] for q in QIDS] for d in DIMS} for a in ARMS}
    overall = {a: [sum(judgments[(q, a)][d] for d in DIMS) / 4 for q in QIDS] for a in ARMS}
    verdicts = {a: [judgments[(q, a)]["verdict"] for q in QIDS] for a in ARMS}
    correct = {a: [v == "correct" for v in verdicts[a]] for a in ARMS}
    gold_in_context = {
        a: [any(answers[(q, a)]["arxiv"] in u["doc_path"] for u in answers[(q, a)]["sources"])
            for q in QIDS]
        for a in ["bm25", "dense", "rrf"]
    }
    gold_id = {a: [answers[(q, a)]["arxiv"] in answers[(q, a)]["answer"] for q in QIDS] for a in ARMS}
    kw = {
        a: [sum(k.lower() in answers[(q, a)]["answer"].lower()
                for k in answers[(q, a)]["kw_list"]) / len(answers[(q, a)]["kw_list"])
            for q in QIDS]
        for a in ARMS
    }
    wall = {a: [answers[(q, a)]["wall_s"] for q in QIDS] for a in ARMS}
    cost = {a: [answers[(q, a)].get("cost_usd") or 0.0 for q in QIDS] for a in ARMS}

    for a in ARMS:
        for d in DIMS:
            got = round_half_even(sum(scores[a][d]) / 10)
            if got != summary[a][d]:
                raise ValueError(f"Aggregate mismatch {a}/{d}: {got} vs {summary[a][d]}")
        got = round_half_even(sum(overall[a]) / 10)
        if got != summary[a]["overall"]:
            raise ValueError(f"Overall mismatch {a}: {got} vs {summary[a]['overall']}")
        counts = {v: verdicts[a].count(v) for v in ("correct", "partial", "incorrect")}
        counts = {k: c for k, c in counts.items() if c}
        if counts != summary[a]["verdicts"]:
            raise ValueError(f"Verdict mismatch {a}")
        if round_half_even(sum(gold_id[a]) / 10) != summary[a]["gold_id_rate"]:
            raise ValueError(f"Gold-ID mismatch {a}")
        if round_half_even(sum(kw[a]) / 10) != summary[a]["kw_coverage"]:
            raise ValueError(f"Keyword mismatch {a}")

    paired = {}
    for a in ["bm25", "dense", "rrf"]:
        diff = [overall["hmrs-agent"][i] - overall[a][i] for i in range(10)]
        entry = {"overall_diff": diff}
        for d in DIMS:
            dd = [scores["hmrs-agent"][d][i] - scores[a][d][i] for i in range(10)]
            p, n, pos = sign_test(dd)
            entry[d] = {"mean_diff": sum(dd) / 10, "p": p, "nonzero": n, "hmrs_better": pos}
        b, c, p = mcnemar(correct["hmrs-agent"], correct[a])
        entry["verdict"] = {"hmrs_only": b, "base_only": c, "p": p}
        paired[a] = entry

    intervals = {a: wilson(sum(correct[a]), 10) for a in ARMS}
    return {
        "scores": scores, "overall": overall, "verdicts": verdicts,
        "correct": correct, "gold_in_context": gold_in_context,
        "gold_id": gold_id, "kw": kw, "wall": wall, "cost": cost,
        "paired": paired, "wilson": intervals,
    }


def decorate(ax, grid_axis: str | None = "y") -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if grid_axis:
        ax.grid(axis=grid_axis, color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)


def panel_a(ax, v: dict) -> None:
    width = 0.19
    rng = np.random.default_rng(20261120)
    for j, d in enumerate(DIMS):
        for k, a in enumerate(ARMS):
            x = j + (k - 1.5) * width
            vals = v["scores"][a][d]
            mean = sum(vals) / 10
            ax.bar(x, mean, width * 0.92, color=ARM_COLOR[a], alpha=0.45,
                   edgecolor=ARM_COLOR[a], linewidth=0.8, zorder=2)
            jitter = rng.uniform(-width * 0.30, width * 0.30, 10)
            ax.scatter(x + jitter, vals, s=7, color=ARM_COLOR[a], edgecolor=WHITE,
                       linewidth=0.3, zorder=3)
            ax.text(x, 5.30 + 0.24 * (k % 2), f"{mean:.1f}", ha="center", va="bottom",
                    fontsize=7.0, color=INK)
    ax.set_xticks(range(4), DIM_LABEL, rotation=18, ha="right")
    ax.set_ylim(0, 6.05)
    ax.set_yticks(range(1, 6))
    ax.set_ylabel("Judged score (1--5)")
    ax.set_xlim(-0.55, 3.55)
    decorate(ax)
    ax.set_title("(a) Dimension scores, mean and per-question values", loc="left", fontweight="bold")


def panel_b(ax, v: dict):
    ypos = {a: 3 - i for i, a in enumerate(ARMS)}
    for a in ARMS:
        y = ypos[a]
        left = 0
        for verdict in ("correct", "partial", "incorrect"):
            count = v["verdicts"][a].count(verdict)
            if count:
                ax.barh(y, count, left=left, height=0.52, color=VERDICT_COLOR[verdict],
                        edgecolor=WHITE, linewidth=0.8, zorder=2)
                ax.text(left + count / 2, y, str(count), ha="center", va="center",
                        color=WHITE, fontsize=7.6, fontweight="bold", zorder=3)
            left += count
        lo, hi = v["wilson"][a]
        rate = sum(v["correct"][a]) / 10
        ax.plot([lo * 10, hi * 10], [y + 0.36, y + 0.36], color=INK, linewidth=1.0, zorder=4)
        for x in (lo * 10, hi * 10):
            ax.plot([x, x], [y + 0.30, y + 0.42], color=INK, linewidth=1.0, zorder=4)
        ax.scatter([rate * 10], [y + 0.36], s=16, color=WHITE, edgecolor=INK,
                   linewidth=0.9, zorder=5)
    ax.set_yticks([ypos[a] for a in ARMS], [LABEL[a] for a in ARMS])
    ax.set_xlim(0, 10.6)
    ax.set_xticks(range(0, 11, 2))
    ax.set_xlabel("Questions (of 10)")
    ax.set_ylim(-0.55, 3.85)
    decorate(ax, grid_axis="x")
    handles = [Patch(facecolor=VERDICT_COLOR[k], label=k.capitalize())
               for k in ("correct", "partial", "incorrect")]
    handles.append(Line2D([0], [0], color=INK, linewidth=1.0, marker="o", markersize=4,
                          markerfacecolor=WHITE, markeredgecolor=INK,
                          label="Correct rate, Wilson 95%"))
    ax.set_title("(b) Verdicts and correct-rate intervals", loc="left", fontweight="bold")
    return handles


def panel_c(ax, v: dict) -> None:
    matrix = np.array([v["overall"][a] for a in ARMS])
    cmap = LinearSegmentedColormap.from_list("hmrs", [FILL, LSTEEL, STEEL])
    ax.imshow(matrix, cmap=cmap, vmin=1.0, vmax=5.0, aspect="auto")
    for i, a in enumerate(ARMS):
        for j in range(10):
            val = matrix[i, j]
            ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=7.0,
                    color=WHITE if val > 3.9 else INK)
    ax.set_xticks(range(10), [q.replace("BQ", "") for q in QIDS])
    ax.set_yticks(range(4), [LABEL[a] for a in ARMS])
    ax.set_xlabel("Benchmark question (BQ01--BQ10)")
    ax.set_xticks(np.arange(-0.5, 10, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, 4, 1), minor=True)
    ax.grid(which="minor", color=WHITE, linewidth=1.2)
    ax.tick_params(which="minor", length=0)
    ax.tick_params(which="major", length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title("(c) Per-question overall score", loc="left", fontweight="bold")


def panel_d(ax, v: dict) -> None:
    offsets = {"bm25": -0.24, "dense": 0.0, "rrf": 0.24}
    for a in ("bm25", "dense", "rrf"):
        diff = v["paired"][a]["overall_diff"]
        xs = np.arange(10) + offsets[a]
        ax.vlines(xs, 0, diff, color=ARM_COLOR[a], linewidth=1.0, zorder=2)
        ax.scatter(xs, diff, s=14, color=ARM_COLOR[a], edgecolor=WHITE,
                   linewidth=0.4, zorder=3, label=f"HMRS $-$ {LABEL[a]}")
    ax.axhline(0, color=INK, linewidth=0.9, linestyle=(0, (3, 2)), zorder=1)
    ax.set_xticks(range(10), [q.replace("BQ", "") for q in QIDS])
    ax.set_xlabel("Benchmark question (BQ01--BQ10)")
    ax.set_ylabel("Overall-score difference")
    ax.set_ylim(-1.65, 3.55)
    ax.set_xlim(-0.6, 9.6)
    decorate(ax)
    ax.legend(loc="lower left", frameon=False, handletextpad=0.4)
    ax.set_title("(d) Paired overall-score difference", loc="left", fontweight="bold")


def main() -> None:
    answers, judgments, summary = load_sources()
    v = derive(answers, judgments, summary)
    fig, axes = plt.subplots(2, 2, figsize=(7.1, 5.05))
    panel_a(axes[0, 0], v)
    verdict_handles = panel_b(axes[0, 1], v)
    panel_c(axes[1, 0], v)
    panel_d(axes[1, 1], v)
    fig.tight_layout(pad=0.9, h_pad=1.6, w_pad=1.4)
    fig.subplots_adjust(bottom=0.16)
    fig.legend(handles=verdict_handles, loc="lower center", ncol=4, frameon=False,
               bbox_to_anchor=(0.5, 0.028), columnspacing=1.4, handletextpad=0.5)
    FIG.mkdir(exist_ok=True)
    pdf_path = FIG / "fig_baseline_quality.pdf"
    png_path = FIG / "fig_baseline_quality.png"
    fig.savefig(pdf_path)
    fig.savefig(png_path, dpi=300)
    plt.close(fig)
    manifest = {
        "figure": "fig_baseline_quality",
        "sources_sha256": {name: sha256(DATA / name) for name in EXPECTED_SHA256},
        "outputs_sha256": {"figs/fig_baseline_quality.pdf": sha256(pdf_path),
                           "figs/fig_baseline_quality.png": sha256(png_path)},
        "plotted_values": {
            "dimension_means": {a: {d: round_half_even(sum(v["scores"][a][d]) / 10)
                                      for d in DIMS} for a in ARMS},
            "overall_means": {a: round_half_even(sum(v["overall"][a]) / 10) for a in ARMS},
            "verdict_counts": {a: {k: v["verdicts"][a].count(k)
                                    for k in ("correct", "partial", "incorrect")} for a in ARMS},
            "wilson_correct": {a: [round(x, 4) for x in v["wilson"][a]] for a in ARMS},
            "overall_per_question": v["overall"],
            "paired_overall_diff": {a: v["paired"][a]["overall_diff"] for a in ("bm25", "dense", "rrf")},
            "gold_doc_in_baseline_context": {a: sum(v["gold_in_context"][a]) for a in ("bm25", "dense", "rrf")},
            "gold_id_in_answer": {a: sum(v["gold_id"][a]) for a in ARMS},
            "kw_coverage": {a: round_half_even(sum(v["kw"][a]) / 10) for a in ARMS},
            "mean_wall_s": {a: round(sum(v["wall"][a]) / 10, 1) for a in ARMS},
            "mean_cost_usd": {a: round(sum(v["cost"][a]) / 10, 4) for a in ARMS},
            "paired_tests": v["paired"],
        },
    }
    (DATA / "figure-values.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False),
                                                encoding="utf-8")
    print("overall means:", manifest["plotted_values"]["overall_means"])
    print("paired verdict tests:", {a: v["paired"][a]["verdict"] for a in ("bm25", "dense", "rrf")})
    print("wrote", pdf_path.name, png_path.name, "figure-values.json")


if __name__ == "__main__":
    main()
