#!/usr/bin/env python3
"""Containment and recorded costs on the 72 gold questions, from frozen traces.

Calls are all tool calls. Trace-recorded text bytes can include repeat reads;
they are not a measurement of model tokens or unique document content.
A0h versus PD changes more than the navigation layer.
The later record is shown only for seven audited arms; intervals and costs
are from the earlier frozen aggregate.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import NullLocator
import numpy as np

HERE = Path(__file__).resolve().parent
BENCH = HERE.parents[1] / "review" / "experiment-redesign-20261101" / "artifacts" / "final_bench"
REPLICATION = HERE / "fig_ladder_20261112_snapshot.json"
OUT = HERE / "kbs_revision_20261111"
TARGET = HERE.parent / "tex" / "journal_20p" / "figs"

spec = importlib.util.spec_from_file_location("kbs_fig_helpers", HERE / "figures.py")
helper = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = helper
spec.loader.exec_module(helper)

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": [helper.FONT, "Arial", "DejaVu Sans"],
    "font.size": 8.5, "axes.labelsize": 8.5, "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5, "axes.linewidth": .8,
    "xtick.direction": "in", "ytick.direction": "in", "pdf.fonttype": 42,
    "ps.fonttype": 42, "savefig.facecolor": "white",
})

ARMS = [("A0", "A0"), ("A0f", "A0f"), ("A0h", "A0h"), ("PD", "PD"),
        ("A1b", "A1b"), ("A2", "A2"), ("A3", "A3"), ("A1-readall", "Read-all")]
REPLICATION_ARMS = {"A0", "A0f", "A0h", "PD", "A1b", "A2", "A3"}


def main() -> None:
    helper.OUT = OUT
    OUT.mkdir(parents=True, exist_ok=True)
    TARGET.mkdir(parents=True, exist_ok=True)
    stats = json.loads((BENCH / "s6_stats.json").read_text(encoding="utf-8"))["per_arm"]
    traces = json.loads((BENCH / "s4_traces_final.json").read_text(encoding="utf-8"))
    replicated = json.loads(REPLICATION.read_text(encoding="utf-8"))
    calls, kb, rates, lower, upper = [], [], [], [], []
    for key, _ in ARMS:
        rows = [row for row in traces[key] if not row["is_refusal"]]
        assert len(rows) == stats[key]["n_gold"] == 72
        assert sum(row["gold_hit"] for row in rows) == stats[key]["gold_hits"]
        calls.append(sum(row["calls"] for row in rows) / len(rows))
        kb.append(sum(row["bytes_ingested"] for row in rows) / len(rows) / 1000)
        assert abs(kb[-1] * 1000 - stats[key]["avg_bytes_gold"]) <= 1
        rate = stats[key]["gold_rate"] * 100
        lo, hi = [v * 100 for v in stats[key]["gold_ci95"]]
        rates.append(rate)
        lower.append(rate - lo)
        upper.append(hi - rate)
        print(f"{key}: {stats[key]['gold_hits']}/72, calls={calls[-1]:.3f}, trace KB={kb[-1]:.3f}")

    rep_y, rep_rates = [], []
    for i, (key, _) in enumerate(ARMS):
        if key not in REPLICATION_ARMS:
            continue
        rows = [row for row in replicated[key] if not row["is_refusal"]]
        baseline = [row for row in traces[key] if not row["is_refusal"]]
        assert len(rows) == 72
        assert {row["qid"] for row in rows} == {row["qid"] for row in baseline}
        hits = sum(row["gold_hit"] for row in rows)
        rep_y.append(i + .13)
        rep_rates.append(hits * 100 / len(rows))
        print(f"12 November {key}: {hits}/72 ({rep_rates[-1]:.1f}%)")

    fig, (quality, cost, volume) = plt.subplots(1, 3, figsize=(6.96, 3.65),
                                  gridspec_kw={"width_ratios": [1.52, 1, 1]})
    fig.subplots_adjust(left=.14, right=.985, bottom=.18, top=.80, wspace=.32)
    y = np.arange(len(ARMS))
    quality.errorbar(rates, y - .13, xerr=[lower, upper], fmt="o", markersize=5,
                     color="#0072B2", ecolor="#20262E", elinewidth=.8,
                     capsize=2.5, capthick=.8, zorder=3)
    quality.scatter(rep_rates, rep_y, s=29, marker="^", color="#D55E00", zorder=4)
    quality.axvline(rates[0], color="#8A949D", linestyle=(0, (4, 3)), linewidth=.8)
    quality.set_xlim(0, 110)
    quality.set_xticks([0, 50, 100])
    quality.set_xlabel("Containment (%)")
    cost.scatter(calls, y, marker="s", s=27, color="#0072B2", zorder=3)
    volume.scatter(kb, y, marker="^", s=32, color="#E69F00", zorder=3)
    for ax in (cost, volume):
        ax.set_xscale("log")
        ax.xaxis.set_minor_locator(NullLocator())
    cost.set_xlim(.8, 2000)
    cost.set_xticks([1, 10, 100, 1000], ["1", "10", "100", "1000"])
    volume.set_xlim(.6, 100000)
    volume.set_xticks([1, 100, 10000], ["1", "100", "10000"])
    cost.set_xlabel("Tool calls / question")
    volume.set_xlabel("Trace KB / question")
    for ax in (quality, cost, volume):
        ax.set_ylim(len(ARMS) - .4, -.6)
        ax.set_yticks(y)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="x", color="#D8DDE2", linewidth=.5)
        ax.set_axisbelow(True)
        ax.tick_params(length=3, width=.8)
    quality.set_yticklabels([label for _, label in ARMS])
    cost.set_yticklabels([])
    volume.set_yticklabels([])
    quality.text(0, 1.02, "(a)", transform=quality.transAxes, fontsize=9, fontweight="bold")
    cost.text(0, 1.02, "(b) 11 Nov aggregate", transform=cost.transAxes, fontsize=9, fontweight="bold")
    fig.legend(handles=[
        Line2D([], [], color="#0072B2", marker="o", linestyle="none", markersize=5,
               label="11 Nov aggregate (95% CI)"),
        Line2D([], [], color="#D55E00", marker="^", linestyle="none", markersize=5,
               label="12 Nov record"),
    ], loc="upper center", bbox_to_anchor=(.5, .99), ncol=2, frameon=False,
       handletextpad=.35, columnspacing=1.5)
    helper.save(fig, "fig_ladder_optimization")
    for ext in ("pdf", "png"):
        shutil.copy2(OUT / f"fig_ladder_optimization.{ext}", TARGET / f"fig_ladder_optimization.{ext}")


if __name__ == "__main__":
    main()
