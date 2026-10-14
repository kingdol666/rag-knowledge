#!/usr/bin/env python3
"""Fig 11 --- three-arm end-to-end comparison on the arXiv corpus (30 cells).

Reads only measured artifacts and refuses to draw if the numbers it is about to
plot disagree with the graded counts, so the figure can never drift from the
run it cites:

  benchmark-suite/results/runs/run-20261013T094350Z-5f9faac/track_*.json
      -> latency / cost / tool counts, recomputed here per arm
  benchmark-suite/results/exp_r2_grade_corrected.json
      -> deterministic gold-ID / keyword / citation-marker counts per arm

House style is imported from paper-kbs/figures/figures.py (Arial, 8 pt floor,
pinned page size, overflow + page-size asserts) rather than re-implemented.
"""
from __future__ import annotations

import json
import pathlib
import statistics as st
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]          # figures <- paper-kbs <- repo root
RUN = REPO / "benchmark-suite/results/runs/run-20261013T094350Z-5f9faac"
GRADE = REPO / "benchmark-suite/results/exp_r2_grade_corrected.json"

sys.path.insert(0, str(HERE))
import figures as F  # noqa: E402  (house style + save()/guard helpers)

F.RESULTS = REPO / "benchmark-suite/results"   # retarget the house RESULTS root
OUTDIR = REPO / "paper-kbs/figures"
# the LaTeX build reads \graphicspath{{figs/}} relative to journal_20p, and the
# canonical artwork lives in paper-kbs/figures: keep both copies in lockstep so
# the compiled PDF can never be a build behind the figure.
TEXDIR = REPO / "paper-kbs/tex/journal_20p/figs"

C = F.C
plt = F.plt

ARMS = ["a2", "b", "c"]
# single-line tick labels: the two-line forms collided at print width; the
# caption and Table tab:e5-arms carry the full arm definitions.
LABELS = {"a2": "Platform", "b": "Bare agent", "c": "Dense"}
COLS = {"a2": C["blue"], "b": C["green"], "c": C["orange"]}

# ---------------------------------------------------------------- load + check
g = json.loads(GRADE.read_text(encoding="utf-8"))
assert g["run_dir"] == RUN.name, f"grader ran on {g['run_dir']}, not {RUN.name}"
graded = g["grades"]

cells = {t: [] for t in ARMS}
for t in ARMS:
    for f in sorted(RUN.glob(f"track_{t}_*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        cells[t].append(dict(
            qid=d["qid"], lat=float(d["latency_s"]),
            cost=float(d["total_cost_usd"]),
            tools=int(d.get("tool_call_count") or 0)))
for t in ARMS:
    assert len(cells[t]) == 10, f"{t}: {len(cells[t])} cells"

# the figure's own arithmetic vs the grader's --- disagreement means one of them
# is stale, and a paper number drawn from a stale artifact is worse than no
# figure at all.
n = sum(len(cells[t]) for t in ARMS)
total_cost = round(sum(c["cost"] for t in ARMS for c in cells[t]), 2)
assert n == 30 and total_cost == 17.25, (n, total_cost)
assert [graded[t]["gold_hit"] for t in ARMS] == [10, 10, 10]

# ------------------------------------------------------------------- panel (a)
fig, (a1, a2) = plt.subplots(1, 2, figsize=(F.W_FULL, 2.42),
                             gridspec_kw={"width_ratios": [1.12, 1]},
                             layout="constrained")

metrics = [("gold-ID coverage", "gold_hit"),
           ("strict keyword coverage", "kw_ok"),
           ("citation-marker hits", "cited")]
shade = {"gold-ID coverage": 1.0, "strict keyword coverage": 0.62,
         "citation-marker hits": 0.32}
