"""Fig. 7: paired containment and observed retrieval-workflow duration.

Inputs are the manuscript's per-question frozen/follow-up CSV exports. Timing
is per retrieval workflow and excludes final answer generation. Observations
are reused questions, not an independent test set.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

HERE = Path(__file__).resolve().parent
ARMS = ("A0", "A0f", "A0h", "PD", "A1b", "A2")
FROZEN_HITS = (37, 45, 52, 46, 39, 25)
FOLLOWUP_HITS = (39, 44, 51, 45, 39, 25)


def load(name: str) -> dict[str, list[dict[str, str]]]:
    out = {key: [] for key in ARMS}
    with (HERE.parent / name).open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row["arm"] in out and row["is_refusal"] == "False":
                out[row["arm"]].append(row)
    return out


def wilson(hits: int, n: int) -> tuple[float, float]:
    z = 1.959963984540054
    p = hits / n
    denom = 1 + z * z / n
    c = (p + z * z / (2 * n)) / denom
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return c - h, c + h


def main() -> None:
    old, new = load("supp_traces_frozen.csv"), load("supp_traces_followup.csv")
    series = []
    times = []
    for data, expected in ((old, FROZEN_HITS), (new, FOLLOWUP_HITS)):
        current = []
        for i, arm in enumerate(ARMS):
            rows = data[arm]
            assert len(rows) == len({r["qid"] for r in rows}) == 72, arm
            hits = sum(r["gold_hit"] == "True" for r in rows)
            assert hits == expected[i], (arm, hits)
            p = hits / 72
            lo, hi = wilson(hits, 72)
            current.append((p, p - lo, hi - p))
        series.append(current)
    for arm in ARMS:
        assert {r["qid"] for r in old[arm]} == {r["qid"] for r in new[arm]}
        values = np.array([float(r["tool_seconds"]) for r in new[arm]])
        assert len(values) == 72 and np.all(np.isfinite(values))
        assert np.all(values > 0), "Zero/nonpositive values require explicit scale handling"
        times.append(values)
        print(f"{arm}: n=72, mean={np.mean(values):.2f}, "
              f"median={np.median(values):.2f}, max={max(values):.2f} s")

    plt.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"],
        "font.size": 8.5, "axes.labelsize": 8.5, "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5, "axes.linewidth": .8, "xtick.direction": "in",
        "ytick.direction": "in", "pdf.fonttype": 42, "ps.fonttype": 42,
        "savefig.facecolor": "white",
    })
    fig, (quality, time_ax) = plt.subplots(1, 2, figsize=(6.96, 3.35),
                                            gridspec_kw={"width_ratios": [1.05, 1]})
    fig.subplots_adjust(left=.09, right=.985, bottom=.17, top=.76, wspace=.39)
    x = np.arange(len(ARMS))
    for j, (marker, color, label) in enumerate((("o", "#0072B2", "Frozen"),
                                                 ("^", "#D55E00", "Follow-up"))):
        values = series[j]
        quality.errorbar(x + (-.09 if j == 0 else .09), [v[0] for v in values],
                         yerr=[[v[1] for v in values], [v[2] for v in values]],
                         fmt=marker, color=color, markersize=4.5, elinewidth=.9,
                         capsize=2.2, zorder=3, label=label)
    quality.set_ylim(0, 1.03)
    quality.set_yticks([0, .2, .4, .6, .8, 1])
    quality.set_ylabel("Gold-string containment")
    quality.set_xticks(x, ARMS)
    quality.legend(loc="lower left", bbox_to_anchor=(-.02, 1.01), ncol=2,
                   fontsize=8.3, frameon=False, handlelength=1.3,
                   columnspacing=.7, borderaxespad=0)
    quality.annotate("51/72", xy=(2.09, 51/72), xytext=(2.3, .86), fontsize=8.3,
                     color="#A34A00", arrowprops={"arrowstyle": "-", "lw": .7,
                                                    "color": "#A34A00"})

    # The dots show all 72 records per arm. Horizontal jitter is deterministic
    # and does not modify values; points with identical time can overlap.
    rng = np.random.default_rng(20261116)
    for i, values in enumerate(times):
        time_ax.scatter(i + rng.uniform(-.17, .17, size=len(values)), values,
                        s=7, color="#8C9AA5", alpha=.35, linewidths=0, zorder=2)
    time_ax.boxplot(times, positions=x, widths=.38, patch_artist=True,
                    showfliers=False, showmeans=True,
                    boxprops={"facecolor": "#D9EAF2", "edgecolor": "#385B6D", "linewidth": .8},
                    medianprops={"color": "#006C67", "linewidth": 1.5},
                    whiskerprops={"color": "#385B6D", "linewidth": .8},
                    capprops={"color": "#385B6D", "linewidth": .8},
                    meanprops={"marker": "D", "markerfacecolor": "#6E4B82", "markeredgecolor": "#6E4B82", "markersize": 3.6},
                    whis=1.5, zorder=3)
    time_ax.set_yscale("log")
    time_ax.set_ylim(.065, 1000)
    time_ax.set_yticks([.1, 1, 10, 100, 1000], ["0.1", "1", "10", "100", "1000"])
    time_ax.set_ylabel("Workflow elapsed time (s, log)")
    time_ax.set_xticks(x, ARMS)
    time_ax.legend(handles=[
        Line2D([], [], color="#006C67", linewidth=1.5, label="Median"),
        Line2D([], [], marker="D", color="#6E4B82", linestyle="none", markersize=4, label="Mean"),
    ], loc="lower left", bbox_to_anchor=(-.02, 1.01), ncol=2, fontsize=8.3,
        frameon=False, handlelength=1.1, columnspacing=.7, borderaxespad=0)
    time_ax.annotate("540.9 s", (0, 540.9), xytext=(.15, 650), fontsize=7.8, color="#455A64")
    time_ax.annotate("60.7 s", (5, 60.7), xytext=(3.75, 110), fontsize=7.8, color="#455A64")
    for ax in (quality, time_ax):
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", color="#D8DDE2", linewidth=.5, which="major")
        ax.set_axisbelow(True)
        ax.tick_params(length=3, width=.8)
    fig.text(.09, .96, "(a) Gold-string containment", ha="left", va="top",
             fontsize=9, fontweight="bold")
    fig.text(.56, .96, "(b) Follow-up workflow duration", ha="left", va="top",
             fontsize=9, fontweight="bold")
    fig.savefig(HERE / "fig_r3_content_followup.pdf")
    if len(sys.argv) > 1:
        fig.savefig(Path(sys.argv[1]), dpi=300)
    plt.close(fig)


if __name__ == "__main__":
    main()
