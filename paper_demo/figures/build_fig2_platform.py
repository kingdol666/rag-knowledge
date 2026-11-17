"""Build a compact, vector overview of the platform and its two workflows."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

HERE = Path(__file__).resolve().parent
OUT = HERE / "submission-20261104"
OUT.mkdir(exist_ok=True)

INK = "#20272B"
SLATE = "#687579"
TEAL = "#009E73"
ORANGE = "#D55E00"
PALE = "#F3F8F6"
LINE = "#CBD4D6"


def box(ax, x, y, w, h, title, body, *, edge=LINE, fill="white",
        title_color=INK, title_size=8.5, body_size=8.5, body_color=INK,
        body_offset=0.085):
    patch = FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.008,rounding_size=0.012",
        linewidth=0.9, edgecolor=edge, facecolor=fill, transform=ax.transAxes,
    )
    ax.add_patch(patch)
    ax.text(x + 0.012, y + h - 0.04, title, transform=ax.transAxes,
            fontsize=title_size, fontweight="bold", color=title_color,
            va="center", ha="left")
    ax.text(x + 0.012, y + h - body_offset, body, transform=ax.transAxes,
            fontsize=body_size, color=body_color, va="top", ha="left",
            linespacing=1.16)


def arrow(ax, x1, y1, x2, y2, color=SLATE, lw=0.8):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2), transform=ax.transAxes,
        arrowstyle="-|>", mutation_scale=6, linewidth=lw,
        color=color, shrinkA=1, shrinkB=1,
    ))


def lane(ax, y, label, steps, accent):
    ax.text(0.012, y + 0.065, label, transform=ax.transAxes,
            fontsize=8.5, fontweight="bold", color=accent, va="center")
    start, width, gap, height = 0.155, 0.155, 0.011, 0.205
    for i, (title, body) in enumerate(steps):
        x = start + i * (width + gap)
        highlighted = title in {"Verify", "Judge"}
        box(ax, x, y, width, height, title, body,
            edge=accent if highlighted else LINE,
            fill=(PALE if accent == TEAL else "#FFF7F2") if highlighted else "white",
            title_color=accent if highlighted else INK,
            title_size=8.5, body_size=8.5, body_offset=0.085)
        if i < len(steps) - 1:
            arrow(ax, x + width + 0.001, y + height / 2,
                  x + width + gap - 0.001, y + height / 2,
                  color=accent, lw=0.8)


def main() -> None:
    plt.rcParams.update({
        "font.family": "Arial", "font.size": 8.5,
        "pdf.fonttype": 42, "ps.fonttype": 42,
    })
    fig, ax = plt.subplots(figsize=(7.05, 2.25))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    top = [
        (0.012, "ACCESS", "Web · CLI · MCP\n42 tools + skills"),
        (0.260, "SHARED KB", "Base > doc > part\n> section addresses\nMarkdown + registries"),
        (0.508, "INDEXES", "ChromaDB · BGE-M3\nOptional Neo4j graph"),
        (0.756, "CAPABILITIES", "CRUD · tags · search\nGraph · experience\nSOUL personas"),
    ]
    top_y, top_h, top_w = 0.66, 0.30, 0.232
    for x, title, body in top:
        shared = title == "SHARED KB"
        box(ax, x, top_y, top_w, top_h, title, body,
            edge=TEAL if shared else LINE,
            fill=PALE if shared else "white",
            title_color=TEAL if shared else INK,
            title_size=8.5, body_size=8.5, body_offset=0.085)
    # Connect the shared address model to storage and user-facing functions.
    arrow(ax, 0.247, 0.81, 0.258, 0.81)
    arrow(ax, 0.495, 0.81, 0.506, 0.81)
    arrow(ax, 0.743, 0.81, 0.754, 0.81)

    organize = [
        ("Source", "PDF /\nOffice"),
        ("Parse", "OCR /\nstructure"),
        ("Prepare", "Exact + near\nduplicates"),
        ("Describe", "Route · tag\n5-field cards"),
        ("Verify", "Index /\nC1–C9"),
    ]
    retrieve = [
        ("Query", "Rewrite\nselect lane"),
        ("Navigate", "Catalog\nbase + docs"),
        ("Recall", "Vector /\nexact scan"),
        ("Judge", "Laya gate\nscore ≥ 0.5"),
        ("Read / answer", "Cited answer\nor not-found"),
    ]
    lane(ax, 0.355, "ORGANIZE", organize, TEAL)
    lane(ax, 0.075, "RETRIEVE", retrieve, ORANGE)

    fig.savefig(OUT / "fig2-platform-overview.pdf", bbox_inches="tight")
    fig.savefig(OUT / "fig2-platform-overview.png", dpi=300, bbox_inches="tight")
    print("Wrote", OUT / "fig2-platform-overview.pdf")


if __name__ == "__main__":
    main()
