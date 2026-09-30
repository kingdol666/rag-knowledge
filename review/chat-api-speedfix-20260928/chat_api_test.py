#!/usr/bin/env python3
"""chat API kbEnhanced 测速复测 (2026-09-28 修复后) — 同题对比 215.5s 基线.

修复内容: kb-instruction.ts 工具原生快速路径 + KB_RETRIEVAL_TOOLS 预授权只读
MCP 工具(免 permission 往返) + kb 路径默认 medium 推理 + 全局陈旧 KB skill 删除.
基线: review/librarian-fast-skilltest-v2/cell_chat_api.json (wall 215.5s).
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SUITE = REPO / "benchmark-suite"
sys.path.insert(0, str(SUITE / "scripts"))
sys.path.insert(0, str(SUITE / "experiments"))

from chat_tracks import CHAT, _token, _deny  # noqa: E402
from dev_smoke import OPENER  # noqa: E402
from lib import login_refresh  # noqa: E402

# web 刚重启: 旧 loop-auth token 会静默返回空目录(kb_list 0 库), 先强制重登
login_refresh()

QUESTION = ("CoRoT 卫星的系外行星计划有哪些科学目标？它何时开始科学观测、任务延长到"
            "什么时候？截至 2010 年夏共收集了多少条光变曲线？为什么 CoRoT-7b 这类超级"
            "地球只能在较亮恒星的光变曲线中发现？")

payload = {"prompt": QUESTION, "engine": "claude", "kbEnhanced": True,
           "kbIds": ["1e6199ea-f380-44e2-94fc-d431f0f9bb6b"],
           "maxTurns": 30}

req = urllib.request.Request(CHAT, method="POST",
                             data=json.dumps(payload).encode("utf-8"))
req.add_header("Content-Type", "application/json")
req.add_header("Accept", "text/event-stream")
req.add_header("Authorization", f"Bearer {_token()}")

t0 = time.perf_counter()
tools: list[str] = []
texts: list[str] = []
timeline: list[dict] = []
perm = {"ok": 0, "denied": 0}

with OPENER.open(req, timeout=600) as resp:
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
        mtype = msg.get("type")
        if cur == "permission_request" or msg.get("type") == "permission_request" \
                or msg.get("type") == "can_use_tool":
            tool = msg.get("toolName") or msg.get("tool_name") or ""
            ok = tool.startswith("mcp__kb-mcp__") or tool.startswith("mcp__plugin_rag-knowledge")
            sid = msg.get("sessionId") or msg.get("session_id") or ""
            tid = msg.get("toolUseId") or msg.get("tool_use_id") or ""
            if ok:
                perm["ok"] += 1
                preq = urllib.request.Request(
                    CHAT.replace("/chat", "/permission"), method="POST",
                    data=json.dumps({"sessionId": sid, "toolUseId": tid,
                                     "behavior": "allow"}).encode("utf-8"))
                preq.add_header("Content-Type", "application/json")
                preq.add_header("Authorization", f"Bearer {_token()}")
                try:
                    OPENER.open(preq, timeout=30).read()
                    timeline.append({"t": round(time.perf_counter() - t0, 1),
                                     "e": "permission_allow", "tool": tool})
                except Exception as exc:
                    timeline.append({"t": round(time.perf_counter() - t0, 1),
                                     "e": "permission_allow_failed", "tool": tool,
                                     "err": str(exc)[:80]})
            else:
                perm["denied"] += 1
                _deny(_token(), sid, tid)
                timeline.append({"t": round(time.perf_counter() - t0, 1),
                                 "e": "permission_deny", "tool": tool})
            cur = ""
            continue
        if mtype == "system" and msg.get("subtype") == "init":
            timeline.append({"t": round(time.perf_counter() - t0, 1), "e": "init",
                             "model": str(msg.get("model"))[:40]})
        elif mtype == "assistant":
            for blk in (msg.get("message") or {}).get("content", []):
                if blk.get("type") == "tool_use":
                    inp = json.dumps(blk.get("input"), ensure_ascii=False)[:140]
                    tools.append(blk.get("name"))
                    timeline.append({"t": round(time.perf_counter() - t0, 1),
                                     "e": "tool", "name": blk.get("name"), "input": inp})
                elif blk.get("type") == "text" and (blk.get("text") or "").strip():
                    texts.append(blk["text"])
                    timeline.append({"t": round(time.perf_counter() - t0, 1),
                                     "e": "text", "len": len(blk["text"])})
        elif mtype == "result":
            usage = msg.get("usage") or {}
            out = {"wall_s": round(time.perf_counter() - t0, 1), "tools": tools,
                   "timeline": timeline, "perm": perm,
                   "answer": (texts[-1] if texts else str(msg.get("result", ""))),
                   "tokens": {"input": usage.get("input_tokens"),
                              "output": usage.get("output_tokens"),
                              "cache_read": usage.get("cache_read_input_tokens")},
                   "cost": msg.get("total_cost_usd"),
                   "num_turns": msg.get("num_turns"), "is_error": msg.get("is_error")}
            outpath = REPO / "review" / "chat-api-speedfix-20260928" / "cell_chat_api.json"
            outpath.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                               encoding="utf-8")
            print("WALL", out["wall_s"], "s · turns", out["num_turns"],
                  "· perm", perm, "· tools:", tools)
            print("tokens", out["tokens"], "cost", out["cost"])
            print("ANSWER_HEAD:", (out["answer"] or "")[:400])
            break
