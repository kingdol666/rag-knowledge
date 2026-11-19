#!/usr/bin/env python3
"""Rebuild Figures 9 and S4 only in the isolated verified journal copy.

The other historical drawing functions are kept for reference. The entry point
reads three checksum-verified archives and writes only these two figures (PDF
and PNG) and their ordering summaries. It does not run the experiments.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from io import BytesIO
from itertools import combinations
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, NullLocator
from matplotlib.transforms import ScaledTranslation


# ---------------------------------------------------------------------------
# Paths and source validation
# ---------------------------------------------------------------------------

def find_repo() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "paper-kbs").is_dir() and (parent / "benchmark-suite").is_dir():
            return parent
    raise RuntimeError("Could not locate rag-knowledge repository root")


ROOT = find_repo()
TARGET = Path(__file__).resolve().parents[1]
FIG = TARGET / "figs"
DATA = TARGET / "experiment_data"
SOURCE_MANIFEST = DATA / "figure-source-manifest.json"

FROZEN_CSV = DATA / "supp_traces_frozen.csv"
FOLLOWUP_CSV = DATA / "supp_traces_followup.csv"
FLOOR_CSV = DATA / "supp_traces_floor.csv"

ORIG_GRADE = ROOT / "benchmark-suite" / "results" / "exp_r2_grade_corrected.json"
REP_GRADE = ROOT / "benchmark-suite" / "results" / "exp_rerun5_grade.json"
OOD = ROOT / "paper-kbs" / "experiments" / "results" / "exp3_abstention.json"
SCORES = ROOT / "paper-kbs" / "experiments" / "results" / "exp1_retrieval.json"
ORDER = ROOT / "paper-kbs" / "experiments" / "results" / "exp5_judge_filter.json"
ANATOMY = ROOT / "paper-kbs" / "experiments" / "results" / "exp5_q2_anatomy.json"

# QID-to-gold fragments is the annotation used by the archived verifier score
# experiment.  It is kept here so the redraw does not execute an experiment
# module whose historical path points at a different checkout.
GOLD_DOCS = {
    "Q1": ["EVA封装膜工艺要点", "EVA封装膜湿热老化失效物理机理"],
    "Q2": ["EL-2025-0317"],
    "Q3": ["EVA封装膜湿热老化失效物理机理"],
    "Q4": ["POE胶膜工艺要点"],
    "Q5": ["发电量骤降排查手册", "电站运维经验教训"],
    "Q6": ["收口件克重警报值守条款"],
    "Q7": ["根因修订与跨频道对齐"],
    "Q8": ["PET双向拉伸薄膜工艺规程"],
    "Q9": ["逆变器告警处置手册"],
    "Q10": ["组件热斑检测与处置规程"],
    "Q11": ["组串失配分析方法"],
    "Q12": ["PP流延薄膜工艺规程"],
    "Q13": ["克重寻优-阶梯激励"],
    "Q14": ["FT全功能大考"],
    "Q15": ["三模态闭环"],
    "Q16": ["heatdecay092补偿后验证"],
}

# ---------------------------------------------------------------------------
# Publication style: one visual grammar for all eight result figures
# ---------------------------------------------------------------------------
INK = "#23394F"
STEEL = "#35689A"
LSTEEL = "#8FB3C9"
MSTEEL = "#5B8DB3"
OCHRE = "#C58A2E"
LOCHRE = "#D9A45B"
BRICK = "#A9542F"
LBRICK = "#C9775A"
SLATE = "#8D98A4"
GRID = "#E3E8ED"
FILL = "#EDF2F6"
WHITE = "#FFFFFF"

ARM_COLOR = {
    "A0": LSTEEL,
    "A0f": MSTEEL,
    "A0h": STEEL,
    "PD": OCHRE,
    "A1b": LOCHRE,
    "A2": BRICK,
    "A3": LBRICK,
    "A1-readall": SLATE,
}
ARM_LABEL = {"A1-readall": "Read-all"}
ARM_ORDER = ["A0h", "PD", "A0f", "A1b", "A0", "A3", "A2"]
FROZEN_COUNTS = {
    "A0": 37,
    "A0f": 45,
    "A0h": 52,
    "PD": 46,
    "A1b": 39,
    "A2": 25,
    "A3": 33,
    "A1-readall": 72,
}
FOLLOWUP_COUNTS = {"A0": 39, "A0f": 44, "A0h": 51, "PD": 45, "A1b": 39, "A2": 25, "A3": 25}

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Liberation Sans", "DejaVu Sans"],
        "font.size": 8.2,
        "axes.labelsize": 8.2,
        "axes.titlesize": 8.2,
        "xtick.labelsize": 8.0,
        "ytick.labelsize": 8.0,
        "legend.fontsize": 8.0,
        "axes.linewidth": 0.8,
        "axes.edgecolor": INK,
        "text.color": INK,
        "axes.labelcolor": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "xtick.direction": "in",
        "ytick.direction": "in",
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
        "xtick.minor.width": 0.6,
        "ytick.minor.width": 0.6,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "savefig.facecolor": WHITE,
        "figure.facecolor": WHITE,
        "axes.facecolor": WHITE,
        "savefig.dpi": 300,
    }
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_sources() -> dict[str, str]:
    manifest = read_json(SOURCE_MANIFEST)
    hashes: dict[str, str] = {}
    for relative, expected in manifest["sources_sha256"].items():
        source = ROOT / Path(relative)
        # The manifest mixes repository-relative archives with sources kept
        # beside the manuscript.  Resolve the latter from TARGET so the
        # reproducible builder works from a clean checkout as well.
        if not source.is_file():
            source = TARGET / Path(relative)
        if not source.is_file():
            raise FileNotFoundError(f"Manifest source is missing: {source}")
        actual = sha256(source)
        if actual != expected:
            raise ValueError(f"Source hash changed for {relative}: {actual} != {expected}")
        hashes[relative] = actual

    expected_csv = {
        "supp_traces_frozen.csv": "66b4a00d",
        "supp_traces_followup.csv": "2b23d58b",
        "supp_traces_floor.csv": "944c0fb9",
    }
    for name, prefix in expected_csv.items():
        path = DATA / name
        actual = sha256(path)
        if not actual.startswith(prefix):
            raise ValueError(f"Packaged trace checksum mismatch for {name}: {actual}")
        hashes[str(path.relative_to(TARGET)).replace("\\", "/")] = actual
    return hashes


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def in_domain(row: dict[str, str]) -> bool:
    return not row["qid"].startswith("R")


def trace_rows(path: Path) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in read_csv(path):
        if not in_domain(row):
            continue
        grouped.setdefault(row["arm"], []).append(row)
    for arm, rows in grouped.items():
        if len(rows) != 72 or len({row["qid"] for row in rows}) != 72:
            raise ValueError(f"Expected 72 in-domain rows for {arm} in {path.name}")
    return grouped


def bool_value(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def hits(rows: list[dict[str, str]], field: str = "gold_hit") -> int:
    return sum(bool_value(row.get(field)) for row in rows)


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    p = k / n
    denominator = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return max(0.0, centre - half), min(1.0, centre + half)


def mcnemar(a: list[dict[str, str]], b: list[dict[str, str]], field: str = "gold_hit") -> tuple[int, int, int, int, float]:
    a_by = {row["qid"]: bool_value(row.get(field)) for row in a}
    b_by = {row["qid"]: bool_value(row.get(field)) for row in b}
    if a_by.keys() != b_by.keys():
        raise ValueError("Paired rows have different qid sets")
    first = sum(a_by[q] and not b_by[q] for q in a_by)
    second = sum(b_by[q] and not a_by[q] for q in a_by)
    both = sum(a_by[q] and b_by[q] for q in a_by)
    neither = len(a_by) - first - second - both
    discordant = first + second
    tail = sum(math.comb(discordant, k) for k in range(min(first, second) + 1))
    p = min(1.0, 2 * tail / (2**discordant)) if discordant else 1.0
    return first, second, both, neither, p


def decorate(ax, grid_axis: str | None = "y") -> None:
    for spine in ax.spines.values():
        spine.set_color(INK)
        spine.set_linewidth(0.8)
    ax.tick_params(axis="both", direction="in", length=3.0, width=0.8, top=True, right=True, pad=3)
    ax.tick_params(which="minor", direction="in", length=1.6, width=0.6, top=True, right=True)
    ax.set_axisbelow(True)
    if grid_axis:
        ax.grid(axis=grid_axis, color=GRID, linewidth=0.5)


def panel(ax, label: str) -> None:
    ax.text(0.015, 0.985, label, transform=ax.transAxes, fontsize=9.3, fontweight="bold", ha="left", va="top")


def save_figure(fig, name: str, *, crop: tuple[float, float, float, float] | None = None) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    pdf_path = FIG / f"{name}.pdf"
    if crop is None:
        fig.savefig(pdf_path, format="pdf", facecolor=WHITE)
    else:
        # Match the shipped PDFs' crop boxes; TeX uses the cropped dimensions.
        import pymupdf

        pdf = BytesIO()
        fig.savefig(pdf, format="pdf", facecolor=WHITE)
        with pymupdf.open(stream=pdf.getvalue(), filetype="pdf") as doc:
            doc[0].set_cropbox(pymupdf.Rect(crop))
            doc.save(pdf_path)
    fig.savefig(FIG / f"{name}.png", format="png", dpi=300, facecolor=WHITE)
    plt.close(fig)


def write_csv(name: str, rows: list[dict], fields: list[str]) -> None:
    with (DATA / name).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Main-paper result figures
# ---------------------------------------------------------------------------

def draw_route(frozen: dict[str, list[dict[str, str]]]) -> None:
    a0, a3, read_all = frozen["A0"], frozen["A3"], frozen["A1-readall"]
    assert hits(a0, "route_correct") == 72
    assert hits(a3, "route_correct") == 37
    assert hits(a0) == 37 and hits(a3) == 33 and hits(read_all) == 72

    # The route audit is used in the main text as a single-column figure.  A
    # vertical stack preserves legible labels at \columnwidth; the panels are
    # kept compact (narrow hspace, shared axis limits) so the column is not
    # dominated by inter-panel whitespace.
    fig = plt.figure(figsize=(3.38, 5.30))
    grid = fig.add_gridspec(
        3, 1,
        height_ratios=[0.62, 0.92, 1.12],
        left=0.18, right=0.99, bottom=0.155, top=0.99,
        hspace=0.30,
    )
    ax_route = fig.add_subplot(grid[0, 0])
    ax_contain = fig.add_subplot(grid[1, 0])
    ax_volume = fig.add_subplot(grid[2, 0])
    records: list[dict] = []

    for ax, values, title, field, labels in [
        (ax_route, [("A0", a0), ("A3", a3)], "Gold-domain selection (%)", "route_correct", ["A0", "A3"]),
        (ax_contain, [("A0", a0), ("A3", a3), ("Read-all", read_all)], "Gold-string containment (%)", "gold_hit", ["A0", "A3", "Read-all"]),
    ]:
        for y, ((arm, rows), label) in enumerate(zip(values, labels)):
            k = hits(rows, field)
            lo, hi = wilson(k, 72)
            color = ARM_COLOR["A1-readall"] if arm == "Read-all" else ARM_COLOR[arm]
            ax.errorbar(
                k / 72 * 100, y,
                xerr=[[(k / 72 - lo) * 100], [(hi - k / 72) * 100]],
                fmt="o", ms=5.6, mfc=color, mec=INK, ecolor=INK,
                elinewidth=0.9, capsize=2.5, capthick=0.9,
                linestyle="none", zorder=3,
            )
            ax.annotate(
                f"{k}/72", (k / 72 * 100, y),
                xytext=(0, -7 if y == len(values) - 1 else 7),
                textcoords="offset points", ha="center",
                va="top" if y == len(values) - 1 else "bottom", fontsize=7.6,
            )
            records.append({
                "panel": "route" if field == "route_correct" else "containment",
                "arm": arm, "n": 72, "hits": k,
                "percent": round(k / 72 * 100, 4),
                "wilson_low": round(lo * 100, 4),
                "wilson_high": round(hi * 100, 4),
            })
        ax.set_yticks(range(len(values)), labels)
        ax.set_xlim(0, 108)
        ax.set_xticks([0, 25, 50, 75, 100])
        ax.set_xlabel(title, fontsize=7.6, labelpad=2)
        ax.set_ylim(-0.6, len(values) - 0.4)
        decorate(ax, "x")
    panel(ax_route, "(a)")
    panel(ax_contain, "(b)")

    means: dict[str, float] = {}
    for arm, rows in frozen.items():
        means[arm] = float(np.mean([float(row["bytes_ingested"]) for row in rows])) / 1_000_000
    assert round(means["A0h"], 3) == 0.309 and round(means["A1-readall"], 1) == 24.3
    y_positions = {arm: FROZEN_COUNTS[arm] / 72 * 100 for arm in FROZEN_COUNTS}
    point_offsets = {"A0h": (0, 0), "PD": (8, 0), "A0f": (-8, 0)}
    marker_by_arm = {"A0": "o", "A0f": "^", "A0h": "P", "PD": "s", "A1b": "v", "A2": "X", "A3": "D", "A1-readall": "*"}
    legend_handles = []
    for arm in FROZEN_COUNTS:
        x, y = means[arm], y_positions[arm]
        color = ARM_COLOR[arm]
        marker = marker_by_arm[arm]
        offset_x, offset_y = point_offsets.get(arm, (0, 0))
        point_transform = ax_volume.transData + ScaledTranslation(offset_x / 72, offset_y / 72, fig.dpi_scale_trans)
        ax_volume.scatter(x, y, s=48, marker=marker, transform=point_transform, facecolor=color, edgecolor=INK, linewidth=0.7, zorder=3)
        legend_handles.append(Line2D([0], [0], marker=marker, color=color, markerfacecolor=color, markeredgecolor=INK, linestyle="none", markersize=5.3, label=ARM_LABEL.get(arm, arm)))
        records.append({"panel": "volume", "arm": arm, "n": 72, "hits": FROZEN_COUNTS[arm], "percent": round(y, 4), "mean_mb": round(x, 6), "display_offset_pt_x": offset_x, "display_offset_pt_y": offset_y})
    ax_volume.set_xscale("log")
    ax_volume.set_xlim(0.001, 80)
    ax_volume.set_xticks([0.001, 0.01, 0.1, 1, 10])
    ax_volume.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:g}"))
    ax_volume.xaxis.set_minor_locator(NullLocator())
    ax_volume.set_ylim(0, 108)
    ax_volume.set_yticks([0, 25, 50, 75, 100])
    ax_volume.set_xlabel("Recorded text (MB/question; log)", fontsize=7.6, labelpad=2)
    ax_volume.set_ylabel("Gold-string containment (%)", fontsize=7.6)
    decorate(ax_volume, "y")
    panel(ax_volume, "(c)")
    ax_volume.legend(
        handles=legend_handles, loc="upper center", bbox_to_anchor=(0.5, -0.30),
        ncol=4, frameon=False, handletextpad=0.25, columnspacing=0.5,
        fontsize=7.1, borderaxespad=0.0,
    )
    write_csv("redraw_route_summary.csv", records, ["panel", "arm", "n", "hits", "percent", "wilson_low", "wilson_high", "mean_mb", "display_offset_pt_x", "display_offset_pt_y"])
    save_figure(fig, "fig_opt_route")


def draw_content(frozen: dict[str, list[dict[str, str]]], followup: dict[str, list[dict[str, str]]]) -> None:
    assert {arm: hits(rows) for arm, rows in frozen.items()} == FROZEN_COUNTS
    assert {arm: hits(rows) for arm, rows in followup.items()} == FOLLOWUP_COUNTS
    fig, (ax_rank, ax_pair) = plt.subplots(1, 2, figsize=(7.15, 2.90), gridspec_kw={"width_ratios": [1.18, 1.0]})
    fig.subplots_adjust(left=0.105, right=0.985, top=0.88, bottom=0.18, wspace=0.43)
    y_by_arm = {arm: i for i, arm in enumerate(reversed(ARM_ORDER))}
    y_by_arm["A1-readall"] = 7
    rows_out: list[dict] = []
    ax_rank.axhspan(y_by_arm["A0h"] - 0.42, y_by_arm["A0h"] + 0.42, color=FILL, zorder=0)
    ax_rank.axvline(FROZEN_COUNTS["A0"] / 72 * 100, color=SLATE, linewidth=0.8, linestyle=(0, (4, 3)), zorder=1)
    for arm in FROZEN_COUNTS:
        y = y_by_arm[arm]
        k = FROZEN_COUNTS[arm]
        lo, hi = wilson(k, 72)
        color = ARM_COLOR[arm]
        ax_rank.errorbar(k / 72 * 100, y - 0.12, xerr=[[(k / 72 - lo) * 100], [(hi - k / 72) * 100]], fmt="o", ms=5.2, mfc=color, mec=INK, ecolor=color, elinewidth=0.9, capsize=2.4, capthick=0.8, linestyle="none", zorder=3)
        follow = FOLLOWUP_COUNTS.get(arm)
        if follow is not None:
            ax_rank.scatter(follow / 72 * 100, y + 0.12, s=29, marker="^", facecolor=WHITE, edgecolor=OCHRE, linewidth=0.9, zorder=4)
            count = f"{k}/{follow}"
        else:
            count = f"{k}/--"
        ax_rank.text(0.98, y, count, transform=ax_rank.get_yaxis_transform(), fontsize=8.0, ha="right", va="center")
        rows_out.append({"panel": "aggregate", "arm": arm, "frozen": k, "followup": "" if follow is None else follow, "wilson_low": round(lo * 100, 4), "wilson_high": round(hi * 100, 4)})
    ax_rank.set_yticks(range(8), ["A2", "A3", "A0", "A1b", "A0f", "PD", "A0h", "Read-all"])
    ax_rank.set_xlim(0, 133)
    ax_rank.set_xticks([0, 20, 40, 60, 80, 100])
    ax_rank.set_xlabel("Gold-string containment (%)")
    ax_rank.set_ylim(-0.7, 7.7)
    decorate(ax_rank, "x")
    panel(ax_rank, "(a)")

    contrasts = [("A0h–A1b", "A0h", "A1b"), ("A0h–PD", "A0h", "PD"), ("PD–A1b", "PD", "A1b"), ("A0h–A0", "A0h", "A0"), ("A0f–A0", "A0f", "A0"), ("A2–A0", "A2", "A0")]
    discordance: list[dict] = []
    yvals = list(range(len(contrasts)))[::-1]
    for y, (label, first_arm, second_arm) in zip(yvals, contrasts):
        first, second, _, _, p = mcnemar(frozen[first_arm], frozen[second_arm])
        expected = {"A0h–A1b": (13, 0), "A0h–PD": (7, 1), "PD–A1b": (7, 0), "A0h–A0": (15, 0), "A0f–A0": (8, 0), "A2–A0": (6, 18)}[label]
        assert (first, second) == expected
        max_value = max(first, second)
        ax_pair.hlines(y, 0, max_value, color=GRID, linewidth=2.6, zorder=1)
        ax_pair.scatter(first, y + 0.10, s=31, marker="o", facecolor=STEEL, edgecolor=INK, linewidth=0.6, zorder=3)
        ax_pair.scatter(second, y - 0.10, s=31, marker="^", facecolor=WHITE, edgecolor=OCHRE, linewidth=0.9, zorder=3)
        ax_pair.annotate(str(first), (first, y + 0.10), xytext=(4, 0), textcoords="offset points", fontsize=8.0, color=STEEL, va="center")
        ax_pair.annotate(str(second), (second, y - 0.10), xytext=(4, 0), textcoords="offset points", fontsize=8.0, color=OCHRE, va="center")
        p_text = "p<0.001" if p < 0.001 else f"p={p:.3f}".rstrip("0").rstrip(".")
        ax_pair.text(27.5, y, p_text, fontsize=8.0, ha="right", va="center")
        discordance.append({"contrast": label, "first_only": first, "second_only": second, "p": f"{p:.12g}"})
    ax_pair.set_yticks(yvals, [item[0] for item in contrasts])
    ax_pair.set_xlim(-1.0, 29)
    ax_pair.set_xticks([0, 5, 10, 15, 20])
    ax_pair.set_xlabel("Discordant questions (n=72)")
    ax_pair.set_ylim(-0.7, 5.7)
    decorate(ax_pair, "x")
    panel(ax_pair, "(b)")
    fig.legend(handles=[Line2D([0], [0], marker="o", color=STEEL, linestyle="none", markersize=5.2, label="Frozen (Wilson 95% CI)"), Line2D([0], [0], marker="^", markerfacecolor=WHITE, markeredgecolor=OCHRE, color=OCHRE, linestyle="none", markersize=5.6, label="Same-question follow-up")], loc="upper center", bbox_to_anchor=(0.5, 0.995), ncol=2, frameon=False, handletextpad=0.35, columnspacing=1.4)
    write_csv("redraw_content_summary.csv", rows_out + discordance, ["panel", "arm", "frozen", "followup", "wilson_low", "wilson_high", "contrast", "first_only", "second_only", "p"])
    save_figure(fig, "fig_opt_content")


def read_grade(path: Path) -> dict:
    grade = read_json(path)
    rows = grade["rows"]
    qids = [f"BQ{i:02d}" for i in range(1, 11)]
    for track in ("a2", "b", "c"):
        assert [row["qid"] for row in rows if row["track"] == track] == qids
    return grade


def draw_answer(orig: dict, rep: dict) -> None:
    matrices = {(name, track): [row for row in source["rows"] if row["track"] == track] for source, name in [(orig, "original"), (rep, "common") ] for track in ("a2", "b", "c")}
    for name, expected_markers, expected_strict, expected_alias in [
        ("original", {"a2": 9, "b": 7, "c": 2}, {"a2": 9, "b": 9, "c": 9}, {"a2": 10, "b": 10, "c": 10}),
        ("common", {"a2": 9, "b": 9, "c": 9}, {"a2": 7, "b": 7, "c": 8}, {"a2": 9, "b": 9, "c": 10}),
    ]:
        for track in ("a2", "b", "c"):
            data = matrices[(name, track)]
            assert sum(bool_value(row["cited"]) for row in data) == expected_markers[track]
            assert sum(bool_value(row["pass"]) for row in data) == expected_strict[track]
            assert sum(bool_value(row["kw_alias_ok"]) for row in data) == expected_alias[track]
            assert sum(bool_value(row["gold_hit"]) for row in data) == 10
    colors = {"a2": STEEL, "b": OCHRE, "c": BRICK}
    labels = {"a2": "P", "b": "F", "c": "C"}
    fig, axes = plt.subplots(1, 2, figsize=(7.15, 2.55), sharey=True)
    fig.subplots_adjust(left=0.075, right=0.955, top=0.79, bottom=0.29, wspace=0.16)
    output: list[dict] = []
    for ax, name, title in [(axes[0], "original", "Original substrates"), (axes[1], "common", "Common five-library substrate")]:
        for j, track in enumerate(("a2", "b", "c")):
            y = 2 - j
            data = matrices[(name, track)]
            for i, row in enumerate(data):
                marker = bool_value(row["cited"])
                ax.scatter(i, y, s=42, marker="s", facecolor=colors[track] if marker else WHITE, edgecolor=colors[track], linewidth=0.9, zorder=3)
                output.append({"grid": name, "arm": labels[track], "qid": row["qid"], "marker": int(marker), "gold_id": int(bool_value(row["gold_hit"])), "strict": int(bool_value(row["pass"])), "alias": int(bool_value(row["kw_alias_ok"]))})
            count = sum(bool_value(row["cited"]) for row in data)
            ax.text(10.15, y, f"{count}/10", fontsize=8.0, color=colors[track], fontweight="bold", va="center")
        ax.set_xlim(-0.6, 11.1)
        ax.set_ylim(2.6, -0.6)
        ax.set_xticks(range(10), [f"{i:02d}" for i in range(1, 11)])
        ax.set_yticks([2, 1, 0], ["P", "F", "C"])
        ax.set_xlabel("Question (BQ)")
        decorate(ax, "both")
        ax.text(0.015, 1.02, title, transform=ax.transAxes, fontsize=8.3, fontweight="bold", va="bottom")
    axes[0].set_ylabel("Answer-grid arm")
    fig.legend(handles=[Line2D([0], [0], marker="s", color=INK, markerfacecolor=STEEL, linestyle="none", markersize=5.8, label="Marker present"), Line2D([0], [0], marker="s", color=INK, markerfacecolor=WHITE, linestyle="none", markersize=5.8, label="No marker")], loc="upper center", bbox_to_anchor=(0.5, 0.985), ncol=2, frameon=False, handletextpad=0.35, columnspacing=1.4)
    write_csv("redraw_answer_matrix.csv", output, ["grid", "arm", "qid", "marker", "gold_id", "strict", "alias"])
    save_figure(fig, "fig_opt_answer")


def ordering_replay(order: dict) -> tuple[list[dict], dict[str, int]]:
    """Validate the historical comparison of orders on verifier survivors."""
    run = sorted(order["rows"], key=lambda item: int(item["qid"][1:]))
    if [row["qid"] for row in run] != [f"Q{i}" for i in range(1, 17)]:
        raise ValueError("Expected one historical ordering replay for each of Q1–Q16")
    counts = {}
    # exp5_judge_filter.py derives filter_only by intersecting the pre-judge
    # fusion order with cut.kept; judged sorts those survivors by score.
    for key in ("filter_only", "judged"):
        for row in run:
            entry = row[key]
            rank = entry["best_rank"]
            if entry["hit"] is not (rank is not None and 1 <= rank <= 5):
                raise ValueError(f"Hit@5 and best rank disagree: {row['qid']} {key}")
        counts[key] = sum(row[key]["hit"] for row in run)
        if counts[key] / len(run) != order["summary"][key]["hit@5"]:
            raise ValueError(f"Per-question Hit@5 does not match the summary: {key}")
    return run, counts


def draw_verifier(scores: dict, run: list[dict], counts: dict[str, int]) -> None:
    score_rows: list[dict] = []
    for row in scores["rows"]:
        if row.get("method") not in {"qdcvr_hybrid", "hmrs_hybrid"} or "judge_scores" not in row:
            continue
        qid = row["qid"]
        for candidate, value in row["judge_scores"]["all"].items():
            is_gold = any(fragment.lower() in candidate.lower() for fragment in GOLD_DOCS[qid])
            score_rows.append({"qid": qid, "group": "Gold" if is_gold else "Non-gold", "score": float(value)})
    gold = [item["score"] for item in score_rows if item["group"] == "Gold"]
    non = [item["score"] for item in score_rows if item["group"] == "Non-gold"]
    assert [len(gold), len(non)] == [17, 174]
    assert min(gold + non) > 0.5
    assert round(float(np.median(gold)), 2) == 0.88 and round(float(np.median(non)), 2) == 0.86

    fig, (ax_score, ax_order) = plt.subplots(1, 2, figsize=(7.15, 2.55), gridspec_kw={"width_ratios": [1.0, 1.45]})
    fig.subplots_adjust(left=0.095, right=0.975, top=0.82, bottom=0.25, wspace=0.50)
    rng = np.random.default_rng(523)
    for i, (values, color, marker) in enumerate([(gold, STEEL, "o"), (non, SLATE, "s")]):
        jitter = rng.uniform(-0.15, 0.15, len(values)) + i
        ax_score.scatter(jitter, values, s=15, marker=marker, facecolor=color, edgecolor="none", alpha=0.55, zorder=2)
        median = float(np.median(values))
        ax_score.hlines(median, i - 0.23, i + 0.23, colors=INK, linewidth=1.5, zorder=3)
        ax_score.annotate(f"{median:.2f}", (i + 0.25, median), fontsize=8.0, va="center")
    ax_score.axhline(0.5, color=INK, linewidth=0.8, linestyle=(0, (4, 3)))
    ax_score.set_xlim(-0.55, 1.55)
    ax_score.set_ylim(0.45, 1.03)
    ax_score.set_yticks([0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
    ax_score.set_xticks([0, 1], ["Gold\n(n=17)", "Non-gold\n(n=174)"])
    ax_score.set_ylabel("Verifier score")
    decorate(ax_score, "y")
    panel(ax_score, "(a)")

    for y, key, color, marker in [(1, "judged", BRICK, "o"), (0, "filter_only", STEEL, "s")]:
        for x, item in enumerate(run):
            hit = item[key]["hit"]
            ax_order.scatter(x, y, s=37, marker=marker, facecolor=color if hit else WHITE, edgecolor=color, linewidth=0.9, zorder=3)
        ax_order.text(17.45, y, f"{counts[key]}/{len(run)}", fontsize=8.2, color=color, fontweight="bold", va="center", ha="right")
    ax_order.set_xlim(-0.6, 18.0)
    ax_order.set_ylim(1.55, -0.55)
    ax_order.set_yticks([1, 0], ["Verifier-score\norder", "Fusion order\n(retained only)"])
    ax_order.set_xticks([0, 3, 7, 11, 15], ["1", "4", "8", "12", "16"])
    ax_order.set_xlabel("Question number")
    decorate(ax_order, "both")
    panel(ax_order, "(b)")
    fig.legend(handles=[Line2D([0], [0], marker="s", color=STEEL, markerfacecolor=STEEL, linestyle="none", markersize=5.5, label="Hit@5"), Line2D([0], [0], marker="s", color=STEEL, markerfacecolor=WHITE, linestyle="none", markersize=5.5, label="Miss")], loc="upper center", bbox_to_anchor=(0.5, 0.985), ncol=2, frameon=False, handletextpad=0.35, columnspacing=1.4)
    write_csv("redraw_verifier_scores.csv", score_rows, ["qid", "group", "score"])
    write_csv("redraw_verifier_order.csv", [{"qid": item["qid"], "filter_only_hit": int(item["filter_only"]["hit"]), "judged_hit": int(item["judged"]["hit"])} for item in run], ["qid", "filter_only_hit", "judged_hit"])
    save_figure(fig, "fig_opt_verifier", crop=(18.04, 4.72, 507.56, 163.40))


# ---------------------------------------------------------------------------
# Supplementary result figures
# ---------------------------------------------------------------------------

def draw_supp_answer(original: dict) -> None:
    grades = original["grades"]
    expected = {"a2": (10, 9, 9), "b": (10, 9, 7), "c": (10, 9, 2)}
    for track, values in expected.items():
        assert (grades[track]["gold_hit"], grades[track]["kw_ok"], grades[track]["cited"]) == values
    fig, ax = plt.subplots(figsize=(3.45, 2.45))
    fig.subplots_adjust(left=0.16, right=0.985, top=0.72, bottom=0.22)
    metrics = [("Gold-ID", "gold_hit", STEEL), ("Strict keywords", "kw_ok", LSTEEL), ("Markers", "cited", BRICK)]
    arms = [("P", "a2"), ("F", "b"), ("C", "c")]
    width = 0.24
    records: list[dict] = []
    for metric_index, (label, key, color) in enumerate(metrics):
        for arm_index, (arm, track) in enumerate(arms):
            value = grades[track][key]
            x = arm_index + (metric_index - 1) * width
            ax.bar(x, value, width=width, color=color, edgecolor=WHITE, linewidth=0.4, zorder=3)
            ax.text(x, value + 0.18, str(value), ha="center", va="bottom", fontsize=7.8)
            records.append({"arm": arm, "metric": label, "n": 10, "value": value})
    ax.axhline(10, color=SLATE, linewidth=0.6, linestyle=(0, (4, 3)))
    ax.set_xticks(range(3), [arm[0] for arm in arms])
    ax.set_ylim(0, 12.5)
    ax.set_yticks([0, 2, 4, 6, 8, 10])
    ax.set_ylabel("Questions (of 10)")
    ax.set_xlabel("Answer-grid arm")
    decorate(ax, "y")
    ax.legend(handles=[Line2D([0], [0], color=color, marker="s", linestyle="none", markersize=5.0, label=label) for label, _, color in metrics], loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=3, frameon=False, fontsize=8.0, handletextpad=0.3, columnspacing=0.8, borderaxespad=0.0)
    write_csv("redraw_supp_answer.csv", records, ["arm", "metric", "n", "value"])
    save_figure(fig, "fig_opt_s_answer")


def draw_supp_ood(ood: dict) -> None:
    labels = ["Battery", "Vaccination", "Python", "Mould"]
    rows = ood["probes"]
    assert len(rows) == 4
    fig, ax = plt.subplots(figsize=(3.45, 2.65))
    fig.subplots_adjust(left=0.26, right=0.97, bottom=0.18, top=0.78)
    records: list[dict] = []
    for i, (row, label) in enumerate(zip(rows, labels)):
        survivor = row["kept_n"]
        dense = row["vector_above_0.35"]
        ax.scatter(survivor, i - 0.15, s=31, marker="o", facecolor=STEEL, edgecolor=INK, linewidth=0.5, zorder=3)
        ax.scatter(dense, i + 0.15, s=31, marker="s", facecolor=OCHRE, edgecolor=INK, linewidth=0.5, zorder=3)
        ax.annotate(str(survivor), (survivor, i - 0.15), xytext=(4, 0), textcoords="offset points", va="center", fontsize=8.0, color=STEEL)
        ax.annotate(str(dense), (dense, i + 0.15), xytext=(4, 0), textcoords="offset points", va="center", fontsize=8.0, color=OCHRE)
        records.append({"qid": row["qid"], "topic": row["topic"], "judge_survivors_documents": survivor, "dense_chunks_ge_0_35": dense, "merged_candidates": row["merge_n"]})
    ax.set_yticks(range(4), labels)
    ax.set_ylim(3.55, -0.55)
    ax.set_xlim(0, 14)
    ax.set_xticks([0, 3, 6, 9, 12])
    ax.set_xlabel("Count per probe")
    decorate(ax, "x")
    ax.legend(handles=[Line2D([0], [0], marker="o", color=STEEL, linestyle="none", markersize=5.0, label="Surviving documents"), Line2D([0], [0], marker="s", color=OCHRE, linestyle="none", markersize=5.0, label="Dense chunks ≥ 0.35")], loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=1, frameon=False, borderaxespad=0.0)
    write_csv("redraw_supp_ood.csv", records, ["qid", "topic", "judge_survivors_documents", "dense_chunks_ge_0_35", "merged_candidates"])
    save_figure(fig, "fig_exp_s3")


def draw_supp_margin(ood: dict, counts: dict[str, int], n: int) -> None:
    cut = ood["cut_replay"]
    keys = ["0.05", "0.1", "0.15", "0.2", "0.25", "0.3", "0.35"]
    margins = [float(key) for key in keys]
    gold_kept = [int(cut[key]["gold_kept"]) for key in keys]
    mean_kept = [float(cut[key]["mean_kept"]) for key in keys]
    assert gold_kept == [8, 14, 16, 17, 17, 17, 17]
    assert mean_kept == [6.4, 8.9, 10.4, 11.1, 11.4, 11.7, 11.9]
    roles = [("filter_only", "Fusion order", STEEL), ("judged", "Verifier score order", BRICK)]
    fig, (ax_margin, ax_roles) = plt.subplots(1, 2, figsize=(7.15, 2.45), gridspec_kw={"width_ratios": [1.05, 1.0]})
    fig.subplots_adjust(left=0.085, right=0.985, top=0.84, bottom=0.22, wspace=0.37)
    ax_margin.plot(margins, gold_kept, color=STEEL, marker="o", markersize=4.6, linewidth=1.0, zorder=3)
    ax_margin.axvline(0.15, color=SLATE, linewidth=0.9, linestyle=(0, (4, 3)), zorder=1)
    ax_margin.axvline(0.20, color=STEEL, linewidth=0.9, linestyle=(0, (4, 3)), zorder=1)
    ax_margin.annotate("16/17", (0.15, 16), xytext=(-5, 6), textcoords="offset points", fontsize=8.0, ha="right")
    ax_margin.annotate("17/17", (0.20, 17), xytext=(5, 6), textcoords="offset points", fontsize=8.0, ha="left")
    ax_margin.set_xlim(0.035, 0.365)
    ax_margin.set_ylim(0, 18.5)
    ax_margin.set_xticks(margins)
    ax_margin.set_yticks([0, 4, 8, 12, 16])
    ax_margin.set_xlabel("Relative margin m")
    ax_margin.set_ylabel("Gold instances kept (of 17)")
    decorate(ax_margin, "y")
    panel(ax_margin, "(a)")
    for i, (key, _, color) in enumerate(roles):
        hits = counts[key]
        value = hits / n
        ax_roles.bar(i, value, width=0.39, color=color, edgecolor=WHITE, linewidth=0.4, zorder=3)
        ax_roles.text(i, value + 0.018, f"{hits}/{n}", ha="center", va="bottom", fontsize=8.0)
    ax_roles.set_xlim(-0.5, len(roles) - 0.5)
    ax_roles.set_xticks(range(len(roles)), [label for _, label, _ in roles])
    ax_roles.set_ylim(0, 1.10)
    ax_roles.set_yticks([0, 0.5, 1.0])
    ax_roles.set_ylabel("Hit@5")
    ax_roles.set_xlabel("Order of retained candidates")
    decorate(ax_roles, "y")
    panel(ax_roles, "(b)")
    records = [{"panel": "margin", "margin": margin, "gold_kept": gold, "mean_kept": mean} for margin, gold, mean in zip(margins, gold_kept, mean_kept)] + [{"panel": "role", "role": key, "hit_at_5": counts[key] / n} for key, _, _ in roles]
    write_csv("redraw_supp_margin.csv", records, ["panel", "margin", "gold_kept", "mean_kept", "role", "hit_at_5"])
    save_figure(fig, "fig_opt_s_margin", crop=(15.16, 19.84, 512.60, 164.48))


def draw_supp_anatomy(anatomy: dict) -> None:
    response = anatomy["response"]
    fusion = [path.replace("\\", "/") for path in response["merge"]["judged_candidates"]]
    scores = {row["doc_path"].replace("\\", "/"): float(row["score"]) for row in response["cut"]["kept"]}
    assert len(fusion) == len(scores) == 12 and set(fusion) == set(scores)
    judged = sorted(scores, key=lambda path: -scores[path])

    def candidate_class(path: str) -> str:
        if "EL-2025-0317" in path:
            return "Gold"
        if "aw-industrial/【演示线1" in path:
            return "Telemetry"
        return "Other"

    classes = [candidate_class(path) for path in fusion]
    assert classes.count("Gold") == 1 and classes.count("Telemetry") == 5
    colors = {"Gold": STEEL, "Telemetry": OCHRE, "Other": SLATE}
    fig, axes = plt.subplots(1, 2, figsize=(7.15, 2.80), sharey=True)
    fig.subplots_adjust(left=0.10, right=0.97, bottom=0.23, top=0.80, wspace=0.30)
    records: list[dict] = []
    for ax, output_order, title in [(axes[0], judged, "Verifier order"), (axes[1], fusion, "Filter-only order")]:
        ax.axhspan(0.5, 5.5, color=FILL, zorder=0)
        for i, path in enumerate(fusion):
            kind = candidate_class(path)
            rank = output_order.index(path) + 1
            ax.plot([0, 1], [i + 1, rank], color=colors[kind], linewidth=1.7 if kind == "Gold" else 0.9 if kind == "Telemetry" else 0.6, marker="o", markersize=3.7 if kind == "Gold" else 2.8, zorder=4 if kind == "Gold" else 3)
            records.append({"input_rank": i + 1, "output_rank": rank, "score": round(scores[path], 6), "class": kind})
        ax.set_xlim(-0.12, 1.12)
        ax.set_ylim(12.8, 0.2)
        ax.set_xticks([0, 1], ["Fusion", "Output"])
        ax.set_yticks([1, 5, 9, 12])
        decorate(ax, None)
        ax.text(0.015, 1.04, title, transform=ax.transAxes, fontsize=8.4, fontweight="bold", va="bottom")
    axes[0].set_ylabel("Rank (1 = highest)")
    axes[1].set_yticklabels([])
    fig.legend(handles=[Line2D([0], [0], color=STEEL, linewidth=1.6, label="Gold"), Line2D([0], [0], color=OCHRE, linewidth=1.0, label="Telemetry"), Line2D([0], [0], color=SLATE, linewidth=0.8, label="Other")], loc="lower center", bbox_to_anchor=(0.5, 0.01), ncol=3, frameon=False, handlelength=1.3, columnspacing=1.4)
    write_csv("redraw_supp_anatomy.csv", records, ["input_rank", "output_rank", "score", "class"])
    save_figure(fig, "fig_exp_s5")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    if TARGET != ROOT / "paper-kbs" / "tex" / "journal_20p-verified-20261118":
        raise RuntimeError(f"Refusing to rebuild outside the isolated verified copy: {TARGET}")
    if any(path.resolve().parent != TARGET for path in (FIG, DATA)):
        raise RuntimeError("Figure and data directories must resolve inside the isolated copy")
    for path in (
        *(FIG / f"{stem}.{ext}" for stem in ("fig_opt_verifier", "fig_opt_s_margin") for ext in ("pdf", "png")),
        DATA / "redraw_verifier_order.csv",
        DATA / "redraw_supp_margin.csv",
    ):
        if path.resolve().parent != path.parent:
            raise RuntimeError(f"Refusing redirected output: {path}")

    # Figure 9a: logged scores; S4a: relative-margin cut replay. Neither is
    # computed from the separate ordering record used by both (b) panels.
    frozen_hashes = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))["sources_sha256"]
    archives = {}
    for source in (SCORES, OOD, ORDER):
        key = source.relative_to(ROOT).as_posix()
        raw = source.read_bytes()
        if hashlib.sha256(raw).hexdigest() != frozen_hashes[key]:
            raise ValueError(f"Frozen archive checksum mismatch: {source}")
        archives[source] = json.loads(raw)
    run, counts = ordering_replay(archives[ORDER])
    draw_verifier(archives[SCORES], run, counts)
    draw_supp_margin(archives[OOD], counts, len(run))
    print(f"Rebuilt only Figures 9 and S4 (and their ordering CSVs) in {TARGET}")


if __name__ == "__main__":
    main()
