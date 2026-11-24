#!/usr/bin/env python3
"""Build the single-column tiered access diagram as vector artwork."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib.text import Text
from matplotlib.transforms import Bbox

FIGURES = Path(__file__).resolve().parents[1] / "figs"
WIDTH, HEIGHT = 252, 361  # Canvas coordinates and font sizes in PDF points.
INK, MUTED = "#172F46", "#344B60"
ARROW = "#4B6279"
DARK = ("#244863", "#244863")
ROUTE = ("#EDF3F8", "#68839A")
COMMON = ("#E0EBF4", "#5C7C98")
DECISION = ("#FFFFFF", "#708598")
ANSWER = ("#E9F3F0", "#48766C")
NO_SUPPORT = ("#F0F3F6", "#718393")
INCOMPLETE = ("#FCF2DF", "#91703C")
TITLE_SIZE, DETAIL_SIZE = 10.0, 8.6
Box = tuple[float, float, float, float]
Point = tuple[float, float]
Label = tuple[Text, Box]


def node(
    ax: Axes,
    bounds: Box,
    title: str,
    detail: str = "",
    palette: tuple[str, str] = ROUTE,
) -> list[Label]:
    x, y, width, height = bounds
    face, edge = palette
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            width,
            height,
            boxstyle="round,pad=0,rounding_size=3.5",
            facecolor=face,
            edgecolor=edge,
            linewidth=0.85,
            zorder=2,
        )
    )
    center_x, center_y = x + width / 2, y + height / 2
    title_y = center_y - (10 if "\n" in detail else 5.7) if detail else center_y
    title_color = "white" if palette == DARK else INK
    detail_color = "#EAF2F8" if palette == DARK else MUTED
    heading = ax.text(
        center_x, title_y, title, fontsize=TITLE_SIZE, weight="bold",
        color=title_color, ha="center", va="center", zorder=3,
    )
    labels = [(heading, bounds)]
    if detail:
        description = ax.text(
            center_x, center_y + 5.4, detail, fontsize=DETAIL_SIZE,
            color=detail_color, ha="center", va="center", linespacing=1.1,
            zorder=3,
        )
        labels.append((description, bounds))
    return labels


def connect(ax: Axes, *points: Point, arrow: bool = True) -> None:
    ax.add_patch(
        FancyArrowPatch(
            *points[-2:],
            arrowstyle="-|>" if arrow else "-",
            mutation_scale=8,
            shrinkA=0,
            shrinkB=0.3 if arrow else 0,
            color=ARROW,
            linewidth=0.9,
            zorder=1,
        )
    )
    if len(points) > 2:
        ax.plot(*zip(*points[:-1]), color=ARROW, linewidth=0.9, zorder=1)


def branch_label(ax: Axes, center: Point, text: str, clearance: Box) -> Label:
    artist = ax.text(
        *center, text, fontsize=DETAIL_SIZE, color=MUTED,
        ha="center", va="center", zorder=3,
    )
    return artist, clearance


def check_text(ax: Axes, labels: list[Label]) -> None:
    ax.figure.canvas.draw()
    renderer = ax.figure.canvas.get_renderer()
    extents: list[tuple[str, Bbox]] = []
    for artist, (x, y, width, height) in labels:
        extent = artist.get_window_extent(renderer).transformed(ax.transData.inverted())
        extent = Bbox.from_extents(extent.xmin, extent.ymin, extent.xmax, extent.ymax)
        if not (
            x + 3 <= extent.x0 <= extent.x1 <= x + width - 3
            and y + 1.5 <= extent.y0 <= extent.y1 <= y + height - 1.5
        ):
            raise ValueError(f"Figure label exceeds its clear area: {artist.get_text()!r}")
        for prior_text, prior_extent in extents:
            if extent.overlaps(prior_extent):
                raise ValueError(f"Figure labels overlap: {artist.get_text()!r} and {prior_text!r}")
        extents.append((artist.get_text(), extent))


def main() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Liberation Sans", "DejaVu Sans"],
            "pdf.fonttype": 42,
            "figure.dpi": 144,
        }
    )
    fig = plt.figure(figsize=(WIDTH / 72, HEIGHT / 72), facecolor="white")
    ax = fig.add_axes((0, 0, 1, 1), xlim=(0, WIDTH), ylim=(HEIGHT, 0))
    ax.set_axis_off()

    labels = node(
        ax, (33, 4, 186, 33), "Question and query rewrite",
        "Use one or both access paths", DARK,
    )
    labels += node(ax, (3, 53, 118, 34), "Pinned search", "Vector or two-stage")
    labels += node(ax, (131, 53, 118, 34), "Catalogue navigation", "Select documents from shelf")
    labels += node(
        ax, (40, 103, 172, 34), "Candidate references", "Merge and cap as configured", COMMON,
    )
    labels += node(ax, (3, 154, 118, 34), "Direct access", "Read selected passages")
    labels += node(
        ax, (131, 154, 118, 34), "Optional Laya gate", "Fetch, score, and admit",
    )
    labels += node(ax, (40, 205, 172, 23), "Inspect available evidence", palette=COMMON)
    labels += node(ax, (3, 242, 118, 24), "Review complete?", palette=DECISION)
    labels += node(
        ax, (143, 233, 106, 42), "Incomplete review",
        "Scope, errors, and\navailable evidence", INCOMPLETE,
    )
    labels += node(ax, (3, 285, 118, 24), "Support found?", palette=DECISION)
    labels += node(ax, (3, 325, 118, 32), "Answer", "With source references", ANSWER)
    labels += node(
        ax, (131, 325, 118, 32), "Scoped not-found", "Scope and blind spots", NO_SUPPORT,
    )

    # Access paths split from the question and merge before evidence selection.
    connect(ax, (126, 37), (126, 45), arrow=False)
    connect(ax, (126, 45), (62, 45), (62, 53))
    connect(ax, (126, 45), (190, 45), (190, 53))
    connect(ax, (62, 87), (62, 95), (190, 95), (190, 87), arrow=False)
    connect(ax, (126, 95), (126, 103))
    connect(ax, (126, 137), (126, 145), arrow=False)
    connect(ax, (126, 145), (62, 145), (62, 154))
    connect(ax, (126, 145), (190, 145), (190, 154))
    connect(ax, (62, 188), (62, 196), (190, 196), (190, 188), arrow=False)
    connect(ax, (126, 196), (126, 205))

    # Completion and support are separate decisions with distinct reports.
    connect(ax, (126, 228), (126, 232), (62, 232), (62, 242))
    connect(ax, (121, 254), (143, 254))
    labels.append(branch_label(ax, (132, 245), "No", (121, 238, 22, 14)))
    connect(ax, (62, 266), (62, 285))
    labels.append(branch_label(ax, (78, 275.5), "Yes", (66, 267, 24, 17)))
    connect(ax, (62, 309), (62, 325))
    labels.append(branch_label(ax, (78, 317), "Yes", (66, 309, 24, 16)))
    connect(ax, (121, 297), (190, 297), (190, 325))
    labels.append(branch_label(ax, (154, 287.5), "No", (143, 280, 22, 15)))

    check_text(ax, labels)
    stem = FIGURES / "fig_tiered_workflow_vector"
    fig.savefig(stem.with_suffix(".pdf"), metadata={"CreationDate": None})
    fig.savefig(stem.with_suffix(".png"), dpi=300)
    plt.close(fig)


if __name__ == "__main__":
    main()
