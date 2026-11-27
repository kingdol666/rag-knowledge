#!/usr/bin/env python3
"""Draw the verifier score distributions and paired pool outcomes (Figure 8).

The two panels use separate records over the same 16 pools. The empirical
CDFs exclude the one unrecorded score; the outcome matrix includes every
pool in the ordering replay. Neither panel measures passage admission.
"""
from __future__ import annotations

import argparse
import csv
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.ticker import PercentFormatter


WIDTH, HEIGHT = 518, 171  # Artwork coordinates in points.
BLUE = "#1f4e79"
ORANGE = "#a64717"
INK = "#202a33"
GRID = "#e3e8ed"
MUTED = "#52606c"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def draw(scores_path: Path, order_path: Path, output: Path) -> None:
    scores = read_csv(scores_path)
    pools = read_csv(order_path)
    gold = sorted(float(r["score"]) for r in scores if r["group"] == "Gold")
    non_gold = sorted(float(r["score"]) for r in scores if r["group"] == "Non-gold")
    assert len(scores) == 191 and len(gold) == 17 and len(non_gold) == 174
    assert abs(statistics.median(gold) - 0.8759) < 1e-9
    assert abs(statistics.median(non_gold) - 0.86265) < 1e-9
    assert all(0.5 < score <= 1 for score in gold + non_gold)

    qids = [f"Q{i}" for i in range(1, 17)]
    assert sorted((r["qid"] for r in pools), key=lambda q: int(q[1:])) == qids
    outcomes: dict[tuple[int, int], list[str]] = defaultdict(list)
    for row in sorted(pools, key=lambda r: int(r["qid"][1:])):
        outcomes[int(row["fusion_hit"]), int(row["verifier_hit"])].append(row["qid"])
    assert {key: len(outcomes[key]) for key in ((1, 1), (1, 0), (0, 1), (0, 0))} == {
        (1, 1): 7, (1, 0): 8, (0, 1): 0, (0, 0): 1,
    }

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Liberation Sans", "DejaVu Sans"],
        "font.size": 9.2,
        "axes.labelsize": 9.3,
        "axes.labelcolor": INK,
        "axes.edgecolor": MUTED,
        "axes.linewidth": 0.7,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "xtick.color": INK,
        "ytick.color": INK,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "text.color": INK,
    })
    fig = plt.figure(figsize=(WIDTH / 72, HEIGHT / 72), facecolor="white")

    def text(x: float, y: float, label: str, **kwargs) -> None:
        fig.text(x / WIDTH, y / HEIGHT, label, va="center", **kwargs)

    text(3, 162, "(a) Verifier score distributions", fontsize=10.5, weight="bold")
    text(279, 162, "(b) Paired top-five outcomes", fontsize=10.5, weight="bold")
    ax = fig.add_axes([41 / WIDTH, 30 / HEIGHT, 219 / WIDTH, 103 / HEIGHT])
    for values, label, color, style in (
        (gold, "Gold (n = 17)", BLUE, "-"),
        (non_gold, "Non-gold (n = 174)", ORANGE, (0, (3.5, 2.1))),
    ):
        n = len(values)
        ax.step([0.5, *values, 1.0], [0, *(i / n for i in range(1, n + 1)), 1.0],
                where="post", color=color, linestyle=style, lw=1.6, label=label)
    ax.set(xlim=(0.5, 1.0), ylim=(0, 1.025), xticks=[0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
           yticks=[0, 0.25, 0.5, 0.75, 1.0], xlabel="Laya verifier score",
           ylabel="Cumulative share (%)")
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=1, decimals=0, symbol=""))
    ax.set_axisbelow(True)
    ax.grid(axis="y", color=GRID, lw=0.55)
    ax.tick_params(length=2.5, width=0.6, pad=3)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.035), ncol=2, frameon=False,
              borderaxespad=0, handlelength=2.4, handletextpad=0.55, columnspacing=1.3)

    # Rows are Fusion outcomes, columns are verifier-score outcomes. Colour
    # only highlights the contrast; the labels and counts encode it directly.
    mx, my, cw, ch = 333, 19, 90, 55
    text(mx + cw, 143, "Verifier-score order", ha="center", weight="bold")
    text(282, my + ch, "Fusion order", rotation=90, ha="center", weight="bold")
    for index, label in enumerate(("Hit", "Miss")):
        text(mx + (index + 0.5) * cw, 133.5, label, ha="center")
        text(mx - 9, my + (1.5 - index) * ch, label, ha="right")
    cells = (
        (1, 1, "#eef3f8", BLUE),
        (1, 0, "#faeee6", ORANGE),
        (0, 1, "#f7f8fa", MUTED),
        (0, 0, "#f2f4f6", MUTED),
    )
    for first, second, fill, color in cells:
        x, y = mx + (1 - second) * cw, my + first * ch
        fig.add_artist(Rectangle((x / WIDTH, y / HEIGHT), cw / WIDTH, ch / HEIGHT,
                                 transform=fig.transFigure, facecolor=fill,
                                 edgecolor="white", linewidth=1.1))
        ids = outcomes[first, second]
        center = x + cw / 2
        text(center, y + (36 if ids else ch / 2), str(len(ids)), ha="center",
             fontsize=19, weight="bold", color=color)
        if ids:
            lines = [", ".join(ids[i:i + 4]) for i in range(0, len(ids), 4)]
            text(center, y + 15, "\n".join(lines), ha="center", fontsize=8.6)

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", pad_inches=0.028)
    fig.savefig(output.with_suffix(".png"), dpi=320, bbox_inches="tight", pad_inches=0.028)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scores", type=Path)
    parser.add_argument("order", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    draw(args.scores, args.order, args.output)
