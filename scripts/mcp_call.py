#!/usr/bin/env python3
"""mcp_call — 通过官方 MCP SSE 传输调用 kb-mcp 工具（常驻服务已启动则直接连接）。

用法：
  python scripts/mcp_call.py kb_list '{"lightweight": true}'
  python scripts/mcp_call.py kb_search_vector '{"query": "BERT 分词器", "top_k": 5}'
  python scripts/mcp_call.py --tools            # 列出全部工具名

协议：GET /sse 拿 endpoint → POST JSON-RPC → 从 SSE 流读同 id 响应。
输出预算：默认截断到 4000 字符（头部 3200 + 尾部 600 + 截断提示），防止大载荷
（20k 文档正文 / 30 条向量命中）灌爆 agent 上下文——这正是检索"看起来慢"的
根因：检索本身秒级，慢的是 subagent 反复消化巨量工具输出的 LLM 轮次。
`--raw` 取完整输出；`--max-chars N` 自定义预算。
安全边界：HTTP 连接在构造时绑定字面量回环主机 127.0.0.1:8000，路径仅用于
本机 MCP 服务，无任何可配置主机入口（SSRF 防护）。
本 helper 只是传输层；业务语义（先检索→再读→判卷→早退）由调用方 agent 按
skill 契约自行编排。
"""
from __future__ import annotations

import http.client
import json
import queue
import sys
import threading
import time

PROTOCOL_VERSION = "2024-11-05"
DEFAULT_TIMEOUT = 660.0  # kb_laya_judge 机器级锁可能排队（另一会话判卷中）
# 主机/端口在连接构造处字面量固定——URL 路径无法改变目标（SSRF 防护）
HOST, PORT = "127.0.0.1", 8000


def sse_reader(q: queue.Queue) -> None:
    conn = http.client.HTTPConnection(HOST, PORT, timeout=600)
    conn.request("GET", "/sse")
    resp = conn.getresponse()
    event = None
    while True:
        line = resp.readline()
        if not line:
            break
        line = line.decode("utf-8", "replace").rstrip("\r\n")
        if line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            q.put((event or "message", line[5:].strip()))


def main() -> int:
    args = sys.argv[1:]
    list_tools = "--tools" in args
    raw_out = "--raw" in args
    max_chars = 4000
    if "--max-chars" in args:
        i = args.index("--max-chars")
        if i + 1 < len(args):
            max_chars = max(200, int(args[i + 1]))
            del args[i:i + 2]
    args = [a for a in args if a != "--raw"]
    if list_tools:
        args = args[: args.index("--tools")]
    if len(args) < 1 and not list_tools:
        print(__doc__)
        return 2
    tool = args[0] if args else None
    raw_args = args[1] if len(args) > 1 else None
    if raw_args is not None and raw_args.startswith("@"):
        with open(raw_args[1:], encoding="utf-8") as f:  # @file: payload exceeds argv limits
            raw_args = f.read()
    tool_args = json.loads(raw_args) if raw_args is not None else {}

    q: queue.Queue = queue.Queue()
    threading.Thread(target=sse_reader, args=(q,), daemon=True).start()

    endpoint = None
    deadline = time.time() + 30
    while endpoint is None and time.time() < deadline:
        try:
            ev, data = q.get(timeout=1)
        except queue.Empty:
            continue
        if ev == "endpoint":
            endpoint = data if data.startswith("/") else f"/{data}"
    if endpoint is None:
        print("ERROR: no endpoint event from /sse", file=sys.stderr)
        return 1

    # POST 通道：独立连接，主机字面量固定，路径仅接受 /messages/ 形态
    if not endpoint.startswith("/messages/"):
        print(f"ERROR: unexpected endpoint {endpoint!r}", file=sys.stderr)
        return 1
    post_conn = http.client.HTTPConnection(HOST, PORT, timeout=60)

    def post(payload: dict) -> None:
        body = json.dumps(payload)  # ensure_ascii=True: http.client encodes str bodies latin-1 only
        post_conn.request("POST", endpoint, body=body,
                          headers={"Content-Type": "application/json"})
        post_conn.getresponse().read()

    def wait_response(want_id: int, timeout: float) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                ev, data = q.get(timeout=1)
            except queue.Empty:
                continue
            if ev != "message":
                continue
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                continue
            if msg.get("id") == want_id:
                return msg
        raise TimeoutError(f"no response for id={want_id} in {timeout:.0f}s")

    post({"jsonrpc": "2.0", "id": 1, "method": "initialize",
          "params": {"protocolVersion": PROTOCOL_VERSION, "capabilities": {},
                     "clientInfo": {"name": "mcp-call", "version": "1.0"}}})
    resp = wait_response(1, 60)
    if "error" in resp:
        print(f"ERROR initialize: {json.dumps(resp['error'])[:200]}", file=sys.stderr)
        return 1
    post({"jsonrpc": "2.0", "method": "notifications/initialized"})

    if list_tools:
        post({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        listing = wait_response(2, 60)
        tools = [t.get("name") for t in (listing.get("result") or {}).get("tools", [])]
        print(json.dumps(tools, ensure_ascii=False, indent=0))
        return 0

    post({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
          "params": {"name": tool, "arguments": tool_args}})
    resp = wait_response(2, DEFAULT_TIMEOUT)
    if resp.get("error"):
        print(f"ERROR {tool}: {json.dumps(resp['error'])[:300]}", file=sys.stderr)
        return 1
    for block in (resp.get("result") or {}).get("content", []):
        if block.get("type") == "text":
            text = block["text"]
            if not raw_out and len(text) > max_chars:
                head = int(max_chars * 0.8)
                tail = max_chars - head
                kept = text[:head] + \
                    f"\n…[截断 {len(text) - max_chars} 字符；总 {len(text)} 字符。" \
                    f"筛选用途已足够；需要全文用 --raw 或 kb_doc_read(offset) 精读…]" + \
                    (text[-tail:] if tail else "")
                print(kept)
            else:
                print(text)
            return 0
    print("{}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
