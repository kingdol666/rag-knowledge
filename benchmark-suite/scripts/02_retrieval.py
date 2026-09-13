#!/usr/bin/env python3
"""模块 B — 基于内容的逐级检索 vs 传统向量 baseline(全部经 kb-mcp MCP 真链路).

方法:
  content_staged  确定性 QDCVR 规程(knowledgebase-search skill 的程序化展开):
    kb_list 选库上下文 → kb_search_two_stage(全局, balance) → Step2.5 阈值0.35+去重
    → kb_doc_read×top-3 内容验证 → 验证得分重排(content-overrides-vector)
  vector_baseline 传统一次性向量检索: kb_search_vector(top_k=10) — 对比基线
    (Chroma + BAAI/bge-m3; 两阶段检索的时延单列为加速项)

指标: Hit@1/3/5(命中率) · Recall@3/5(召回率=金标覆盖) · Precision@5(准确率) · MRR · 时延
双轮: --round 1/2 各跑一次, 确定性管线应逐位一致(延迟除外)。
输出: results/module_b_retrieval_r{1,2}.json
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import (DATA, RESULTS, McpClient, doc_basename,  # noqa: E402
                 env_fingerprint, eval_ranking, mean, norm_t, now_iso, step25)

ROUND = sys.argv[1] if len(sys.argv) > 1 else "1"
QUERIES = Path(sys.argv[2]) if len(sys.argv) > 2 else DATA / "queries.jsonl"
OUT_SUFFIX = "_std" if "standard" in str(QUERIES) else ""


def wait_index_ready(mc: McpClient, timeout_s: int = 900) -> bool:
    """预热: 重索引后首个 two-stage 触发 BM25 全量重建(数分钟), 等到稳定可用."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            t0 = time.perf_counter()
            r = mc.call("kb_search_two_stage",
                        {"query": "history war 2007 politics science probe",
                         "kb_id": "", "stage1_top_k": 20, "stage2_top_k": 5},
                        timeout=420)
            dt = time.perf_counter() - t0
            n = len(((r.get("stage2") or {}).get("results") or []))
            if n > 0 and dt < 30:  # 有结果且不再处于重建长耗时状态
                print(f"  index warm (attempt, {dt:.1f}s, {n} hits)", flush=True)
                return True
            print(f"  index warming: {n} hits in {dt:.0f}s, wait 20s", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"  warm probe error: {str(e)[:80]}", flush=True)
        time.sleep(20)
    return False


def staged_retrieval(mc: McpClient, question: str) -> dict:
    t0 = time.perf_counter()
    calls = 0
    mc.call("kb_list", {"lightweight": True})
    calls += 1
    t_search = time.perf_counter()
    res = mc.call("kb_search_two_stage",
                  {"query": question, "kb_id": "", "stage1_top_k": 40,
                   "stage2_top_k": 10, "balance_kbs": True}, timeout=420)
    calls += 1
    t_search = time.perf_counter() - t_search
    stage1 = [str(c.get("doc_path", ""))
              for c in (res.get("stage1") or {}).get("candidates") or []]
    ranked = step25((res.get("stage2") or {}).get("results") or [])
    stage2 = [str(r.get("doc_path", "")) for r in ranked]

    # Step3 内容验证: 读 top-3 正文, 命中查询词越多越可信(content-overrides-vector)
    terms = [t.lower() for t in
             __import__("re").findall(r"[a-zA-Z\u4e00-\u9fff\u3040-\u30ff]{2,}", question)
             if len(t) >= 2]
    t_verify = time.perf_counter()
    verified: dict[str, int] = {}
    reads = []  # QDCVR 留痕: 每次内容验证的读取量与判定
    for doc_path in stage2[:3]:
        try:
            d = mc.call("kb_doc_read", {"doc_path": doc_path, "max_chars": 3000},
                        timeout=120)
            content = str(d.get("content") or d.get("raw") or "")
            score = sum(1 for t in terms if t in content.lower())
            verified[doc_path] = score
            reads.append({"doc": doc_basename(doc_path), "chars_read": len(content),
                          "score": score, "passed": score > 0})
        except Exception as e:  # noqa: BLE001
            verified[doc_path] = 0
            reads.append({"doc": doc_basename(doc_path), "chars_read": 0,
                          "score": 0, "passed": False, "error": str(e)[:80]})
        calls += 1
    t_verify = time.perf_counter() - t_verify

    # 重排: 验证得分降序, 未验证保持原序
    def key(dp: str):
        return (0, -verified.get(dp, 0)) if dp in verified else (1, 0)
    final = sorted(stage2, key=key)
    seen, uniq = set(), []
    for d in final:
        k = d.lower()
        if k not in seen:
            seen.add(k)
            uniq.append(d)
    rerank_changed = [d.lower() for d in uniq[:3]] != [d.lower() for d in stage2[:3]]
    return {"docs": uniq, "stage1": stage1, "stage2": stage2,
            "latency_total": time.perf_counter() - t0,
            "latency_search": t_search, "latency_verify": t_verify,
            "calls": calls, "reads": reads, "rerank_changed": rerank_changed}


