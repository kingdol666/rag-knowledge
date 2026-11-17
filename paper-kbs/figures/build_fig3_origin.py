"""Rebuild Figure 3 directly from the frozen routing-audit traces.

The figure uses Matplotlib's native plotting backend and writes editable-vector
PDF plus a 600 dpi PNG. No HTML or browser renderer is involved.
"""
from __future__ import annotations

import csv
import json
from math import comb
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FixedFormatter, FixedLocator, FuncFormatter, LogLocator


ROOT = Path(__file__).resolve().parents[2]
TRACE = ROOT / "review/experiment-redesign-20261101/artifacts/final_bench/s4_traces_final.json"
FIG_DIR = ROOT / "paper-kbs/tex/journal_20p/figs"
FIGURES_DIR = ROOT / "paper-kbs/figures"
DATA_CSV = FIGURES_DIR / "fig3_origin_data.csv"
SUMMARY_CSV = FIGURES_DIR / "fig3_origin_summary.csv"
PAIRS_CSV = FIGURES_DIR / "fig3_origin_paired_tests.csv"
PDF_OUT = FIG_DIR / "fig3_routing.pdf"
PNG_OUT = FIG_DIR / "fig3_routing.png"

ARMS = ("A0", "A3", "A1-readall")
ARM_LABELS = {
    "A0": "A0",
    "A3": "A3",
    "A1-readall": "A1\n(read-all)",
}
COLORS = {"A0": "#0072B2", "A3": "#E69F00", "A1-readall": "#009E73"}


def wilson(successes: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """Two-sided 95% Wilson score interval, returned in proportions."""
    if n == 0:
        raise ValueError("Wilson interval requires n > 0")
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def filtered_rows(traces: dict[str, list[dict]]) -> dict[str, list[dict]]:
    selected: dict[str, list[dict]] = {}
    for arm in ARMS:
        if arm not in traces:
            raise KeyError(f"Missing arm {arm!r} in {TRACE}")
        rows = [row for row in traces[arm] if not row.get("is_refusal", False)]
        if len(rows) != 72:
            raise ValueError(f"Expected 72 non-refusal rows for {arm}; got {len(rows)}")
        selected[arm] = rows
    return selected


def save_csvs(rows_by_arm: dict[str, list[dict]]) -> list[dict]:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    with DATA_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "qid", "arm", "route_correct", "gold_string_contained",
                "bytes_ingested", "tool_seconds",
            ],
        )
        writer.writeheader()
        for arm, rows in rows_by_arm.items():
            for row in rows:
                writer.writerow({
                    "qid": row["qid"],
                    "arm": arm,
                    "route_correct": row.get("route_correct", ""),
                    "gold_string_contained": row.get("gold_hit", ""),
                    "bytes_ingested": row.get("bytes_ingested", ""),
                    "tool_seconds": row.get("tool_seconds", ""),
                })

    summary: list[dict] = []
    for arm, rows in rows_by_arm.items():
        n = len(rows)
        rec: dict = {
            "arm": arm,
            "n": n,
            "route_correct_n": sum(bool(r.get("route_correct")) for r in rows) if arm != "A1-readall" else "",
            "route_correct_rate": sum(bool(r.get("route_correct")) for r in rows) / n if arm != "A1-readall" else "",
            "gold_string_contained_n": sum(bool(r.get("gold_hit")) for r in rows),
            "gold_string_contained_rate": sum(bool(r.get("gold_hit")) for r in rows) / n,
            "mean_bytes_per_query": float(np.mean([r["bytes_ingested"] for r in rows])),
            "median_bytes_per_query": float(np.median([r["bytes_ingested"] for r in rows])),
            "mean_tool_seconds_per_query": float(np.mean([r["tool_seconds"] for r in rows])),
            "median_tool_seconds_per_query": float(np.median([r["tool_seconds"] for r in rows])),
        }
        summary.append(rec)
    with SUMMARY_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)

    def exact_mcnemar(a: list[dict], b: list[dict], field: str) -> dict:
        a_by_qid = {r["qid"]: bool(r.get(field)) for r in a}
        b_by_qid = {r["qid"]: bool(r.get(field)) for r in b}
        if a_by_qid.keys() != b_by_qid.keys():
            raise ValueError(f"Unmatched qids for paired test {field}")
        a_only = sum(a_by_qid[q] and not b_by_qid[q] for q in a_by_qid)
        b_only = sum(b_by_qid[q] and not a_by_qid[q] for q in a_by_qid)
        both = sum(a_by_qid[q] and b_by_qid[q] for q in a_by_qid)
        neither = len(a_by_qid) - a_only - b_only - both
        discordant = a_only + b_only
        tail = sum(comb(discordant, k) for k in range(min(a_only, b_only) + 1))
        p_value = min(1.0, 2.0 * tail / (2 ** discordant)) if discordant else 1.0
        return {
            "endpoint": field,
            "arm_a": "",
            "arm_b": "",
            "n": len(a_by_qid),
            "both_positive": both,
            "a_only_positive": a_only,
            "b_only_positive": b_only,
            "both_negative": neither,
            "mcnemar_exact_two_sided_p": f"{p_value:.12g}",
        }

    pair_specs = [
        ("route_correct", "A0", "A3"),
        ("gold_hit", "A0", "A3"),
        ("gold_hit", "A1-readall", "A0"),
    ]
    pairs = []
    for field, arm_a, arm_b in pair_specs:
        result = exact_mcnemar(rows_by_arm[arm_a], rows_by_arm[arm_b], field)
        result["arm_a"], result["arm_b"] = arm_a, arm_b
        pairs.append(result)
    with PAIRS_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(pairs[0]))
        writer.writeheader()
        writer.writerows(pairs)
    return summary


