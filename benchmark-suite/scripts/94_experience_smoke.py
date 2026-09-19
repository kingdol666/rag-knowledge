#!/usr/bin/env python3
"""Step 4 — 经验总结冒烟测试(无 LLM, 确定性).

1) experience_extract(heuristic, dry_run) 统计候选;
2) experience_extract(heuristic) 写入草稿池;
3) experience_create 手工创建 1 条经验 → experience_search_global 命中验证。
输出 results/experience_smoke.json。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE / "scripts"))

from lib import McpClient  # noqa: E402

KB_NAME = "Papers"
EXP = {"title": "Benchmark smoke: multi-field papers need per-paper probing",
       "scenario": "kbqa-smoke", "category": "tip",
       "problem": "Verifying ingestion of many multi-field papers is error-prone "
                  "if done manually one by one.",
       "solution": "Upload all papers through the official parse chain, then "
                   "probe each paper with its own title terms until the vector "
                   "index answers.",
       "key_lessons": ["Always probe per document after batch ingestion",
                       "Use the official parse chain, never ad-hoc extraction"],
       "tags": ["benchmark", "ingestion", "smoke"]}


def main() -> int:
    mc = McpClient()
    t0 = time.perf_counter()
    dry = mc.call("experience_extract",
                  {"kb_id": KB_NAME, "dry_run": True, "mode": "heuristic"},
                  timeout=300)
    candidates = (dry or {}).get("total_candidates", 0)
    wet = mc.call("experience_extract",
                  {"kb_id": KB_NAME, "dry_run": False, "mode": "heuristic"},
                  timeout=300)
    drafts = (wet or {}).get("drafts_created", 0)
    created = mc.call("experience_create", {"kb_id": KB_NAME, **EXP}, timeout=180)
    exp_id = (created or {}).get("exp_id") or (created or {}).get("id") or ""
    ok_create = bool((created or {}).get("success", exp_id))
    search = mc.call("experience_search_global",
                     {"query": "per-paper probing batch ingestion",
                      "top_k": 5}, timeout=180)
    items = (search or {}).get("results") or (search or {}).get("experiences") or []
    hit = any((exp_id and (it or {}).get("exp_id") == exp_id)
              or EXP["title"] in str((it or {}).get("title", ""))
              for it in items)
    lst = mc.call("experience_list", {"kb_id": KB_NAME}, timeout=120)
    n_list = len((lst or {}).get("experiences") or (lst or {}).get("results") or [])
    mc.close()
    out = {"extract_candidates": candidates, "drafts_created": drafts,
           "create_ok": ok_create, "search_hit": hit, "list_count": n_list,
           "seconds": round(time.perf_counter() - t0, 1)}
    ok = bool(ok_create and hit)
    out["pass"] = ok
    (SUITE / "results" / "experience_smoke.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
