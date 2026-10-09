#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exp 6 — leave-one-question-out validation of the cut margin (review C6/R1#4).

Round-3 review: "margin 0.20 is selected and validated on the same 17 gold
instances" (in-sample). This replay addresses it with LOO folds: for each
holdout question, select the smallest margin on the remaining 15 questions
such that every training gold survives the relative cut, then apply the
selected margin to the holdout and check its gold.

Data: exp1_retrieval.json qdcvr_hybrid rows (logged per-candidate judge
scores, 16 questions, 17 in-pool gold instances). No service calls.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kbcommon import QUESTIONS, RESULTS

GRID = [round(0.05 + 0.01 * i, 2) for i in range(36)]  # 0.05 .. 0.40


def load() -> list[dict]:
    rows = json.loads((RESULTS / "exp1_retrieval.json").read_text(
        encoding="utf-8"))["rows"]
    out = []
    for r in rows:
        if r.get("method") != "qdcvr_hybrid" or "judge_scores" not in r:
            continue
        q = next(qq for qq in QUESTIONS if qq["qid"] == r["qid"])
        allsc = {p: s for p, s in r["judge_scores"]["all"].items()}
        goldsubs = [g.lower() for g in q["gold_doc_substrings"]]
        gold_paths = [p for p in allsc
                      if any(g in p.lower() for g in goldsubs)]
        if not allsc:
            continue
        out.append({"qid": r["qid"], "scores": allsc,
                    "gold_paths": gold_paths})
    return out


def golds_survive(item: dict, margin: float) -> bool:
    sc = item["scores"]
    best = max(sc.values())
    ordered = sorted(sc, key=lambda p: -sc[p])
    kept = set(ordered[:5])  # top-5 floor
    kept |= {p for p, s in sc.items() if s >= best - margin}
    return all(g in kept for g in item["gold_paths"])


def kept_size(item: dict, margin: float) -> int:
    sc = item["scores"]
    best = max(sc.values())
    ordered = sorted(sc, key=lambda p: -sc[p])
    kept = set(ordered[:5])
    kept |= {p for p, s in sc.items() if s >= best - margin}
    return len(kept)


def main() -> int:
    items = load()
    print(f"questions with logged pools: {len(items)}, "
          f"gold instances: {sum(len(i['gold_paths']) for i in items)}")
    folds = []
    for hold in items:
        train = [i for i in items if i["qid"] != hold["qid"]]
        m_star = None
        for m in GRID:
            if all(golds_survive(t, m) for t in train):
                m_star = m
                break
        hold_ok = golds_survive(hold, m_star) if m_star is not None else False
        fixed_ok = golds_survive(hold, 0.20)
        folds.append({"holdout": hold["qid"], "m_star": m_star,
                      "holdout_gold_kept": hold_ok,
                      "fixed_020_gold_kept": fixed_ok,
                      "holdout_kept_n": kept_size(hold, m_star or 0.20)})
        print(f"holdout {hold['qid']}: m*={m_star} "
              f"gold_kept={hold_ok} fixed0.20={fixed_ok}")
    ok = sum(f["holdout_gold_kept"] for f in folds)
    fixed = sum(f["fixed_020_gold_kept"] for f in folds)
    ms = sorted({f["m_star"] for f in folds})
    summary = {"folds": folds, "n_folds": len(folds),
               "loo_gold_survival": ok / len(folds),
               "fixed_020_gold_survival": fixed / len(folds),
               "m_star_values": [str(m) for m in ms],
               "note": "smallest-margin selection on 15 training questions; "
                       "grid 0.05-0.40 step 0.01"}
    out = RESULTS / "exp6_loo_margin.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"\nLOO gold survival: {ok}/{len(folds)} | fixed 0.20: "
          f"{fixed}/{len(folds)} | m* values: {ms}")
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
