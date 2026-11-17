"""Build Figure 1: a concrete not-found example from the demo trace."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE = Path(__file__).resolve().parent
OUT = HERE / "submission-20261104"
OUT.mkdir(exist_ok=True)

INK = "#20272B"
SLATE = "#687579"
TEAL = "#009E73"
ORANGE = "#D55E00"
PALE = "#F5F7F7"
LINE = "#CBD4D6"


def card(ax, x, y, w, h, edge, fill="white", lw=1.0):
    patch = FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.018",
        linewidth=lw, edgecolor=edge, facecolor=fill, transform=ax.transAxes,
    )
    ax.add_patch(patch)


def main() -> None:
    plt.rcParams.update({
        "font.family": "Arial", "font.size": 9.5, "pdf.fonttype": 42,
        "ps.fonttype": 42, "text.color": INK,
    })
    fig, ax = plt.subplots(figsize=(7.05, 1.36))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # One actual query introduces the same running example used in Section 3.
    card(ax, 0.015, 0.57, 0.97, 0.40, SLATE, PALE)
    ax.text(0.035, 0.88, "OUT-OF-CORPUS QUESTION", transform=ax.transAxes,
            fontsize=8.6, fontweight="bold", color=SLATE, va="center")
    ax.text(0.035, 0.77,
            "“Which training epochs did the fictitious paper",
            transform=ax.transAxes, fontsize=9.1, color=INK, va="center")
    ax.text(0.035, 0.67,
            "Spectral Tuning for Low-Resource Odor Recognition use?”",
            transform=ax.transAxes, fontsize=9.1, color=INK, va="center")

    # Two juxtaposed evidence cards show the tempting near-miss and the
    # system's actual outcome; no pipeline is implied.
    card(ax, 0.015, 0.06, 0.47, 0.47, ORANGE, "white")
    card(ax, 0.515, 0.06, 0.47, 0.47, TEAL, "white")
    ax.text(0.04, 0.45, "NEAR-MISS", transform=ax.transAxes,
            fontsize=8.6, fontweight="bold", color=ORANGE, va="center")
    ax.text(0.04, 0.34, "BERT fine-tuning recipe", transform=ax.transAxes,
            fontsize=9.1, fontweight="bold", color=INK, va="center")
    ax.text(0.04, 0.22, "Not evidence about the named paper.",
            transform=ax.transAxes, fontsize=8.6, color=INK, va="center")
    ax.text(0.04, 0.12, "Query's top vector score: 0.52",
            transform=ax.transAxes, fontsize=8.6, color=SLATE, va="center")

    ax.text(0.54, 0.45, "REPORTED OUTCOME", transform=ax.transAxes,
            fontsize=8.6, fontweight="bold", color=TEAL, va="center")
    ax.text(0.54, 0.34, "Scoped not-found", transform=ax.transAxes,
            fontsize=9.1, fontweight="bold", color=INK, va="center")
    ax.text(0.54, 0.22, "10 generic hits · 12 weak title matches",
            transform=ax.transAxes, fontsize=8.6, color=INK, va="center")
    ax.text(0.54, 0.12, "No segment to grade; no epoch inferred.",
            transform=ax.transAxes, fontsize=8.6, color=INK, va="center")

    fig.savefig(OUT / "fig1-motivated-example.pdf", bbox_inches="tight")
    fig.savefig(OUT / "fig1-motivated-example.png", dpi=260, bbox_inches="tight")
    print("Wrote", OUT / "fig1-motivated-example.pdf")


if __name__ == "__main__":
    main()
