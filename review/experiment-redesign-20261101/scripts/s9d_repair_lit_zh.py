# -*- coding: utf-8 -*-
"""修复 MD语料-文学-中文 的向量索引（本会话开始前该库向量已丢失——0 命中 @threshold 0），
并验证检索恢复。只动这一个 KB；异步 reindex 轮询到 done（S2 断链同根因：异步未等待）。"""
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

KBMCP_DIR = Path(r"D:/codes/ClaudeGPT/rag_project/rag-knowledge/kb-mcp")
STDIO_CMD = ["uv", "run", "--no-sync", "--directory", str(KBMCP_DIR), "python", str(KBMCP_DIR / "server.py")]
KB_LIT_ZH = "3d5e65f7-5bd1-4fa3-8e36-cd2b015f75cc"
PROBE = "贾雨村靠什么接济进京赶考？"


def cj(res):
    try:
        return json.loads(res.content[0].text)
    except Exception:
        return {"_raw": [getattr(c, "text", str(c)) for c in res.content]}


async def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    async with stdio_client(StdioServerParameters(command=STDIO_CMD[0], args=STDIO_CMD[1:])) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            d = cj(await s.call_tool("kb_reindex", {"kb_id": KB_LIT_ZH, "force": True}))
            print("reindex submitted:", {k: d.get(k) for k in ("success", "task_id", "status")})
            tid = d.get("task_id")
            if tid:
                for i in range(90):
                    await asyncio.sleep(4)
                    ts = cj(await s.call_tool("kb_task_status", {"task_id": tid}))
                    st = str(ts.get("status", "")).lower()
                    if st in ("done", "completed", "success", "finished"):
                        print(f"reindex done after ~{i*4}s")
                        break
                    if st in ("error", "failed"):
                        print("reindex FAILED:", ts)
                        sys.exit(1)
                else:
                    print("reindex timeout (180s) — continuing to probe anyway")
            ok = False
            for attempt in range(20):
                await asyncio.sleep(5)
                d = cj(await s.call_tool("kb_search_vector", {
                    "query": PROBE, "kb_id": KB_LIT_ZH, "top_k": 5,
                    "score_threshold": 0.35, "slim": True}))
                res = d.get("results") or []
                if res:
                    ok = True
                    print(f"search verified: {len(res)} hits @0.35, top={res[0].get('score')}")
                    for h in res[:3]:
                        print("   ", h.get("score"), str(h.get("doc_path", ""))[:50])
                    break
                print(f"probe {attempt + 1}: 0 hits, waiting for index settle...")
            print("REPAIR_" + ("PASS" if ok else "FAIL"))


if __name__ == "__main__":
    asyncio.run(main())