def vector_baseline(mc: McpClient, question: str) -> dict:
    t0 = time.perf_counter()
    r = mc.call("kb_search_vector", {"query": question, "kb_id": "", "top_k": 10},
                timeout=420)
    seen, docs = set(), []
    for x in (r.get("results") or []):
        dp = str(x.get("doc_path", ""))
        k = dp.lower()
        if k not in seen:
            seen.add(k)
            docs.append(dp)  # chunk 级结果按文档去重(保留首次出现)
    return {"docs": docs, "latency": time.perf_counter() - t0}


def main() -> int:
    queries = [json.loads(l) for l in QUERIES.open(encoding="utf-8")]
    mc = McpClient()
    wait_index_ready(mc)

    rows = {"staged": [], "vector": []}
    try:
        for i, q in enumerate(queries):
            golden = {norm_t(t) for t in q["golden_pages"]}
            st = staged_retrieval(mc, q["question"])
            m_st = eval_ranking(st["docs"], golden)
            m_st["latency_s"] = round(st["latency_total"], 3)
            m_st["search_s"] = round(st["latency_search"], 3)
            m_st["verify_s"] = round(st["latency_verify"], 3)
            m_st["calls"] = st["calls"]
            m_st["chars_read"] = sum(r["chars_read"] for r in st["reads"])
            m_st["verification_passed"] = sum(1 for r in st["reads"] if r.get("passed"))
            m_st["rerank_changed"] = st["rerank_changed"]
            # 逐级命中: 金标最早出现在哪个阶段
            def has(docs):
                return any(norm_t(doc_basename(d)) in golden for d in docs)
            m_st["first_stage"] = ("stage1" if has(st["stage1"])
                                   else "stage2" if has(st["stage2"])
                                   else "stage3" if has(st["docs"]) else "miss")
            rows["staged"].append({"qid": q["qid"], "lang": q["lang"], **m_st})

            vb = vector_baseline(mc, q["question"])
            m_v = eval_ranking(vb["docs"], golden)
            m_v["latency_s"] = round(vb["latency"], 3)
            rows["vector"].append({"qid": q["qid"], "lang": q["lang"], **m_v})
            print(f"  [{i+1}/{len(queries)}] {q['qid']} "
                  f"staged hit@3={m_st['hit@3']} vec hit@3={m_v['hit@3']}", flush=True)
    finally:
        mc.close()

    def agg(rs):
        out = {}
        for k in ("hit@1", "hit@3", "hit@5", "recall@3", "recall@5",
                  "precision@5", "mrr"):
            out[k] = mean(r[k] for r in rs)
        out["latency_s_mean"] = mean(r["latency_s"] for r in rs)
        if any("first_stage" in r for r in rs):
            stages = {}
            for r in rs:
                stages[r["first_stage"]] = stages.get(r["first_stage"], 0) + 1
            out["first_stage_dist"] = stages
        out["qdcvr_chars_read_per_query"] = mean(
            [r.get("chars_read", 0) for r in rs])
        out["qdcvr_verify_pass_rate"] = mean(
            [r.get("verification_passed", 0) / 3 for r in rs])
        out["qdcvr_rerank_changed_rate"] = mean(
            [1 if r.get("rerank_changed") else 0 for r in rs])
        return out

    by_lang = {}
    for lang in ("en", "zh", "ja", "cross"):
        sub_s = [r for r in rows["staged"] if r["lang"] == lang]
        sub_v = [r for r in rows["vector"] if r["lang"] == lang]
        if sub_s:
            by_lang[lang] = {"staged": agg(sub_s), "vector": agg(sub_v),
                             "n": len(sub_s)}
    result = {
        "meta": {"round": ROUND, "n_queries": len(queries),
                 "methods": {
                     "content_staged": "QDCVR deterministic (two_stage recall + doc_read verification rerank)",
                     "vector_baseline": "kb_search_vector top-10 (Chroma + BAAI/bge-m3)"},
                 "env": env_fingerprint(),
                 "generated": now_iso()},
        "summary": {"overall": {"staged": agg(rows["staged"]),
                                "vector": agg(rows["vector"])},
                    "by_lang": by_lang},
        "rows": rows,
    }
    out = RESULTS / f"module_b_retrieval{OUT_SUFFIX}_r{ROUND}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"-> {out}")
    print("overall:", json.dumps(result["summary"]["overall"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
