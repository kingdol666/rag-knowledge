#!/usr/bin/env python3
"""标准语料赛道检索评测 — QDCVR 确定性管线 vs 三类基线 + 答案级内容判定.

方法（全部经 kb-mcp MCP 真链路，同一语料、同一查询）：
  bm25      — kb_search_two_stage 的 stage1 候选（稀疏 BM25 检索，
              Robertson & Zaragoza 2009；BEIR 论文基线同款）
  twostage  — stage2 精排 + Step2.5 阈值/去重（混合检索，未做内容验证）
  dense     — kb_search_vector top-10（BAAI/bge-m3 稠密向量，Chen et al. 2024）
  qdcvr     — 本系统规程：两阶段 → Step2.5 → kb_doc_read×3 内容验证重排
              （content-overrides-vector，knowledgebase-search skill Step1-3）

答案级判定（检索到的内容能否"真实回答出问题"，对四种方法对称执行，
同一 kb_doc_read 读取缓存）：
  SQuAD   — answer@k：金标答案串出现在 top-k 检索文档正文（全文读取后子串匹配）
  SciFact — claim_evidence：top-1 文档正文对 claim 内容词（去停用词）的覆盖率；
            support@1 = 覆盖率 ≥ 0.5 的查询占比

指标：Hit@k / Recall@k / nDCG@10 / Precision@5 / MRR（BEIR qrels 金标）。
输出：results/module_b_std2_r{1,2}.json
烟测：BENCH_LIMIT=3 python scripts/22_std2_retrieval.py 1 （每数据集只跑前 3 查询）
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import (DATA, McpClient, doc_basename, env_fingerprint,  # noqa: E402
                 mean, norm_t, now_iso, step25)

ROUND = sys.argv[1] if len(sys.argv) > 1 else "1"
LIMIT = int(os.environ.get("BENCH_LIMIT", "0"))
RESULTS = Path(__file__).resolve().parent.parent / "results"

STOP = set("""the a an of in on for to and or is are was were be been being with as
by at from that this these those it its we our their they he she his her you your
i not no do does did can could may might will would should shall than then so such
which who whom whose what when where why how also into over under between during
""".split())


def doc_cid(doc_path: str) -> str:
    """md 文件名形如 'Title [cid].md' — 提取尾部 [cid] 作为语料库文档 id."""
    b = doc_basename(doc_path)
    m = re.search(r"\[([^\[\]]+)\]\s*$", b)
    return m.group(1) if m else b


def dedupe(seq: list[str]) -> list[str]:
    """文档级去重(保留首次出现) — 向量检索按 chunk 返回, 同文档多 chunk 只计一次。"""
    seen, out = set(), []
    for x in seq:
        k = x.lower()
        if k not in seen:
            seen.add(k)
            out.append(x)
    return out


def content_words(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z]{2,}", text.lower()) if t not in STOP]


class ReadCache:
    """kb_doc_read 读取缓存 — 答案级判定对四种方法对称, 同文档只读一次."""

    def __init__(self, mc: McpClient, max_chars: int = 6000):
        self.mc = mc
        self.max_chars = max_chars
        self.cache: dict[str, str] = {}
        self.misses = 0

    def content(self, doc_path: str) -> str:
        k = doc_path.lower()
        if k not in self.cache:
            try:
                d = self.mc.call("kb_doc_read",
                                 {"doc_path": doc_path,
                                  "max_chars": self.max_chars}, timeout=120)
                self.cache[k] = str(d.get("content") or d.get("raw") or "")
                self.misses += 1
            except Exception:  # noqa: BLE001
                self.cache[k] = ""
        return self.cache[k]

    def topk_join(self, paths: list[str], k: int) -> str:
        return " ".join(self.content(p) for p in paths[:k]).lower()


def eval_vs_qrels(ranked_cids: list[str], relevant: set[str],
                  k_list=(1, 3, 5, 10)) -> dict:
    out = {}
    for k in k_list:
        matched = len({c for c in ranked_cids[:k] if c in relevant})
        out[f"recall@{k}"] = matched / len(relevant) if relevant else 0.0
        out[f"hit@{k}"] = 1 if matched else 0
    dcg = sum((1 / math.log2(i + 2)) for i, c in enumerate(ranked_cids[:10])
              if c in relevant)
    n_rel = min(len(relevant), 10)
    idcg = sum(1 / math.log2(i + 2) for i in range(n_rel)) or 1.0
    out["ndcg@10"] = dcg / idcg
    rel5 = sum(1 for c in ranked_cids[:5] if c in relevant)
    out["precision@5"] = rel5 / 5.0
    out["mrr"] = next((1.0 / (i + 1) for i, c in enumerate(ranked_cids)
                       if c in relevant), 0.0)
    return out


def eval_ranking(ranked: list[str], golden: set[str]) -> dict:
    hits = [1 if norm_t(c) in golden else 0 for c in ranked]
    out = {}
    for k in (1, 3, 5, 10):
        out[f"hit@{k}"] = 1 if any(hits[:k]) else 0
        matched = sum(hits[:k])
        out[f"recall@{k}"] = matched / len(golden) if golden else 0.0
    rel5 = sum(hits[:5])
    out["precision@5"] = rel5 / 5.0
    out["mrr"] = next((1.0 / (i + 1) for i, h in enumerate(hits) if h), 0.0)
    dcg = sum(h / math.log2(i + 2) for i, h in enumerate(hits[:10]))
    n_rel = min(sum(hits), 10)
    idcg = sum(1 / math.log2(i + 2) for i in range(n_rel)) or 1.0
    out["ndcg@10"] = dcg / idcg
    return out


def staged_all(mc: McpClient, question: str) -> dict:
    """单次两阶段调用抽出 3 种方法 + QDCVR 内容验证重排.

    返回: bm25/twostage/qdcvr 三种 doc_path 排序列表 + 验证证据。
    """
    t0 = time.perf_counter()
    mc.call("kb_list", {"lightweight": True})
    res = mc.call("kb_search_two_stage",
                  {"query": question, "kb_id": "", "stage1_top_k": 40,
                   "stage2_top_k": 10, "balance_kbs": True}, timeout=420)
    stage1 = [str(c.get("doc_path", ""))
              for c in (res.get("stage1") or {}).get("candidates") or []]
    ranked = step25((res.get("stage2") or {}).get("results") or [])
    stage2 = [str(r.get("doc_path", "")) for r in ranked]
    terms = [t.lower() for t in
             re.findall(r"[a-zA-Z\u4e00-\u9fff\u3040-\u30ff]{2,}", question)
             if len(t) >= 2]
    verified: dict[str, int] = {}
    chars = 0
    for doc_path in stage2[:3]:
        try:
            d = mc.call("kb_doc_read", {"doc_path": doc_path, "max_chars": 3000},
                        timeout=120)
            content = str(d.get("content") or d.get("raw") or "")
            chars += len(content)
            verified[doc_path] = sum(1 for t in terms if t in content.lower())
        except Exception:  # noqa: BLE001
            verified[doc_path] = 0
    final = sorted(stage2, key=lambda dp: (0, -verified.get(dp, 0))
                   if dp in verified else (1, 0))
    uniq = dedupe(final)
    return {"bm25": dedupe(stage1), "twostage": dedupe(stage2), "qdcvr": uniq,
            "latency": time.perf_counter() - t0, "chars_read": chars,
            "verify_pass": sum(1 for v in verified.values() if v > 0)}


def dense_baseline(mc: McpClient, question: str) -> tuple[list[str], float]:
    t0 = time.perf_counter()
    r = mc.call("kb_search_vector", {"query": question, "kb_id": "", "top_k": 10},
                timeout=420)
    paths = dedupe([str(x.get("doc_path", "")) for x in (r.get("results") or [])])
    return paths, time.perf_counter() - t0


def run_dataset(mc: McpClient, rc: ReadCache, name: str, queries: list[dict]) -> dict:
    """跑一个数据集: 每查询 4 方法 + 答案级判定. 返回 {method: [rows]}."""
    rows: dict[str, list] = {m: [] for m in ("bm25", "twostage", "dense", "qdcvr")}
    for i, q in enumerate(queries):
        st = staged_all(mc, q["question"])
        dense, t_dense = dense_baseline(mc, q["question"])
        lists = {"bm25": st["bm25"], "twostage": st["twostage"],
                 "qdcvr": st["qdcvr"], "dense": dense}
        for method, paths in lists.items():
            if name == "scifact":
                relevant = {norm_t(c) for c in q["golden_ids"]}
                m = eval_vs_qrels(dedupe([doc_cid(d) for d in paths]), relevant)
                top1_content = rc.content(paths[0]) if paths else ""
                qw = content_words(q["question"])
                cov = (len({w for w in content_words(top1_content)} & set(qw))
                       / len(qw)) if qw and top1_content else 0.0
                m["claim_evidence"] = round(cov, 4)
                m["support@1"] = 1 if cov >= 0.5 else 0
            else:
                golden = {norm_t(t) for t in q["golden_pages"]}
                m = eval_ranking(dedupe([doc_basename(d) for d in paths]), golden)
                answers = [a.lower() for a in q.get("answers") or []]
                for k in (1, 3, 5):
                    body = rc.topk_join(paths, k)
                    m[f"answer@{k}"] = (1 if any(a in body for a in answers)
                                        else 0) if answers else 0
            m["latency_s"] = round(st["latency"] if method != "dense"
                                   else t_dense, 3)
            rows[method].append({"qid": q["qid"], **m})
        if name == "scifact":
            rows["qdcvr"][-1]["chars_read"] = st["chars_read"]
            rows["qdcvr"][-1]["verify_pass"] = st["verify_pass"]
        print(f"  [{name} {i+1}/{len(queries)}] "
              f"qdcvr hit@3={rows['qdcvr'][-1].get('hit@3', '?')} "
              f"dense hit@3={rows['dense'][-1].get('hit@3', '?')}", flush=True)
    return rows


def agg(rs: list, extra: tuple = ()) -> dict:
    keys = ["hit@1", "hit@3", "hit@5", "hit@10", "recall@3", "recall@5",
            "recall@10", "ndcg@10", "precision@5", "mrr", "answer@1",
            "answer@3", "answer@5", "claim_evidence", "support@1"]
    out = {}
    for k in keys:
        vals = [r[k] for r in rs if k in r]
        if vals:
            out[k] = round(mean(vals), 4)
    out["n"] = len(rs)
    out["latency_s_mean"] = round(mean(r["latency_s"] for r in rs), 3)
    for k in extra:
        vals = [r[k] for r in rs if k in r]
        if vals:
            out[k] = round(mean(vals), 1)
    return out


def main() -> int:
    mc = McpClient()
    rc = ReadCache(mc)
    try:
        qs = [json.loads(l) for l in
              (DATA / "standard2" / "scifact" / "queries.jsonl").open(encoding="utf-8")]
        if LIMIT:
            qs = qs[:LIMIT]
        print(f"[scifact] {len(qs)} queries", flush=True)
        scifact = run_dataset(mc, rc, "scifact", qs)

        qs = [json.loads(l) for l in
              (DATA / "standard2" / "squad" / "queries-squad.jsonl").open(encoding="utf-8")]
        if LIMIT:
            qs = qs[:LIMIT]
        print(f"[squad] {len(qs)} queries", flush=True)
        squad = run_dataset(mc, rc, "squad", qs)
    finally:
        mc.close()

    result = {
        "meta": {"round": ROUND, "env": env_fingerprint(), "generated": now_iso(),
                 "methods": {
                     "bm25": "stage1 sparse BM25 (two_stage candidates)",
                     "twostage": "stage2 rerank + threshold/dedup, no content verification",
                     "dense": "kb_search_vector BAAI/bge-m3 top-10",
                     "qdcvr": "two-stage + threshold + kb_doc_read content "
                              "verification rerank (skill QDCVR)"},
                 "answer_judging": {
                     "squad": "answer@k = gold answer string occurs in top-k "
                              "retrieved docs' full content (kb_doc_read)",
                     "scifact": "claim_evidence = content-word coverage of the "
                                "claim in top-1 doc content; support@1 = cov>=0.5"},
                 "scifact": {"queries": len(scifact["qdcvr"]),
                             "protocol": "BEIR qrels gold, Recall/nDCG"},
                 "squad": {"queries": len(squad["qdcvr"]),
                           "protocol": "article-level gold + answer-in-content"}},
        "summary": {
            "scifact": {m: agg(scifact[m], ("chars_read", "verify_pass"))
                        for m in ("bm25", "twostage", "dense", "qdcvr")},
            "squad": {m: agg(squad[m]) for m in ("bm25", "twostage", "dense", "qdcvr")},
        },
        "rows": {"scifact": scifact, "squad": squad},
    }
    suffix = "_smoke" if LIMIT else ""
    out = RESULTS / f"module_b_std2_r{ROUND}{suffix}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"-> {out}")
    for ds in ("scifact", "squad"):
        print(f"== {ds} ==")
        for m, a in result["summary"][ds].items():
            print(f"  {m:9s}", json.dumps(a, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
