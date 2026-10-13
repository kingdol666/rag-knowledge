#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""原始 chat 响应探针（只读诊断）：打印服务端 JSON 全文与 HTTP 状态。

为什么需要：152_mount_probe 走的是 chat_tracks.chat_stream 的解析层，服务端
提前返回（0.2s 空回答）时它只留下 answer=''。本脚本打同一端点，把服务端返回的
**原始** code/error/success 字段打出来，用于区分 503 KB_MCP_DOWN、参数校验失败、
或挂载门禁拒绝。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE))
sys.path.insert(0, str(SUITE / "experiments"))
sys.path.insert(0, str(SUITE / "scripts"))

import chat_tracks  # noqa: E402
import lib  # noqa: E402


def main() -> int:
    qfile = SUITE / "data" / "papers" / "qa_questions.json"
    raw = json.loads(qfile.read_text(encoding="utf-8"))
    questions = raw.get("questions") if isinstance(raw, dict) else raw
    q = next((x for x in questions if str(x.get("id")) == "BQ01"), questions[0])
    spec = chat_tracks.TRACKS["a2"]
    prompt = chat_tracks.build_prompt("a2", q)

    url = f"{lib.WEB}/api/claude/chat"
    payload = {
        "prompt": prompt,
        "cwd": spec["cwd"],
        "engine": "claude",
        "maxTurns": 12,
        "stream": False,
        "mcpMount": "stdio",
    }
    if spec.get("allowed_tools"):
        payload["allowedTools"] = spec["allowed_tools"]
    if spec.get("permission_mode"):
        payload["permissionMode"] = spec["permission_mode"]

    print(f"[raw-chat] POST {url}")
    print(f"[raw-chat] payload keys: {sorted(payload)}  allowedTools={len(payload.get('allowedTools') or [])}")
    try:
        data = lib.http_post(url, payload, timeout=900)
    except Exception as e:  # noqa: BLE001
        print(f"[raw-chat] EXCEPTION {type(e).__name__}: {e}")
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            try:
                body = str(getattr(e, "body", "") or "")
            except Exception:  # noqa: BLE001
                body = ""
        if body:
            print("[raw-chat] error body:", body[:2000])
        else:
            print("[raw-chat] error body: <unavailable>")
        return 1
    if isinstance(data, dict):
        show = {k: v for k, v in data.items() if k not in ("answer", "message")}
        print("[raw-chat] meta:", json.dumps(show, ensure_ascii=False)[:1500])
        ans = str(data.get("answer") or "")
        print(f"[raw-chat] answer[:300]={ans[:300]!r}")
    else:
        print("[raw-chat] raw:", str(data)[:1500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
