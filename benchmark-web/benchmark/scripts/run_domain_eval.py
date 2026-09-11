#!/usr/bin/env python3
"""领域集评测（Track 2 Phase C）— 40 条人工标注查询对当前系统 KB, 立即可跑.

数据: docs/paper/benchmark/datasets/queries.json
  字段: qid / query / expected_kb(KB名) / relevant_docs(文件名片段) / intent
  无需 wiki 语料 — 直接打当前系统的既有知识库, 现在就能得到真实分数。

方法组:
  two_stage     系统两阶段检索 (S0 主方法)
  vector_flat   全库平面向量 (B1, NaiveRAG 锚点)
  two_stage_bal two_stage + balance_kbs (消融 +多库均衡)

指标:
  检索: P@1/P@5, MRR, nDCG@5（relevant_docs 文件名片段命中 doc_path）
  路由: KB Routing Acc = top5 结果中出现 expected_kb 的查询占比
  误召回: FPR = top5 中来自非 expected KB 的比例
  时延: 平均 ms

用法:
  export RAG_BENCH_TOKEN=mcp-xxxx
  python run_domain_eval.py                # 全 40 条 × 3 方法
  python run_domain_eval.py --limit 5      # 冒烟
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
from bench_http import get_json, post_json, validated_url  # noqa: E402

QUERIES_FILE = Path(__file__).resolve().parents[3] / "docs" / "paper" / "benchmark" / "datasets" / "queries.json"
RESULTS_DIR = SCRIPTS_DIR.parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
STORAGE_ROOT = Path(__file__).resolve().parents[3] / "storage" / "tree-file-system"


def kb_name_to_uuid() -> dict[str, str]:
    """从磁盘 .knowledge-base.yml 读取 KB 名 → uuid（只读, 不走 API 的兜底路径）。"""
    mapping: dict[str, str] = {}
    for yml in STORAGE_ROOT.glob("*/.knowledge-base.yml"):
        try:
            text = yml.read_text(encoding="utf-8")
        except OSError:
            continue
        head = text[:800]
        m_name = re.search(r"^  path:\s*(.+)$", head, re.M)
        m_id = re.search(r"^  id:\s*([0-9a-f-]{36})", head, re.M)
        if m_name and m_id:
            mapping[m_name.group(1).strip()] = m_id.group(1)
    return mapping


def norm_frag(name: str) -> str:
    return name.lower().removesuffix(".md").strip()


def eval_query(results: list[dict], golden_frags: set[str], golden_kb_uuid: str) -> dict:
    top5 = results[:5]
    hits = [1 if any(f in str(r.get("doc_path", "")).lower() for f in golden_frags) else 0
            for r in top5]
    hits += [0] * (5 - len(hits))
    dcg = sum(h / math.log2(i + 2) for i, h in enumerate(hits))
    idcg = sum(1 / math.log2(i + 2) for i in range(min(sum(hits), 5))) or 1.0
    rr = next((1.0 / (i + 1) for i, h in enumerate(hits) if h), 0.0)
    kb_ids = [str(r.get("kb_id", "")) for r in top5]
    routed = int(golden_kb_uuid in kb_ids) if golden_kb_uuid else 0
    fpr = (sum(1 for k in kb_ids if k and k != golden_kb_uuid) / 5) if golden_kb_uuid else 0.0
    return {"p1": hits[0], "p5": sum(hits) / 5, "mrr": rr,
            "ndcg5": dcg / idcg if idcg else 0.0,
            "routing": routed, "fpr": fpr}


def run(method: str, samples: list[dict], kb_map: dict[str, str],
        token: str, backend: str) -> tuple[list[dict], list[float]]:
    out, lats = [], []
    for i, s in enumerate(samples):
        if method == "vector_flat":
            payload = {"query": s["query"], "kb_id": "", "top_k": 5,
                       "score_threshold": 0.0, "balance_kbs": False}
            path = "/api/v1/search/vector"
        elif method in ("two_stage", "two_stage_bal"):
            payload = {"query": s["query"], "kb_id": "", "stage1_top_k": STAGE1_TOP_K,
                       "stage2_top_k": 5, "score_threshold": 0.0}
            if method == "two_stage_bal":
                payload["balance_kbs"] = True
            path = "/api/v1/search/two-stage"
        else:
            raise ValueError(method)
        import time
        t0 = time.perf_counter()
        resp = post_json(backend, path, payload, token)
        lats.append((time.perf_counter() - t0) * 1000)
        # two-stage 响应结构: {stage1, stage2:{results}, total_results}; vector: {results}
        results = (resp.get("stage2", {}).get("results") if path.endswith("two-stage")
                   else resp.get("results")) or []
        golden_frags = {norm_frag(d) for d in s.get("relevant_docs", [])}
        golden_kb_uuid = kb_map.get(s.get("expected_kb", ""), "")
        m = eval_query(results, golden_frags, golden_kb_uuid)
        m["qid"] = s["qid"]
        out.append(m)
        if (i + 1) % 10 == 0:
            print(f"  [{i+1}/{len(samples)}] {method} running MRR="
                  f"{statistics.mean(x['mrr'] for x in out):.3f}", flush=True)
    return out, lats


STAGE1_TOP_K = 20


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--methods", default="two_stage,vector_flat,two_stage_bal")
    ap.add_argument("--stage1-top-k", type=int, default=20,
                    help="stage1 BM25 candidate budget (20=default; raise to resist "
                         "corpus-scale dominance when a large wiki corpus is indexed)")
    args = ap.parse_args()
    global STAGE1_TOP_K
    STAGE1_TOP_K = args.stage1_top_k

    token = os.environ.get("RAG_BENCH_TOKEN", "")
    if not token:
        print("❌ 缺少 RAG_BENCH_TOKEN")
        return 2
    backend = validated_url(os.environ.get("RAG_BENCH_URL", "http://localhost:8770"))
    # 连通性预检（web 层 health）
    try:
        get_json(validated_url(os.environ.get("RAG_BENCH_WEB_URL",
                                              "http://localhost:6789")), "/api/kb/catalog", token)
    except Exception as e:
        print(f"⚠ web 层不可达({e}), 仅测后端; KB uuid 从磁盘 yml 解析")

    kb_map = kb_name_to_uuid()
    print(f"KB 映射: {len(kb_map)} 个知识库")

    samples = json.loads(QUERIES_FILE.read_text(encoding="utf-8"))
    if args.limit:
        samples = samples[:args.limit]
    # expected_kb 不在当前系统的查询单独统计（不影响检索指标, routing 记 0）
    known = [s for s in samples if s.get("expected_kb") in kb_map or not s.get("expected_kb")]
    unknown_kbs = {s.get("expected_kb") for s in samples} - set(kb_map)
    print(f"查询: {len(samples)} 条 (expected_kb 缺失映射: {sorted(k for k in unknown_kbs if k) or '无'})")

    report: dict = {
        "dataset": "domain-queries", "n_queries": len(samples),
        "backend": backend, "kb_map_size": len(kb_map),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "methods": {}, "significance": {},
    }
    per_method_scores: dict[str, list[float]] = {}
    for method in [m.strip() for m in args.methods.split(",")]:
        print(f"\n=== {method} ===", flush=True)
        per_q, lats = run(method, samples, kb_map, token, backend)
        per_method_scores[method] = [x["ndcg5"] for x in per_q]
        agg = {k: round(statistics.mean(x[k] for x in per_q), 4)
               for k in ["p1", "p5", "mrr", "ndcg5", "routing", "fpr"]}
        agg["latency_ms"] = round(statistics.mean(lats), 1)
        report["methods"][method] = agg
        print(f"  -> {json.dumps(agg)}")

    if "two_stage" in per_method_scores:
        base = per_method_scores["two_stage"]
        for m, sc in per_method_scores.items():
            if m != "two_stage":
                report["significance"][f"two_stage_vs_{m}"] = _paired_t(base, sc)

    out = RESULTS_DIR / "eval-domain40.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✓ saved {out}")
    return 0


def _paired_t(a: list[float], b: list[float]) -> dict:
    diffs = [x - y for x, y in zip(a, b)]
    n = len(diffs)
    mean_d = statistics.mean(diffs)
    sd = statistics.stdev(diffs) if n > 1 else 0.0
    if sd == 0:
        return {"t": 0.0, "p": 1.0, "cohens_d": 0.0}
    t = mean_d / (sd / math.sqrt(n))
    from math import erf
    p = 2 * (1 - 0.5 * (1 + erf(abs(t) / math.sqrt(2))))
    pooled = math.sqrt((statistics.variance(a) + statistics.variance(b)) / 2)
    return {"t": round(t, 4), "p": round(p, 6),
            "cohens_d": round(mean_d / pooled, 4) if pooled else 0.0}


if __name__ == "__main__":
    sys.exit(main())
