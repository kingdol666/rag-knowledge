#!/usr/bin/env python3
"""检索评测 runner — QDCVR 多 KB 系统对比实验（带 token 鉴权）.

方法组:
  B1 vector_flat    kb_id="" 全库平面向量检索        (对应 NaiveRAG 锚点)
  B2 vector_domain  oracle 域内检索（需 golden KB）   (上界参照)
  S0 two_stage      系统两阶段检索(BM25→向量+图扩展)  (本系统主方法)
  S0b two_stage_nb  two_stage 关闭图扩展 (消融 -graph)
  S0c two_stage_bal balance_kbs=true (消融 +均衡多库)

指标: P@1/P@3/P@5, Recall@5, nDCG@5, MRR, FPR, 平均时延
统计: S0 vs 每个 baseline 的配对 t 检验 + Cohen's d

用法:
  export RAG_BENCH_TOKEN=mcp-xxxx            # 必填（.env 的 MCP_AUTH_TOKEN）
  python run_eval.py --dataset hotpotqa --methods all --top-k 5
  python run_eval.py --dataset popqa --limit 200   # 快速冒烟
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import math
import os
import socket
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

BENCH_DIR = Path(__file__).resolve().parent.parent / "data" / "benchmarks"
RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_BASE = os.environ.get("RAG_BENCH_URL", "http://localhost:8770")
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def validate_base_url(base: str) -> str:
    """SSRF 边界: 仅 http(s); 默认仅允许本机回环地址, 远程目标需显式放行环境变量。

    本 runner 的合法目标只有本机 rag-knowledge 后端; 禁止云元数据/链路本地地址。
    """
    parsed = urlparse(base)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"仅允许 http/https: {base}")
    host = (parsed.hostname or "").lower()
    if not host:
        raise ValueError(f"URL 缺少主机名: {base}")
    if host not in _LOCAL_HOSTS:
        if os.environ.get("RAG_BENCH_ALLOW_REMOTE") != "1":
            raise ValueError(
                f"非本机目标 {host} 被拒绝; 如确需远程后端, 设 RAG_BENCH_ALLOW_REMOTE=1")
        infos = {ai[4][0] for ai in socket.getaddrinfo(host, None)}
        for ip in infos:
            addr = ipaddress.ip_address(ip)
            if (addr.is_link_local or addr.is_loopback and False
                    or str(addr) == "169.254.169.254"):
                raise ValueError(f"目标解析到受限地址: {ip}")
    return base.rstrip("/")


BASE_URL = validate_base_url(DEFAULT_BASE)


def api_post(path: str, data: dict, token: str, timeout: int = 60) -> dict:
    url = f"{BASE_URL}/api/v1{path}"
    req = urllib.request.Request(
        url, data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {token}"},
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def ndcg_at_k(hits: list[int], k: int = 5) -> float:
    dcg = sum(h / math.log2(i + 2) for i, h in enumerate(hits[:k]))
    ideal_n = sum(1 for _ in range(min(sum(hits), k)))
    idcg = sum(1 / math.log2(i + 2) for i in range(ideal_n))
    return dcg / idcg if idcg > 0 else 0.0


def eval_query(hits: list[int]) -> dict:
    """hits: top-5 的 0/1 相关性列表"""
    k = len(hits)
    rr = next((1.0 / (i + 1) for i, h in enumerate(hits) if h), 0.0)
    return {
        "p1": hits[0] if k >= 1 else 0,
        "p3": sum(hits[:min(3, k)]) / min(3, k) if k else 0,
        "p5": sum(hits) / k if k else 0,
        "r5": (1.0 if any(hits) else 0.0),  # 单 golden doc 协议（FlashRAG 语料按页切分）
        "ndcg5": ndcg_at_k(hits),
        "mrr": rr,
    }


def paired_t(a: list[float], b: list[float]) -> dict:
    """配对 t 检验(无 scipy 依赖) + Cohen's d"""
    n = len(a)
    diffs = [x - y for x, y in zip(a, b)]
    mean_d = statistics.mean(diffs)
    sd = statistics.stdev(diffs) if n > 1 else 0.0
    if sd == 0:
        return {"t": 0.0, "p": 1.0, "cohens_d": 0.0, "n": n}
    t = mean_d / (sd / math.sqrt(n))
    # 正态近似 p 值（n≥30 时误差可忽略; 论文终稿用 scipy 重算）
    from math import erf
    p = 2 * (1 - 0.5 * (1 + erf(abs(t) / math.sqrt(2))))
    pooled = math.sqrt((statistics.variance(a) + statistics.variance(b)) / 2)
    d = mean_d / pooled if pooled else 0.0
    return {"t": round(t, 4), "p": round(p, 6), "cohens_d": round(d, 4), "n": n}


