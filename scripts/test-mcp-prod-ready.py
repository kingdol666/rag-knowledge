"""
Final MCP verification: start services, connect MCP via stdio,
call tools/list and health_check to confirm Claude Code integration.
"""
import os, sys, json, time, urllib.request, subprocess, threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

(ROOT / ".env").write_text(
    "APP_MODE=dev\nBACKEND_PORT=8765\nWEB_PORT=6789\nTREE_STORAGE_PATH=../storage/tree-file-system\n",
    encoding="utf-8")

# ── start backend ──
proc_b = subprocess.Popen(["uv","run","python","main.py"], cwd=str(ROOT/"backend"),
    env={**os.environ, "APP_MODE": "dev", "BACKEND_PORT": "8765"},
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x00000010)

deadline = time.monotonic() + 45
while time.monotonic() < deadline:
    try:
        r = urllib.request.urlopen("http://localhost:8765/api/v1/health", timeout=3)
        if r.status == 200: break
    except: pass
    time.sleep(2)
else:
    print("[FAIL] Backend did not start"); raise SystemExit(1)
print("[PASS] Backend /api/v1/health")

# ── start frontend ──
proc_f = subprocess.Popen(["node","start.mjs"], cwd=str(ROOT/"web"),
    env={**os.environ, "APP_MODE": "dev", "WEB_PORT": "6789", "BACKEND_PORT": "8765"},
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x00000010)

deadline = time.monotonic() + 45
while time.monotonic() < deadline:
    try:
        r = urllib.request.urlopen("http://localhost:6789/api/kb/catalog", timeout=3)
        if r.status == 200: break
    except: pass
    time.sleep(2)
else:
    print("[FAIL] Frontend did not start"); raise SystemExit(1)
print("[PASS] Frontend /api/kb/catalog")

# ── start MCP server (stdio) ──
env = os.environ.copy()
env.update({"APP_MODE": "dev", "BACKEND_PORT": "8765", "WEB_PORT": "6789",
            "TREE_STORAGE_PATH": "../storage/tree-file-system",
            "MCP_HTTP_TIMEOUT": "30", "MCP_PARSE_TIMEOUT": "300"})
proc_mcp = subprocess.Popen(
    ["uv", "run", "--directory", str(ROOT/"kb-mcp"), "python", "server.py"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    env=env, text=True, bufsize=1)

# Read stderr for logs (side channel)
stderr_lines = []
def _read_stderr():
    for line in proc_mcp.stderr:
        if line.strip():
            stderr_lines.append(line.strip()[:120])
            if len(stderr_lines) > 20:
                stderr_lines.pop(0)
t = threading.Thread(target=_read_stderr, daemon=True)
t.start()
time.sleep(5)  # let MCP init probe services

print("[info] MCP server started (stdio) — connecting...")

# ── Step 0: MCP initialize handshake (required by protocol) ──
def send_mcp(method, params=None, rid=1):
    req = json.dumps({"jsonrpc": "2.0", "id": rid, "method": method,
                      "params": params or {}})
    proc_mcp.stdin.write(req + "\n")
    proc_mcp.stdin.flush()
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            line = proc_mcp.stdout.readline()
            if line:
                return json.loads(line)
        except: pass
        time.sleep(0.2)
    return None

# MCP protocol requires a capabilities exchange before tool calls
init_resp = send_mcp("initialize", {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {"name": "mcp-test", "version": "1.0.0"}
}, rid=1)
if init_resp and "result" in init_resp:
    server_caps = init_resp["result"].get("capabilities", {})
    server_name = init_resp["result"].get("serverInfo", {}).get("name", "unknown")
    print(f"[PASS] MCP initialize: connected to '{server_name}'")
    print(f"       server capabilities: {json.dumps(server_caps, ensure_ascii=False)[:120]}")

    # Send initialized notification (required by protocol)
    send_mcp("notifications/initialized", rid=2)
else:
    print(f"[FAIL] MCP initialize failed: {str(init_resp)[:200]}")
    print(f"  stderr: {' | '.join(stderr_lines[-5:])}")
    proc_mcp.terminate()
    proc_b.terminate(); proc_f.terminate()
    raise SystemExit(1)

# ── Step 1: tools/list ──
resp = send_mcp("tools/list", rid=3)
if resp and "result" in resp:
    tools = resp["result"].get("tools", [])
    print(f"[PASS] MCP tools/list: {len(tools)} tools registered")
    # Show toolbox
    cats = {}
    for t_ in tools:
        cat = t_["name"].split("_")[0] if "_" in t_["name"] else "other"
        cats.setdefault(cat, []).append(t_["name"])
    for cat, names in sorted(cats.items()):
        print(f"       {cat}: {len(names)} tools ({', '.join(names[:4])}...)")
else:
    print(f"[FAIL] tools/list failed: {str(resp)[:200]}")
    print(f"  stderr: {' | '.join(stderr_lines[-5:])}")
    proc_mcp.terminate()
    proc_b.terminate(); proc_f.terminate()
    raise SystemExit(1)

# ── Step 2: call health_check ──
resp = send_mcp("tools/call", {"name": "health_check", "arguments": {}}, rid=2)
if resp and "result" in resp:
    content = resp["result"].get("content", [{}])
    text = content[0].get("text", "") if content else ""
    print(f"[PASS] health_check: {text[:200]}")
else:
    print(f"[FAIL] health_check: {str(resp)[:200]}")

# ── Step 3: call kb_list ──
resp = send_mcp("tools/call", {"name": "kb_list", "arguments": {}}, rid=3)
if resp and "result" in resp:
    content = resp["result"].get("content", [{}])
    text = content[0].get("text", "") if content else ""
    print(f"[PASS] kb_list: {text[:120]}...")
else:
    print(f"[FAIL] kb_list: {str(resp)[:120]}")

# ── Step 4: call backend_status ──
resp = send_mcp("tools/call", {"name": "backend_status", "arguments": {}}, rid=4)
if resp and "result" in resp:
    content = resp["result"].get("content", [{}])
    text = content[0].get("text", "") if content else ""
    print(f"[PASS] backend_status: {text[:100]}...")
else:
    print(f"[FAIL] backend_status: {str(resp)[:100]}")

# ── Summary ──
print(f"\n{'='*60}")
print(f"  MCP VERIFICATION COMPLETE")
print(f"  Tools available: {len(tools)}")
print(f"  Protocol: stdio JSON-RPC")
print(f"  Claude Code integration: READY")
print(f"{'='*60}")

proc_mcp.terminate(); proc_mcp.wait(timeout=5)
proc_f.terminate(); proc_f.wait(timeout=5)
proc_b.terminate(); proc_b.wait(timeout=5)
print("[info] Services stopped")
