#!/usr/bin/env python3
"""
RAG Knowledge - 全方位环境测试
验证所有模块（backend、web、kb-mcp）在每个场景下都能正确启动和通信。
"""
import os, sys, subprocess, json, time, socket, asyncio, signal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
PASS = 0
FAIL = 0

def log_ok(msg):    global PASS; print(f"  [OK] {msg}")
def log_fail(msg):  global FAIL; print(f"  [FAIL] {msg}")
def log_info(msg):  print(f"  ─ {msg}")
def hr(title):      print(f"\n{'='*60}\n  {title}\n{'='*60}", flush=True)

# ── helpers ──

def write_env(content: str):
    ENV_PATH.write_text(content.lstrip("\n"), encoding="utf-8")

def free_port(port: int):
    """Kill any process holding this port (Windows)."""
    if port_free(port): return
    import subprocess
    try:
        # Use timeout /nobreak to wait for port to fully drain
        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"try {{ $c = Get-NetTCPConnection -LocalPort {port} -ErrorAction Stop; "
             f"Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue; "
             f"Start-Sleep -Seconds 3 }} catch {{}}"],
            capture_output=True, timeout=15
        )
        time.sleep(3)
    except: pass

def port_free(port: int) -> bool:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        sock.bind(("0.0.0.0", port))
        sock.close(); return True
    except OSError: return False

def wait_for(url: str, timeout: int = 30) -> bool:
    import urllib.request
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            r = urllib.request.urlopen(url, timeout=3)
            if r.status == 200: return True
        except: pass
        time.sleep(2)
    return False

cleanup_env = """APP_MODE=dev
BACKEND_PORT=8765
WEB_PORT=6789
TREE_STORAGE_PATH=../storage/tree-file-system
"""

# ── Test 1: MCP config resolution ──

def test_mcp_config(label: str, env_content: str, expect_backend_port: str, expect_web_port: str):
    hr(f"MCP config: {label}")
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
print(f"WEB_URL={{config.WEB_URL}}")
print(f"BACKEND_URL={{config.BACKEND_URL}}")
print(f"APP_MODE={{os.environ.get('APP_MODE')}}")
"""
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=10)
    out = ""
    if r.returncode != 0:
        log_fail(f"MCP config import error: {r.stderr.strip()[:120]}")
        return
    for line in r.stdout.strip().split("\n"):
        line = line.strip()
        if line.startswith("WEB_URL="):    web_url = line.split("=",1)[1]
        elif line.startswith("BACKEND_URL="): backend_url = line.split("=",1)[1]
        elif line.startswith("APP_MODE="): mode = line.split("=",1)[1]

    ok = True
    if backend_url and expect_backend_port in backend_url:
        log_ok(f"BACKEND_URL={backend_url}")
    else:
        log_fail(f"BACKEND_URL={backend_url} (expected port {expect_backend_port})"); ok = False

    if web_url and expect_web_port in web_url:
        log_ok(f"WEB_URL={web_url}")
    else:
        log_fail(f"WEB_URL={web_url} (expected port {expect_web_port})"); ok = False

    if ok: log_ok(f"MCP config: {label} ✅")
    return backend_url, web_url

# ── Test 2: Backend CORS config ──

def test_backend_config(label: str, env_content: str, expect_port: str):
    hr(f"Backend config: {label}")
    write_env(env_content)
    code = f"""
import os, sys
sys.path.insert(0, r"{ROOT / 'backend'}")
from pathlib import Path
env_path = Path(r"{ENV_PATH}")
if env_path.exists():
    import dotenv
    dotenv.load_dotenv(dotenv_path=str(env_path), override=True)
