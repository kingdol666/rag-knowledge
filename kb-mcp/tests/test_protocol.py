# -*- coding: utf-8 -*-
"""Test kb-mcp server via the actual JSON-RPC protocol over stdio."""
import subprocess
import json
import os
import sys
import threading

# 默认 dev 模式（6789/8765）；直接 `uv run python tests/test_protocol.py` 不带 APP_MODE 时
# 避免回退 prod 打到 3000 端口（无服务）致全部请求失败。
# 设 APP_MODE=prod 或已设值时尊重已有值。
os.environ.setdefault("APP_MODE", "dev")

import config

# server.py 在 kb-mcp/ 根目录（不在 tests/），subprocess 必须以仓库根为 cwd 才能找到它。
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

env = dict(os.environ)
env["WEB_URL"] = config.WEB_URL
env["BACKEND_URL"] = config.BACKEND_URL
env["PYTHONIOENCODING"] = "utf-8"

proc = subprocess.Popen(
    [sys.executable, "-u", "server.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
    env=env,
    cwd=_PROJECT_ROOT,
)

messages = [
    json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                           "clientInfo": {"name": "test", "version": "1.0"}}}),
    json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
    json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}),
    json.dumps({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                "params": {"name": "health_check", "arguments": {}}}),
    json.dumps({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                "params": {"name": "kb_list", "arguments": {}}}),
]

proc.stdin.write(("\n".join(messages) + "\n").encode("utf-8"))
proc.stdin.flush()

responses = {}

def reader():
    for raw in proc.stdout:
        line = raw.decode("utf-8", errors="replace").strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
            rid = msg.get("id")
            if rid:
                responses[rid] = msg
        except json.JSONDecodeError:
            pass

t = threading.Thread(target=reader, daemon=True)
t.start()
t.join(timeout=20)

proc.terminate()

tool_count = 0
health_ok = False
kb_count = 0

if 1 in responses:
    si = responses[1].get("result", {}).get("serverInfo", {})
    print(f"[INIT] Server: {si.get('name')} v{si.get('version')}")

if 2 in responses:
    tools = responses[2].get("result", {}).get("tools", [])
    tool_count = len(tools)
    print(f"[TOOLS/LIST] {tool_count} tools discovered")

if 3 in responses:
    content = responses[3].get("result", {}).get("content", [])
    if content:
        data = json.loads(content[0].get("text", "{}"))
        health_ok = data.get("all_ok", False)
        print(f"[CALL health_check] all_ok={health_ok} backend={data.get('backend')} mineru={data.get('mineru')} web={data.get('web')}")
else:
    print("[CALL health_check] NO RESPONSE")

if 4 in responses:
    content = responses[4].get("result", {}).get("content", [])
    if content:
        data = json.loads(content[0].get("text", "{}"))
        kb_count = data.get("count", 0)
        print(f"[CALL kb_list] {kb_count} knowledge bases found")
else:
    print("[CALL kb_list] NO RESPONSE")

print()
all_ok = tool_count >= 73 and health_ok and kb_count > 0
if all_ok:
    print(f"=== MCP PROTOCOL TEST PASSED ({tool_count} tools, health={health_ok}, {kb_count} KBs) ===")
else:
    print(f"=== TEST FAILED: tools={tool_count} health={health_ok} kbs={kb_count} ===")
    sys.exit(1)
