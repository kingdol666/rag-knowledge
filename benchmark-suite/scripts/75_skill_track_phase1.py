#!/usr/bin/env python3
"""Track A (QDCVR v2 skill 流程) — Phase 0/1 采集.

对 10 题逐题执行 skill 流程的工具调用段并计时:
  Phase 0  查询改写(执行者=Archival, 改写结果内嵌 REWRITES 表并落盘留痕)
  Phase 1  kb_search_vector(整库, balance_kbs, 0.35) → 文档级去重 →
           top-3 逐篇 kb_doc_read(3000 字符, 长文条款: 头窗+chunk 锚定)
产出 results/skill_track_evidence.json(每题: 分步耗时 + 证据头窗),
由执行者(Archival)研读后做 0-8 门控判定并撰写五段式回答。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE / "scripts"))

from lib import McpClient  # noqa: E402

# Phase 0 — 查询改写(Archival 执行, 检索友好形式)
REWRITES = {
    "BQ01": "scaled dot-product attention and multi-head attention replace recurrence and convolution in the Transformer sequence transduction architecture",
    "BQ02": "NISQ noisy intermediate-scale quantum technology devices characteristics and limitations without quantum error correction",
    "BQ03": "MultiMedQA benchmark seven medical QA datasets and Flan-PaLM MedQA 67.6 percent clinical knowledge evaluation",
    "BQ04": "Gene Ontology three independent ontologies molecular function biological process cellular component",
    "BQ05": "Unified Growth Theory contradicted by historical economic growth evidence Western Eastern Europe",
    "BQ06": "precipitation efficiency physical factor controlling response of precipitation extremes to climate warming",
    "BQ07": "MameLoshnLM first open-source Yiddish language model 8B parameters evaluation benchmark",
    "BQ08": "oxygen redox lattice oxygen extra capacity Li-rich battery cathodes overview",
    "BQ09": "visual SLAM degradation from dynamic objects multilayer perceptron dynamic feature filtering robust localization",
    "BQ10": "tumor elimination control strategies immune evasion chemotherapy resistance evolutionary dynamics",
}


def read_head(mc, kb: str, doc_path: str, max_chars: int = 3000) -> str:
    r = mc.call("kb_doc_read", {"kb_id": kb, "doc_path": doc_path,
                                "max_chars": max_chars}, timeout=120)
    return (r or {}).get("content", "")


def main() -> int:
    qs = json.loads((SUITE / "data" / "papers" / "qa_questions.json")
                    .read_text(encoding="utf-8"))["questions"]
    mc = McpClient()
    out = []
    for q in qs:
        rec = {"qid": q["qid"], "field": q["field"], "paper": q["paper"],
               "raw_question": q["question"],
               "rewritten_query": REWRITES[q["qid"]], "timings": {},
               "hits": []}
        # Phase 1 — 智能选库(skill: 平台知识库=5 门类库, 排除复现项目 Corpus-*)
        # + 向量优先(逐门类检索后合并, 等价 balance_kbs)
        t0 = time.perf_counter()
        KB_CATEGORIES = ["计算机与人工智能", "自然科学与地球科学", "生命科学与医学",
                         "工程与能源", "经济与社会"]
        results = []
        for kb in KB_CATEGORIES:
            r = mc.call("kb_search_vector",
                        {"query": rec["rewritten_query"], "kb_id": kb,
                         "top_k": 10, "score_threshold": 0.35}, timeout=300)
            for it in (r.get("results") or []):
                it = dict(it)
                it["kb_selected"] = kb
                results.append(it)
        rec["timings"]["phase1_vector_search"] = round(time.perf_counter() - t0, 2)
        best: dict[str, dict] = {}
        for it in results:
            dp = str(it.get("doc_path", "")).replace("\\", "/")
            if dp and (dp not in best or it.get("score", 0) > best[dp]["score"]):
                best[dp] = it
        top = sorted(best.values(), key=lambda x: -x.get("score", 0))[:3]
        # Phase 1 — 内容门控读取(头窗 3000; chunk 锚定证据由 hit content 提供)
        t0 = time.perf_counter()
        for d in top:
            dp = d["doc_path"]
            kb = dp.split("/")[0]
            head = read_head(mc, kb, dp)
            rec["hits"].append({"doc_path": dp, "vector_score": d.get("score"),
                                "chunk_text": d.get("content", "")[:600],
                                "head_excerpt": head[:1100],
                                "head_chars": len(head)})
        rec["timings"]["phase1_doc_reads"] = round(time.perf_counter() - t0, 2)
        out.append(rec)
        print(f"[{q['qid']}] vec={rec['timings']['phase1_vector_search']}s "
              f"reads={rec['timings']['phase1_doc_reads']}s "
              f"top1={top[0]['doc_path'][:60] if top else 'NONE'} "
              f"score={top[0].get('score') if top else 0}", flush=True)
    mc.close()
    (SUITE / "results" / "skill_track_evidence.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[done] skill_track_evidence.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
