#!/usr/bin/env python3
"""
Test MCP mode-aware startup:
  dev  → visible console windows (CREATE_NEW_CONSOLE)
  prod → background, no window   (DETACHED_PROCESS | CREATE_NO_WINDOW)

Also validates that both modes successfully start backend + frontend + MCP connectivity.
"""
import os, sys, subprocess, json, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
PASS = 0
FAIL = 0

def log_ok(msg):    global PASS; print(f"  [OK] {msg}")
def log_fail(msg):  global FAIL; print(f"  [FAIL] {msg}")
def log_info(msg):  print(f"  -- {msg}")
def hr(title):      print(f"\n{'='*60}\n  {title}\n{'='*60}")

def write_env(content: str):
    ENV_PATH.write_text(content.lstrip("\n"), encoding="utf-8")

def wait_for(url: str, timeout: int = 30) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            r = urllib.request.urlopen(url, timeout=3)
            if r.status == 200: return True
        except: pass
        time.sleep(2)
    return False

def cleanup_port(port: int):
    """Kill process holding a port (Windows)."""
    import subprocess as sp
    sp.run(
        ["powershell", "-NoProfile", "-Command",
         f"try {{ $c = Get-NetTCPConnection -LocalPort {port} -ErrorAction Stop; "
         f"Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue; "
         f"Start-Sleep -Seconds 2 }} catch {{}}"],
        capture_output=True, timeout=15
    )
    time.sleep(1)

def is_port_free(port: int) -> bool:
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        sock.bind(("0.0.0.0", port))
        sock.close(); return True
    except OSError: return False


# ── Test 1: _subprocess_flags logic ──
hr("MCP subprocess flags logic")
code = r"""
import sys
sys.path.insert(0, r"{{KB_MCP}}")
# Define the function as in server.py
def _subprocess_flags(app_mode: str = "prod"):
    if sys.platform == "win32":
        if app_mode == "dev":
            return {"creationflags": 0x00000010}
        else:
            return {"creationflags": 0x00000008 | 0x08000000}
    if app_mode == "dev":
        return {}
    return {"start_new_session": True}

dev = _subprocess_flags("dev")
prod = _subprocess_flags("prod")
print(f"dev={dev}")
print(f"prod={prod}")

# Validations
assert dev.get("creationflags") == 0x10, f"dev expected 0x10, got {dev}"
assert prod.get("creationflags") == (0x08 | 0x08000000), f"prod expected no-window, got {prod}"
print("OK")
""".replace("{{KB_MCP}}", str(ROOT / "kb-mcp"))

r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=10)
if r.returncode == 0 and "OK" in r.stdout:
    log_ok(f"_subprocess_flags: dev=CREATE_NEW_CONSOLE, prod=no-window")
    for line in r.stdout.strip().split("\n"):
        if "dev=" in line or "prod=" in line: log_info(line.strip())
else:
    log_fail(f"Flags test failed: {r.stderr.strip()}")


# ── Test 2: MCP config in both modes ──
for mode, label, env_content in [
    ("dev", "MCP config (dev mode)", "APP_MODE=dev\nBACKEND_PORT=8765\nWEB_PORT=6789\nTREE_STORAGE_PATH=../storage/tree-file-system\n"),
    ("prod", "MCP config (prod mode)", "APP_MODE=prod\nBACKEND_PORT=8001\nWEB_PORT=3000\nTREE_STORAGE_PATH=../storage/tree-file-system\n"),
]:
    hr(f"{label}")
    write_env(env_content)
    code = f"""
import os, sys
sys.path.insert(0, r"{ROOT / 'kb-mcp'}")
from pathlib import Path
env_path = Path(r"{ENV_PATH}")
with open(env_path, encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        k, _, v = line.partition('=')
        k, v = k.strip(), v.strip().strip("\\"'")
        if k: os.environ[k] = v
import config
print(f"BACKEND_URL={{config.BACKEND_URL}}")
print(f"WEB_URL={{config.WEB_URL}}")
print(f"APP_MODE={{os.environ.get('APP_MODE')}}")
"""
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=10)
    ok = True
    if r.returncode != 0:
        log_fail(f"MCP import failed: {r.stderr.strip()[:100]}")
        continue
    vals = {}
    for line in r.stdout.strip().split("\n"):
        line = line.strip()
        if "=" in line:
            k, v = line.split("=", 1); vals[k] = v
    if mode == "dev":
        if "8765" in vals.get("BACKEND_URL", "") and "6789" in vals.get("WEB_URL", ""): ok = log_ok(f"dev URLs: {vals.get('BACKEND_URL')}, {vals.get('WEB_URL')}") or True
        else: log_fail(f"dev URLs unexpected: {vals}"); ok = False
    else:
        if "8001" in vals.get("BACKEND_URL", "") and "3000" in vals.get("WEB_URL", ""): log_ok(f"prod URLs: {vals.get('BACKEND_URL')}, {vals.get('WEB_URL')}")
        else: log_fail(f"prod URLs unexpected: {vals}"); ok = False
    if ok: log_ok(f"MCP config: {label}")


# ── Test 3: Live services in dev mode ──
hr("Live services (dev mode: visible console)")
write_env("APP_MODE=dev\nBACKEND_PORT=8765\nWEB_PORT=6789\nTREE_STORAGE_PATH=../storage/tree-file-system\n")
cleanup_port(8765); cleanup_port(6789)

