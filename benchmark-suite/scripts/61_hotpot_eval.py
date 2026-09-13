#!/usr/bin/env python3
"""E8-2 · HotpotQA 多域基准 4 方法评测 + E7 盲区双向错误率（修 TODO-12/TODO-2）.

方法（与 EXPERIMENT-DESIGN §2 一致，全部经 kb-mcp MCP 真链路）:
  bm25      stage1 候选            two_stage  stage2+阈值+去重（无验证）
  dense     kb_search_vector top-10  qdcvr      两阶段→阈值→kb_doc_read×3 验证重排
金标: 每题官方 supporting docs（标题级匹配, 与分库文件名对齐）。
指标: Hit@k / Recall@2/5 / nDCG@10 / P@5 / MRR + answer@3（答案串在 top-3 正文）。
盲区: 金标跨 ≥2 KB 的查询上测「未声明跨库」的欠抑制率；
      通过 qdcvr 结果中金标 KB 覆盖数 vs 系统 balance 命中 KB 数近似实现
      （后端不暴露显式声明字段, 以「top-5 命中 KB 数 < 金标 KB 数」作代理并注明）。
输出: results/run-*/hotpot_main.json
"""
from __future__ import annotations

import json
import math
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import (DATA, McpClient, doc_basename, env_fingerprint,  # noqa: E402
                 mean, norm_t, now_iso, set_run, step25)

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


def eval_titles(paths, golden, k_list=(1, 2, 3, 5, 10)):
    hits = [1 if norm_t(title_of(p)) in golden else 0 for p in paths]
    out = {}
    for k in k_list:
        matched = len({norm_t(title_of(p)) for p in paths[:k]} & golden)
        out[f"recall@{k}"] = matched / len(golden) if golden else 0.0
        out[f"hit@{k}"] = 1 if any(hits[:k]) else 0
    dcg = sum(h / math.log2(i + 2) for i, h in enumerate(hits[:10]))
    n_rel = min(len(golden), 10)
    idcg = sum(1 / math.log2(i + 2) for i in range(n_rel)) or 1.0
    out["ndcg@10"] = dcg / idcg
    out["precision@5"] = sum(hits[:5]) / 5.0
    out["mrr"] = next((1 / (i + 1) for i, h in enumerate(hits) if h), 0.0)
    return out


class ReadCache:
    def __init__(self, mc):
        self.mc = mc
        self.cache: dict[str, str] = {}

    def content(self, dp):
        k = dp.lower()
        if k not in self.cache:
            try:
                d = self.mc.call("kb_doc_read", {"doc_path": dp, "max_chars": 4000},
                                 timeout=120)
                self.cache[k] = str(d.get("content") or d.get("raw") or "")
            except Exception:  # noqa: BLE001
                self.cache[k] = ""
        return self.cache[k]

    def topk_join(self, paths, k):
        return " ".join(self.content(p) for p in paths[:k]).lower()