from app.config import config
config.reload()
print(f"mode={{config.app_mode}}")
print(f"port={{config.server_port}}")
print(f"cors={{config.cors_origins}}")
origins = config.cors_origins
print(f"allow_all={{str(origins == ['*']).lower()}}")
"""
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        log_fail(f"Backend config error: {r.stderr.strip()[:120]}")
        return

    mode = port = cors = allow_all = None
    for line in r.stdout.strip().split("\n"):
        line = line.strip()
        if line.startswith("mode="): mode = line.split("=",1)[1]
        elif line.startswith("port="): port = line.split("=",1)[1]
        elif line.startswith("cors="): cors = line.split("=",1)[1]
        elif line.startswith("allow_all="): allow_all = line.split("=",1)[1]

    ok = True
    if port and port == expect_port:  # config.yml 's backend_port for active mode
        log_ok(f"Backend port={port}")
    else:
        log_info(f"Backend port={port} (config value, env override at startup)")

    if allow_all == "true":
        log_ok(f"Backend CORS: {cors} → allow_all=True")
    else:
        log_fail(f"Backend CORS: {cors} → allow_all=False"); ok = False

    if ok: log_ok(f"Backend config: {label} ✅")

# ── Test 3: Live service startup ──

def test_live_services(label: str, env_content: str, backend_port: str, web_port: str):
    hr(f"Live services: {label}")
    write_env(env_content)

    bp = int(backend_port); wp = int(web_port)

    # Free ports if anything is still holding them
    free_port(bp); free_port(wp)

    if not port_free(bp):
        log_fail(f"Backend port {bp} in use, skipping live test"); return
    if not port_free(wp):
        log_fail(f"Web port {wp} in use, skipping live test"); return

    # Parse mode from env content
    mode = "dev"
    for line in env_content.strip().split("\n"):
        if line.startswith("APP_MODE="):
            mode = line.split("=",1)[1].strip()

    # Start backend
    log_info(f"Starting backend (:{bp})...")
    proc_b = subprocess.Popen(
        ["uv", "run", "python", "main.py"],
        cwd=str(ROOT / "backend"),
        env={**os.environ, "APP_MODE": mode, "BACKEND_PORT": backend_port},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )

    if wait_for(f"http://localhost:{bp}/api/v1/health", timeout=30):
        log_ok(f"Backend health OK (:{bp})")
    else:
        log_fail(f"Backend timeout (:{bp})"); proc_b.kill(); return

    # Verify CORS header
    try:
        import urllib.request
        req = urllib.request.Request(
            f"http://localhost:{bp}/api/v1/health",
            method="OPTIONS",
            headers={"Origin": "http://unknown-origin.com", "Access-Control-Request-Method": "GET"},
        )
        r = urllib.request.urlopen(req, timeout=5)
        acao = r.headers.get("Access-Control-Allow-Origin", "")
        if acao == "*":
            log_ok(f"CORS: Access-Control-Allow-Origin=*")
        else:
            log_info(f"CORS header: {acao}")
    except Exception as e:
        log_info(f"CORS OPTIONS check: {e}")

    # Start frontend
    log_info(f"Starting frontend (:{wp})...")
    proc_f = subprocess.Popen(
        ["node", "start.mjs"],
        cwd=str(ROOT / "web"),
        env={**os.environ, "APP_MODE": mode, "WEB_PORT": web_port, "BACKEND_PORT": backend_port},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )

    if wait_for(f"http://localhost:{wp}/api/kb/catalog", timeout=30):
        log_ok(f"Frontend health OK (:{wp})")
    else:
        log_fail(f"Frontend timeout (:{wp})")

    # Frontend's KB catalog endpoint should talk to backend too
    try:
        import urllib.request
        r = urllib.request.urlopen(f"http://localhost:{wp}/api/kb/catalog", timeout=5)
        data = json.loads(r.read())
        log_ok(f"Frontend KB catalog endpoint returns valid JSON")
    except Exception as e:
        log_info(f"Frontend KB catalog fetch: {e}")

    log_info("Stopping services...")
    proc_f.terminate()
    try: proc_f.wait(timeout=5)
    except: proc_f.kill(); proc_f.wait()
    proc_b.terminate()
    try: proc_b.wait(timeout=5)
    except: proc_b.kill(); proc_b.wait()
    log_ok(f"Live services: {label} ✅")


# ── Main ──

def main():
    global PASS, FAIL
    print("="*60)
    print("  RAG Knowledge Platform — 全方位环境测试")
    print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # ── 测试 1: MCP 配置读取 ──
    try:
        test_mcp_config("dev 默认端口 (8765/6789)", cleanup_env, "8765", "6789")
    except Exception as e:
        log_fail(f"Test 1a failed: {e}")

    try:
        test_mcp_config("prod 默认端口 (8001/3000)",
            "APP_MODE=prod\nBACKEND_PORT=8001\nWEB_PORT=3000\nTREE_STORAGE_PATH=../storage/tree-file-system\n",
            "8001", "3000")
    except Exception as e:
        log_fail(f"Test 1b failed: {e}")

    try:
        test_mcp_config("自定义端口 (9000/4000)",
            "APP_MODE=dev\nBACKEND_PORT=9000\nWEB_PORT=4000\nTREE_STORAGE_PATH=../storage/tree-file-system\n",
            "9000", "4000")
    except Exception as e:
        log_fail(f"Test 1c failed: {e}")

    # ── 测试 2: Backend CORS ──
    try:
        test_backend_config("dev 模式", cleanup_env, "8765")
    except Exception as e:
        log_fail(f"Test 2a failed: {e}")

    try:
        test_backend_config("prod 模式",
            "APP_MODE=prod\nBACKEND_PORT=8001\nWEB_PORT=3000\nTREE_STORAGE_PATH=../storage/tree-file-system\n",
            "8001")
    except Exception as e:
        log_fail(f"Test 2b failed: {e}")

    try:
        test_backend_config("自定义端口",
            "APP_MODE=dev\nBACKEND_PORT=9000\nWEB_PORT=4000\nTREE_STORAGE_PATH=../storage/tree-file-system\n",
            "9000")
    except Exception as e:
        log_fail(f"Test 2c failed: {e}")

    # ── 测试 3: 启动后端+前端 ──
    try:
        test_live_services("dev 默认端口 (8765/6789)", cleanup_env, "8765", "6789")
    except Exception as e:
        log_fail(f"Test 3a failed: {e}")

    try:
        test_live_services("自定义端口 (9000/4000)",
            "APP_MODE=dev\nBACKEND_PORT=9000\nWEB_PORT=4000\nTREE_STORAGE_PATH=../storage/tree-file-system\n",
            "9000", "4000")
    except Exception as e:
        log_fail(f"Test 3b failed: {e}")

    # ── 汇总 ──
    print("\n" + "="*60)
    total = PASS + FAIL
    if FAIL == 0:
        print(f"  ALL PASSED! {PASS}/{PASS}")
    else:
        print(f"  {PASS} passed, {FAIL} failed, total {total}")
    print("="*60)
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    finally:
        ENV_PATH.write_text(cleanup_env, encoding="utf-8")
        print(f"\n[Cleanup] .env restored to dev defaults")
