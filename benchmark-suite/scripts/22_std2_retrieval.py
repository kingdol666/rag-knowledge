#!/usr/bin/env python3
"""标准语料赛道检索评测 — QDCVR 确定性管线 vs 向量 baseline.

SciFact: 金标 = qrels 相关文档集(多篇) → Hit@k / Recall@k / nDCG@10 / P@5 / MRR
SQuAD:   金标 = 文章文档 → 同上 + answer_hit(答案文本出现在检索文档正文)
方法: content_staged(QDCVR 确定性展开, 经 MCP) vs vector_baseline(kb_search_vector)
输出: results/module_b_std2_r{1,2}.json
"""
from __future__ import annotations

import json
import math
import re
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import (DATA, McpClient, doc_basename, env_fingerprint, mean,  # noqa: E402
                 norm_t, now_iso, step25)

ROUND = sys.argv[1] if len(sys.argv) > 1 else "1"
RESULTS = Path(__file__).resolve().parent.parent / "results"


def doc_cid(doc_path: str) -> str:
    """md 文件名形如 'Title [cid].md' — 提取尾部 [cid] 作为语料库文档 id."""
    b = doc_basename(doc_path)
    m = re.search(r"\[([^\[\]]+)\]\s*$", b)
    return m.group(1) if m else b


def dedupe(seq: list[str]) -> list[str]:
    """文档级去重(保留首次出现) — 向量检索按 chunk 返回, 同文档多 chunk 须只计一次。"""
    seen, out = set(), []
    for x in seq:
        k = x.lower()
        if k not in seen:
            seen.add(k)
            out.append(x)
    return out


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


def staged_qdcvr(mc: McpClient, question: str) -> dict:
    t0 = time.perf_counter()
    mc.call("kb_list", {"lightweight": True})
    res = mc.call("kb_search_two_stage",
                  {"query": question, "kb_id": "", "stage1_top_k": 40,
                   "stage2_top_k": 10, "balance_kbs": True}, timeout=420)
    ranked = step25((res.get("stage2") or {}).get("results") or [])
    docs = [str(r.get("doc_path", "")) for r in ranked]
    terms = [t.lower() for t in
             re.findall(r"[a-zA-Z\u4e00-\u9fff\u3040-\u30ff]{2,}", question)
             if len(t) >= 2]
    verified: dict[str, int] = {}
    chars = 0
    for doc_path in docs[:3]:
        try:
            d = mc.call("kb_doc_read", {"doc_path": doc_path, "max_chars": 3000},
                        timeout=120)
            content = str(d.get("content") or d.get("raw") or "")
            chars += len(content)
            verified[doc_path] = sum(1 for t in terms if t in content.lower())
        except Exception:  # noqa: BLE001
            verified[doc_path] = 0
    final = sorted(docs, key=lambda dp: (0, -verified.get(dp, 0))
                   if dp in verified else (1, 0))
    seen, uniq = set(), []
    for d in final:
        k = d.lower()
        if k not in seen:
            seen.add(k)
            uniq.append(d)
    return {"cids": dedupe([doc_cid(d) for d in uniq]),
            "basenames": dedupe([doc_basename(d) for d in uniq]),
            "latency": time.perf_counter() - t0, "chars_read": chars,
            "verify_pass": sum(1 for v in verified.values() if v > 0)}


def vector_baseline(mc: McpClient, question: str) -> dict:
    t0 = time.perf_counter()
    r = mc.call("kb_search_vector", {"query": question, "kb_id": "", "top_k": 10},
                timeout=420)
    docs = [str(x.get("doc_path", "")) for x in (r.get("results") or [])]
    cids = dedupe([doc_cid(d) for d in docs])
    base = dedupe([doc_basename(d) for d in docs])
    return {"cids": cids, "basenames": base,
            "latency": time.perf_counter() - t0}


