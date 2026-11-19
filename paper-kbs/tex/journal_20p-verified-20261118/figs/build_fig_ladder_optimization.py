"""Rebuild Fig. 8 from the two per-question CSVs in the parent directory.

The later record reuses questions. Frozen trace bytes can count overlapping
text. The read-all condition is a mechanical scan, not an answering agent.
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
from matplotlib.ticker import NullLocator

HERE = Path(__file__).resolve().parent
ARMS = ("A0", "A0f", "A0h", "PD", "A1b", "A2", "A3", "A1-readall")
LABELS = ("A0", "A0f", "A0h", "PD", "A1b", "A2", "A3", "Read-all")
EXPECTED_FROZEN = (37, 45, 52, 46, 39, 25, 33, 72)
EXPECTED_FOLLOWUP = (39, 44, 51, 45, 39, 25, 25)


def load(name: str) -> dict[str, list[dict[str, str]]]:
    result = {key: [] for key in ARMS}
    with (HERE.parent / name).open(encoding="utf-8", newline="") as src:
        for row in csv.DictReader(src):
            if row["arm"] in result and row["is_refusal"] == "False":
                result[row["arm"]].append(row)
    return result


def wilson(hits: int, n: int) -> tuple[float, float]:
    z = 1.959963984540054
    p = hits / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return 100 * (center - half), 100 * (center + half)


def main() -> None:
    frozen = load("supp_traces_frozen.csv")
    followup = load("supp_traces_followup.csv")
    rates, low, high, calls, kb = [], [], [], [], []
    for i, arm in enumerate(ARMS):
        rows = frozen[arm]
        assert len(rows) == len({row["qid"] for row in rows}) == 72, arm
        hits = sum(row["gold_hit"] == "True" for row in rows)
        assert hits == EXPECTED_FROZEN[i], (arm, hits)
        rate = hits / 72 * 100
        lo, hi = wilson(hits, 72)
        rates.append(rate)
        low.append(rate - lo)
        high.append(hi - rate)
        calls.append(sum(float(row["calls"]) for row in rows) / 72)
        kb.append(sum(float(row["bytes_ingested"]) for row in rows) / 72000)
        print(f"{arm}: {hits}/72, calls={calls[-1]:.3f}, KB={kb[-1]:.3f}")

    later = []
    for i, arm in enumerate(ARMS[:-1]):
        rows = followup[arm]
        assert len(rows) == len({row["qid"] for row in rows}) == 72, arm
        assert {r["qid"] for r in rows} == {r["qid"] for r in frozen[arm]}, arm
        hits = sum(row["gold_hit"] == "True" for row in rows)
        assert hits == EXPECTED_FOLLOWUP[i], (arm, hits)
        later.append(hits / 72 * 100)
        print(f"{arm} follow-up: {hits}/72")

    plt.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"],
        "font.size": 8.5, "axes.labelsize": 8.5, "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5, "axes.linewidth": .8, "xtick.direction": "in",
        "ytick.direction": "in", "pdf.fonttype": 42, "ps.fonttype": 42,
        "savefig.facecolor": "white",
    })
    fig, (quality, cost, volume) = plt.subplots(
        1, 3, figsize=(6.96, 3.65), gridspec_kw={"width_ratios": [1.52, 1, 1]})
    fig.subplots_adjust(left=.14, right=.985, bottom=.16, top=.74, wspace=.32)
    y = list(range(len(ARMS)))
    quality.errorbar(rates, [i - .13 for i in y], xerr=[low, high], fmt="o",
                     markersize=5, color="#0072B2", ecolor="#20262E",
                     elinewidth=.8, capsize=2.5, capthick=.8, zorder=3)
    quality.scatter(later, [i + .13 for i in y[:-1]], s=29, marker="^",
                    color="#D55E00", zorder=4)
    quality.axvline(rates[0], color="#8A949D", linestyle=(0, (4, 3)), linewidth=.8)
    quality.set_xlim(0, 110)
    quality.set_xticks([0, 50, 100])
    quality.set_xlabel("Containment (%)")
    quality.legend(handles=[
        Line2D([], [], color="#0072B2", marker="o", linestyle="none", markersize=5,
               label="Frozen (95% CI)"),
        Line2D([], [], color="#D55E00", marker="^", linestyle="none", markersize=5,
               label="Same-question follow-up"),
    ], loc="lower left", bbox_to_anchor=(-.06, 1.005), frameon=False,
       fontsize=8.3, handletextpad=.35, borderaxespad=0, labelspacing=.25)

    cost.scatter(calls, y, marker="s", s=27, color="#5C6774", zorder=3)
    volume.scatter(kb, y, marker="D", s=25, color="#007F78", zorder=3)
    for ax in (cost, volume):
        ax.set_xscale("log")
        ax.xaxis.set_minor_locator(NullLocator())
    cost.set_xlim(.8, 2000)
    cost.set_xticks([1, 10, 100, 1000], ["1", "10", "100", "1000"])
    volume.set_xlim(.6, 100000)
    volume.set_xticks([1, 100, 10000], ["1", "100", "10000"])
    cost.set_xlabel("Tool calls / question")
    volume.set_xlabel("Trace KB / question")
    cost.legend(handles=[Line2D([], [], color="#5C6774", marker="s", linestyle="none",
                                markersize=5, label="Calls")], loc="lower left",
                bbox_to_anchor=(-.06, 1.005), frameon=False, fontsize=8.3,
                handletextpad=.3, borderaxespad=0)
    volume.legend(handles=[Line2D([], [], color="#007F78", marker="D", linestyle="none",
                                  markersize=4.5, label="Trace KB")], loc="lower left",
                  bbox_to_anchor=(-.06, 1.005), frameon=False, fontsize=8.3,
                  handletextpad=.3, borderaxespad=0)

    for ax in (quality, cost, volume):
        ax.set_ylim(len(ARMS) - .4, -.6)
        ax.set_yticks(y)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="x", color="#D8DDE2", linewidth=.5)
        ax.set_axisbelow(True)
        ax.tick_params(length=3, width=.8)
    quality.set_yticklabels(LABELS)
    cost.set_yticklabels([])
    volume.set_yticklabels([])
    fig.text(.14, .965, "(a) Gold-string containment", ha="left", va="top",
             fontsize=9, fontweight="bold")
    fig.text(.535, .965, "(b) Frozen cost profile", ha="left", va="top",
             fontsize=9, fontweight="bold")
    output = HERE / "fig_ladder_optimization.pdf"
    preview = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    fig.savefig(output)
    if preview:
        fig.savefig(preview, dpi=300)
    plt.close(fig)


if __name__ == "__main__":
    main()
