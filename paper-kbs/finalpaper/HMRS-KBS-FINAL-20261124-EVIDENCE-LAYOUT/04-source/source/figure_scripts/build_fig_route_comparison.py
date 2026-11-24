"""Draw the routing result separately from evidence-pack containment."""

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def draw(traces: Path, output: Path) -> None:
    runs = ("frozen", "followup", "rerun_20261117")
    hits = {"A0": [], "A3": []}
    for run in runs:
        with (traces / f"supp_traces_{run}.csv").open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        for arm in hits:
            records = [r for r in rows if r["arm"] == arm and r["qid"] not in {"R1", "R2", "R3", "R4"}]
            assert len(records) == len({r["qid"] for r in records}) == 72
            hits[arm].append(sum(r["route_correct"] == "True" for r in records))
    assert hits == {"A0": [72, 72, 72], "A3": [37, 49, 49]}

    # Arial matches the other figures of the manuscript.
    plt.rcParams.update({"font.family": "sans-serif",
                         "font.sans-serif": ["Arial", "Liberation Sans", "DejaVu Sans"],
                         "font.size": 8.4,
                         "pdf.fonttype": 42, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.linewidth": 0.65})
    fig, ax = plt.subplots(figsize=(3.37, 1.78))
    fig.subplots_adjust(left=0.14, right=0.975, top=0.76, bottom=0.22)
    x = list(range(len(runs)))
    for arm, offset, colour, name in (("A0", -0.155, "#225b82", "A0: name and description"),
                                       ("A3", 0.155, "#aa5b22", "A3: name-only variant")):
        bars = ax.bar([i + offset for i in x], hits[arm], width=0.29,
                      color=colour, label=name, zorder=3)
        ax.bar_label(bars, padding=1.6, fontsize=8.1)
    ax.set(ylim=(0, 82), yticks=[0, 24, 48, 72], xlim=(-0.48, 2.48))
    ax.set_xticks(x, ["Frozen", "Follow-up", "Later rerun"])
    ax.set_ylabel("Correct routes (of 72)")
    ax.grid(axis="y", color="#dce2e8", linewidth=0.65)
    ax.tick_params(length=2.5, pad=2)
    ax.legend(loc="lower left", bbox_to_anchor=(-0.01, 1.02), ncol=1,
              frameon=False, borderaxespad=0, fontsize=7.3,
              handlelength=1.0, handletextpad=0.45, labelspacing=0.25)
    fig.savefig(output)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("traces", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    draw(args.traces, args.output)