def main() -> int:
    mc = McpClient()
    rows = {"scifact_staged": [], "scifact_vector": [],
            "squad_staged": [], "squad_vector": []}
    try:
        # ── SciFact: qrels 多相关文档 → Recall/nDCG ──
        qs = [json.loads(l) for l in
              (DATA / "standard2" / "scifact" / "queries.jsonl").open(encoding="utf-8")]
        for i, q in enumerate(qs):
            relevant = {norm_t(c) for c in q["golden_ids"]}
            st = staged_qdcvr(mc, q["question"])
            m = eval_vs_qrels(st["cids"], relevant)
            m.update({"latency_s": round(st["latency"], 3),
                      "chars_read": st["chars_read"],
                      "verify_pass": st["verify_pass"]})
            rows["scifact_staged"].append({"qid": q["qid"], **m})
            vb = vector_baseline(mc, q["question"])
            mv = eval_vs_qrels(vb["cids"], relevant)
            mv["latency_s"] = round(vb["latency"], 3)
            rows["scifact_vector"].append({"qid": q["qid"], **mv})
            if (i + 1) % 10 == 0:
                print(f"  [scifact {i+1}/{len(qs)}] "
                      f"staged nDCG@10={mean(r['ndcg@10'] for r in rows['scifact_staged'])}",
                      flush=True)

        # ── SQuAD: 文章级金标 + 答案命中 ──
        qs = [json.loads(l) for l in
              (DATA / "standard2" / "squad" / "queries-squad.jsonl").open(encoding="utf-8")]
        for i, q in enumerate(qs):
            golden = {norm_t(t) for t in q["golden_pages"]}
            answers = [a.lower() for a in q.get("answers") or []]
            st = staged_qdcvr(mc, q["question"])
            m = eval_ranking(st["basenames"], golden)
            m["answer_hit"] = 1 if any(
                a in norm_t(b) for a in answers
                for b in st["basenames"][:5]) or any(
                a in b.lower() for a in answers for b in st["basenames"][:5]) else 0
            m["latency_s"] = round(st["latency"], 3)
            rows["squad_staged"].append({"qid": q["qid"], **m})
            vb = vector_baseline(mc, q["question"])
            mv = eval_ranking(vb["basenames"], golden)
            mv["answer_hit"] = 1 if any(
                a in b.lower() for a in answers for b in vb["basenames"][:5]) else 0
            mv["latency_s"] = round(vb["latency"], 3)
            rows["squad_vector"].append({"qid": q["qid"], **mv})
            if (i + 1) % 8 == 0:
                print(f"  [squad {i+1}/{len(qs)}]", flush=True)
    finally:
        mc.close()

    def agg(rs, extra=()):
        out = {}
        keys = ["hit@1", "hit@3", "hit@5", "hit@10", "recall@3", "recall@5",
                "recall@10", "ndcg@10", "precision@5", "mrr", "answer_hit"]
        for k in keys:
            vals = [r[k] for r in rs if k in r]
            if vals:
                out[k] = mean(vals)
        out["latency_s_mean"] = mean(r["latency_s"] for r in rs)
        for k in extra:
            vals = [r[k] for r in rs if k in r]
            if vals:
                out[k] = mean(vals)
        return out

    result = {
        "meta": {"round": ROUND, "env": env_fingerprint(), "generated": now_iso(),
                 "scifact": {"queries": len(rows["scifact_staged"]),
                             "protocol": "BEIR qrels gold, Recall/nDCG"},
                 "squad": {"queries": len(rows["squad_staged"]),
                           "protocol": "article-level gold + answer-hit"}},
        "summary": {
            "scifact": {"staged": agg(rows["scifact_staged"], ("chars_read", "verify_pass")),
                        "vector": agg(rows["scifact_vector"])},
            "squad": {"staged": agg(rows["squad_staged"], ("answer_hit",)),
                      "vector": agg(rows["squad_vector"], ("answer_hit",))},
        },
        "rows": rows,
    }
    out = RESULTS / f"module_b_std2_r{ROUND}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"-> {out}")
    print("scifact:", json.dumps(result["summary"]["scifact"], ensure_ascii=False))
    print("squad:", json.dumps(result["summary"]["squad"], ensure_ascii=False))
    return 0


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


if __name__ == "__main__":
    sys.exit(main())
