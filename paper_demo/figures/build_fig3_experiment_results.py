"""Build the paper's experiment results figure from saved five-arm traces.

Primary containment rates use the 72 in-domain gold questions only.
Four out-of-domain probes are summarized separately in panel (c).
"""
from __future__ import annotations

import json
import math
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ART = (HERE.parents[1] / "review" / "experiment-redesign-20261101" / "artifacts").resolve()
OUT = HERE / "submission-20261104"
OUT.mkdir(exist_ok=True)

TEAL = "#009E73"       # Okabe-Ito green
ORANGE = "#D55E00"     # Okabe-Ito vermilion
GRAY = "#A0A8AA"
GRAY_D = "#687579"
INK = "#20272B"
ARMS = ["A0", "A1-readall", "A1b", "A2", "A3"]
LABELS = ["Ladder", "Full read", "Global vector", "No gate", "No descriptions"]
COLORS = [TEAL, ORANGE, GRAY, GRAY, GRAY]


def load(name: str):
    return json.loads((ART / name).read_text(encoding="utf-8"))


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """Wilson score interval, stable for the 72/72 full-read ceiling."""
    p = k / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, center - half), min(1.0, center + half)


def exact_mcnemar(a: list[bool], b: list[bool]) -> float:
    """Two-sided exact binomial test on paired, discordant gold outcomes."""
    a_only = sum(x and not y for x, y in zip(a, b))
    b_only = sum(not x and y for x, y in zip(a, b))
    n = a_only + b_only
    if not n:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(min(a_only, b_only) + 1))
    return min(1.0, 2 * tail / (2**n))


