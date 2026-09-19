#!/usr/bin/env python3
"""Step 3 — 内容检索 QA 测试: 每篇论文 1 个问题(共 50), 金标文档命中 + 关键词核验.

题目即本文件逻辑(单一事实源): 经典 6 篇用内容问题(FAMOUS 表, 按 arXiv id 匹配),
其余用标题问题(关键词取自标题, 必然在文内)。确定性判定, 不用 LLM:
  pass = 金标文档进 two_stage 前 3 且 top-3 内容含 ≥1 个关键词
输出 results/retrieval_qa.json。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE / "scripts"))

from lib import McpClient  # noqa: E402

PAPERS = SUITE / "data" / "papers"

# 经典篇目(按 arXiv id 前缀): 内容问题(关键词必须在论文正文出现)
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


def build_questions() -> list[dict]:
    manifest = json.loads((PAPERS / "manifest.json").read_text(encoding="utf-8"))
    out = []
    for i, p in enumerate(manifest["papers"], 1):
        aid = p["arxiv_id"].split("v")[0]
        if aid in FAMOUS:
            q, kws = FAMOUS[aid]
        else:
            words = [w for w in re.findall(r"[A-Za-z]{5,}", p["title"])][:4]
            q = f"What does the paper titled '{p['title']}' study?"
            kws = [w.lower() for w in words]
        out.append({"qid": f"Q{i:02d}", "field": p["field"], "arxiv_id": aid,
                    "question": q, "keywords": kws,
                    "expect_prefix": f"Papers/{p['field']}__{aid}__"})
    return out


def main() -> int:
    questions = build_questions()
    mc = McpClient()
    rows, passed = [], 0
    for q in questions:
        r = mc.call("kb_search_two_stage",
                    {"query": q["question"], "kb_id": "", "stage1_top_k": 20,
                     "stage2_top_k": 5, "score_threshold": 0.30,
                     "balance_kbs": True}, timeout=300)
        results = (r or {}).get("stage2", {}).get("results") or []
        best: dict[str, dict] = {}
        for item in results:
            dp = str(item.get("doc_path", "")).replace("\\", "/")
            if dp and (dp not in best or item.get("score", 0) > best[dp]["score"]):
                best[dp] = item
        top3 = sorted(best.values(), key=lambda x: -x.get("score", 0))[:3]
        hit = any(d["doc_path"].startswith(q["expect_prefix"]) for d in top3)
        blob = " ".join(str(d.get("content", "")).lower() for d in top3)
        kw_hit = [k for k in q["keywords"] if k.lower() in blob]
        ok = bool(hit and kw_hit)
        passed += ok
        rows.append({**q, "doc_hit": hit, "keywords_hit": kw_hit,
                     "top_docs": [d["doc_path"] for d in top3], "pass": ok})
        print(f"[{'PASS' if ok else 'FAIL'}] {q['qid']} ({q['field']}) "
              f"doc_hit={hit} kw={kw_hit}", flush=True)
    mc.close()
    out = {"total": len(rows), "passed": passed,
           "pass_rate": round(passed / len(rows), 3), "rows": rows}
    (SUITE / "results" / "retrieval_qa.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[done] {passed}/{len(rows)} passed ({out['pass_rate']:.0%})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
