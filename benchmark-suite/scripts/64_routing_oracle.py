#!/usr/bin/env python3
"""E13 · 路由 oracle 实验（响应评审 W1/Q1: 路由层无测量）.

在 HotpotQA 九库基准上测三种检索范围条件，量化"完美路由"的上限:
  always_all   全库平衡检索(kb_id="", balance) —— 系统现状(复用 hotpot_main r1)
  oracle_1kb   限定在金标库之一内检索(确定性规则: 字典序首个金标标题所在库)
               —— 模拟"完美单库路由器"
  oracle_best  两个金标库各自检索取更优 —— 理论上限(多库受限检索的理想值)
方法: two_stage 与 dense(两种主要召回形态)。
指标: Hit@2 / Recall@2 / nDCG@10。
诚实说明: 系统真实路由器(基于库描述打分)未实现 oracle 精度; 本实验给出
路由价值的上界, 而非已实现组件的精度。
输出: results/run-*/routing_oracle.json
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import DATA, McpClient, doc_basename, mean, now_iso, set_run  # noqa: E402
import re

ROUND = sys.argv[1] if len(sys.argv) > 1 else "1"


def dedupe(seq):
    seen, out = set(), []
    for x in seq:
        k = x.lower()
        if k not in seen:
            seen.add(k)
            out.append(x)
    return out


def title_of(doc_path: str) -> str:
    b = doc_basename(doc_path)
    b = b.replace("\\", "/").split("/")[-1]
    return re.sub(r"\s*\[hotpot-[0-9a-f]{8}\]\s*$", "", b)


def eval_titles(paths, golden):
    hits = [1 if title_of(p).strip().lower() in golden else 0 for p in paths]
    matched2 = len({title_of(p).strip().lower() for p in paths[:2]} & golden)
    out = {"recall@2": matched2 / len(golden) if golden else 0.0,
           "hit@2": 1 if any(hits[:2]) else 0}
    dcg = sum(h / math.log2(i + 2) for i, h in enumerate(hits[:10]))
    n_rel = min(len(golden), 10)
    idcg = sum(1 / math.log2(i + 2) for i in range(n_rel)) or 1.0
    out["ndcg@10"] = dcg / idcg
    return out


def main() -> int:
    outdir = set_run()
    mc = McpClient()
    rows = {"always_all": [], "oracle_1kb": [], "oracle_best": []}
    try:
        qs = [json.loads(l) for l in
              (DATA / "hotpotqa" / "queries.jsonl").open(encoding="utf-8")]
        # 标题→库
        kb_of_title = {}
        for d in (DATA / "hotpotqa" / "docs").iterdir():
            if d.is_dir():
                for f in d.glob("*.md"):
                    t = f.name.split(" [hotpot")[0].strip().lower()
                    kb_of_title[t] = d.name
        print(f"[oracle] {len(qs)} queries", flush=True)
        for i, q in enumerate(qs):
            golden = {t.strip().lower() for t in q["golden_titles"]}
            gold_kbs = sorted({kb_of_title.get(t, "KB-Hotpot-General")
                               for t in golden})
            q["_gold_kbs"] = gold_kbs
            # oracle_1kb: 字典序首个金标标题所在库(确定性)
            first_gold = sorted(q["golden_titles"])[0].strip().lower()
            q["_oracle_kb"] = kb_of_title.get(first_gold, "KB-Hotpot-General")

            def run(kb_id, method):
                if method == "two_stage":
                    r = mc.call("kb_search_two_stage",
                                {"query": q["question"], "kb_id": kb_id,
                                 "stage1_top_k": 40, "stage2_top_k": 10,
                                 "balance_kbs": kb_id == ""}, timeout=420)
                    return dedupe([str(x.get("doc_path", ""))
                                   for x in (r.get("stage2") or {}).get("results") or []])
                r = mc.call("kb_search_vector",
                            {"query": q["question"], "kb_id": kb_id, "top_k": 10},
                            timeout=420)
                return dedupe([str(x.get("doc_path", ""))
                               for x in r.get("results") or []])

            res = {}
            for method in ("two_stage", "dense"):
                res[("always_all", method)] = run("", method)
                res[("oracle_1kb", method)] = run(q["_oracle_kb"], method)
                per_kb = [run(kb, method) for kb in q["_gold_kbs"]]

                def better(a, b):
                    ea, eb = eval_titles(a, golden), eval_titles(b, golden)
                    return a if (ea["ndcg@10"], ea["recall@2"]) >= \
                                (eb["ndcg@10"], eb["recall@2"]) else b
                best = per_kb[0]
                for p_ in per_kb[1:]:
                    best = better(best, p_)
                res[("oracle_best", method)] = best
            for cond in ("always_all", "oracle_1kb", "oracle_best"):
                for method in ("two_stage", "dense"):
                    m = eval_titles(res[(cond, method)], golden)
                    m["method"] = method
                    m["cross_kb"] = 1 if len(q["_gold_kbs"]) >= 2 else 0
                    rows[cond].append({"qid": q["qid"], **m})
            print(f"  [{i+1}/{len(qs)}] done", flush=True)
    finally:
        mc.close()

    summary = {}
    for cond, rs in rows.items():
        summary[cond] = {}
        for method in ("two_stage", "dense"):
            sub = [r for r in rs if r["method"] == method]
            summary[cond][method] = {
                "hit@2": round(mean(r["hit@2"] for r in sub), 4),
                "recall@2": round(mean(r["recall@2"] for r in sub), 4),
                "ndcg@10": round(mean(r["ndcg@10"] for r in sub), 4),
                "n": len(sub)}
        # 跨库子集
        cross = [r for r in rs if r["cross_kb"]]
        summary[cond]["cross_kb_only"] = {
            "hit@2": round(mean(r["hit@2"] for r in cross), 4),
            "recall@2": round(mean(r["recall@2"] for r in cross), 4),
            "ndcg@10": round(mean(r["ndcg@10"] for r in cross), 4),
            "n": len(cross)}
    result = {"experiment": "E13 routing oracle (review W1/Q1)", "round": ROUND,
              "conditions": {"always_all": "global balanced search (deployed)",
                             "oracle_1kb": "restricted to one gold KB (deterministic "
                                           "first-gold-title rule)",
                             "oracle_best": "best per-gold-KB search (upper bound)"},
              "summary": summary, "rows": rows,
              "meta": {"generated": now_iso()}}
    out = outdir / f"routing_oracle_{ROUND}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"-> {out}")
    for cond, s in summary.items():
        print(f"  {cond:12s} two_stage nDCG={s['two_stage']['ndcg@10']} "
              f"dense nDCG={s['dense']['ndcg@10']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