w = 0.26
for k, (mname, key) in enumerate(metrics):
    for i, t in enumerate(ARMS):
        v = graded[t][key]
        x = i + (k - 1) * w
        a1.bar(x, v, width=w, color=COLS[t], alpha=shade[mname],
               edgecolor="white", linewidth=0.4)
        a1.text(x + w / 2, v + 0.18, str(v), ha="left", va="bottom")
a1.axhline(10, color=C["dgrey"], lw=0.6, ls="--")
a1.set_xticks(range(len(ARMS)))
a1.set_xticklabels([LABELS[t] for t in ARMS])
a1.set_ylabel("questions (of 10)")
a1.set_ylim(0, 11.9)
a1.set_yticks([0, 2, 4, 6, 8, 10])
a1.legend(handles=[F.Patch(fc=C["dgrey"], alpha=shade[m], ec="white",
                           label=m) for m, _ in metrics],
          frameon=False, loc="upper center",
          bbox_to_anchor=(0.5, 1.005), ncol=3, columnspacing=0.7,
          handlelength=1.0, handletextpad=0.4, borderaxespad=0.1,
          borderpad=0.0, labelspacing=0.25)
a1.tick_params(length=2, pad=1.5)
F.hide_top_right(a1, left=True)
a1.set_title("(a) Coverage checks", loc="left")

# ------------------------------------------------------------------- panel (b)
for i, t in enumerate(ARMS):
    xs = [c["lat"] for c in cells[t]]
    ys = [c["cost"] for c in cells[t]]
    a2.scatter(xs, ys, s=20, color=COLS[t], alpha=0.85, zorder=3,
               edgecolors="white", linewidths=0.4)
    mx, my = st.mean(xs), st.mean(ys)
    a2.scatter([mx], [my], s=86, marker="X", color=COLS[t], zorder=5,
               edgecolors="white", linewidths=0.6)
    a2.annotate(f"${my:.2f} / {mx:.0f}s", (mx, my),
                textcoords="offset points",
                xytext={0: (7, -2), 1: (8, 5), 2: (7, 6)}[i],
                ha="left", color=COLS[t])
a2.set_xlabel("End-to-end wall time (s)")
a2.set_ylabel("Cost per question (USD)")
a2.set_xlim(2, 112)
a2.set_ylim(0.28, 1.30)
a2.set_xticks([20, 40, 60, 80, 100])
a2.set_yticks([0.4, 0.6, 0.8, 1.0])
a2.legend(handles=[F.Patch(fc=COLS[t], label=LABELS[t].replace("\n", " "))
                   for t in ARMS],
          frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.005),
          ncol=1, handlelength=1.0, handletextpad=0.4, borderaxespad=0.1,
          borderpad=0.0, labelspacing=0.25)
a2.tick_params(length=2, pad=1.5)
F.hide_top_right(a2, left=True)
a2.set_title("(b) Time and cost", loc="left")

F.save(fig, "fig11_three_arms")
for ext in ("pdf", "png"):
    src = OUTDIR / f"fig11_three_arms.{ext}"
    if src.exists():
        (TEXDIR / src.name).write_bytes(src.read_bytes())
src = RUN.name
print(f"fig11_three_arms written  run={src}  cells={n}  total=${total_cost}")
for t in ARMS:
    lat = [c["lat"] for c in cells[t]]
    cost = [c["cost"] for c in cells[t]]
    tl = [c["tools"] for c in cells[t]]
    print(f"  {t:>2}: gold-ID {graded[t]['gold_hit']}/10"
          f"  strict-key {graded[t]['kw_ok']}/10"
          f"  alias-key {graded[t].get('kw_alias_ok', graded[t]['kw_ok'])}/10"
          f"  markers {graded[t]['cited']}/10  chunks {graded[t]['cited_chunk']}"
          f"  lat {st.mean(lat):.1f}s ({min(lat):.1f}-{max(lat):.1f})"
          f"  ${st.mean(cost):.3f} (sum ${sum(cost):.2f})"
          f"  tools {st.mean(tl):.1f} ({min(tl)}-{max(tl)})")
