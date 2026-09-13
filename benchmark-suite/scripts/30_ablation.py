#!/usr/bin/env python3
"""E1 · 同查询集消融实验（修 TODO-9/F12）.

在 BEIR SciFact 30 查询（与主表相同查询集与金标）上运行 QDCVR 组件消融：

系统形态变体（stage2_top_k=10，与部署一致）:
  qdcvr_full   阈值0.35+文档去重 → kb_doc_read×3 内容验证重排（系统规程）
  verify_k1    内容验证只读 top-1
  verify_k5    内容验证读 top-5
  no_verify    无内容验证（= 两阶段混合检索，对应论文 -ContentVerify）
  no_dedup     评测不去重（同一文档多 chunk 占多席，暴露去重的 P@5 收益）

深度候选池阈值扫描（stage2_top_k=40，阈值在此才真正 binding——
后端返回的 top-10 分数已 ≥0.379，0.35 阈值已在后端生效，客户端扫不动）:
  deep_t_0.20 / deep_t_0.35 / deep_t_0.50 / deep_t_off

每查询 2 次两阶段调用 + 5 次内容读取，全部变体共享。
输出: results/run-*/ablation_scifact_<round>.json（逐查询×逐变体，供 E2 统计）
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import (DATA, McpClient, doc_basename, env_fingerprint, mean,  # noqa: E402
                 now_iso, set_run)

ROUND = sys.argv[1] if len(sys.argv) > 1 else "1"


def doc_cid(doc_path: str) -> str:
    b = doc_basename(doc_path)
    m = re.search(r"\[([^\[\]]+)\]\s*$", b)
    return m.group(1) if m else b


def dedupe(seq):
    seen, out = set(), []
    for x in seq:
        k = x.lower()
        if k not in seen:
            seen.add(k)
            out.append(x)
    return out


def dedup_keep_best(results: list[dict]) -> list[dict]:
    """文档级去重(保留最高分)+分数降序 — 不做阈值过滤(阈值由变体施加)."""
    best: dict[str, dict] = {}
    for r in results:
        dp = str(r.get("doc_path", ""))
        s = float(r.get("score", 0) or 0)
        if dp not in best or s > float(best[dp].get("score", 0) or 0):
            best[dp] = r
    return sorted(best.values(), key=lambda r: -float(r.get("score", 0) or 0))


def apply_threshold(ranked: list[dict], threshold: float) -> list[dict]:
    if threshold <= 0:
        return list(ranked)
    return [r for r in ranked if float(r.get("score", 0) or 0) >= threshold]


def rerank(paths: list[str], verified: dict[str, int], k: int) -> list[str]:
    if k <= 0:
        return paths
    keys = {dp for dp in paths[:k]}
    return sorted(paths, key=lambda dp: (0, -verified.get(dp, 0)) if dp in keys else (1, 0))


def eval_qrels(ranked_cids, relevant, k_list=(1, 3, 5, 10)):
    out = {}
    for k in k_list:
        matched = len({c for c in ranked_cids[:k] if c in relevant})
        out[f"recall@{k}"] = matched / len(relevant) if relevant else 0.0
        out[f"hit@{k}"] = 1 if matched else 0
    dcg = sum(1 / math.log2(i + 2) for i, c in enumerate(ranked_cids[:10]) if c in relevant)
    n_rel = min(len(relevant), 10)
    idcg = sum(1 / math.log2(i + 2) for i in range(n_rel)) or 1.0
    out["ndcg@10"] = dcg / idcg
    out["precision@5"] = sum(1 for c in ranked_cids[:5] if c in relevant) / 5.0
    out["mrr"] = next((1 / (i + 1) for i, c in enumerate(ranked_cids) if c in relevant), 0.0)
    return out


VARIANTS = ("qdcvr_full", "verify_k1", "verify_k5", "no_verify", "no_dedup",
            "deep_t_0.20", "deep_t_0.35", "deep_t_0.50", "deep_t_off")


def main() -> int:
    outdir = set_run()
    mc = McpClient()
    rows: dict[str, list] = {v: [] for v in VARIANTS}
    try:
        qs = [json.loads(l) for l in
              (DATA / "standard2" / "scifact" / "queries.jsonl").open(encoding="utf-8")]
        print(f"[ablation] SciFact {len(qs)} queries × {len(VARIANTS)} variants", flush=True)
        for i, q in enumerate(qs):
            relevant = {c.strip().lower() for c in q["golden_ids"]}
            terms = [t_.lower() for t_ in
                     re.findall(r"[a-zA-Z\u4e00-\u9fff\u3040-\u30ff]{2,}", q["question"])
                     if len(t_) >= 2]

            base = {"query": q["question"], "kb_id": "", "stage1_top_k": 40,
                    "stage2_top_k": 10, "balance_kbs": True}
            r10 = mc.call("kb_search_two_stage", base, timeout=420)
            r40 = mc.call("kb_search_two_stage", {**base, "stage2_top_k": 40}, timeout=420)
            s10 = (r10.get("stage2") or {}).get("results") or []
            s40 = (r40.get("stage2") or {}).get("results") or []

            verified: dict[str, int] = {}
            chars = 0
            for dp in dedupe([str(r.get("doc_path", "")) for r in dedup_keep_best(s10)])[:5]:
                try:
                    d = mc.call("kb_doc_read", {"doc_path": dp, "max_chars": 3000},
                                timeout=120)
                    content = str(d.get("content") or d.get("raw") or "")
                    chars += len(content)
                    verified[dp] = sum(1 for t_ in terms if t_ in content.lower())
                except Exception:  # noqa: BLE001
                    verified[dp] = 0

            def pipeline(pool, t, use_dedup=True, k=3, do_rerank=True, eval_dedup=True):
                ranked = apply_threshold(dedup_keep_best(pool) if use_dedup else list(pool), t)
                paths = [str(r.get("doc_path", "")) for r in ranked]
                if do_rerank:
                    paths = rerank(paths, verified, k)
                cids = [doc_cid(d) for d in paths]
                if eval_dedup:
                    cids = dedupe(cids)
                return eval_qrels(cids, relevant)

            rows["qdcvr_full"].append({"qid": q["qid"],
                                       **pipeline(s10, 0.35, True, 3, True, True)})
            rows["verify_k1"].append({"qid": q["qid"],
                                      **pipeline(s10, 0.35, True, 1, True, True)})
            rows["verify_k5"].append({"qid": q["qid"],
                                      **pipeline(s10, 0.35, True, 5, True, True)})
            rows["no_verify"].append({"qid": q["qid"],
                                      **pipeline(s10, 0.35, True, 0, False, True)})
            rows["no_dedup"].append({"qid": q["qid"],
                                     **pipeline(s10, 0.35, True, 3, True, False)})
            for name, t in (("deep_t_0.20", 0.20), ("deep_t_0.35", 0.35),
                            ("deep_t_0.50", 0.50), ("deep_t_off", 0.0)):
                rows[name].append({"qid": q["qid"],
                                   **pipeline(s40, t, True, 3, True, True)})
            print(f"  [{i+1}/{len(qs)}] full={rows['qdcvr_full'][-1]['ndcg@10']:.3f} "
                  f"no_verify={rows['no_verify'][-1]['ndcg@10']:.3f} "
                  f"deep_t050={rows['deep_t_0.50'][-1]['ndcg@10']:.3f}", flush=True)
    finally:
        mc.close()

    summary = {name: {k: mean(r[k] for r in rs)
                      for k in ("hit@1", "hit@3", "hit@5", "recall@3", "recall@5",
                                "recall@10", "ndcg@10", "precision@5", "mrr")}
               for name, rs in rows.items()}
    result = {"experiment": "E1 ablation (same query set as main table, TODO-9/F12)",
              "round": ROUND, "dataset": "BEIR SciFact 30 queries, official qrels",
              "note": "threshold sweep runs on stage2_top_k=40 pool; deployed top-10 "
                      "scores are already backend-prefiltered (min 0.379 observed)",
              "summary": summary, "rows": rows,
              "meta": {"generated": now_iso(), "env": env_fingerprint()}}
    out = outdir / f"ablation_scifact_{ROUND}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"-> {out}")
    for name, s in summary.items():
        print(f"  {name:12s} P@5={s['precision@5']:.4f} nDCG@10={s['ndcg@10']:.4f} "
              f"R@5={s['recall@5']:.4f} MRR={s['mrr']:.4f} Hit@3={s['hit@3']:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
