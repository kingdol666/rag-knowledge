#!/usr/bin/env python3
"""Draw the verifier-score and fixed-pool ordering diagnostics (Figure 8).

The two panels read separate records over the same 16 pools. The score archive
contains 191 recorded candidates (17 gold, 174 non-gold); the order archive
contains one Hit@5 flag per pool. Assertions keep the published denominators
and counts fixed while the Origin-style artwork is regenerated.
"""
from __future__ import annotations

import argparse
import csv
import statistics
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


BLUE = "#1f4e79"
ORANGE = "#d55e00"
INK = "#222222"
GRID = "#d9e2ea"
MUTED = "#65727e"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def offsets(seed: int, count: int, span: float) -> list[float]:
    return [(((i * 37 + seed * 19) % 101) / 100 - 0.5) * span
            for i in range(count)]


def draw(scores_path: Path, order_path: Path, output: Path) -> None:
    scores = read_csv(scores_path)
    pools = read_csv(order_path)
    assert len(scores) == 191
    assert sum(r["group"] == "Gold" for r in scores) == 17
    assert sum(r["group"] == "Non-gold" for r in scores) == 174
    assert len(pools) == 16
    assert sum(int(r["fusion_hit"]) for r in pools) == 15
    assert sum(int(r["verifier_hit"]) for r in pools) == 7

    gold = [float(r["score"]) for r in scores if r["group"] == "Gold"]
    non_gold = [float(r["score"]) for r in scores if r["group"] == "Non-gold"]
    assert abs(statistics.median(gold) - 0.8759) < 1e-9
    assert abs(statistics.median(non_gold) - 0.86265) < 1e-9
    assert all(float(r["score"]) > 0.5 for r in scores)

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Liberation Sans", "DejaVu Sans"],
        "font.size": 9.0,
        "axes.labelsize": 9.0,
        "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5,
        "axes.facecolor": "white",
        "figure.facecolor": "white",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.60,
    })

    fig = plt.figure(figsize=(7.15, 3.35))
    grid = fig.add_gridspec(1, 2, width_ratios=(1.05, 0.95), wspace=0.32,
                            left=0.09, right=0.98, top=0.84, bottom=0.22)
    ax, bx = fig.add_subplot(grid[0, 0]), fig.add_subplot(grid[0, 1])

    for label, values, y, colour, seed in (
        ("Gold", gold, 0, BLUE, 3),
        ("Non-gold", non_gold, 1, ORANGE, 8),
    ):
        for value, dy in zip(values, offsets(seed, len(values), 0.42)):
            ax.scatter(value, y + dy, s=15, color=colour, alpha=0.78,
                       edgecolor="white", linewidth=0.3, zorder=2)
        median = statistics.median(values)
        ax.plot([median, median], [y - 0.27, y + 0.27], color=INK,
                linewidth=2.0, zorder=4)
        ax.text(median, y - 0.34, f"median {median:.4f}", ha="center",
                va="top", fontsize=8.5, color=INK)

    ax.axvline(0.5, color=MUTED, linestyle="--", linewidth=0.9)
    ax.text(0.505, 1.48, "cutoff 0.5", fontsize=8.0, color=MUTED, va="top")
    ax.set(xlim=(0.48, 1.01), ylim=(-0.55, 1.58),
           yticks=[0, 1], yticklabels=["Gold (n=17)", "Non-gold (n=174)"],
           xlabel="Recorded Laya verifier score")
    ax.set_title("(a) Candidate scores (191 of 192)", loc="left",
                 pad=12, fontweight="bold")
    ax.grid(axis="x", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    ax.text(0.99, -0.42, "Q14: one candidate has no recorded score",
            transform=ax.get_xaxis_transform(), ha="right", va="top",
            fontsize=8.0, color=MUTED)

    qids = [f"Q{i}" for i in range(1, 17)]
    bx.set(xlim=(-0.5, 1.5), ylim=(15.7, -0.7), xticks=[0, 1],
           xticklabels=["Fusion order", "Verifier-score order"],
           yticks=range(16), yticklabels=qids)
    for y, row in enumerate(pools):
        fusion, verifier = int(row["fusion_hit"]), int(row["verifier_hit"])
        bx.plot([0, 1], [y, y], color=GRID, linewidth=1.4, zorder=1)
        bx.scatter(0, y, s=31, marker="o", color=BLUE if fusion else "white",
                   edgecolor=BLUE, linewidth=1.0, zorder=3)
        bx.scatter(1, y, s=31, marker="D", color=ORANGE if verifier else "white",
                   edgecolor=ORANGE, linewidth=1.0, zorder=3)
    bx.set_title("(b) Paired pool hits (Hit@5)", loc="left", pad=12,
                 fontweight="bold")
    bx.grid(axis="x", color=GRID, linewidth=0.6)
    bx.set_axisbelow(True)
    bx.tick_params(axis="y", length=0)
    bx.tick_params(axis="x", length=2.5, pad=3)

    fig.text(0.98, 0.075,
             "Fusion 15/16; verifier 7/16; 8 lost, 0 gained; exact McNemar p=0.0078",
             ha="right", fontsize=8.0, color=MUTED)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", pad_inches=0.035)
    fig.savefig(output.with_suffix(".png"), dpi=360, bbox_inches="tight", pad_inches=0.035)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scores", type=Path)
    parser.add_argument("order", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    draw(args.scores, args.order, args.output)
