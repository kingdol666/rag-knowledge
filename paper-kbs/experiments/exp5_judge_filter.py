#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exp 5 — judge-as-filter vs judge-as-re-ranker.

For each of the 16 gold questions, ONE kb_hybrid_search(enable_judge=true)
call yields both the fusion order (merge.judged_candidates, pre-judge) and
the per-candidate judge scores (cut.kept). From these we evaluate, offline:

  judged        : judge-score order (the shipped re-ranking)  [measured]
  filter_only   : fusion order filtered to judge survivors     [derived]
  rrf_fuse      : RRF fusion of fusion-rank and judge-rank     [derived]

All three are configurations of the same pipeline run; metrics from the
same 12-candidate pools make the attribution exact.
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kbcommon import QUESTIONS, RESULTS, McpClient, gold_hit, norm_path

TOP_K = 5


def main() -> int:
    mc = McpClient()
    rows_out = []
    for q in QUESTIONS:
        r = mc.call("kb_hybrid_search",
                    {"query": q["text"], "candidate_cap": 12,
                     "enable_judge": True}, timeout=300)
        fusion = [norm_path(p)
                  for p in ((r.get("merge") or {}).get("judged_candidates")
                            or [])]
        kept = (r.get("cut", {}) or {}).get("kept", []) or []
        scores = {norm_path(k["doc_path"]): float(k.get("score") or 0)
                  for k in kept}
        judged_order = sorted(scores, key=lambda p: -scores[p])

        survivors = [p for p in fusion if p in scores]
        filter_order = survivors  # fusion order, judge acts as filter

        # RRF fusion of the two rankings (k=60)
        rrf: dict[str, float] = {}
        for i, p in enumerate(fusion):
            rrf[p] = rrf.get(p, 0.0) + 1.0 / (60 + i + 1)
        for i, p in enumerate(judged_order):
            rrf[p] = rrf.get(p, 0.0) + 1.0 / (60 + i + 1)
        rrf_order = [p for p, _ in sorted(rrf.items(), key=lambda kv: -kv[1])]

        row = {"qid": q["qid"], "n_fusion": len(fusion),
               "n_survivors": len(survivors)}
        for name, ranked in (("judged", judged_order),
                             ("filter_only", filter_order),
                             ("rrf_fuse", rrf_order)):
            hits, best = gold_hit(ranked, q["gold_doc_substrings"], TOP_K)
            row[name] = {"hit": hits > 0,
                         "recall": hits / len(q["gold_doc_substrings"]),
                         "mrr": (1.0 / best) if best else 0.0,
                         "best_rank": best}
        rows_out.append(row)
        print(f"[exp5] {q['qid']} fusion={len(fusion)} surv={len(survivors)} "
              f"judged_hit={row['judged']['hit']} "
              f"filter_hit={row['filter_only']['hit']} "
              f"rrf_hit={row['rrf_fuse']['hit']}", flush=True)

    summary = {}
    for variant in ("judged", "filter_only", "rrf_fuse"):
        rs = rows_out
        summary[variant] = {
            "hit@5": sum(r[variant]["hit"] for r in rs) / len(rs),
            "recall@5": sum(r[variant]["recall"] for r in rs) / len(rs),
            "mrr": sum(r[variant]["mrr"] for r in rs) / len(rs),
        }
        s = summary[variant]
        print(f"{variant:<12} hit@5={s['hit@5']:.2f} recall@5={s['recall@5']:.2f} "
              f"mrr={s['mrr']:.3f}")
    out = RESULTS / "exp5_judge_filter.json"
    out.write_text(json.dumps({"rows": rows_out, "summary": summary},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