def main() -> None:
    traces = load("s4_traces_final.json")
    route = load("s8_route_v2.json")
    gold = {
        arm: sorted((t for t in traces[arm] if not t.get("is_refusal")),
                    key=lambda t: t["qid"])
        for arm in ARMS
    }
    stats = {}
    for arm in ARMS:
        rows = gold[arm]
        k, n = sum(bool(t.get("gold_hit")) for t in rows), len(rows)
        lo, hi = wilson(k, n)
        stats[arm] = {
            "n_gold": n, "gold_hits": k, "gold_rate": k / n,
            "wilson_95": [lo, hi],
            "avg_bytes_gold": round(statistics.mean(t.get("bytes_ingested", 0) for t in rows)),
            "avg_tool_seconds_gold": round(statistics.mean(t.get("tool_seconds", 0) for t in rows), 1),
            "avg_digest_seconds_gold": round(statistics.mean(t.get("llm_digest_seconds", 0) for t in rows), 1),
        }
    stats["mcnemar_exact_vs_A0"] = {
        arm: exact_mcnemar(
            [bool(t.get("gold_hit")) for t in gold["A0"]],
            [bool(t.get("gold_hit")) for t in gold[arm]],
        )
        for arm in ARMS[1:]
    }
    gate_arms = ("A0", "A1b", "A3")
    stats["ood_gate_rejections"] = {
        arm: {
            "n_probes": sum(bool(t.get("is_refusal")) for t in traces[arm]),
            "rejections": sum(
                bool(t.get("refusal_ok")) for t in traces[arm] if t.get("is_refusal")
            ),
        }
        if arm in gate_arms else None
        for arm in ARMS
    }
    stats["scope_note"] = (
        "Gold containment uses the 72 in-domain questions. The four out-of-domain "
        "probes are reported separately. A1b/A2 and dense/RRF used unscoped "
        "global search and returned collections outside the evaluation corpus; "
        "those vector-arm results are exploratory, not controlled comparisons."
    )
    (OUT / "figure-results.json").write_text(
        json.dumps(stats, indent=2), encoding="utf-8"
    )

    plt.rcParams.update({
        "font.family": "Arial",
        "font.size": 9.2,
        "axes.edgecolor": INK,
        "axes.labelcolor": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "text.color": INK,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })
    fig, axes = plt.subplots(1, 3, figsize=(7.05, 1.93),
                             gridspec_kw={"width_ratios": [1.55, 1.0, 1.15]})
    ax_a, ax_b, ax_c = axes

    # (a) Gold-string containment over the 72 in-domain questions only.
    xs = list(range(len(ARMS)))
    rates = [100 * stats[a]["gold_rate"] for a in ARMS]
    lows = [100 * stats[a]["wilson_95"][0] for a in ARMS]
    highs = [100 * stats[a]["wilson_95"][1] for a in ARMS]
    byte_labels = []
    for arm in ARMS:
        b = stats[arm]["avg_bytes_gold"]
        byte_labels.append(
            f"{round(b / 1_000_000):.0f}M"
            if b >= 1_000_000
            else f"{b / 1_000:.1f}k"
            if b < 2_000
            else f"{round(b / 1_000):.0f}k"
        )
    ax_a.bar(xs, rates, width=0.62, color=COLORS, zorder=3)
    ax_a.errorbar(xs, rates,
                  yerr=[[v - lo for v, lo in zip(rates, lows)],
                        [hi - v for hi, v in zip(highs, rates)]],
                  fmt="none", ecolor=INK, elinewidth=1.0, capsize=2.8, zorder=4)
    for i, v in enumerate(rates):
        ax_a.text(i, highs[i] + 2.0, f"{v:.0f}%", ha="center",
                  va="bottom", fontsize=8.6, fontweight="bold")
    short = ["A0", "A1", "A1b", "A2", "A3"]
    ax_a.set_xticks(xs, [f"{arm}\n{b}" for arm, b in zip(short, byte_labels)],
                    fontsize=8.5)
    ax_a.set_ylim(0, 112)
    ax_a.set_ylabel("Gold evidence hit (%)", fontsize=8.8)
    ax_a.set_title("(a) In-domain containment\n72 questions; Wilson 95% CI",
                   fontsize=9.0, loc="left", pad=5)
    ax_a.grid(axis="y", color="#DDE2E3", linewidth=0.5, zorder=0)
    ax_a.set_axisbelow(True)

    # (b) Routing attribution. Denominators are kept visible because the legacy
    # audit used 66 questions while the other conditions used 72.
    enr = route["enriched_route_acc"]
    old = route["old_route_acc"]
    enr_k, enr_n = [int(x) for x in enr.split("/")]
    old_k, old_n = [int(x) for x in old.split()[0].split("/")]
    a3 = [t for t in traces["A3"] if not t.get("is_refusal")]
    a3_k, a3_n = sum(bool(t.get("route_correct")) for t in a3), len(a3)
    values = [100 * old_k / old_n, 100 * enr_k / enr_n, 100 * a3_k / a3_n]
    fractions = [f"{old_k}/{old_n}", f"{enr_k}/{enr_n}", f"{a3_k}/{a3_n}"]
    ax_b.bar(range(3), values, width=0.58, color=[GRAY, TEAL, ORANGE], zorder=3)
    for i, (v, f) in enumerate(zip(values, fractions)):
        ax_b.text(i, v + 2.4, f"{v:.0f}%\n{f}", ha="center",
                  va="bottom", fontsize=8.5, fontweight="bold")
    ax_b.set_xticks(range(3), ["Legacy\ncards", "Content\nsummary", "Name\nonly"],
                    fontsize=8.5)
    ax_b.set_ylim(0, 125)
    ax_b.set_ylabel("Routing accuracy (%)", fontsize=8.5)
    ax_b.set_title("(b) Description attribution", fontsize=9.0,
                   loc="left", pad=5)
    ax_b.grid(axis="y", color="#DDE2E3", linewidth=0.5, zorder=0)
    ax_b.set_axisbelow(True)

    # (c) Evidence-gate outcomes only; A1 has no gate and A2 disables it.
    refusal_counts = []
    for arm in ARMS:
        rows = [t for t in traces[arm] if t.get("is_refusal")]
        refusal_counts.append(
            sum(bool(t.get("refusal_ok")) for t in rows)
            if arm in gate_arms else None
        )
    for i, count in enumerate(refusal_counts):
        if count is None:
            ax_c.text(i, 0.16, "N/A", ha="center", va="bottom",
                      fontsize=8.5, color=GRAY_D)
            continue
        ax_c.bar(i, count, width=0.62,
                 color=COLORS[i] if count else "#D6DBDC", zorder=3)
        ax_c.text(i, count + 0.16 if count else 0.12, f"{count}/4",
                  ha="center", va="bottom", fontsize=8.5, fontweight="bold")
    ax_c.set_xticks(xs, short, fontsize=8.5)
    ax_c.set_ylim(0, 4.7)
    ax_c.set_yticks([0, 1, 2, 3, 4])
    ax_c.set_ylabel("Gate rejections (count)", fontsize=8.5)
    ax_c.set_title("(c) Evidence gate on four OOD probes", fontsize=9.0,
                   loc="left", pad=5)
    ax_c.grid(axis="y", color="#DDE2E3", linewidth=0.5, zorder=0)
    ax_c.set_axisbelow(True)

    fig.tight_layout(pad=0.45, w_pad=1.15)
    fig.savefig(OUT / "fig3-experiment-results.pdf", bbox_inches="tight")
    fig.savefig(OUT / "fig3-experiment-results.png", dpi=300, bbox_inches="tight")
    print("Wrote vector figure:", OUT / "fig3-experiment-results.pdf")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
