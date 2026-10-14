#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Recompute every number the paper cites from exp1/exp2 raw data."""
import io
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = HERE / "results"

rows = json.loads((RES / "exp1_retrieval.json").read_text(encoding="utf-8"))["rows"]
methods = ["bm25", "dense", "rrf", "graph", "twostage", "fusion_only",
           "qdcvr_hybrid"]

print("== Table 3 (16 questions) ==")
for m in methods:
    rs = [r for r in rows if r.get("method") == m and "error" not in r]
    lats = [r["latency_s"] for r in rs]
    print(f"{m:<14} hit5={sum(r['hit@5'] for r in rs)/len(rs):.2f} "
          f"rec5={sum(r['recall@5'] for r in rs)/len(rs):.2f} "
          f"mrr={sum(r['mrr'] for r in rs)/len(rs):.3f} "
          f"lat_mean={statistics.mean(lats)*1000:.1f}ms "
          f"lat_med={statistics.median(lats)*1000:.1f}ms n={len(rs)}")

print("\n== per-method miss lists ==")
for m in methods:
    misses = [r["qid"] for r in rows
              if r.get("method") == m and "error" not in r and not r["hit@5"]]
    print(f"{m:<14} {misses}")

print("\n== judge inflation (qdcvr_hybrid rows) ==")
gold, nongold = [], []
for r in rows:
    if r.get("method") != "qdcvr_hybrid" or "judge_scores" not in r:
        continue
    gold += r["judge_scores"]["gold"]
    for p, sc in r["judge_scores"]["all"].items():
        glds = None
        sys.path.insert(0, str(HERE))
        from kbcommon import QUESTIONS
        q = next(qq for qq in QUESTIONS if qq["qid"] == r["qid"])
        if not any(g.lower() in p.lower() for g in q["gold_doc_substrings"]):
            nongold.append(sc)
print(f"gold n={len(gold)} median={statistics.median(gold):.3f} "
      f"min={min(gold):.3f} max={max(gold):.3f}")
print(f"nongold n={len(nongold)} median={statistics.median(nongold):.3f} "
      f"min={min(nongold):.3f} max={max(nongold):.3f}")
try:
    from scipy.stats import mannwhitneyu
    u, p = mannwhitneyu(gold, nongold, alternative="two-sided")
    print(f"Mann-Whitney U={u:.0f} p={p:.3f}")
except ImportError:
    print("(scipy not available here)")

print("\n== threshold/cut behaviour ==")
n_runs = n_kept = n_dropped = 0
for r in rows:
    if r.get("method") != "qdcvr_hybrid" or "judge_scores" not in r:
        continue
    n_runs += 1
    n_kept += len(r["judge_scores"]["all"])
print(f"runs={n_runs} kept_total={n_kept} (cap 12/run -> {n_kept}/{12*n_runs})")
