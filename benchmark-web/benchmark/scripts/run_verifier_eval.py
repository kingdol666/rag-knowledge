#!/usr/bin/env python3
"""内容验证器评测 — 对标 CRAG (NAACL'24) Table 4 协议.

协议（与 CRAG 同源）:
  * 标签来源: PopQA 自带 golden wiki title 作为相关性信号（CRAG 论文同款用法）
  * 样本: 正例 = 检索结果中命中 golden title 的 chunk;
          难负例 = 同查询检索结果中未命中 golden title 的高分 chunk
  * 评分: 系统内容验证 0-8 rubric（topic 0-3 + scenario 0-2 + evidence 0-3）
          阈值化三分类: ≥6 Correct / 3-5 Ambiguous / ≤2 Incorrect（系统 P0/P1/P2 约定）
  * 指标: 三分类 accuracy、二分类 accuracy、FPR(负例判 Correct)、Correct 类 P/R/F1

CRAG Table 4 锚点: T5-based 84.3 / ChatGPT-few-shot 64.7 / ChatGPT-CoT 62.4 / ChatGPT 58.0

两个评分器:
  heuristic  — 系统内容验证启发式（词面覆盖, 零外部依赖, 逐字节可复现）← 默认
  llm        — 同一 rubric 的 LLM 版（需 RAG_QA_* 环境变量, 用于论文正文数字）

用法:
  export RAG_BENCH_TOKEN=mcp-xxxx
  python run_verifier_eval.py --dataset popqa --limit 500
  RAG_QA_BASE_URL=... RAG_QA_API_KEY=... RAG_QA_MODEL=... \
    python run_verifier_eval.py --dataset popqa --limit 500 --scorers heuristic,llm
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
from bench_http import post_json, validated_url  # noqa: E402

BENCH_DIR = SCRIPTS_DIR.parent / "data" / "benchmarks"
RESULTS_DIR = SCRIPTS_DIR.parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

STOPWORDS = {"the", "a", "an", "of", "in", "on", "at", "to", "for", "and", "or",
             "is", "are", "was", "were", "what", "which", "who", "whom", "how",
             "did", "do", "does", "by", "with", "from", "as", "it", "its"}

LLM_RUBRIC_PROMPT = (
    "You are a retrieval relevance verifier. Given a QUESTION and a PASSAGE, "
    "score the passage's usefulness for answering the question on a 0-8 integer scale:\n"
    "topic relevance 0-3, scenario/entity match 0-2, evidence support 0-3.\n"
    "Reply with ONLY the integer score.\n\nQuestion: {q}\n\nPassage: {p}\n\nScore:")


def content_score_0_8(query: str, chunk: str) -> int:
    """系统内容验证 0-8 rubric 启发式（与 experience_service 同构的词面版）.

    topic 0-3 查询核心词覆盖 · scenario 0-2 专名命中 · evidence 0-3 覆盖度证据分
    """
    q_words = [w for w in re.findall(r"[a-z0-9]+", query.lower()) if w not in STOPWORDS]
    c_words = set(re.findall(r"[a-z0-9]+", chunk.lower()))
    if not q_words:
        return 0
    topic_cov = sum(1 for w in q_words if w in c_words) / len(q_words)
    topic = round(topic_cov * 3)
    proper = [w for w in re.findall(r"[A-Z][a-z]+", query) if w.lower() not in STOPWORDS]
    scenario = 2 if proper and all(p.lower() in c_words for p in proper) else \
        (1 if any(p.lower() in c_words for p in proper) else 0)
    evidence = 2 if topic_cov >= 0.6 else (1 if topic_cov >= 0.3 else 0)
    return topic + scenario + evidence


def content_score_llm(query: str, chunk: str, llm_base: str) -> int:
    payload = {"model": os.environ["RAG_QA_MODEL"], "temperature": 0.0,
               "messages": [{"role": "user", "content": LLM_RUBRIC_PROMPT.format(
                   q=query, p=chunk[:1200])}]}
    headers = {"Authorization": f"Bearer {os.environ['RAG_QA_API_KEY']}"}
    resp = post_json(llm_base, "/chat/completions", payload, token="",
                     timeout=60, extra_headers=headers)
    text = resp["choices"][0]["message"]["content"]
    m = re.search(r"[0-8]", text)
    return int(m.group()) if m else 0


def to_class(score: int) -> str:
    return "Correct" if score >= 6 else ("Ambiguous" if score >= 3 else "Incorrect")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="popqa")
    ap.add_argument("--limit", type=int, default=500)
    ap.add_argument("--top-k", type=int, default=8, help="每查询取的 chunk 数（正例+难负例来源）")
    ap.add_argument("--scorers", default="heuristic")
    args = ap.parse_args()

    token = os.environ.get("RAG_BENCH_TOKEN", "")
    if not token:
        print("❌ 缺少 RAG_BENCH_TOKEN")
        return 2
    backend = validated_url(os.environ.get("RAG_BENCH_URL", "http://localhost:8770"))

    scorers = [s.strip() for s in args.scorers.split(",")]
    llm_base = ""
    if "llm" in scorers:
        if not all(os.environ.get(k) for k in
                   ("RAG_QA_BASE_URL", "RAG_QA_API_KEY", "RAG_QA_MODEL")):
            print("⚠ LLM 评分器环境变量不全, 自动降级为仅 heuristic")
            scorers = ["heuristic"]
        else:
            llm_base = validated_url(os.environ["RAG_QA_BASE_URL"])

    samples = [json.loads(l) for l in
               (BENCH_DIR / f"{args.dataset}.jsonl").open(encoding="utf-8") if l.strip()]
    samples = [s for s in samples if s.get("golden_titles")][:args.limit]
    if not samples:
        print(f"❌ {args.dataset} 无 golden_titles 样本（该集不适用本协议）")
        return 2

    rows: dict[str, list[dict]] = {s: [] for s in scorers}
    for i, s in enumerate(samples):
        golden = set(t.lower() for t in s["golden_titles"])
        try:
            resp = post_json(backend, "/api/v1/search/two-stage",
                             {"query": s["question"], "kb_id": "", "stage1_top_k": 20,
                              "stage2_top_k": args.top_k, "score_threshold": 0.0}, token)
        except Exception as e:
            print(f"  [{i}] retrieve failed: {e}")
            continue
        for r in (resp.get("stage2", {}).get("results") or [])[:args.top_k]:
            is_pos = any(g in str(r.get("doc_path", "")).lower() for g in golden)
            chunk = str(r.get("content", ""))[:1500]
            for sc in scorers:
                score = (content_score_0_8(s["question"], chunk) if sc == "heuristic"
                         else content_score_llm(s["question"], chunk, llm_base))
                rows[sc].append({"label": "Correct" if is_pos else "Incorrect",
                                 "score": score, "pred": to_class(score)})
        if (i + 1) % 100 == 0:
            print(f"  [{i+1}/{len(samples)}] chunks scored: {len(rows[scorers[0]])}", flush=True)

    anchors = {"CRAG T5-based (Table 4)": 84.3, "ChatGPT-few-shot": 64.7,
               "ChatGPT-CoT": 62.4, "ChatGPT zero-shot": 58.0}
    report: dict = {
        "dataset": args.dataset, "n_queries": len(samples), "top_k": args.top_k,
        "protocol": "PopQA golden-title proxy labels; >=6 Correct / 3-5 Ambiguous / <=2 Incorrect",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scorers": {}, "crag_table4_anchors": anchors,
    }
    for sc, items in rows.items():
        if not items:
            continue
        acc3 = statistics.mean(1.0 if r["pred"] == r["label"] else 0.0 for r in items)
        acc2 = statistics.mean(
            1.0 if (r["score"] >= 6) == (r["label"] == "Correct") else 0.0 for r in items)
        tp = sum(1 for r in items if r["label"] == "Correct" and r["score"] >= 6)
        fp = sum(1 for r in items if r["label"] != "Correct" and r["score"] >= 6)
        fn = sum(1 for r in items if r["label"] == "Correct" and r["score"] < 6)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        report["scorers"][sc] = {
            "n_chunks": len(items),
            "acc_3class_pct": round(acc3 * 100, 1),
            "acc_binary_pct": round(acc2 * 100, 1),
            "fpr_pct": round(fp / (fp + tp + fn) * 100, 1) if tp + fp + fn else 0.0,
            "correct_precision": round(precision, 3),
            "correct_recall": round(recall, 3),
            "correct_f1": round(2 * precision * recall / (precision + recall), 3)
                          if precision + recall else 0.0,
        }
        print(f"\n[{sc}] {json.dumps(report['scorers'][sc], indent=2)}")

    out = RESULTS_DIR / f"verifier-{args.dataset}.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✓ saved {out}\n对比: acc_3class/acc_binary vs CRAG 锚点 {anchors}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