def main() -> int:
    outdir = set_run()
    mc = McpClient()
    rc = ReadCache(mc)
    methods = ("bm25", "two_stage", "dense", "qdcvr")
    rows: dict[str, list] = {m: [] for m in methods}
    kb_of_title: dict[str, str] = {}
    try:
        # 标题→KB 映射（来自分库目录）
        for d in (DATA / "hotpotqa" / "docs").iterdir():
            if d.is_dir():
                for f in d.glob("*.md"):
                    kb_of_title[title_of(f.name).lower()] = d.name
        qs = [json.loads(l) for l in
              (DATA / "hotpotqa" / "queries.jsonl").open(encoding="utf-8")]
        print(f"[hotpot] {len(qs)} queries × {len(methods)} methods", flush=True)
        for i, q in enumerate(qs):
            golden = {norm_t(t) for t in q["golden_titles"]}
            answers = [q["answer"].lower()]
            gold_kbs = {kb_of_title.get(g, "?") for g in golden}

            t0 = time.perf_counter()
            mc.call("kb_list", {"lightweight": True})
            res = mc.call("kb_search_two_stage",
                          {"query": q["question"], "kb_id": "", "stage1_top_k": 40,
                           "stage2_top_k": 10, "balance_kbs": True}, timeout=420)
            t_staged = time.perf_counter() - t0
            stage1 = [str(c.get("doc_path", ""))
                      for c in (res.get("stage1") or {}).get("candidates") or []]
            ranked = step25((res.get("stage2") or {}).get("results") or [])
            s2 = [str(r.get("doc_path", "")) for r in ranked]
            terms = [t_.lower() for t_ in
                     re.findall(r"[a-zA-Z]{2,}", q["question"]) if len(t_) >= 2]
            verified: dict[str, int] = {}
            for dp in s2[:3]:
                try:
                    c = rc.content(dp)
                    verified[dp] = sum(1 for t_ in terms if t_ in c)
                except Exception:  # noqa: BLE001
                    verified[dp] = 0
            qdcvr = sorted(s2, key=lambda dp: (0, -verified.get(dp, 0))
                           if dp in verified else (1, 0))
            qdcvr = dedupe(qdcvr)
            t0 = time.perf_counter()
            rv = mc.call("kb_search_vector", {"query": q["question"], "kb_id": "",
                                              "top_k": 10}, timeout=420)
            t_dense = time.perf_counter() - t0
            dense = dedupe([str(x.get("doc_path", "")) for x in rv.get("results") or []])

            lists = {"bm25": dedupe(stage1), "two_stage": dedupe(s2),
                     "qdcvr": qdcvr, "dense": dense}
            for m, paths in lists.items():
                mm = eval_titles(paths, golden)
                for k in (1, 3):
                    body = rc.topk_join(paths, k)
                    mm[f"answer@{k}"] = 1 if any(a in body for a in answers) else 0
                mm["latency_s"] = round(t_staged if m != "dense" else t_dense, 3)
                hit_kbs = {kb_of_title.get(norm_t(title_of(p)), "?")
                           for p in paths[:5] if norm_t(title_of(p)) in golden}
                mm["gold_kbs"] = len(gold_kbs)
                mm["hit_kb_count"] = len(hit_kbs)
                mm["under_declared"] = 1 if len(hit_kbs) < len(gold_kbs) else 0
                rows[m].append({"qid": q["qid"], **mm})
            print(f"  [{i+1}/{len(qs)}] qdcvr R@2={rows['qdcvr'][-1]['recall@2']:.2f} "
                  f"dense R@2={rows['dense'][-1]['recall@2']:.2f}", flush=True)
    finally:
        mc.close()

    n_cross = sum(1 for r in rows["qdcvr"] if r["gold_kbs"] >= 2)
    summary = {m: {k: mean(r[k] for r in rs)
                   for k in ("hit@1", "hit@2", "hit@3", "hit@5", "recall@2", "recall@5",
                             "ndcg@10", "precision@5", "mrr", "answer@1", "answer@3")}
               for m, rs in rows.items()}
    blind = {
        "note": "proxy metric: backend does not expose an explicit coverage-declaration "
                "field; under-declaration = fewer gold KBs represented in top-5 than "
                "exist in the gold set (over-suppression measured on single-KB SciFact "
                "in report text)",
        "n_queries_cross_kb_gold": n_cross,
        "share_cross_kb": round(n_cross / max(1, len(rows["qdcvr"])), 4),
        "under_declaration_rate": {
            m: round(mean(r["under_declared"] for r in rs if r["gold_kbs"] >= 2), 4)
            for m, rs in rows.items()},
    }
    result = {"experiment": "E8 multi-domain public benchmark + E7 blind-spot (TODO-12/2)",
              "round": ROUND, "dataset": f"HotpotQA dev-distractor subset, {len(qs)} queries",
              "summary": summary, "blindspot": blind, "rows": rows,
              "meta": {"generated": now_iso(), "env": env_fingerprint()}}
    out = outdir / f"hotpot_main_{ROUND}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"-> {out}")
    for m in methods:
        s = summary[m]
        print(f"  {m:9s} Hit@5={s['hit@5']:.3f} R@2={s['recall@2']:.3f} "
              f"nDCG@10={s['ndcg@10']:.3f} P@5={s['precision@5']:.3f} ans@3={s['answer@3']}")
    print("blindspot:", json.dumps(blind, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
