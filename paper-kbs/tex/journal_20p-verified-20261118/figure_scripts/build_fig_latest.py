#!/usr/bin/env python3
"""Build the two latest-results PDFs from the three shipped trace CSVs.

Run: python -I figure_scripts/build_fig_latest.py [--check-only | --force]
Paths are relative to this script. Only plotting requires Matplotlib. The
frozen aggregate, Nov 12 follow-up, and Nov 17 rerun reuse the same questions.
The outcome columns are archived labels, not newly scored responses.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "experiment_data"
N = 72
ARMS = ("A0", "A0f", "A0h", "PD", "A1b", "A2", "A3")
ROUTE_ARMS = ("A0", "A3")
READ_ALL = "A1-readall"
ROUTE_PDF = ROOT / "figs" / "fig_latest_route.pdf"
CONTENT_PDF = ROOT / "figs" / "fig_latest_content.pdf"


@dataclass(frozen=True)
class Campaign:
    label: str  # archival label retained in the validation report
    run: str
    filename: str
    route_group: str  # date-free display label
    route_check: tuple[int, int]
    hit_check: tuple[int, ...]


# Reference counts from the archived paper table and route audit. Plots and
# reported values are calculated from the CSV labels, not these checks.
CAMPAIGNS = (
    Campaign("Frozen aggregate", "frozen-20261111", "supp_traces_frozen.csv",
             "Frozen\naggregate", (72, 37), (37, 45, 52, 46, 39, 25, 33)),
    Campaign("Nov 12 follow-up", "followup-20261112", "supp_traces_followup.csv",
             "Follow-up", (72, 49), (39, 44, 51, 45, 39, 25, 25)),
    Campaign("Nov 17 rerun", "rerun-20261117", "supp_traces_rerun_20261117.csv",
             "Main\ncomparison", (72, 49), (36, 41, 48, 42, 36, 23, 26)),
)


@dataclass(frozen=True)
class Trace:
    refusal: bool
    hit: bool
    route: bool | None


Records = dict[str, dict[str, Trace]]  # arm -> qid -> trace


def boolean(value: str, location: str) -> bool:
    if value not in ("True", "False"):
        raise ValueError(f"{location}: expected True or False, got {value!r}")
    return value == "True"


def read_campaign(campaign: Campaign) -> tuple[Records, str]:
    path = DATA / campaign.filename
    source = path.read_bytes()
    reader = csv.DictReader(io.StringIO(source.decode("utf-8-sig"), newline=""), strict=True)
    required = {"run", "arm", "qid", "is_refusal", "route_correct", "gold_hit"}
    fields = reader.fieldnames or []
    if not required <= set(fields) or len(fields) != len(set(fields)):
        raise ValueError(f"{path.name}: missing required or duplicate headers")
    arms: Records = {}
    for row in reader:
        location = f"{path.name}:{reader.line_num}"
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"{location}: incorrect number of fields")
        arm, qid = row["arm"], row["qid"]
        if row["run"] != campaign.run or arm not in (*ARMS, READ_ALL):
            raise ValueError(f"{location}: unexpected run/arm {row['run']!r}/{arm!r}")
        if not qid or qid != qid.strip():
            raise ValueError(f"{location}: empty or whitespace-padded qid")
        records = arms.setdefault(arm, {})
        if qid in records:
            raise ValueError(f"{location}: duplicate (arm, qid) {(arm, qid)!r}")
        refusal = boolean(row["is_refusal"], f"{location} is_refusal")
        hit = boolean(row["gold_hit"], f"{location} gold_hit")
        route = (boolean(row["route_correct"], f"{location} route_correct")
                 if arm in ROUTE_ARMS and not refusal else None)
        records[qid] = Trace(refusal, hit, route)
    return arms, hashlib.sha256(source).hexdigest()


def validate_ids(batches: list[Records]) -> tuple[str, ...]:
    ids = {qid: row.refusal for qid, row in batches[0].get("A0", {}).items()}
    in_domain = tuple(sorted(qid for qid, refusal in ids.items() if not refusal))
    if len(in_domain) != N or len(ids) != N + 4:
        raise ValueError(f"Frozen A0 must have {N} in-domain and four refusal IDs")
    for campaign, arms in zip(CAMPAIGNS, batches):
        for arm in ARMS:
            rows = arms.get(arm, {})
            missing = sorted(ids.keys() - rows.keys())
            extra = sorted(rows.keys() - ids.keys())
            changed = sorted(q for q in ids.keys() & rows.keys() if rows[q].refusal != ids[q])
            if missing or extra or changed:
                raise ValueError(f"{campaign.label}, {arm}: ID/refusal mismatch: "
                                 f"missing={missing}, extra={extra}, refusal_changed={changed}")
        # Read-all is deliberately not pooled with the bounded-pack arms.
        read_all = arms.get(READ_ALL, {})
        if campaign == CAMPAIGNS[0]:
            if {q: row.refusal for q, row in read_all.items()} != ids:
                raise ValueError("Frozen read-all does not match the reference IDs")
        elif read_all:
            raise ValueError(f"{campaign.label}: unexpected read-all rows in the shipped CSV")
    return in_domain


def wilson(k: int, n: int) -> tuple[float, float]:
    z = 1.959963984540054
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def discordance(first: dict[str, Trace], second: dict[str, Trace],
                ids: tuple[str, ...], outcome: str = "hit") -> dict[str, int | float]:
    pairs = [(getattr(first[q], outcome), getattr(second[q], outcome)) for q in ids]
    first_only = sum(a is True and b is False for a, b in pairs)
    second_only = sum(b is True and a is False for a, b in pairs)
    n = first_only + second_only
    p = min(1.0, 2 * sum(math.comb(n, k) for k in range(min(first_only, second_only) + 1)) / 2**n)
    return {"first_only": first_only, "second_only": second_only,
            "mcnemar_exact_two_sided_unadjusted_p": p}


def summarize() -> dict[str, Any]:
    loaded = [read_campaign(campaign) for campaign in CAMPAIGNS]
    batches = [rows for rows, _ in loaded]
    ids = validate_ids(batches)
    records = []
    for campaign, (arms, checksum) in zip(CAMPAIGNS, loaded):
        routes = tuple(sum(arms[arm][qid].route is True for qid in ids) for arm in ROUTE_ARMS)
        hits = tuple(sum(arms[arm][qid].hit for qid in ids) for arm in ARMS)
        if routes != campaign.route_check or hits != campaign.hit_check:
            raise ValueError(f"{campaign.label}: reference count mismatch: routes={routes}, hits={hits}")
        read_all = arms.get(READ_ALL, {})
        read_all_hits = sum(read_all[qid].hit for qid in ids) if read_all else None
        if read_all and read_all_hits != N:
            raise ValueError(f"{campaign.label}: frozen read-all reference count mismatch")
        records.append({
            "label": campaign.label,
            "run": campaign.run,
            "source": f"experiment_data/{campaign.filename}",
            "sha256": checksum,
            "route_correct": {a: {"k": k, "rate": k/N} for a, k in zip(ROUTE_ARMS, routes)},
            "route_A0_vs_A3": discordance(arms["A0"], arms["A3"], ids, "route"),
            "target_containment": {a: {"k": k, "rate": k/N, "wilson_95": wilson(k, N)}
                                   for a, k in zip(ARMS, hits)},
            "containment_arm_vs_A0": {a: discordance(arms[a], arms["A0"], ids)
                                      for a in ARMS if a != "A0"},
            "containment_A0h_vs_PD": discordance(arms["A0h"], arms["PD"], ids),
            "read_all_in_domain_rows_in_csv": N if read_all else 0,
            "read_all_containment_hits_in_csv": read_all_hits,
        })
    return {
        "status": "pass",
        "same_ids_in_all_seven_arms_and_three_campaigns": True,
        "n_in_domain": len(ids),
        "n_excluded_refusal_probes_per_arm": 4,
        "campaigns_in_chronological_order": records,
        "latest_vs_history_containment": {
            campaign.label: {
                arm: {"hit_delta": (records[-1]["target_containment"][arm]["k"]
                                    - records[i]["target_containment"][arm]["k"]),
                      "same_hit_miss_label": sum(batches[-1][arm][qid].hit == batches[i][arm][qid].hit
                                                 for qid in ids)}
                for arm in ARMS
            }
            for i, campaign in enumerate(CAMPAIGNS[:-1])
        },
    }


INK = "#162735"
STEEL = "#285471"
BRICK = "#984928"
PALE_BRICK = "#F5E8E1"
SLATE = "#586774"
GRID = "#DDE4EA"
COLUMN = 252 / 72.27  # elsarticle 5p: (522 pt text width - 18 pt gutter) / 2
TEXT_WIDTH = 522 / 72.27
STYLE = {
    "font.family": "DejaVu Sans", "font.size": 8.2,
    "axes.labelsize": 8.2, "axes.linewidth": .65, "axes.edgecolor": SLATE,
    "axes.labelcolor": INK, "text.color": INK, "xtick.color": INK, "ytick.color": INK,
    "xtick.labelsize": 7.8, "ytick.labelsize": 7.8, "legend.fontsize": 7.6,
    "pdf.fonttype": 42, "text.usetex": False, "figure.facecolor": "white",
    "savefig.facecolor": "white", "savefig.bbox": None,
}


def style_axis(ax: Any) -> None:
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="both", length=2.5, width=.65, pad=3)
    ax.set_axisbelow(True)


def route_figure(plt: Any, records: list[dict[str, Any]]) -> Any:
    from matplotlib.patches import Patch

    fig, axes = plt.subplots(2, 1, figsize=(COLUMN, 3.48), sharex=True, sharey=True)
    fig.subplots_adjust(left=.155, right=.975, top=.797, bottom=.173, hspace=.42)
    a0_style = {"facecolor": STEEL, "edgecolor": STEEL, "linewidth": .7}
    a3_style = {"facecolor": PALE_BRICK, "edgecolor": BRICK, "linewidth": .7, "hatch": "///"}
    fig.legend(handles=[Patch(**a0_style, label="A0 Full cards"),
                        Patch(**a3_style, label="A3 Nominally name-only")],
               loc="upper left", bbox_to_anchor=(.122, .977), ncol=2, frameon=False,
               handlelength=1.25, columnspacing=1.15, borderaxespad=0)
    for ax, key, title in zip(axes, ("route_correct", "target_containment"),
                              ("(a) Labelled-collection selection", "(b) Target-string containment")):
        style_axis(ax)
        ax.set_title(title, loc="left", fontsize=9.1, fontweight="bold", pad=6)
        ax.set_ylim(0, 1.17)  # headroom for the 72/72 labels
        ax.set_xlim(-.48, 2.48)
        ax.set_yticks([0, .5, 1], ["0%", "50%", "100%"])
        ax.grid(axis="y", color=GRID, linewidth=.65)
        ax.tick_params(axis="both", length=0)
        ax.axvspan(1.54, 2.47, color="#F2F6F9", zorder=0)
        for arm, offset, appearance in (("A0", -.195, a0_style), ("A3", .195, a3_style)):
            for i, record in enumerate(records):
                k, rate = record[key][arm]["k"], record[key][arm]["rate"]
                ax.bar(i + offset, rate, width=.26, zorder=3, **appearance)
                ax.annotate(f"{k}/{N}", (i + offset, rate), xytext=(0, 3),
                            textcoords="offset points", ha="center", va="bottom", fontsize=7.8)
    axes[1].set_xticks(range(len(CAMPAIGNS)), [c.route_group for c in CAMPAIGNS])
    axes[1].get_xticklabels()[-1].set_fontweight("bold")
    fig.text(.155, .029, "Same 72 in-domain questions in each campaign", fontsize=7.4, color=SLATE)
    return fig


def content_figure(plt: Any, records: list[dict[str, Any]]) -> Any:
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    frozen, followup, latest = records
    fig = plt.figure(figsize=(TEXT_WIDTH, 3.30))
    forest = fig.add_axes((.077, .152, .441, .604))
    paired = fig.add_axes((.655, .152, .312, .604), sharey=forest)
    fig.text(.077, .955, "(a) Containment by arm", fontsize=9.5, fontweight="bold", va="top")
    fig.text(.655, .955, "(b) Paired outcomes vs A0", fontsize=9.5, fontweight="bold", va="top")
    fig.legend(handles=[Line2D([], [], marker="o", color=STEEL, markersize=5, linewidth=1.1,
                               label="Main comparison (95% Wilson CI)")],
               loc="upper left", bbox_to_anchor=(.074, .893), frameon=False,
               handlelength=1.6, borderaxespad=0)
    history_markers = ((frozen, "s", .08), (followup, "^", .34))
    fig.text(.077, .803, "Historical:", fontsize=7.6, color=SLATE, va="center")
    fig.legend(handles=[Line2D([], [], marker=marker, color=SLATE, markerfacecolor="white",
                               markersize=3.7, linestyle="none", label=label)
                        for (_, marker, _), label in zip(history_markers, ("Frozen aggregate", "Follow-up"))],
               loc="center left", bbox_to_anchor=(.156, .803), frameon=False, ncol=2,
               columnspacing=1.0, handletextpad=.3, handlelength=1.05, borderaxespad=0)
    a0_bar = {"facecolor": "#E8EDF1", "edgecolor": SLATE, "linewidth": .8, "hatch": "///"}
    arm_bar = {"facecolor": STEEL, "edgecolor": STEEL, "linewidth": .8}
    fig.legend(handles=[Patch(**a0_bar, label="A0 only"), Patch(**arm_bar, label="Other arm only")],
               loc="upper left", bbox_to_anchor=(.653, .893), frameon=False, ncol=2,
               handlelength=1.3, columnspacing=1.0, borderaxespad=0)
    fig.text(.655, .803, "Paired by question ID", fontsize=7.6, color=SLATE, va="center")

    for ax in (forest, paired):
        style_axis(ax)
        ax.set_ylim(len(ARMS) - .5, -.5)
        ax.set_yticks(range(len(ARMS)), ARMS)
        ax.tick_params(axis="y", length=0)
        for i in range(len(ARMS) - 1):
            ax.axhline(i + .5, color=GRID, linewidth=.55, zorder=0)
    forest.set_xlim(0, 1)
    forest.set_xticks([0, .25, .5, .75, 1], ["0%", "25%", "50%", "75%", "100%"])
    forest.set_xlabel("Target-string containment", labelpad=4)
    forest.grid(axis="x", color=GRID, linewidth=.6)
    forest.text(1.126, 1.013, "Hits", transform=forest.transAxes,
                ha="center", va="bottom", fontsize=7.6, fontweight="bold")
    paired.set_xlim(-21, 21)
    paired.set_xticks([-20, -10, 0, 10, 20], ["20", "10", "0", "10", "20"])
    paired.set_xlabel("Discordant questions (count)", labelpad=4)
    paired.tick_params(axis="y", labelleft=False)
    paired.vlines(0, .5, len(ARMS) - .5, color=SLATE, linewidth=.7, zorder=1)
    paired.text(0, 0, "Reference arm", color=SLATE, ha="center", va="center", fontsize=7.8)

    for i, arm in enumerate(ARMS):
        outcome = latest["target_containment"][arm]
        p = outcome["rate"]
        lo, hi = outcome["wilson_95"]
        forest.errorbar(p, i - .23, xerr=[[p-lo], [hi-p]], fmt="o", color=STEEL,
                        markersize=4.4, elinewidth=1.05, capsize=2.25, zorder=4)
        for past, marker, offset in history_markers:
            forest.plot(past["target_containment"][arm]["rate"], i + offset, marker,
                        markerfacecolor="white", color=SLATE, markersize=3.6, zorder=3)
        forest.text(1.126, i - .23, f"{outcome['k']}/{N}", transform=forest.get_yaxis_transform(),
                    ha="center", va="center", fontsize=8.2)
        if arm != "A0":
            pair = latest["containment_arm_vs_A0"][arm]
            for delta, style in ((-pair["second_only"], a0_bar), (pair["first_only"], arm_bar)):
                if delta:
                    paired.barh(i, delta, height=.41, **style, zorder=2)
            for count, side in ((pair["second_only"], -1), (pair["first_only"], 1)):
                paired.annotate(str(count), (side * count, i), textcoords="offset points",
                                xytext=(side * 3, 0), ha="right" if side < 0 else "left",
                                va="center", fontsize=7.8)
    fig.text(.077, .015, "Same 72 in-domain questions across campaigns. Read-all is only in the Frozen aggregate traces.",
             fontsize=7.4, color=SLATE)
    return fig


def write_figures(report: dict[str, Any], force: bool) -> None:
    for path in (ROUTE_PDF, CONTENT_PDF):
        if path.is_symlink() or (path.exists() and not force):
            raise ValueError(f"Refusing to replace {path}; use --force for existing regular outputs")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    records = report["campaigns_in_chronological_order"]
    with plt.style.context("default"), plt.rc_context(STYLE):
        for builder, path, title in (
            (route_figure, ROUTE_PDF, "Route-card comparison across archived campaigns"),
            (content_figure, CONTENT_PDF, "Main comparison evidence-pack containment"),
        ):
            fig = builder(plt, records)
            try:
                fig.savefig(path, metadata={"Title": title, "CreationDate": None})
            finally:
                plt.close(fig)
    report["matplotlib"] = matplotlib.__version__
    report["outputs"] = [str(path) for path in (ROUTE_PDF, CONTENT_PDF)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check-only", action="store_true", help="validate and report without writing PDFs")
    mode.add_argument("--force", action="store_true", help="regenerate only the two new PDF filenames")
    args = parser.parse_args()
    try:
        report = summarize()
        if not args.check_only:
            write_figures(report, args.force)
    except (OSError, ImportError, csv.Error, ValueError) as exc:
        parser.exit(1, f"FAIL: {exc}\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
