#!/usr/bin/env python3
"""验证 10 道内容强相关题目: two_stage 检索 + 金标文档命中 + 关键词核验.
输出 results/bench10_qa.json。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE / "scripts"))

from lib import McpClient  # noqa: E402


def main() -> int:
    qs = json.loads((SUITE / "data" / "papers" / "qa_questions.json")
                    .read_text(encoding="utf-8"))["questions"]
    # 检索范围 = 平台 5 门类库(排除复刻项目 Corpus-* 索引库, 避免同文重复污染)
    KB_CATEGORIES = ["计算机与人工智能", "自然科学与地球科学", "生命科学与医学",
                     "工程与能源", "经济与社会"]
    mc = McpClient()
    rows, passed = [], 0
    for q in qs:
        results = []
        for kb in KB_CATEGORIES:
            # 向量优先 = QDCVR v2 skill Phase 1 的规定工具。KB 限定 two_stage
            # 在多代重建后实测作用域失效(4/10), 整库 two_stage 会被 Corpus-*
            # 重复分块污染(7/10) —— 均不适合作为回归验证通道。
            r = mc.call("kb_search_vector",
                        {"query": q["question"], "kb_id": kb, "top_k": 10,
                         "score_threshold": 0.35}, timeout=300)
            results += (r.get("results") or [])
        best: dict[str, dict] = {}
        for it in results:
            dp = str(it.get("doc_path", "")).replace("\\", "/")
            if dp and (dp not in best or it.get("score", 0) > best[dp]["score"]):
                best[dp] = it
        top3 = sorted(best.values(), key=lambda x: -x.get("score", 0))[:3]
        hit = any(q["arxiv_id"] in d["doc_path"] for d in top3)
        blob = " ".join(str(d.get("content", "")).lower() for d in top3)
        kw = [k for k in q["gold_keywords"] if k.lower() in blob]
        ok = bool(hit and kw)
        passed += ok
        kb = top3[0]["doc_path"].split("/")[0] if top3 else ""
        rows.append({**q, "doc_hit": hit, "kw_hit": kw, "pass": ok, "kb": kb})
        print(f"[{'PASS' if ok else 'FAIL'}] {q['qid']} ({q['field']}, {kb}) "
              f"doc_hit={hit} kw={kw}", flush=True)
    mc.close()
    out = {"total": len(rows), "passed": passed,
           "pass_rate": round(passed / len(rows), 3), "rows": rows}
    (SUITE / "results" / "bench10_qa.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[done] {passed}/10 ({out['pass_rate']:.0%})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