def add_panel_label(ax, label: str, x: float = 0.0) -> None:
    ax.text(x, 1.035, label, transform=ax.transAxes, fontsize=10,
            fontweight="bold", va="bottom", ha="left")


def rate_panel(ax, rows_by_arm: dict[str, list[dict]], metric: str,
               arms: tuple[str, ...], ylabel: str, panel_label: str,
               panel_label_x: float = 0.0) -> None:
    x = np.arange(len(arms), dtype=float)
    for xpos, arm in zip(x, arms):
        rows = rows_by_arm[arm]
        successes = sum(bool(r.get(metric)) for r in rows)
        n = len(rows)
        lo, hi = wilson(successes, n)
        p = successes / n
        color = COLORS[arm]
        ax.errorbar(
            xpos, p * 100,
            yerr=np.array([[(p - lo) * 100], [(hi - p) * 100]]),
            fmt="o", markersize=6.2, color=color, ecolor="#222222",
            elinewidth=1.05, capsize=3.2, capthick=1.05, zorder=3,
        )
        # Keep count labels clear of the Wilson interval. For saturated rates,
        # retain a smaller offset so the label stays inside the panel frame.
        y_offset = 8 if p >= 0.9 else 15
        if xpos == 0:
            offset, align = (8, y_offset), "left"
        elif xpos == len(arms) - 1:
            offset, align = (-8, y_offset), "right"
        else:
            offset, align = (0, y_offset), "center"
        ax.annotate(f"{successes}/{n}", (xpos, p * 100), xytext=offset,
                    textcoords="offset points", ha=align, va="bottom",
                    fontsize=8.2, color="#222222")
    ax.set_xticks(x, [ARM_LABELS[a] for a in arms])
    ax.set_ylabel(ylabel)
    ax.set_ylim(-3, 108)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}"))
    ax.grid(axis="y", color="#D9DDE2", linewidth=0.55, zorder=0)
    ax.set_axisbelow(True)
    add_panel_label(ax, panel_label, panel_label_x)


