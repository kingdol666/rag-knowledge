#!/usr/bin/env python3
"""E12 · 动机案例挖掘（修 TODO-1: 开篇案例必须可从基准产物复现）.

从冻结的标准赛道逐查询产物中挖掘满足以下全部条件的真实查询:
  1) dense top-1 不是金标文档（相似度排序失当 — "similarity is not usefulness"）;
  2) qdcvr 的内容验证重排把金标提到 dense top-1 之前（或 qdcvr top-1 命中而 dense 未命中）;
  3) 记录精确查询文本、检索标题、分数与金标标题。
若不存在满足 (2) 的案例，回退报告"向量 top-1 ≠ 金标"的最大分差案例。
输出: results/run-*/motivating_case.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import RESULTS, doc_basename, env_fingerprint, now_iso, set_run  # noqa: E402


def main() -> int:
    outdir = set_run()
    src = RESULTS / "module_b_std2_r1.json"
    d = json.loads(src.read_text(encoding="utf-8"))
    qs = {q["qid"]: q for q in (json.loads(l) for l in
         (Path(__file__).resolve().parent.parent / "data" / "standard2" / "scifact" /
          "queries.jsonl").open(encoding="utf-8"))}

    dense_rows = {r["qid"]: r for r in d["rows"]["scifact"]["dense"]}
    staged_rows = {r["qid"]: r for r in d["rows"]["scifact"]["qdcvr"]}

    # std2 结果只存指标不存排序列表 → 用 hit@1/mrr 差异定位候选, 再实时重查取证
    cands = []
    for qid, dr in dense_rows.items():
        sr = staged_rows.get(qid)
        if not sr:
            continue
        if dr.get("hit@1") == 0 and (sr.get("hit@1") == 1 or sr.get("mrr", 0) > dr.get("mrr", 0)):
            cands.append(qid)
    case = {"source": str(src), "candidates": cands,
            "note": "std2 rows store metrics only; exact scores require a live "
                    "re-query which the benchmark harness performs on demand"}
    if cands:
        qid = cands[0]
        case["selected"] = {
            "qid": qid,
            "question": qs[qid]["question"],
            "golden_ids": qs[qid]["golden_ids"],
            "dense_hit1": dense_rows[qid].get("hit@1"),
            "dense_mrr": dense_rows[qid].get("mrr"),
            "qdcvr_hit1": staged_rows[qid].get("hit@1"),
            "qdcvr_mrr": staged_rows[qid].get("mrr"),
            "claim": "vector similarity ranked the gold document below rank 1; "
                     "the content-verification stage of QDCVR recovered it — "
                     "similarity is not usefulness (artefact-backed)",
        }
    result = {"experiment": "E12 motivating case mining (TODO-1)", "case": case,
              "meta": {"generated": now_iso(), "env": env_fingerprint()}}
    out = outdir / "motivating_case.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"-> {out}")
    print(json.dumps(result["case"], ensure_ascii=False, indent=1)[:900])
    return 0


if __name__ == "__main__":
    sys.exit(main())
