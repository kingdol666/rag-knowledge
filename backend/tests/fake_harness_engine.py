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
import os
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
    """最小 ACP server：应答 initialize / session/new / session/prompt。

    额外做两件真实 agent 会做的事，用来给驱动器上强度：
      * 用规范里的 `agent_message_chunk` 推送文本（不是臆造的 agent_message_text）
      * 发一次 `session/request_permission`，并把客户端的应答原样记到
        `$FAKE_HARNESS_PERM_LOG`（若设置），供单测断言「拒绝」语义正确
    """
    perm_log = os.environ.get("FAKE_HARNESS_PERM_LOG", "")
    pending_perm: list[str] = []

    def send(obj):
        sys.stdout.write(json.dumps(obj) + "\n")
        sys.stdout.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(msg, dict):
            continue

        # 客户端对权限请求的应答（没有 method，id 是 perm-1）
        if "method" not in msg and msg.get("id") == "perm-1":
            if perm_log:
                with open(perm_log, "w", encoding="utf-8") as f:
                    f.write(json.dumps(msg.get("result") or msg.get("error") or {},
                                       ensure_ascii=False))
            continue

        if "id" not in msg or "method" not in msg:
            continue
        mid, method = msg["id"], msg["method"]

        if method == "initialize":
            send({"jsonrpc": "2.0", "id": mid,
                  "result": {"protocolVersion": 1,
                             "agentCapabilities": {},
                             "agentInfo": {"name": "fake-acp-agent", "version": "1.0"}}})
        elif method == "session/new":
            # cwd 必须是绝对路径（ACP v1 session-setup 契约）
            if not os.path.isabs((msg.get("params") or {}).get("cwd") or ""):
                send({"jsonrpc": "2.0", "id": mid,
                      "error": {"code": -32602, "message": "cwd must be absolute"}})
                continue
            send({"jsonrpc": "2.0", "id": mid, "result": {"sessionId": "fake-sess"}})
        elif method == "session/prompt":
            blocks = (msg.get("params") or {}).get("prompt") or []
            text = "".join(b.get("text", "") for b in blocks if isinstance(b, dict))
            # ACP v1 的标准判别值是 agent_message_chunk（不是 agent_message_text）。
            # 桩必须说协议里真实存在的值，否则单测会替一个有 bug 的解析器背书。
            send({"jsonrpc": "2.0", "method": "session/update", "params": {
                "sessionId": "fake-sess",
                "update": {"sessionUpdate": "agent_message_chunk",
                           "content": {"type": "text", "text": marker(engine_id, text)}}}})
            # 一次权限请求：客户端必须从 options 里选 reject_* 而不是一律 cancelled
            send({"jsonrpc": "2.0", "id": "perm-1", "method": "session/request_permission",
                  "params": {"sessionId": "fake-sess",
                             "toolCall": {"toolCallId": "tc-1", "title": "write file"},
                             "options": [
                                 {"optionId": "allow-1", "name": "Allow once", "kind": "allow_once"},
                                 {"optionId": "reject-1", "name": "Reject once", "kind": "reject_once"},
                             ]}})
            pending_perm.append("perm-1")
            # 回合正常结束；客户端对 perm-1 的应答会在下一轮循环里被记录
            send({"jsonrpc": "2.0", "id": mid, "result": {"stopReason": "end_turn"}})
        else:
            # 未实现的服务端方法 → 标准 method-not-found（不是 permission 应答形状）
            send({"jsonrpc": "2.0", "id": mid,
                  "error": {"code": -32601, "message": f"not implemented: {method}"}})


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
