"""Draw Figure 7 from the archived, independently checked plot summary."""

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import PercentFormatter


def draw(summary: Path, output: Path) -> None:
    with summary.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    arms = {r["arm"]: r for r in rows if r["panel"] == "aggregate"}
    contrasts = [r for r in rows if r["contrast"]]
    order = ("A1-readall", "A0h", "PD", "A0f", "A1b", "A0", "A3", "A2")
    assert set(arms) == set(order) and len(contrasts) == 6

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8,
                         "pdf.fonttype": 42, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.linewidth": 0.60})
    blue, orange, ink = "#225b82", "#aa5b22", "#242a31"
    fig = plt.figure(figsize=(7.15, 2.85))
    grid = fig.add_gridspec(1, 2, width_ratios=(1.12, 1.0), wspace=0.25,
                            left=0.080, right=0.989, top=0.76, bottom=0.19)
    a_slot = grid[0].subgridspec(1, 2, width_ratios=(3.50, 1.40), wspace=0.09)
    b_slot = grid[1].subgridspec(1, 2, width_ratios=(3.7, 1.0), wspace=0.08)
    a, counts = (fig.add_subplot(a_slot[i]) for i in range(2))
    b, p_axis = (fig.add_subplot(b_slot[i]) for i in range(2))

    a.set(xlim=(0, 100), ylim=(len(order) - 0.5, -0.5),
          xticks=[0, 25, 50, 75, 100], xlabel="Target-string containment")
    a.xaxis.set_major_formatter(PercentFormatter(100, decimals=0))
    a.set_yticks(range(len(order)), ["Read-all", *order[1:]])
    a.axvline(int(arms["A0"]["frozen"]) * 100 / 72, color="#697989",
              linestyle="--", linewidth=0.8)
    counts.set(xlim=(0, 1), ylim=a.get_ylim())
    counts.set_axis_off()
    for x, name in ((0.20, "Frozen"), (0.80, "Follow-up")):
        counts.text(x, 1.04, name, transform=counts.transAxes,
                    ha="center", va="bottom", size=6.6, weight="bold")
    for y, arm in enumerate(order):
        r = arms[arm]
        k = int(r["frozen"])
        rate = k * 100 / 72
        lo, hi = (float(r[key]) for key in ("wilson_low", "wilson_high"))
        f = r["followup"]
        if arm == "A0h":
            for ax in (a, counts):
                ax.axhspan(y - 0.43, y + 0.43, color="#e9eff3", zorder=0)
        a.errorbar(rate, y + (0.11 if f else 0),
                   xerr=[[max(0, rate - lo)], [max(0, hi - rate)]], fmt="o",
                   color=blue, linewidth=0.9, capsize=2, markersize=4.3,
                   zorder=3, clip_on=False)
        if f:
            a.plot(int(f) * 100 / 72, y - 0.15, "^", color=orange,
                   markerfacecolor="white", markersize=5.1, zorder=4)
        counts.text(0.20, y, str(k), ha="center", va="center", color=ink)
        counts.text(0.80, y, f or "\N{EM DASH}", ha="center", va="center", color=ink)

    b.set(xlim=(-0.55, 20), ylim=(len(contrasts) - 0.5, -0.5),
          xticks=[0, 5, 10, 15, 20], xlabel="Discordant questions")
    b.set_yticks(range(len(contrasts)), [r["contrast"] for r in contrasts])
    p_axis.set(xlim=(0, 1), ylim=b.get_ylim())
    p_axis.set_axis_off()
    p_axis.text(0.05, 1.04, r"$p$ value", transform=p_axis.transAxes,
                va="bottom", size=7.5, weight="bold")
    for y, row in enumerate(contrasts):
        x, z = (int(row[key]) for key in ("first_only", "second_only"))
        b.hlines(y, min(x, z), max(x, z), color="#b6c1cb", linewidth=1.0)
        b.plot(x, y, "o", color=blue, markersize=4.3, zorder=3)
        b.plot(z, y, "D", color=orange, markerfacecolor="white", markersize=4.0, zorder=3)
        p = float(row["p"])
        p_axis.text(0.05, y, "<0.001" if p < 0.001 else f"{p:.3f}",
                    va="center", size=7.5, color=ink)

    for ax in (a, b):
        ax.grid(axis="x", color="#dce2e8", linewidth=0.65)
        ax.set_axisbelow(True)
        ax.tick_params(axis="y", length=0, pad=3)
        ax.tick_params(axis="x", length=2.8, pad=3)

    a_title = a.get_position().x0
    b_title = b.get_position().x0 - 0.08
    fig.text(a_title, 0.949, "(a) Coverage by configuration", weight="bold")
    fig.text(b_title, 0.949, "(b) Paired comparison: frozen run", weight="bold")
    fig.legend([Line2D([], [], marker="o", color=blue, markersize=4.3),
                Line2D([], [], marker="^", color=orange, markerfacecolor="white",
                       markersize=5.0, linestyle="None")],
               ["Frozen (95% CI)", "Follow-up"], loc="upper left",
               bbox_to_anchor=(a_title - 0.007, 0.919), ncol=2, frameon=False,
               handlelength=1.2, handletextpad=0.35, columnspacing=0.85,
               borderaxespad=0, fontsize=7.3)
    fig.legend([Line2D([], [], marker="o", color=blue, markersize=4.3,
                       linestyle="None"),
                Line2D([], [], marker="D", color=orange, markerfacecolor="white",
                       markersize=4.0, linestyle="None")],
               ["Only first hits", "Only second hits"], loc="upper left",
               bbox_to_anchor=(b_title - 0.007, 0.919), ncol=2, frameon=False,
               handlelength=1.2, handletextpad=0.35, columnspacing=0.85,
               borderaxespad=0, fontsize=7.3)
    fig.savefig(output)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    draw(args.summary, args.output)
