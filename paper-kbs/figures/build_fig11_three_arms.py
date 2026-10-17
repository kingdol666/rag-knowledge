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

# ------------------------------------------------------- coverage panel (only)
# The figure carries the answer-quality contrasts only. Wall time and cost are
# stated in the text and detailed in the supplementary material; they favour the
# leaner baselines and would otherwise weigh the platform's weakest property as
# heavily as the answer checks the figure is about.
fig, ax = plt.subplots(figsize=(F.W_COL, 2.05), layout="constrained")

metrics = [("gold-ID", "gold_hit"), ("keywords", "kw_ok"), ("markers", "cited")]
ramp = ["#08519C", "#4A90C2", "#A6CEE3"]        # dark -> light, one hue
w = 0.26
for k, (mname, key) in enumerate(metrics):
    for i, t in enumerate(ARMS):
        v = graded[t][key]
        x = i + (k - 1) * w
        ax.bar(x, v, width=w, color=ramp[k], edgecolor="white", linewidth=0.4)
        ax.text(x, v + 0.12, str(v), ha="center", va="bottom")
ax.axhline(10, color=C["dgrey"], lw=0.6, ls="--")
ax.set_xticks(range(len(ARMS)))
ax.set_xticklabels([LABELS[t] for t in ARMS])
ax.set_ylabel("questions (of 10)")
ax.set_ylim(0, 11.9)
ax.set_yticks([0, 2, 4, 6, 8, 10])
ax.legend(handles=[F.Patch(fc=ramp[k], label=m)
                   for k, (m, _) in enumerate(metrics)],
          frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.03),
          ncol=3, columnspacing=0.6, handlelength=1.0, handletextpad=0.35,
          borderaxespad=0.1, borderpad=0.0)
ax.tick_params(length=2, pad=1.5)
F.hide_top_right(ax, left=True)

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
