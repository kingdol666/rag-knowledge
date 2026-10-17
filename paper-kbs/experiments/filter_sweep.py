"""Threshold sweep over the recorded verdict scores (supplementary Table S6).

Tests the verifier's filter role from logged data: for each cut, how many
candidates survive, how many in-pool golds survive, and whether gold retention
outpaces non-gold retention. No retrieval is re-run.

Run: python paper-kbs/experiments/filter_sweep.py
"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

EXP = Path(__file__).resolve().parent
REPO = EXP.parents[1]
sys.path.insert(0, str(EXP))
from kbcommon import QUESTIONS  # noqa: E402

rows = json.loads((EXP / "results/exp1_retrieval.json").read_text(encoding="utf-8"))["rows"]
Q = {q["qid"]: q for q in QUESTIONS}

gold_scores, nongold_scores = [], []
for r in rows:
    if r.get("method") != "qdcvr_hybrid" or "judge_scores" not in r:
        continue
    q = Q[r["qid"]]
    for p, s in r["judge_scores"]["all"].items():
        low = p.replace("\\", "/").lower()
        if any(g.lower() in low for g in q["gold_doc_substrings"]):
            gold_scores.append(float(s))
        else:
            nongold_scores.append(float(s))

total = len(gold_scores) + len(nongold_scores)
print(f"scored candidates {total}  golds {len(gold_scores)}  non-golds {len(nongold_scores)}")
print(f"{'cut':>5} {'survivors':>9} {'surv%':>6} {'golds':>6} {'gold%':>6} {'nongold%':>9}")
for cut in (0.5, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.88, 0.9, 0.92):
    g = sum(1 for s in gold_scores if s >= cut)
    n = sum(1 for s in nongold_scores if s >= cut)
    print(f"{cut:5.2f} {g+n:9d} {100.0*(g+n)/total:6.1f} {g:6d} "
          f"{100.0*g/len(gold_scores):6.1f} {100.0*n/len(nongold_scores):9.1f}")
print(f"\ngold median {st.median(gold_scores):.4f}; non-gold median {st.median(nongold_scores):.4f}")
