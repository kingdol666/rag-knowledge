#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""MCP 挂载模式对比探针（真实调用，会花钱；默认只跑 1 格）。

为什么需要
----------
2026-10-13 论文终测里 a2 轨出现 `KB_TOOLS_NOT_READY`（0 工具调用）。服务端
`web/server/api/claude/chat.post.ts` 的自动重试只在 **非流式** 生效
（`maxAttempts = (kbEnhanced || requestMcpMount) && !streamMode ? ... : 1`），
而 benchmark 轨走的是 `chat_tracks.chat_stream(..., stream=True)` → 永远
`maxAttempts = 1`，一旦挂载竞态就整格作废。本脚本用同一 harness 分别跑
`sse` / `stdio` 两种挂载，直接看首轮工具面是否含 `mcp__kb-mcp__*`。

判读
----
- `kb_tools > 0`  → 该挂载模式可用；若 sse 为 0 而 stdio > 0，则 benchmark
  轨必须钉 stdio（`RAG_BENCH_MCP_MOUNT=stdio`，已是默认），且流式车道需要
  客户端侧哨兵重试兜底。
- `answer == KB_TOOLS_NOT_READY` → 挂载失败，与论文轨的实际故障同型。

用法（在 benchmark-suite/ 下）
    python scripts/152_mount_probe.py                     # stdio，QK01，a2
    python scripts/152_mount_probe.py --mount sse
    python scripts/152_mount_probe.py --mount stdio --track b --qid BQ01
产出：results/mount_probe.json（逐格原始结果）
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE))
sys.path.insert(0, str(SUITE / "experiments"))

RESULTS = SUITE / "results"


def main() -> int:
    ap = argparse.ArgumentParser(description="kb-mcp 挂载模式对比探针")
    ap.add_argument("--mount", default="stdio", choices=["sse", "stdio"],
                    help="MCP 挂载模式（默认 stdio，与 benchmark 轨默认一致）")
    ap.add_argument("--track", default="a2", choices=["a", "a2", "b", "c"])
    ap.add_argument("--qid", default="QK01")
    ap.add_argument("--max-turns", type=int, default=12)
    ap.add_argument("--timeout", type=float, default=900.0)
    args = ap.parse_args()

    os.environ["RAG_BENCH_MCP_MOUNT"] = args.mount

    import chat_tracks  # noqa: E402

    qfile = SUITE / "data" / "papers" / "qa_questions.json"
    raw = json.loads(qfile.read_text(encoding="utf-8"))
    questions = raw.get("questions") if isinstance(raw, dict) else raw
    by_id = {str(q.get("id") or q.get("qid")): q for q in questions}
    if args.qid not in by_id:
        print(f"[mount-probe] 未知题目 {args.qid}；可用：{sorted(by_id)[:12]}")
        return 2
    question = by_id[args.qid]
    spec = chat_tracks.TRACKS[args.track]

    t0 = time.time()
    row = chat_tracks.run_chat_track(
        args.track, question, max_turns=args.max_turns, timeout_s=int(args.timeout),
    )
    dt = time.time() - t0

    calls = row.get("tool_calls") or []
    names: list[str] = []
    for c in calls:
        name = c.get("name") or c.get("tool") or ""
        if name:
            names.append(str(name))
    kb_tools = sum(1 for n in names if n.startswith("mcp__kb-mcp__") or n.startswith("kb_"))
    answer = str(row.get("answer") or "")
    out = {
        "mount": args.mount,
        "track": args.track,
        "qid": args.qid,
        "cwd": spec.get("cwd"),
        "allowed_tools": spec.get("allowed_tools"),
        "elapsed_s": round(dt, 1),
        "latency_s": row.get("latency_s"),
        "tool_calls": len(names),
        "kb_tool_calls": kb_tools,
        "tool_names": names,
        "error": row.get("error"),
        "sentinel": answer.strip() in ("KB_TOOLS_NOT_READY", "KB_NO_RETRIEVAL"),
        "answer_head": answer[:400],
        "cost_usd": row.get("cost_usd"),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    outfile = RESULTS / "mount_probe.json"
    prev = []
    if outfile.exists():
        try:
            prev = json.loads(outfile.read_text(encoding="utf-8"))
            if not isinstance(prev, list):
                prev = [prev]
        except Exception:
            prev = []
    prev.append(out)
    outfile.write_text(json.dumps(prev, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"[mount-probe] mount={args.mount} track={args.track} {args.qid} "
          f"elapsed={out['elapsed_s']}s tools={len(names)} kb_tools={kb_tools} "
          f"sentinel={out['sentinel']} error={out['error']}")
    print(f"[mount-probe] tool_names={names[:12]}")
    print(f"[mount-probe] answer_head={answer[:200]!r}")
    print(f"[mount-probe] 产出：{outfile}")
    return 0 if kb_tools > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
