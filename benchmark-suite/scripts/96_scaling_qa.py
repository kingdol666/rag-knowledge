#!/usr/bin/env python3
"""扩展性实验(检索精度 vs 文档数量) — 固定题集多快照对照.

题集(单一事实源, 确定性生成, 不用 LLM):
  old50 = 既有 manifest 50 篇: 经典 6 篇用内容问题(FAMOUS, 按 arXiv id 匹配),
          其余用标题问题(关键词取自标题, 必然在文内)。
  bq10  = data/papers/qa_questions.json 的 10 道内容强相关题(历史 bench10 口径)。
  new50 = round-2 新增 50 篇: FAMOUS2 内容问题 + 标题问题(仅在 t1/t05 快照可用)。

检索通道(两通道同测, 与 2026-09-19 回归口径一致):
  vec  = QDCVR v2 Phase 1 规定工具 kb_search_vector, 5 门类库逐库 top_k=10 合并去重 [主通道]
  ts   = kb_search_two_stage 整库(kb_id="") stage1=20/stage2=5, balance_kbs  [对照通道]

判分: dedup 后按 doc_path 取最高分; gold = doc_path 含 arxiv_id;
  pass = gold 进 top-3 且 top-3 chunk 文本含 ≥1 关键词。
  另记 doc_hit@1/@3/@5、gold MRR、gold score、top1 score。

用法: python 96_scaling_qa.py --tag t0 [--sets old50,bq10]
输出: results/scaling/scaling_<tag>_<set>.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE / "scripts"))

from lib import McpClient  # noqa: E402

PAPERS = SUITE / "data" / "papers"
OUT = SUITE / "results" / "scaling"

KB_CATEGORIES = ["计算机与人工智能", "自然科学与地球科学", "生命科学与医学",
                 "工程与能源", "经济与社会"]

FAMOUS = {
    "1706.03762": ("What attention mechanism does the Transformer architecture "
                   "use?", ["scaled dot-product", "multi-head"]),
    "1801.00862": ("What does the acronym NISQ stand for in quantum computing?",
                   ["noisy intermediate-scale"]),
    "2212.13138": ("What is MultiMedQA in the paper about large language models "
                   "and clinical knowledge?", ["multimedqa", "medqa"]),
    "1602.01876": ("What are the three ontologies of the Gene Ontology?",
                   ["molecular function", "biological process",
                    "cellular component"]),
    "1512.08067": ("What does this paper conclude about Unified Growth Theory?",
                   ["unified growth theory"]),
    "1503.07557": ("According to the paper, what physical factor governs "
                   "precipitation extremes under climate change?",
                   ["precipitation efficiency"]),
}

FAMOUS2 = {
    "1907.11692": ("What masked-language-model training strategy does RoBERTa "
                   "study?", ["dynamic masking", "roberta"]),
    "2203.02155": ("What alignment method does InstructGPT use to follow "
                   "instructions?", ["reinforcement learning from human feedback",
                                     "reinforcement learning"]),
    "1910.11333": ("What computational task did Google use to claim quantum "
                   "supremacy?", ["random circuit", "supremacy"]),
    "1901.07060": ("What clinical NLP task does this BERT-based paper address?",
                   ["clinical notes", "clinical"]),
}


def questions_from_manifest(papers: list[dict], famous: dict,
                            id_key: str = "arxiv_id") -> list[dict]:
    out = []
    for i, p in enumerate(papers, 1):
        aid = str(p.get(id_key, "")).split("v")[0]
        if aid in famous:
            q, kws = famous[aid]
        else:
            words = [w for w in re.findall(r"[A-Za-z]{5,}", p.get("title", ""))][:4]
            q = f"What does the paper titled '{p.get('title', '')}' study?"
            kws = [w.lower() for w in words]
        out.append({"qid": f"Q{i:02d}", "field": p.get("field", ""),
                    "arxiv_id": aid, "question": q, "keywords": kws})
    return out


def load_sets(sets: list[str]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for s in sets:
        if s == "old50":
            m = json.loads((PAPERS / "manifest.json").read_text(encoding="utf-8"))
            out[s] = questions_from_manifest(m["papers"][:50], FAMOUS)
        elif s == "new50":
            m = json.loads((PAPERS / "manifest.json").read_text(encoding="utf-8"))
            papers = [p for p in m["papers"]
                      if p.get("round", 1) >= 2]
            out[s] = questions_from_manifest(papers, FAMOUS2)
        elif s == "bq10":
            qs = json.loads((PAPERS / "qa_questions.json")
                            .read_text(encoding="utf-8"))["questions"]
            for i, q in enumerate(qs, 1):
                q.setdefault("qid", f"BQ{i:02d}")
                q.setdefault("keywords", q.get("gold_keywords", []))
            out[s] = qs
        else:
            raise SystemExit(f"unknown set: {s}")
    return out


def search_vec(mc, question: str) -> list[dict]:
    results = []
    for kb in KB_CATEGORIES:
        r = mc.call("kb_search_vector",
                    {"query": question, "kb_id": kb, "top_k": 10,
                     "score_threshold": 0.35}, timeout=300)
        results += (r.get("results") or [])
    return results


def search_ts(mc, question: str) -> list[dict]:
    r = mc.call("kb_search_two_stage",
                {"query": question, "kb_id": "", "stage1_top_k": 20,
                 "stage2_top_k": 5, "score_threshold": 0.30,
                 "balance_kbs": True}, timeout=300)
    return (r or {}).get("stage2", {}).get("results") or []


def judge(question: dict, items: list[dict]) -> dict:
    best: dict[str, dict] = {}
    for it in items:
        dp = str(it.get("doc_path", "")).replace("\\", "/")
        if dp and (dp not in best or it.get("score", 0) > best[dp]["score"]):
            best[dp] = it
    ranked = sorted(best.values(), key=lambda x: -x.get("score", 0))
    # slug 中斜杠已转连字符(gr-qc/9805045 → gr-qc-9805045)
    gold_key = question["arxiv_id"].replace("/", "-")
    gold_rank = 0
    for rank, d in enumerate(ranked, 1):
        if gold_key in str(d.get("doc_path", "")):
            gold_rank = rank
            break
    top3 = ranked[:3]
    blob = " ".join(str(d.get("content", "")).lower() for d in top3)
    kws = question.get("keywords") or question.get("gold_keywords") or []
    kw = [k for k in kws if str(k).lower() in blob]
    scores = [round(d.get("score", 0), 4) for d in ranked[:5]]
    return {"qid": question["qid"], "field": question["field"],
            "arxiv_id": question["arxiv_id"],
            "gold_rank": gold_rank,  # 0 = 未进去重后列表
            "n_dedup_docs": len(ranked),
            "doc_hit1": 1 <= gold_rank <= 1,
            "doc_hit3": 1 <= gold_rank <= 3,
            "doc_hit5": 1 <= gold_rank <= 5,
            "kw_hit": kw,
            "pass": bool(gold_rank and gold_rank <= 3 and kw),
            "top_scores": scores,
            "top_docs": [str(d.get("doc_path", "")) for d in ranked[:3]]}


def run_set(mc, name: str, questions: list[dict], tag: str) -> dict:
    rows = {"vec": [], "ts": []}
    t_start = time.perf_counter()
    for q in questions:
        rows["vec"].append(judge(q, search_vec(mc, q["question"])))
        rows["ts"].append(judge(q, search_ts(mc, q["question"])))
        print(f"[{q['qid']}] vec_hit3={rows['vec'][-1]['doc_hit3']} "
              f"ts_hit3={rows['ts'][-1]['doc_hit3']}", flush=True)
    out = {"set": name, "tag": tag, "n": len(questions),
           "seconds": round(time.perf_counter() - t_start, 1)}
    for ch, rr in rows.items():
        n = len(rr)
        mrr = sum((1 / r["gold_rank"]) if r["gold_rank"] else 0 for r in rr) / n
        out[ch] = {
            "pass": sum(r["pass"] for r in rr),
            "pass_rate": round(sum(r["pass"] for r in rr) / n, 3),
            "hit1": round(sum(r["doc_hit1"] for r in rr) / n, 3),
            "hit3": round(sum(r["doc_hit3"] for r in rr) / n, 3),
            "hit5": round(sum(r["doc_hit5"] for r in rr) / n, 3),
            "mrr": round(mrr, 4),
            "mean_top1_score": round(
                sum(r["top_scores"][0] for r in rr if r["top_scores"]) / n, 4),
            "rows": rr}
    (OUT / f"scaling_{tag}_{name}.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[done] {tag}/{name}: vec pass={out['vec']['pass']}/{len(questions)} "
          f"mrr={out['vec']['mrr']} | ts pass={out['ts']['pass']}/{len(questions)} "
          f"mrr={out['ts']['mrr']}", flush=True)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True, help="快照标识: t0/t05/t1/...")
    ap.add_argument("--sets", default="old50,bq10")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    sets = load_sets([s.strip() for s in args.sets.split(",") if s.strip()])
    mc = McpClient()
    for name, qs in sets.items():
        run_set(mc, name, qs, args.tag)
    mc.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