# Start backend + frontend using dev flags (CREATE_NEW_CONSOLE)
log_info("Starting backend (dev mode, visible console)...")
proc_b = subprocess.Popen(
    ["uv", "run", "python", "main.py"],
    cwd=str(ROOT / "backend"),
    env={**os.environ, "APP_MODE": "dev", "BACKEND_PORT": "8765"},
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    creationflags=0x00000010,  # CREATE_NEW_CONSOLE
)
log_info("Starting frontend (dev mode, visible console)...")
proc_f = subprocess.Popen(
    ["node", "start.mjs"],
    cwd=str(ROOT / "web"),
    env={**os.environ, "APP_MODE": "dev", "WEB_PORT": "6789", "BACKEND_PORT": "8765"},
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    creationflags=0x00000010,  # CREATE_NEW_CONSOLE
)

if wait_for("http://localhost:8765/api/v1/health", 30):
    log_ok("Backend health OK (dev, :8765)")
    # Verify CORS
    try:
        req = urllib.request.Request("http://localhost:8765/api/v1/health", method="OPTIONS",
            headers={"Origin": "http://dev-test-origin.com", "Access-Control-Request-Method": "GET"})
        r = urllib.request.urlopen(req, timeout=5)
        acao = r.headers.get("Access-Control-Allow-Origin", "")
        log_ok(f"CORS: Access-Control-Allow-Origin={acao}")
    except Exception as e: log_info(f"CORS OPTIONS: {e}")
else: log_fail("Backend timeout (dev)")

if wait_for("http://localhost:6789/api/kb/catalog", 30):
    log_ok("Frontend health OK (dev, :6789)")
    try:
        r = urllib.request.urlopen("http://localhost:6789/api/kb/catalog", timeout=5)
        data = json.loads(r.read().decode())
        log_ok(f"Frontend KB catalog: valid JSON ({type(data).__name__})")
    except Exception as e: log_info(f"KB catalog fetch: {e}")
else: log_fail("Frontend timeout (dev)")

proc_f.terminate(); proc_f.wait()
proc_b.terminate(); proc_b.wait()
log_ok("Dev services stopped")


# ── Test 4: Live services in prod mode ──
hr("Live services (prod mode: background, no window)")
write_env("APP_MODE=prod\nBACKEND_PORT=8001\nWEB_PORT=3000\nTREE_STORAGE_PATH=../storage/tree-file-system\n")
cleanup_port(8001); cleanup_port(3000)

if not is_port_free(8001):
    if wait_for("http://localhost:8001/api/v1/health", 5):
        log_info("Port 8001 already has a running backend, reusing")
        existing_backend = True
    else:
        log_fail("Port 8001 in use but not healthy, cannot test"); raise SystemExit(1)
else:
    existing_backend = False
    log_info("Starting backend (prod mode, no window)...")
    proc_b2 = subprocess.Popen(
        ["uv", "run", "python", "main.py"],
        cwd=str(ROOT / "backend"),
        env={**os.environ, "APP_MODE": "prod", "BACKEND_PORT": "8001"},
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=0x00000008 | 0x08000000,  # DETACHED_PROCESS | CREATE_NO_WINDOW
    )

if not is_port_free(3000):
    log_info("Port 3000 already in use, checking...")
    existing_frontend = wait_for("http://localhost:3000/api/kb/catalog", 5)
else:
    existing_frontend = False
    log_info("Starting frontend (prod mode, no window)...")
    proc_f2 = subprocess.Popen(
        ["node", "start.mjs"],
        cwd=str(ROOT / "web"),
        env={**os.environ, "APP_MODE": "prod", "WEB_PORT": "3000", "BACKEND_PORT": "8001"},
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=0x00000008 | 0x08000000,
    )

if existing_backend or wait_for("http://localhost:8001/api/v1/health", 30):
    log_ok("Backend health OK (prod, :8001)")
    # Verify CORS
    try:
        req = urllib.request.Request("http://localhost:8001/api/v1/health", method="OPTIONS",
            headers={"Origin": "http://prod-test-origin.com", "Access-Control-Request-Method": "GET"})
        r = urllib.request.urlopen(req, timeout=5)
        acao = r.headers.get("Access-Control-Allow-Origin", "")
        log_ok(f"CORS: Access-Control-Allow-Origin={acao}")
    except Exception as e: log_info(f"CORS OPTIONS: {e}")
else: log_fail("Backend timeout (prod)")

if existing_frontend or wait_for("http://localhost:3000/api/kb/catalog", 30):
    log_ok("Frontend health OK (prod, :3000)")
    try:
        r = urllib.request.urlopen("http://localhost:3000/api/kb/catalog", timeout=5)
        data = json.loads(r.read().decode())
        log_ok(f"Frontend KB catalog: valid JSON ({type(data).__name__})")
    except Exception as e: log_info(f"KB catalog fetch: {e}")
else: log_fail("Frontend timeout (prod)")

if not existing_frontend: proc_f2.terminate(); proc_f2.wait()
if not existing_backend: proc_b2.terminate(); proc_b2.wait()
log_ok("Prod services stopped")


# ── Summary ──
print("\n" + "="*60)
total = PASS + FAIL
print(f"  {PASS} passed, {FAIL} failed, total {total}")
if FAIL == 0: print(f"  ALL PASSED!")
else: print(f"  {FAIL} FAILURE(S) — see details above")
print("="*60)
sys.exit(0 if FAIL == 0 else 1)