def run_method(method: str, samples: list[dict], kb_map: dict[str, str],
               token: str, top_k: int) -> tuple[list[list[int]], list[float], list[float]]:
    all_hits, latencies, fprs = [], [], []
    for i, s in enumerate(samples):
        golden = set(t.lower() for t in s.get("golden_titles", []))
        if method == "vector_flat":
            req = {"query": s["question"], "kb_id": "", "top_k": top_k,
                   "score_threshold": 0.0, "balance_kbs": False}
            path = "/search/vector"
        elif method == "vector_domain":
            kb_id = kb_map.get(s["qid"], "")
            req = {"query": s["question"], "kb_id": kb_id, "top_k": top_k,
                   "score_threshold": 0.0, "balance_kbs": False}
            path = "/search/vector"
        elif method in ("two_stage", "two_stage_nb", "two_stage_bal"):
            kb_id = kb_map.get(s["qid"], "") if method != "two_stage" else ""
            req = {"query": s["question"], "kb_id": kb_id,
                   "stage1_top_k": 20, "stage2_top_k": top_k,
                   "enable_graph_expansion": method != "two_stage_nb",
                   "score_threshold": 0.0, "balance_kbs": method == "two_stage_bal"}
            path = "/search/two-stage"
        else:
            raise ValueError(method)

        t0 = time.perf_counter()
        try:
            resp = api_post(path, req, token)
        except urllib.error.HTTPError as e:
            print(f"\n  HTTP {e.code} on qid={s['qid']}: {e.read()[:200]!r}")
            raise
        latencies.append((time.perf_counter() - t0) * 1000)

        # two-stage 响应结构: {stage1, stage2:{results}, total_results}; vector: {results}
        if path.endswith("two-stage"):
            resp_results = resp.get("stage2", {}).get("results") or []
        else:
            resp_results = resp.get("results") or []
        hits = []
        fpr_hits = 0
        golden_kb = kb_map.get(s["qid"], "")
        for r in resp_results[:top_k]:
            dp = str(r.get("doc_path", "")).lower()
            hit = 1 if any(g in dp for g in golden) else 0
            hits.append(hit)
            if golden_kb and str(r.get("kb_id", "")) and str(r.get("kb_id")) != golden_kb:
                fpr_hits += 1
        # top-5 不足补零（保证分母一致）
        hits += [0] * (top_k - len(hits))
        all_hits.append(hits[:top_k])
        fprs.append(fpr_hits / top_k if golden_kb else 0.0)

        if (i + 1) % 50 == 0:
            p5 = statistics.mean(sum(h) / len(h) for h in all_hits)
            print(f"  [{i+1}/{len(samples)}] running P@5={p5:.3f}", flush=True)
    return all_hits, latencies, fprs


