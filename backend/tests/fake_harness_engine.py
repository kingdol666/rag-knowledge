#!/usr/bin/env python3
"""Fake harness engine — 桩可执行文件，用于无凭据环境验证全部引擎适配链。

用法: python fake_harness_engine.py <engine_id> [args...]
- stdin 引擎 (claude/codex/qwen): 从 stdin 读取 prompt
- arg 引擎 (opencode/gemini/copilot/cursor/crush/goose): prompt = 最后一个 argv
- argfile 引擎 (omp/pi): 读取 @<path> 临时文件
- embedded 引擎 (dsh/hermes): 扮演最小 ACP server（initialize/session/new/session/prompt）

输出含 `FAKE-<ID>-OK:<prompt前16字符>` —— 同时证明「引擎被正确拉起」与
「prompt 按该引擎的投递方式送达」。仅输出预制内容，不消耗任何 LLM token。
"""
from __future__ import annotations

import json
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def marker(engine_id: str, prompt: str) -> str:
    return f"FAKE-{engine_id.upper()}-OK:{prompt[:16]}"


def emit(engine_id: str, prompt: str) -> None:
    mid = marker(engine_id, prompt)
    if engine_id == "omp":
        print(json.dumps({"type": "agent_end", "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": mid}]}}))
    elif engine_id == "claude":
        print(json.dumps({"type": "result", "result": mid, "usage": {"x": 1}}))
    elif engine_id == "codex":
        print(json.dumps({"type": "item.completed",
                          "item": {"type": "agent_message", "text": mid}}))
        print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 5}}))
    elif engine_id == "gemini":
        print(json.dumps({"response": mid, "stats": {}}))
    elif engine_id == "copilot":
        print(json.dumps({"response": mid}))
    elif engine_id == "cursor":
        print(json.dumps({"result": mid, "usage": {"a": 1}}))
    elif engine_id == "goose":
        print(json.dumps({"type": "message", "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": mid}]}}))
    elif engine_id == "pi":
        print(json.dumps({"type": "session", "id": "fake"}))
        print(json.dumps({"type": "message_end", "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": mid}]}}))
    else:  # opencode / crush / qwen —— 纯文本 stdout
        print(mid)


def read_prompt_argfile(argv: list[str]) -> str:
    for a in argv:
        if a.startswith("@"):
            with open(a[1:], encoding="utf-8") as f:
                return f.read()
    return ""


def run_acp(engine_id: str) -> None:
    """最小 ACP server：应答 initialize / session/new / session/prompt。"""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(msg, dict) or "id" not in msg or "method" not in msg:
            continue
        mid, method = msg["id"], msg["method"]

        def send(obj):
            sys.stdout.write(json.dumps(obj) + "\n")
            sys.stdout.flush()

        if method == "initialize":
            send({"jsonrpc": "2.0", "id": mid, "result": {"protocolVersion": 1}})
        elif method == "session/new":
            send({"jsonrpc": "2.0", "id": mid, "result": {"sessionId": "fake-sess"}})
        elif method == "session/prompt":
            blocks = (msg.get("params") or {}).get("prompt") or []
            text = "".join(b.get("text", "") for b in blocks if isinstance(b, dict))
            send({"jsonrpc": "2.0", "method": "session/update", "params": {
                "sessionId": "fake-sess",
                "update": {"sessionUpdate": "agent_message_text",
                           "content": {"type": "text", "text": marker(engine_id, text)}}}})
            send({"jsonrpc": "2.0", "id": mid, "result": {"stopReason": "end_turn"}})
        else:
            send({"jsonrpc": "2.0", "id": mid,
                  "result": {"outcome": {"outcome": "cancelled"}}})


def main() -> None:
    engine_id = sys.argv[1] if len(sys.argv) > 1 else "unknown"
    rest = sys.argv[2:]

    if engine_id in ("dsh", "hermes"):
        run_acp(engine_id)
        return

    if engine_id in ("claude", "codex", "qwen"):
        prompt = sys.stdin.read()
    elif engine_id in ("omp", "pi"):
        prompt = read_prompt_argfile(rest)
    else:  # arg 投递：prompt 是最后一个位置参数
        prompt = rest[-1] if rest else ""

    emit(engine_id, prompt)


if __name__ == "__main__":
    main()
