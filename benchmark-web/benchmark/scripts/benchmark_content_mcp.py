#!/usr/bin/env python3
"""模块 B — 内容检索机制评测(经 kb-mcp MCP 真链路, 确定性 QDCVR 管线).

链路: 本脚本 → MCP stdio (uv run kb-mcp server.py) → KbClient → backend.
这是 Agent 实际使用的工具层; 确定性策略=QDCVR 规程的程序化展开:
  1  kb_project_status                    (skill 强制门)
  2  kb_list(lightweight)                 选库上下文
  3  kb_search_two_stage(balance_kbs)     两阶段召回     ← 工程加速项
  4  Step2.5 硬阈值 0.35 + 文档级去重
  5  kb_doc_read × top-3 内容验证         ← 内容裁决(content-overrides-vector)
对比方法(同一 MCP 层):
  vector baseline  kb_search_vector(top_k=10)            ← 传统向量检索
指标: Recall@{1,5,10} / nDCG@5 / MRR / 逐级命中率(stage1/2/3) / 验证提升 / 时延

用法:
  python benchmark_content_mcp.py --lang en --queries data/benchmarks/hotpotqa-en60.jsonl
  python benchmark_content_mcp.py --lang zh --queries data/benchmarks/miracl-zh-dev.jsonl
  python benchmark_content_mcp.py --lang ja --queries data/benchmarks/miracl-ja-dev.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
from mcp_client import McpClient, step25_dedup_threshold, THRESHOLD  # noqa: E402

REPO_ROOT = SCRIPTS_DIR.parents[2]
DATA_DIR = SCRIPTS_DIR.parent / "data" / "benchmarks"
OUT_DIR = SCRIPTS_DIR.parent / "results" / "benchmark"
OUT_DIR.mkdir(parents=True, exist_ok=True)

LANG_KB = {"en": "KB-CrossLang-EN", "zh": "KB-CrossLang-ZH", "ja": "KB-CrossLang-JA"}
THRESH = 0.35


def norm_title(t: str) -> str:
    t = t.strip().lower()
    return t


def doc_basename(doc_path: str) -> str:
    """归并 doc_path 到源文档基名: 去目录/.md, 递归去 part 与重名计数后缀.

    大文档会被系统多级拆分(Astronaut (part 1 of 3) (1).md), 需循环剥离。"""
    import re
    name = str(doc_path).replace("\\", "/").rsplit("/", 1)[-1]
    if name.endswith(".md"):
        name = name[:-3]
    prev = None
    while prev != name:
        prev = name
        name = re.sub(r" \((?:part \d+ of \d+|\d+)\)$", "", name)
    return name


def eval_ranking(ranked_docs: list[str], golden: set[str], k_list=(1, 5, 10)) -> dict:
    """金标覆盖率: top-k 中命中的不同金标文档数 / 金标总数(<=1, 多金标公平)."""
    out = {}
    for k in k_list:
        matched = len({norm_title(doc_basename(d)) for d in ranked_docs[:k]
                       if norm_title(doc_basename(d)) in golden})
        out[f"recall@{k}"] = (matched / len(golden)) if golden else 0.0
    hits = [1 if norm_title(doc_basename(d)) in golden else 0 for d in ranked_docs]
    dcg = sum(h / math.log2(i + 2) for i, h in enumerate(hits[:5]))
    n_rel = min(sum(hits), 5)
    idcg = sum(1 / math.log2(i + 2) for i in range(n_rel)) or 1.0
    out["ndcg@5"] = dcg / idcg
    rr = next((1.0 / (i + 1) for i, h in enumerate(hits) if h), 0.0)
    out["mrr"] = rr
    out["hit"] = 1 if any(hits) else 0
    return out


def staged_retrieval(client: McpClient, query: str, kb: str) -> tuple[dict, list[dict]]:
    """确定性 QDCVR: 返回 (指标, 逐级记录). 受控检索限定在指定对照库内."""
    t0 = time.perf_counter()
    stages = {"stage1": 0, "stage2": 0, "stage3": 0}
    tool_calls = 0

    client.call("kb_project_status", {"scope": "runtime"})
    tool_calls += 1
    client.call("kb_list", {"lightweight": True})
    tool_calls += 1

    t_search = time.perf_counter()
    res = client.call("kb_search_two_stage",
                      {"query": query, "kb_id": kb, "stage1_top_k": 40,
                       "stage2_top_k": 10, "balance_kbs": True},
                      timeout=420)
    tool_calls += 1
    t_search = time.perf_counter() - t_search

    stage1_docs = [str(c.get("doc_path", ""))
                   for c in (res.get("stage1") or {}).get("candidates") or []]
    ranked = step25_dedup_threshold((res.get("stage2") or {}).get("results") or [],
                                    THRESH)
    stage2_docs = [str(r.get("doc_path", "")) for r in ranked]

    # Step3 内容验证: 读 top-3 文档正文, 命中查询关键词者升序(content-overrides-vector)
    import re
    terms = [t for t in re.findall(r"[a-zA-Z\u4e00-\u9fff\u3040-\u30ff]{2,}", query)]
    verified: list[tuple[str, int, str]] = []
    t_verify = time.perf_counter()
    for doc_path in stage2_docs[:3]:
        try:
            d = client.call("kb_doc_read",
                            {"doc_path": doc_path, "max_chars": 3000})
            content = str(d.get("content") or d.get("raw") or "")
            score = sum(1 for t in terms if t.lower() in content.lower())
            verified.append((doc_path, score, content[:200]))
        except Exception:
            verified.append((doc_path, 0, ""))
        tool_calls += 1
    t_verify = time.perf_counter() - t_verify
    total = time.perf_counter() - t0

    return {
        "stage1_docs": stage1_docs, "stage2_docs": stage2_docs,
        "verified": [(p, s) for p, s, _ in verified],
        "latency_total_s": round(total, 4),
        "latency_search_s": round(t_search, 4),
        "latency_verify_s": round(t_verify, 4),
        "tool_calls": tool_calls,
    }, [res]


def finalize_ranking(st: dict, boost_verified: bool) -> list[str]:
    """stage3: 验证提升后的最终文档序."""
    docs = list(st["stage2_docs"])
    if boost_verified:
        scores = dict(st["verified"])
        docs = [d for d in docs if d]
        docs.sort(key=lambda d: -scores.get(d, 0))
        seen, uniq = set(), []
        for d in docs:
            key = d.lower()
            if key not in seen:
                seen.add(key)
                uniq.append(d)
        return uniq
    seen, uniq = set(), []
    for d in docs:
        key = d.lower()
        if key not in seen:
            seen.add(key)
            uniq.append(d)
    return uniq


def hit_stage(stage1_docs: list[str], stage2_docs: list[str], final: list[str],
              golden: set[str]) -> str:
    def has(docs):
        return any(norm_title(doc_basename(d)) in golden for d in docs)
    if has(stage1_docs):
        return "stage1"
    if has(stage2_docs):
        return "stage2"
    if has(final):
        return "stage3"
    return "miss"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", required=True, choices=["en", "zh", "ja"])
    ap.add_argument("--queries", default="")
    ap.add_argument("--limit", type=int, default=60)
    ap.add_argument("--round", type=int, default=1)
    args = ap.parse_args()

    qpath = Path(args.queries) if args.queries else (
        DATA_DIR / {"en": "cloze-en-dev.jsonl", "zh": "cloze-zh-dev.jsonl",
                    "ja": "cloze-ja-dev.jsonl"}[args.lang])
    items = [json.loads(line) for line in qpath.open(encoding="utf-8")]
    items = items[: args.limit]

    client = McpClient(REPO_ROOT)

    # 预热: 等待 BM25/向量索引就绪(重索引后首轮查询会触发全量重建, 单次可达数分钟)
    import time as _time
    warm = False
    for attempt in range(20):
        try:
            probe = client.call("kb_search_vector",
                                {"query": "history war 2007 politics science",
                                 "kb_id": LANG_KB[args.lang], "top_k": 3},
                                timeout=420)
            if probe.get("results"):
                warm = True
                print(f"  warmup ok (attempt {attempt+1})", flush=True)
                break
        except Exception:
            pass
        print(f"  warmup {attempt+1}/20: index not ready, wait 30s", flush=True)
        _time.sleep(30)
    if not warm:
        print("  warn: warmup 未确认索引就绪, 继续评测(结果可能偏低)", flush=True)

    results = {"staged": [], "vector": [], "meta": {
        "lang": args.lang, "kb": LANG_KB[args.lang], "round": args.round,
        "n_queries": len(items),
        "generated": datetime.now(timezone.utc).isoformat(),
        "mcp_command": "uv run --directory kb-mcp python server.py (stdio JSON-RPC)",
        "policy": "QDCVR deterministic: status→kb_list→two_stage→thr0.35+dedup→doc_read×3",
        "baseline": {"name": "vector top-k (Chroma + BAAI/bge-m3)", "k": 10,
                     "tool": "kb_search_vector"},
    }}
    try:
        for i, it in enumerate(items):
            golden = {norm_title(t) for t in it.get("golden_pages")
                      or it.get("golden_titles") or []}
            if not golden:
                continue
            q = it["question"]

            for _att in range(3):
                try:
                    st, _ = staged_retrieval(client, q, LANG_KB[args.lang])
                    if st["stage1_docs"] or st["stage2_docs"]:
                        break
                except Exception:
                    if _att == 2:
                        raise
                _time.sleep(20)  # 瞬态空结果: 等待后重试
            final = finalize_ranking(st, boost_verified=True)
            base_final = finalize_ranking(st, boost_verified=False)
            m_staged = eval_ranking(final, golden)
            m_noboost = eval_ranking(base_final, golden)
            m_staged["staged_hit"] = hit_stage(st["stage1_docs"], st["stage2_docs"],
                                               final, golden)
            m_staged["verification_boost_delta"] = round(
                m_staged["recall@5"] - m_noboost["recall@5"], 4)
            m_staged.update({k: st[k] for k in
                             ("latency_total_s", "latency_search_s",
                              "latency_verify_s", "tool_calls")})

            tv = time.perf_counter()
            rv = client.call("kb_search_vector",
                             {"query": q, "kb_id": LANG_KB[args.lang],
                              "top_k": 10}, timeout=420)
            t_vec = time.perf_counter() - tv
            vec_docs = [str(r.get("doc_path", ""))
                        for r in (rv.get("results") or [])]
            m_vec = eval_ranking(vec_docs, golden)
            m_vec["latency_s"] = round(t_vec, 4)
            m_vec["two_stage_speedup_note"] = round(
                st["latency_total_s"], 4)

            results["staged"].append({"qid": it["qid"], **m_staged})
            results["vector"].append({"qid": it["qid"], **m_vec})
            if (i + 1) % 10 == 0:
                sr5 = statistics.mean(r["recall@5"] for r in results["staged"])
                vr5 = statistics.mean(r["recall@5"] for r in results["vector"])
                print(f"  [{i+1}/{len(items)}] staged R@5={sr5:.3f} "
                      f"vector R@5={vr5:.3f}", flush=True)
    finally:
        client.close()

    def agg(rows):
        keys = ["recall@1", "recall@5", "recall@10", "ndcg@5", "mrr", "hit"]
        out = {}
        for k in keys:
            vals = [r[k] for r in rows if k in r]
            out[k] = round(statistics.mean(vals), 4) if vals else None
        stages = {}
        for r in rows:
            if "staged_hit" in r:
                stages[r["staged_hit"]] = stages.get(r["staged_hit"], 0) + 1
        if stages:
            out["staged_hit_dist"] = stages
            out["verification_boost_delta_mean"] = round(
                statistics.mean(r["verification_boost_delta"] for r in rows), 4)
            out["tool_calls_per_query"] = round(
                statistics.mean(r["tool_calls"] for r in rows), 2)
            out["latency_total_s_mean"] = round(
                statistics.mean(r["latency_total_s"] for r in rows), 3)
        if any("latency_s" in r for r in rows):
            out["latency_s_mean"] = round(
                statistics.mean(r["latency_s"] for r in rows), 3)
        return out

    results["summary"] = {"staged": agg(results["staged"]),
                          "vector": agg(results["vector"]),
                          "n": len(results["staged"])}

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = OUT_DIR / f"benchmark_content_mcp_{args.lang}_r{args.round}.json"
    alias = OUT_DIR / f"benchmark_content_{args.lang}_{ts}.json"
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    alias.write_text(json.dumps(results, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    print(f"-> {out_path}")
    print(f"-> {alias}")
    print("summary:", json.dumps(results["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
