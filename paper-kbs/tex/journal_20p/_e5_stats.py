#!/usr/bin/env python3
"""Recompute every number the paper's E5 will report, straight from the raw cells.

Writes a small JSON + a human-readable digest so figure and prose numbers come
from one place (no transcription drift).
"""
from __future__ import annotations

import json
import pathlib
import statistics as st

REPO = pathlib.Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge")
RUN = REPO / "benchmark-suite/results/runs/run-20261013T094350Z-5f9faac"
STAB = REPO / "review/stability-multiround-20261013/results"
OUT = pathlib.Path(__file__).resolve().parent

tracks = ("a2", "b", "c")
rows: dict[str, list[dict]] = {t: [] for t in tracks}
for t in tracks:
    for f in sorted(RUN.glob(f"track_{t}_*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        rows[t].append(dict(
            qid=d["qid"], lat=d["latency_s"], cost=d["total_cost_usd"],
            tools=d.get("tool_call_count") or len(d.get("tool_calls") or []),
            turns=d.get("num_turns"), t_in=d["tokens"]["input"],
            t_out=d["tokens"]["output"], cache=d["tokens"].get("cache_read", 0),
            err=bool(d.get("is_error")),
        ))

agg = {}
for t in tracks:
    r = rows[t]
    lat = [x["lat"] for x in r]
    cost = [x["cost"] for x in r]
    tools = [x["tools"] for x in r]
    agg[t] = dict(
        n=len(r),
        lat_mean=round(st.mean(lat), 1), lat_med=round(st.median(lat), 1),
        lat_min=min(lat), lat_max=max(lat),
        cost_mean=round(st.mean(cost), 4), cost_sum=round(sum(cost), 2),
        tools_mean=round(st.mean(tools), 1), tools_min=min(tools), tools_max=max(tools),
        turns_mean=round(st.mean([x["turns"] for x in r]), 1),
        tok_in=sum(x["t_in"] for x in r), tok_out=sum(x["t_out"] for x in r),
        errors=sum(x["err"] for x in r),
    )

# paired a2-vs-b cost and latency gaps
pair = []
for i in range(len(rows["a2"])):
    a, b = rows["a2"][i], rows["b"][i]
    c = rows["c"][i]
    pair.append(dict(qid=a["qid"], dcost_ab=round(a["cost"] - b["cost"], 4),
                     dlat_ab=round(a["lat"] - b["lat"], 1),
                     dcost_ac=round(a["cost"] - c["cost"], 4),
                     dlat_ac=round(a["lat"] - c["lat"], 1)))
dc = [p["dcost_ab"] for p in pair]
dl = [p["dlat_ab"] for p in pair]
n = len(dc)


def paired_t(xs: list[float]) -> float:
    m = st.mean(xs)
    s = st.stdev(xs)
    return m / (s / n ** 0.5)


print("=== per-arm ===")
for t in tracks:
    a = agg[t]
    print(f"[{t}] n={a['n']} lat mean/med {a['lat_mean']}/{a['lat_med']}s "
          f"({a['lat_min']}-{a['lat_max']})  cost ${a['cost_mean']} (sum ${a['cost_sum']})  "
          f"tools {a['tools_mean']} ({a['tools_min']}-{a['tools_max']})  turns {a['turns_mean']}  "
          f"tok in {a['tok_in']:,} out {a['tok_out']:,}")

print("\n=== paired a2 - b ===")
print(f"  cost: a2 dearer on {sum(1 for x in dc if x > 0)}/{n} questions; "
      f"mean diff ${round(st.mean(dc), 4)}; paired t = {round(paired_t(dc), 2)}; "
      f"range ${min(dc)} to ${max(dc)}")
print(f"  latency: a2 slower on {sum(1 for x in dl if x > 0)}/{n}; "
      f"mean diff {round(st.mean(dl), 1)}s; paired t = {round(paired_t(dl), 2)}")
dca = [p["dcost_ac"] for p in pair]
dla = [p["dlat_ac"] for p in pair]
print(f"  (a2 - c) cost mean ${round(st.mean(dca), 4)} t={round(paired_t(dca), 2)}; "
      f"latency mean {round(st.mean(dla), 1)}s t={round(paired_t(dla), 2)}")

tot_cost = round(sum(agg[t]["cost_sum"] for t in tracks), 2)
print(f"\nGRAND TOTAL cost ${tot_cost} over 30 cells")

print("\n=== stability suite ===")
stab = sorted(STAB.glob("r*_*.json"))
beh, lanes = 0, 0
walls, lanes_seen = [], {}
for f in stab:
    d = json.loads(f.read_text(encoding="utf-8"))
    walls.append(d.get("wall_s") or d.get("wall"))
    l = f.stem.split("_")[-1]
    lanes_seen[l] = lanes_seen.get(l, 0) + 1
print(f"  cells {len(stab)} · lanes {lanes_seen}")
print(f"  wall {min(walls):.1f}-{max(walls):.1f}s median {st.median(walls):.1f}s")
print(f"  keys of one cell: {sorted(json.loads(stab[0].read_text(encoding='utf-8')))}")

digest = dict(run="run-20261013T094350Z-5f9faac", per_arm=agg, pair=pair,
              grand_total_cost=tot_cost,
              paired=dict(
                  dcost_ab_mean=round(st.mean(dc), 4), dcost_ab_t=round(paired_t(dc), 2),
                  dcost_ab_a2_dearer=sum(1 for x in dc if x > 0),
                  dlat_ab_mean=round(st.mean(dl), 1), dlat_ab_t=round(paired_t(dl), 2),
                  dcost_ac_mean=round(st.mean(dca), 4), dcost_ac_t=round(paired_t(dca), 2),
                  dlat_ac_mean=round(st.mean(dla), 1), dlat_ac_t=round(paired_t(dla), 2)),
              stability=dict(cells=len(stab), wall_min=min(walls), wall_max=max(walls),
                             wall_median=st.median(walls)))
(OUT / "e5_numbers.json").write_text(json.dumps(digest, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"\nwrote {OUT / 'e5_numbers.json'}")
