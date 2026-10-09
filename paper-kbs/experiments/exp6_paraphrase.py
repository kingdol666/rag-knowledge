#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exp 6b — paraphrased-question robustness (review C2/R3#10).

Round-3 review: BM25's 1.00 "rests on questions authored in corpus
vocabulary". This reruns the full tool layer (the same seven pipelines plus
the two derived configurations) on 16 paraphrases of the gold questions,
reworded to avoid the corpus's phrasing where the intent allows it, with
identical gold mapping. All service calls are the shipped MCP tools.
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kbcommon import QUESTIONS, RESULTS, McpClient, gold_hit, norm_path
from exp1_retrieval import (BM25Okapi, load_corpus, rank_bm25, rank_dense,
                            rank_graph, rank_hybrid, rank_rrf, rank_twostage,
                            tokenize)

TOP_K = 5
RRF_K = 60

# Paraphrases: same intent and gold mapping as QUESTIONS, different wording.
PARAPHRASES = {
    "Q1": "EVA胶膜在层压时应该怎样设定温度、压力和时间参数？要如何保证交联固化到位？",
    "Q2": "组件EL测试出现四周边缘脱层，是什么原因造成的？后续应该怎么处理？",
    "Q3": "EVA胶膜在高温高湿环境下为什么会产生醋酸？它对材料会造成什么破坏？",
    "Q4": "POE粒子作为封装材料防潮表现怎么样？它跟EVA在层压工序上有什么区别？",
    "Q5": "光伏电站在夏天发电量明显偏低，应该按照什么步骤逐项排查？",
    "Q6": "1027线上料称重单元什么时候会报警？允许的重量波动范围是多少？",
    "Q7": "1号线挤出机熔体温度从206度掉到180度，最终查明的故障原因是什么？",
    "Q8": "PET薄膜双向拉伸的生产流程是怎样的？各段温度要怎么控制？",
    "Q9": "逆变器反复报警跳机，现场应该怎么一步步处置？",
    "Q10": "组件出现热斑的判定标准是什么？发现了应该如何处置？",
    "Q11": "光伏组串发生失配的常见因素有哪些？怎样借助IV曲线来分析？",
    "Q12": "PP流延膜的挤出成型要注意哪些参数？激冷辊温度怎么设定？",
    "Q13": "称重闭环第一轮实验里，阶梯激励是怎么设计的？",
    "Q14": "P0优化完成之后，FT全功能回归测试是怎么执行的？",
    "Q15": "多模态诊断如何把标量数据、向量特征和图像信号融合起来做判断？",
    "Q16": "heatdecay092事件做过温度补偿之后，R2恢复阶段的验证结果如何？",
}


def main() -> int:
    mc = McpClient()
    docs, _ = load_corpus(mc)
    bm25 = BM25Okapi([tokenize(d["content"]) for d in docs])
    rows, rows_out = [], []
    for q in QUESTIONS:
        text = PARAPHRASES[q["qid"]]
        t0 = time.time()
        bm25_rank = rank_bm25(bm25, docs, text)
        dense_rank = rank_dense(mc, text)
        rrf_rank = rank_rrf(bm25_rank, dense_rank)
        graph_rank = rank_graph(mc, text)
        twostage_rank = rank_twostage(mc, text)
        lat = round(time.time() - t0, 3)
        fusion_rank, _ = rank_hybrid(mc, text, enable_judge=False)
        judged_rank, jscores = rank_hybrid(mc, text, enable_judge=True)
        lat_h = round(time.time() - t0 - lat, 3)
        judged_order = sorted(jscores, key=lambda p: -jscores[p]) if jscores else []
        filter_order = [p for p in fusion_rank if p in jscores] if jscores else []
        rrf = {}
        for i, p in enumerate(fusion_rank):
            rrf[p] = rrf.get(p, 0.0) + 1.0 / (RRF_K + i + 1)
        for i, p in enumerate(judged_order):
            rrf[p] = rrf.get(p, 0.0) + 1.0 / (RRF_K + i + 1)
        rrf_fuse_order = [p for p, _ in sorted(rrf.items(), key=lambda kv: -kv[1])]
        row = {"qid": q["qid"], "text": text, "latency_s": lat,
               "hybrid_latency_s": lat_h}
        for name, ranked in (("bm25", bm25_rank), ("dense", dense_rank),
                             ("rrf", rrf_rank), ("graph", graph_rank),
                             ("twostage", twostage_rank),
                             ("fusion_only", fusion_rank),
                             ("judged", judged_order),
                             ("filter_only", filter_order),
                             ("rrf_fuse", rrf_fuse_order)):
            hits, best = gold_hit(ranked, q["gold_doc_substrings"], TOP_K)
            row[name] = {"hit": hits > 0, "recall": hits / len(q["gold_doc_substrings"]),
                         "mrr": (1.0 / best) if best else 0.0, "best_rank": best}
        rows_out.append(row)
        print(f"[exp6b] {q['qid']}: bm25={row['bm25']['hit']} "
              f"dense={row['dense']['hit']} hybrid={row['judged']['hit']} "
              f"filter={row['filter_only']['hit']} fusion={row['fusion_only']['hit']}",
              flush=True)
    summary = {}
    for name in ("bm25", "dense", "rrf", "graph", "twostage",
                 "fusion_only", "judged", "filter_only", "rrf_fuse"):
        summary[name] = {
            "hit@5": sum(r[name]["hit"] for r in rows_out) / len(rows_out),
            "recall@5": sum(r[name]["recall"] for r in rows_out) / len(rows_out),
            "mrr": sum(r[name]["mrr"] for r in rows_out) / len(rows_out),
        }
        s = summary[name]
        print(f"{name:<12} hit@5={s['hit@5']:.2f} recall@5={s['recall@5']:.2f} "
              f"mrr={s['mrr']:.3f}")
    out = RESULTS / "exp6_paraphrase.json"
    out.write_text(json.dumps({"rows": rows_out, "summary": summary},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
