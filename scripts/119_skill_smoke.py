#!/usr/bin/env python3
"""KB skill 冒烟测试 — 逐个 skill 调用其主用 MCP 工具（只读）。

目的：证明"每个知识库 skill 都能真正调用并按需求执行"，而不做任何写操作、
不调用被测系统的对外问答 API。所有调用走 kb-mcp 的 **MCP stdio 通道**
（与 IDE 里的 mcp__kb-mcp__* 同一通道），因此结果可代表 skill 的实际执行环境。

只读：本脚本绝不调用 create/update/delete/move/index/reindex/parse 等写工具。

用法（仓库根）：
    python scripts/119_skill_smoke.py
    python scripts/119_skill_smoke.py --only knowledgebase-search,soul
    python scripts/119_skill_smoke.py --out benchmark-suite/results/SKILL-SMOKE.md
退出码：有失败 → 1；否则 0。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "benchmark-suite" / "scripts"))  # lib.py lives here
from lib import McpClient  # noqa: E402

# skill → [(只读工具, 参数, 这一步验证什么)]
PLAN: dict[str, list[tuple[str, dict, str]]] = {
    "knowledgebase": [
        ("kb_list", {"lightweight": True}, "调度器：列库（catalog）"),
    ],
    "knowledgebase-list": [
        ("kb_get_documents", {"lightweight": True, "kb_id": "{kb}"}, "列文档（轻量）"),
    ],
    "knowledgebase-search": [
        ("kb_search_vector", {"query": "precipitation extremes climate change",
                              "top_k": 3, "score_threshold": 0.0,
                              "balance_kbs": True}, "向量召回（Phase 1 主工具）"),
        ("kb_search_stats", {}, "向量索引统计"),
        ("kb_search", {"query": "gene ontology", "top_k": 3}, "元数据检索"),
    ],
    "knowledgebase-ingest": [
        ("kb_get_documents", {"lightweight": True, "kb_id": "{kb}"}, "入库后读回（A7 终检面）"),
        ("fs_get_tree", {"max_depth": 1}, "目录树（入库落盘面）"),
    ],
    "knowledgebase-organize": [
        ("kb_find_duplicates", {"kb_id": "{kb}"}, "重复检测（O 层审计面）"),
    ],
    "knowledgebase-manage": [
        ("kb_get_documents", {"lightweight": True, "kb_id": "{kb}"}, "文档清单（移动/改名前置）"),
    ],
    "knowledgebase-verify": [
        ("kb_search_stats", {}, "三源一致性·向量覆盖"),
        ("kb_graph_stats", {}, "三源一致性·图谱"),
    ],
    "knowledgebase-graph": [
        ("kb_graph_stats", {}, "图谱统计"),
        ("kb_graph_central_documents", {"kb_id": "{kb}"}, "中心文档"),
    ],
    "knowledgebase-experience": [
        ("experience_search_global", {"query": "index stale", "top_k": 3}, "经验检索"),
        ("experience_dashboard", {"kb_id": "{kb}"}, "经验看板"),
    ],
    "knowledgebase-experience-summarize": [
        ("experience_list", {"kb_id": "{kb}"}, "经验清单（汇总前置）"),
    ],
    "knowledgebase-batch": [
        ("kb_list", {"lightweight": True}, "批量操作目标枚举"),
    ],
    "knowledgebase-init": [
        ("kb_project_status", {"scope": "runtime"}, "项目运行状态"),
    ],
    "knowledgebase-update": [
        ("kb_project_status", {"show_version": True}, "版本检查"),
    ],
    "soul": [
        ("soul_list", {}, "人格清单"),
    ],
    "soul-rag": [
        ("soul_list", {}, "人格清单（检索+人格入口）"),
    ],
    "butian": [
        ("kb_list", {"lightweight": True}, "蒸馏产物落地为库"),
    ],
    "knowledgebase-graph-alt": [],   # placeholder removed below
}
PLAN.pop("knowledgebase-graph-alt", None)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--timeout", type=float, default=120.0)
    args = ap.parse_args()

    only = {s.strip() for s in args.only.split(",") if s.strip()}
    plan = {k: v for k, v in PLAN.items() if not only or k in only}

    mc = McpClient()
    rows = []
    fails = 0
    # Several tools require a non-empty kb_id BY DESIGN (you must name a KB).
    # Resolve a real one so the smoke test exercises them correctly.
    kb = ""
    try:
        cat = mc.call("kb_list", {"lightweight": True}, timeout=60)
        cands = cat.get("catalog") or []
        kb = next((str(k.get("kb_id") or k.get("name")) for k in cands
                   if k.get("doc_count")), "")
        if not kb and cands:
            kb = str(cands[0].get("kb_id") or cands[0].get("name") or "")
    except Exception as e:  # noqa: BLE001
        print(f"[smoke] 无法解析 kb_id: {type(e).__name__}")
    print(f"[smoke] kb_id = {kb!r} · 覆盖 {len(plan)} 个 skill")
    try:
        for skill, steps in plan.items():
            for tool, payload, why in steps:
                payload = {k: (kb if v == "{kb}" else v) for k, v in payload.items()}
                t0 = time.perf_counter()
                ok, detail, n = True, "", None
                try:
                    r = mc.call(tool, payload, timeout=args.timeout)
                    if isinstance(r, dict):
                        n = len(r) if len(r) < 10 else f"{len(r)} keys"
                        if r.get("error"):
                            ok, detail = False, str(r["error"])[:120]
                    else:
                        n = type(r).__name__
                except Exception as e:  # noqa: BLE001
                    ok, detail = False, f"{type(e).__name__}: {str(e)[:140]}"
                ms = round((time.perf_counter() - t0) * 1000)
                rows.append({"skill": skill, "tool": tool, "ok": ok,
                             "ms": ms, "shape": n, "why": why, "detail": detail})
                fails += 0 if ok else 1
                print(f"  {'✓' if ok else '✗'} {skill:<34} {tool:<30} "
                      f"{ms:>6}ms {detail}")
    finally:
        mc.close()

    L = ["# KB Skill 冒烟测试报告（只读 · 经 kb-mcp MCP stdio 通道）", "",
         f"- 覆盖 skill：**{len(plan)}** · 调用：**{len(rows)}** 次 · "
         f"失败：**{fails}**",
         "- 全部为**只读**调用；未做任何写操作；未调用被测系统的对外问答 API。", "",
         "| skill | 工具 | 结果 | 耗时 ms | 返回 | 验证点 |",
         "|---|---|:--:|---:|---|---|"]
    for r in rows:
        L.append(f"| `{r['skill']}` | `{r['tool']}` | {'✅' if r['ok'] else '❌'} | "
                 f"{r['ms']} | {r['shape']} | {r['why']}"
                 + (f" · {r['detail']}" if r['detail'] else "") + " |")
    md = "\n".join(L)
    print("\n" + md)
    if args.out:
        out = Path(args.out)
        if not out.is_absolute():
            out = REPO / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
        print(f"\n[smoke] → {out}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