def kb_uuid_lookup() -> dict[str, str]:
    """KB 名 → uuid。优先入库报告, 兜底磁盘 .knowledge-base.yml。"""
    lookup: dict[str, str] = {}
    ingest = RESULTS_DIR / "corpus-ingest-report.json"
    if ingest.exists():
        try:
            rep = json.loads(ingest.read_text(encoding="utf-8"))
            for name, info in rep.get("kbs", {}).items():
                if info.get("kb_id"):
                    lookup[name] = info["kb_id"]
        except (OSError, json.JSONDecodeError):
            pass
    if not lookup:
        import re as _re
        storage = Path(__file__).resolve().parents[3] / "storage" / "tree-file-system"
        for yml in storage.glob("*/.knowledge-base.yml"):
            try:
                head = yml.read_text(encoding="utf-8")[:800]
            except OSError:
                continue
            m_name = _re.search(r"^  path:\s*(.+)$", head, _re.M)
            m_id = _re.search(r"^  id:\s*([0-9a-f-]{36})", head, _re.M)
            if m_name and m_id:
                lookup[m_name.group(1).strip()] = m_id.group(1)
    return lookup


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True,
                    choices=["popqa", "nq", "triviaqa", "hotpotqa", "2wiki",
                             "musique", "bamboogle"])
    ap.add_argument("--methods", default="all",
                    help="逗号分隔: vector_flat,two_stage,two_stage_nb,two_stage_bal,vector_domain | all")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 条(冒烟)")
    args = ap.parse_args()

    token = os.environ.get("RAG_BENCH_TOKEN", "")
    if not token:
        print("❌ 缺少 RAG_BENCH_TOKEN 环境变量（.env 中的 MCP_AUTH_TOKEN）")
        return 2

    data_path = BENCH_DIR / f"{args.dataset}.jsonl"
    samples = [json.loads(l) for l in data_path.open(encoding="utf-8") if l.strip()]
    if args.limit:
        samples = samples[:args.limit]

    # 语料可答性过滤: golden title 不在拆库语料中的查询无法命中（wiki18 为 2018 快照,
    # 约 28% 标题缺失）——默认剔除并在报告中如实记录, 同时报告"全量口径"数字所需信息。
    n_full = len(samples)
    corpus_titles: set[str] = set()
    for shard in (BENCH_DIR / "kb_split").glob("pages_KB-*.jsonl"):
        for line in shard.open(encoding="utf-8"):
            if line.strip():
                corpus_titles.add(json.loads(line)["title"].casefold())
    samples = [s for s in samples
               if any(t.casefold() in corpus_titles for t in s.get("golden_titles", []))]
    n_excluded = n_full - len(samples)
    print(f"语料可答性过滤: {n_full} -> {len(samples)} (排除 {n_excluded} 条 golden 页不在语料)")

    kb_map: dict[str, str] = {}
    kb_assign_path = BENCH_DIR / "kb_split" / "kb_assignments.json"
    if kb_assign_path.exists():
        title2kb = json.loads(kb_assign_path.read_text(encoding="utf-8"))
        uuid_of = kb_uuid_lookup()  # KB 名 → uuid（API 只认 uuid）
        kb_map = {s["qid"]: uuid_of.get(next((title2kb[t] for t in s.get("golden_titles", [])
                                              if t in title2kb), ""), "")
                  for s in samples}

    methods = (["vector_flat", "vector_domain", "two_stage",
                "two_stage_nb", "two_stage_bal"]
               if args.methods == "all"
               else [m.strip() for m in args.methods.split(",")])
    has_golden_kb = bool(kb_map and any(kb_map.values()))
    if not has_golden_kb and "vector_domain" in methods:
        methods.remove("vector_domain")  # 无拆库映射时跳过 oracle 域内法

    report: dict = {
        "dataset": args.dataset, "n_queries": len(samples), "top_k": args.top_k,
        "n_excluded_no_corpus": n_excluded,
        "backend": BASE_URL, "timestamp": datetime.now(timezone.utc).isoformat(),
        "methods": {}, "significance": {},
    }
    per_query_scores: dict[str, list[float]] = {}

    for m in methods:
        print(f"\n=== {m} ({len(samples)} queries) ===", flush=True)
        hits_matrix, lats, fprs = run_method(m, samples, kb_map, token, args.top_k)
        per_q = [eval_query(h) for h in hits_matrix]
        per_query_scores[m] = [x["ndcg5"] for x in per_q]
        agg = {k: round(statistics.mean(x[k] for x in per_q), 4)
               for k in ["p1", "p3", "p5", "r5", "ndcg5", "mrr"]}
        agg["fpr"] = round(statistics.mean(fprs), 4) if kb_map else None
        agg["latency_ms"] = round(statistics.mean(lats), 1)
        report["methods"][m] = agg
        print(f"  -> {json.dumps(agg)}")

    if "two_stage" in per_query_scores:
        base = per_query_scores["two_stage"]
        for m, scores in per_query_scores.items():
            if m != "two_stage":
                report["significance"][f"two_stage_vs_{m}"] = paired_t(base, scores)

    out = RESULTS_DIR / f"eval-{args.dataset}-{'_'.join(methods[:3])}.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✓ saved {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
