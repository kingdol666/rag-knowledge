#!/usr/bin/env python
"""MCP 工具面探针（只读）：按 mcpMount 比对会话里真正可见的 mcp__* 工具。

背景（2026-10-13）：论文终测三轨跑到 a2 第一格就返回字面量 `KB_TOOLS_NOT_READY`
且 0 工具调用。这个哨兵既可能是「SSE 异步挂载输给首个工具轮」，也可能是
「stdio 挂载静默失败（uv 不在 PATH / KB_MCP_SERVERS 端口不通）」。
本探针直接问模型「你现在能调用的 mcp__ 工具名有哪些」，把**工具面**本身
变成可测量的东西，而不是靠哨兵反推。

用法:
    python scripts/152_mcp_toolface_probe.py
    python scripts/152_mcp_toolface_probe.py --mount stdio --mount sse
    python scripts/152_mcp_toolface_probe.py --show-raw
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent / "experiments"))

from chat_tracks import CHAT, OPENER, _token, guard_url  # noqa: E402

PROMPT = ("List every tool name you can currently call whose name starts with `mcp__`. "
          "Output ONLY those names, one per line, no commentary. "
          "If there are none, output exactly NONE.")

# 平台轨 a2 的工具白名单形态（与 chat_tracks.py:132 同源）
A2_TOOLS = ["mcp__kb-mcp__" + n for n in
            ("backend_status", "kb_list", "kb_search_vector", "kb_search",
             "kb_search_two_stage", "kb_search_stats", "kb_doc_read",
             "kb_get_documents", "kb_doc_get_by_tag", "kb_laya_judge",
             "kb_graph_stats", "kb_graph_search", "fs_get_tree", "fs_get_children")]


def ask(mount: str | None, allowed: list[str] | None, timeout: int,
        show_raw: bool = False) -> dict:
    payload = {"prompt": PROMPT,
               "cwd": str(__import__("pathlib").Path(__file__).resolve().parents[1]
                          / "data" / "corpus_md"),
               "engine": "claude", "maxTurns": 3, "stream": True}
    if mount:
        payload["mcpMount"] = mount
    if allowed is not None:
        payload["allowedTools"] = allowed
    guard_url(CHAT)
    req = urllib.request.Request(CHAT, method="POST",
                                 data=json.dumps(payload).encode("utf-8"))
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "text/event-stream")
    req.add_header("Authorization", f"Bearer {_token()}")

    t0 = time.perf_counter()
    texts: list[str] = []
    init_tools: list[str] = []
    result: dict = {}
    with OPENER.open(req, timeout=timeout) as resp:
        cur = ""
        for raw in resp:
            line = raw.decode("utf-8", "replace").strip()
            if line.startswith("event:"):
                cur = line[6:].strip()
                continue
            if not line.startswith("data:"):
                continue
            try:
                msg = json.loads(line[5:].strip())
            except Exception:
                continue
            cur = ""
            if msg.get("type") == "system" and msg.get("subtype") == "init":
                init_tools = [str(t) for t in (msg.get("tools") or [])]
            elif msg.get("type") == "assistant":
                for blk in (msg.get("message") or {}).get("content", []):
                    if blk.get("type") == "text" and (blk.get("text") or "").strip():
                        texts.append(blk["text"])
            elif msg.get("type") == "result":
                result = msg
                break
    answer = (texts[-1] if texts else str(result.get("result", "")))
    if show_raw:
        print("[raw answer]", answer[:400].replace("\n", " | "))
        print("[init tools]", len(init_tools), init_tools[:6])
    names = [ln.strip().strip("`-* ") for ln in answer.splitlines() if "mcp__" in ln]
    return {"mount": mount or "(server default)",
            "kb_tools_in_toolface": len(names),
            "sample": names[:4],
            "sentinel": "KB_TOOLS_NOT_READY" in answer,
            "seconds": round(time.perf_counter() - t0, 1),
            "is_error": result.get("is_error"),
            "init_tool_count": len(init_tools)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mount", action="append",
                    help="待测挂载（可重复）：stdio / sse；缺省测 server 默认 + stdio")
    ap.add_argument("--no-allowed", action="store_true",
                    help="不传 allowedTools（对照：很多 harness 就是这么调的）")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--show-raw", action="store_true")
    args = ap.parse_args()

    mounts: list[str | None] = args.mount if args.mount else [None, "stdio"]
    out = {"probe": "mcp tool face", "allowed_tools_passed": not args.no_allowed,
           "runs": []}
    allowed = None if args.no_allowed else A2_TOOLS
    for m in mounts:
        try:
            out["runs"].append(ask(m, allowed, args.timeout, args.show_raw))
        except Exception as e:  # noqa: BLE001
            out["runs"].append({"mount": m or "(default)", "exception":
                                f"{type(e).__name__}: {e}"})
    best = max((r.get("kb_tools_in_toolface") or 0) for r in out["runs"])
    out["verdict"] = (f"工具面可用：最佳挂载可见 {best} 个 kb 工具" if best
                      else "工具面为空：任何挂载下会话都没有 mcp__ 工具（挂载链路故障）")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if best else 1


if __name__ == "__main__":
    sys.exit(main())