def distribution_panel(ax, rows_by_arm: dict[str, list[dict]], metric: str,
                       ylabel: str, panel_label: str, unit_scale: float,
                       unit_label: str, fixed_limits: tuple[float, float],
                       scale: str = "log") -> None:
    arms = list(ARMS)
    rng = np.random.default_rng(20261106)
    series = [[float(r[metric]) / unit_scale for r in rows_by_arm[arm]] for arm in arms]
    positions = np.arange(1, len(arms) + 1)
    bp = ax.boxplot(
        series, positions=positions, widths=0.48, patch_artist=True,
        showfliers=False, whis=(5, 95),
        medianprops={"color": "#202020", "linewidth": 1.15},
        whiskerprops={"color": "#333333", "linewidth": 0.9},
        capprops={"color": "#333333", "linewidth": 0.9},
        boxprops={"edgecolor": "#333333", "linewidth": 0.9},
    )
    for i, (box, arm, values) in enumerate(zip(bp["boxes"], arms, series), start=1):
        box.set_facecolor(COLORS[arm])
        box.set_alpha(0.26)
        jitter = rng.uniform(-0.13, 0.13, len(values))
        ax.scatter(i + jitter, values, s=8, color=COLORS[arm], alpha=0.19,
                   edgecolors="none", zorder=2)
        mean = float(np.mean(values))
        ax.scatter(i, mean, marker="D", s=30, color="#202020", zorder=4)
        offset = (-4, -7) if i == 3 and metric == "bytes_ingested" else (4, 7)
        ax.annotate(f"{mean:.3g} {unit_label}", (i, mean), xytext=offset,
                    textcoords="offset points", ha="right" if offset[0] < 0 else "left",
                    va="top" if offset[1] < 0 else "bottom",
                    fontsize=8.1, color="#222222")
    if scale == "symlog":
        # Bytes include true zeros. Use a linear interval through 1 KB and
        # logarithmic decades above it so every observation remains visible.
        ax.set_yscale("symlog", base=10, linthresh=0.001, linscale=0.55)
        ax.yaxis.set_major_locator(FixedLocator([0, 0.001, 0.01, 0.1, 1, 10, 100]))
        ax.yaxis.set_major_formatter(FixedFormatter(
            ["0", "1 KB", "10 KB", "100 KB", "1 MB", "10 MB", "100 MB"]
        ))
    elif scale == "log":
        ax.set_yscale("log")
        ax.yaxis.set_major_locator(LogLocator(base=10, numticks=5))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    else:
        raise ValueError(f"Unsupported scale: {scale}")
    ax.set_ylim(*fixed_limits)
    labels = ["A3 (11 zeros)" if metric == "bytes_ingested" and a == "A3"
              else ARM_LABELS[a] for a in arms]
    ax.set_xticks(positions, labels)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", which="major", color="#D9DDE2", linewidth=0.55)
    ax.set_axisbelow(True)
    add_panel_label(ax, panel_label)


def main() -> None:
    traces = json.loads(TRACE.read_text(encoding="utf-8"))
    rows_by_arm = filtered_rows(traces)
    summary = save_csvs(rows_by_arm)

    plt.rcParams.update({
        "font.family": "sans-serif",
        # Elsevier artwork font list: Arial first, with metric-compatible fallbacks.
        "font.sans-serif": ["Arial", "Helvetica", "Liberation Sans", "DejaVu Sans"],
        "font.size": 8.2,
        "axes.labelsize": 8.5,
        "xtick.labelsize": 8.1,
        "ytick.labelsize": 8.1,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "savefig.facecolor": "white",
        "axes.facecolor": "white",
    })
    fig, axs = plt.subplots(2, 2, figsize=(7.15, 4.65), constrained_layout=False)
    fig.subplots_adjust(left=0.105, right=0.985, top=0.965, bottom=0.14,
                        wspace=0.34, hspace=0.48)

    rate_panel(axs[0, 0], rows_by_arm, "route_correct", ("A0", "A3"),
               "Route correctness (%)", "(a)", panel_label_x=0.91)
    rate_panel(axs[0, 1], rows_by_arm, "gold_hit", ARMS,
               "Exact gold-string containment (%)", "(b)")
    distribution_panel(axs[1, 0], rows_by_arm, "bytes_ingested",
                       "Trace-recorded text bytes per query", "(c)",
                       1_000_000, "MB", (0, 100), scale="symlog")
    distribution_panel(axs[1, 1], rows_by_arm, "tool_seconds",
                       "Tool time per question (s, log scale)", "(d)",
                       1.0, "s", (0.35, 700))

    for ax in axs.flat:
        ax.tick_params(direction="in", length=3.0, width=0.75, color="#333333",
                       top=True, right=True)
        for spine in ax.spines.values():
            spine.set_linewidth(0.8)
            spine.set_color("#333333")

    fig.savefig(PDF_OUT, format="pdf", bbox_inches="tight", metadata={
        "Title": "Routing and exact-string containment audit",
        "Subject": "Data-driven publication figure generated from frozen traces",
    })
    fig.savefig(PNG_OUT, format="png", dpi=600, bbox_inches="tight")
    plt.close(fig)

    for row in summary:
        print(
            f"{row['arm']}: n={row['n']}, "
            f"route={row['route_correct_n']}, "
            f"containment={row['gold_string_contained_n']}/{row['n']}, "
            f"mean bytes={row['mean_bytes_per_query']:.1f}, "
            f"mean tool seconds={row['mean_tool_seconds_per_query']:.3f}"
        )
    print(f"Wrote {PDF_OUT}\nWrote {PNG_OUT}\nWrote {DATA_CSV}\n"
          f"Wrote {SUMMARY_CSV}\nWrote {PAIRS_CSV}")


if __name__ == "__main__":
    main()
