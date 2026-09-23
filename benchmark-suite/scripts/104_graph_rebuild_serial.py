#!/usr/bin/env python3
"""L7 图谱串行重建 — 逐库 kb_graph_build(force) 并保活 MCP 进程直到完成.

背景: 并发提交的 force 重建任务卡 running(提交方进程退出疑似带走服务端执行线程),
留下 6 个已删嵌套文档的幽灵 Document 节点。本脚本串行逐库重建, 单个 MCP 长连接,
per-KB 等待「任务非 running」, 全部完成后做全局对账(neo Document 集合 == 五库
当前文档名并集), 不齐则对差库再补一轮。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE / "scripts"))

from lib import McpClient  # noqa: E402

KBs = ["经济与社会", "工程与能源", "生命科学与医学",
       "自然科学与地球科学", "计算机与人工智能"]
PER_KB_TIMEOUT = 1800


def neo_names() -> set:
    from neo4j import GraphDatabase
    drv = GraphDatabase.driver("bolt://127.0.0.1:7687", auth=("neo4j", "123456"))
    with drv.session() as s:
        names = set(x["n"] for x in s.run("MATCH (d:Document) RETURN d.name AS n"))
    drv.close()
    return names


def main() -> int:
    mc = McpClient()
    expected = {}
    for kb in KBs:
        docs = (mc.call("kb_get_documents", {"kb_id": kb}, timeout=180)
                or {}).get("documents") or []
        expected[kb] = {str(x.get("name")) for x in docs}
    union = set().union(*expected.values())

    results = {}
    for kb in KBs:
        t0 = time.time()
        r = mc.call("kb_graph_build", {"kb_id": kb, "force": True}, timeout=300)
        print(f"[submit] {kb}: task={str((r or {}).get('task_id'))[:14]}",
              flush=True)
        ok = False
        while time.time() - t0 < PER_KB_TIMEOUT:
            time.sleep(30)
            st = mc.call("kb_graph_build", {"kb_id": kb, "force": False},
                         timeout=120)
            running = str((st or {}).get("status")) == "running"
            if not running:
                ok = True
                break
        results[kb] = {"submitted_done": ok,
                       "seconds": round(time.time() - t0, 1)}
        print(f"[build-not-running] {kb}: {results[kb]}", flush=True)

    # 全局对账(两轮, 间隔 20s)
    for attempt in range(2):
        neo = neo_names()
        ghosts = sorted(neo - union)
        missing = sorted(union - neo)
        print(f"[reconcile #{attempt}] neo={len(neo)} union={len(union)} "
              f"ghosts={len(ghosts)} missing={len(missing)}", flush=True)
        for g in ghosts[:8]:
            print("   GHOST:", g[:95], flush=True)
        for m in missing[:8]:
            print("   MISSING:", m[:95], flush=True)
        if not ghosts and not missing:
            break
        if attempt == 0 and (ghosts or missing):
            bad = [kb for kb in KBs
                   if set(n for n in ghosts if _in_kb(n, expected[kb]))
                   or set(n for n in missing if n in expected[kb])]
            for kb in bad:
                t0 = time.time()
                mc.call("kb_graph_build", {"kb_id": kb, "force": True},
                        timeout=300)
                while time.time() - t0 < PER_KB_TIMEOUT:
                    time.sleep(30)
                    st = mc.call("kb_graph_build", {"kb_id": kb, "force": False},
                                 timeout=120)
                    if str((st or {}).get("status")) != "running":
                        break
                print(f"[re-rebuild] {kb} done t={time.time()-t0:.0f}s",
                      flush=True)
        time.sleep(20)

    results["reconcile"] = {"ghosts": len(ghosts), "missing": len(missing)}
    (SUITE / "results" / "r2_graph_rebuild.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = not ghosts and not missing
    print(f"[done] graph rebuild {'CLEAN' if ok else 'DIRTY'}", flush=True)
    mc.close()
    return 0 if ok else 1


def _in_kb(n, kb_names: set) -> bool:
    """幽灵名归属判定: 文档名含 field__id slug, 与该库现存文档共享论文前缀即视作本库."""
    for name in kb_names:
        head = name.split(" (part")[0]
        if n.startswith(head[:40]):
            return True
    return False


if __name__ == "__main__":
    sys.exit(main())
