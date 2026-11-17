#!/usr/bin/env python3
"""Attribution of the 35 A0 misses and the repair leverage of the
content-layer arms; single-column vector PDF + PNG.

Data: stage counts are read from the frozen attribution artefact
(review/experiment-redesign-20261101/artifacts/final_bench/
attribution_a0_misses.json: routing 0 / window truncation 5 / judge 30);
repairs (+15 A0h / +9 PD / +8 A0f) are the paired per-question gains over
A0 reported in Section E2c (n8a ladder-opt)."""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
ATTR = (HERE.parent.parent / "review" / "experiment-redesign-20261101"
        / "artifacts" / "final_bench" / "attribution_a0_misses.json")
OUT = HERE / "kbs_revision_20261111"
TARGET = HERE.parent / "KBS-Revision-20261112"

spec = importlib.util.spec_from_file_location("kbs_fig_helpers", HERE / "figures.py")
helper = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = helper
spec.loader.exec_module(helper)

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": [helper.FONT, "Arial", "DejaVu Sans"],
    "font.size": 7, "axes.labelsize": 7, "xtick.labelsize": 7,
    "ytick.labelsize": 7, "legend.fontsize": 7, "axes.linewidth": .8,
    "xtick.direction": "in", "ytick.direction": "in", "pdf.fonttype": 42,
    "ps.fonttype": 42, "savefig.facecolor": "white",
})

AMBER = "#E69F00"
BLUE = "#0072B2"


def main() -> None:
    counts = json.loads(ATTR.read_text(encoding="utf-8"))["counts"]
    misses = [
        ("Judge or\ncandidate sel.", counts["judge-miss"]),
        ("Window\ntruncation", counts["window-truncation-miss"]),
        ("Routing", counts["routing-miss"]),
    ]
    repairs = [("A0h\nwindow union", 15), ("PD\nprecise", 9), ("A0f\nfull window", 8)]

    fig, (left, right) = plt.subplots(1, 2, figsize=(3.54, 1.78))
    fig.subplots_adjust(left=.245, right=.975, bottom=.235, top=.80, wspace=.72)

    for ax, data, color, title, xmax in (
        (left, misses, AMBER, "(a) 35 A0 misses by stage", 37),
        (right, repairs, BLUE, "(b) Repairs over A0", 19),
    ):
        labels = [d[0] for d in data]
        vals = [d[1] for d in data]
        y = np.arange(len(data))[::-1]
        ax.barh(y, vals, height=.58, color=color, edgecolor="white", linewidth=.4)
        for yi, v in zip(y, vals):
            ax.text(v + xmax * .015, yi, str(v), va="center", ha="left", fontsize=7)
        ax.set_yticks(y, labels)
        ax.set_xlim(0, xmax)
        ax.set_xticks([0, 10, 20, 30] if xmax > 25 else [0, 5, 10, 15])
        ax.set_xlabel("Questions")
        ax.set_title(title, fontsize=7, pad=3, loc="left")
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="x", color="#D8DDE2", linewidth=.5)
        ax.set_axisbelow(True)
        ax.tick_params(length=2.5, width=.8)

    helper.OUT = OUT
    OUT.mkdir(parents=True, exist_ok=True)
    TARGET.mkdir(parents=True, exist_ok=True)
    helper.save(fig, "fig_attribution")
    for ext in ("pdf", "png"):
        shutil.copy2(OUT / f"fig_attribution.{ext}", TARGET / f"fig_attribution.{ext}")


if __name__ == "__main__":
    main()
