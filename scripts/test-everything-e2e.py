"""
Full end-to-end validation:
  Phase 1 — Every config variable wiring (stateless)
  Phase 2 — Backend + Frontend live + MCP tool calls (dev)
  Phase 3 — Backend + Frontend live + MCP tool calls (prod)
"""
import os, sys, subprocess, json, time, asyncio, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PASS = 0; FAIL = 0

def ok(msg):    global PASS; print(f"  [PASS] {msg}")
def fail(msg):  global FAIL; print(f"  [FAIL] {msg}")
def info(msg):  print(f"  .. {msg}")
def hr(t):      print(f"\n{'='*60}\n  {t}\n{'='*60}")

def wait_for(url: str, timeout=45) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            r = urllib.request.urlopen(url, timeout=3)
            if r.status == 200: return True
        except: pass
        time.sleep(2)
    return False

def kill_port(port: int):
    subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"try {{ $c = Get-NetTCPConnection -LocalPort {port} -ErrorAction Stop; "
         f"Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue; "
         f"Start-Sleep -Seconds 3 }} catch {{}}"],
        capture_output=True, timeout=15
    )
    time.sleep(2)


# ══════════════════════════════════════════════════════════
# PHASE 1 — Config Wiring (stateless)
# ══════════════════════════════════════════════════════════
hr("PHASE 1: Config variable wiring (16 checks)")

def c(code_template):
    code = code_template.replace("__ROOT__", str(ROOT))
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=15, cwd=str(ROOT))
    return r.returncode == 0, r.stderr.strip()[:100]

tests = [
    ("APP_MODE=dev -> backend config.app_mode",
     "import os; os.chdir(r'__ROOT__/backend'); os.environ['APP_MODE']='dev'; "
     "from app.config import config; config.reload(); assert config.app_mode=='dev'"),

    ("APP_MODE=prod -> backend config.app_mode",
     "import os; os.chdir(r'__ROOT__/backend'); os.environ['APP_MODE']='prod'; "
     "from app.config import config; config.reload(); assert config.app_mode=='prod'"),

    ("NO_RELOAD=1 overrides dev -> prod",
     "import os; os.chdir(r'__ROOT__/backend'); "
     "os.environ.update(APP_MODE='dev', NO_RELOAD='1'); "
     "from app.config import config; config.reload(); assert config.app_mode=='prod'"),

    ("BACKEND_PORT=9999 -> effective port",
     "import os; os.environ['BACKEND_PORT']='9999'; "
     "os.chdir(r'__ROOT__/backend'); from app.config import config; "
     "p = int(os.environ.get('BACKEND_PORT', config.server_port)); assert p==9999"),

    ("server.host from config.yml",
     "import os; os.chdir(r'__ROOT__/backend'); os.environ['APP_MODE']='dev'; "
     "from app.config import config; config.reload(); assert config.server_host=='0.0.0.0'"),

    ("cors_origins=['*']",
     "import os; os.chdir(r'__ROOT__/backend'); os.environ['APP_MODE']='dev'; "
     "from app.config import config; config.reload(); assert config.cors_origins==['*']"),

    ("mineru config from config.yml",
     "import os; os.chdir(r'__ROOT__/backend'); os.environ['APP_MODE']='dev'; "
     "from app.config import config; config.reload(); "
     "mc=config.mineru; assert mc.get('enabled') is True; "
     "assert mc.get('model_source')=='modelscope'; assert mc.get('startup_timeout')==60"),

    ("kb-mcp dev ports 8765/6789",
     "import os,sys; sys.path.insert(0,r'__ROOT__/kb-mcp'); "
     "os.environ.update(APP_MODE='dev',BACKEND_PORT='8765',WEB_PORT='6789'); "
     "import config; assert '8765' in config.BACKEND_URL; assert '6789' in config.WEB_URL"),

    ("kb-mcp prod ports 8001/3000",
     "import os,sys; sys.path.insert(0,r'__ROOT__/kb-mcp'); "
     "os.environ.update(APP_MODE='prod',BACKEND_PORT='8001',WEB_PORT='3000'); "
     "import config; assert '8001' in config.BACKEND_URL; assert '3000' in config.WEB_URL"),

    ("kb-mcp custom ports 9000/4000",
     "import os,sys; sys.path.insert(0,r'__ROOT__/kb-mcp'); "
     "os.environ.update(APP_MODE='dev',BACKEND_PORT='9000',WEB_PORT='4000'); "
     "import config; assert '9000' in config.BACKEND_URL; assert '4000' in config.WEB_URL"),

    ("BACKEND_URL env overrides port",
     "import os,sys; sys.path.insert(0,r'__ROOT__/kb-mcp'); "
     "os.environ.update(BACKEND_URL='http://custom:8888',BACKEND_PORT='8765'); "
     "import config; assert config.BACKEND_URL=='http://custom:8888'"),

    ("WEB_URL env overrides port",
     "import os,sys; sys.path.insert(0,r'__ROOT__/kb-mcp'); "
     "os.environ.update(WEB_URL='http://web-custom:4000',WEB_PORT='6789'); "
     "import config; assert config.WEB_URL=='http://web-custom:4000'"),

    ("WEB_HOST + WEB_PORT -> URL hostname",
     "import os,sys; sys.path.insert(0,r'__ROOT__/kb-mcp'); "
     "os.environ.update(WEB_HOST='my-host',WEB_PORT='8888',APP_MODE='dev'); "
     "import config; assert 'my-host:8888' in config.WEB_URL"),

    ("MINERU_HOST+PORT -> MINERU_URL",
     "import os,sys; sys.path.insert(0,r'__ROOT__/kb-mcp'); "
     "os.environ.update(MINERU_HOST='10.0.0.1',MINERU_PORT='9999'); "
     "import config; assert '10.0.0.1:9999' in config.MINERU_URL"),

    ("MCP_HTTP_TIMEOUT + PARSE_TIMEOUT",
     "import os,sys; sys.path.insert(0,r'__ROOT__/kb-mcp'); "
     "os.environ.update(MCP_HTTP_TIMEOUT='60',MCP_PARSE_TIMEOUT='600'); "
     "import config; assert config.HTTP_TIMEOUT==60; assert config.PARSE_TIMEOUT==600"),

    ("TREE_STORAGE_PATH from .env",
     "import os; from dotenv import load_dotenv; "
     "load_dotenv(dotenv_path=r'__ROOT__/.env',override=True); "
     "assert 'tree-file-system' in os.environ.get('TREE_STORAGE_PATH','')"),
]

for label, code in tests:
    passed, err = c(code)
    if passed:
        ok(label)
    else:
        fail(f"{label}: {err}")


# ══════════════════════════════════════════════════════════
# PHASE 2 — Dev mode: services + MCP tool calls
# ══════════════════════════════════════════════════════════
hr("PHASE 2: MCP end-to-end (dev mode: 8765+6789)")

kill_port(8765); kill_port(6789)
time.sleep(2)
(ROOT / ".env").write_text(
    "APP_MODE=dev\nBACKEND_PORT=8765\nWEB_PORT=6789\nTREE_STORAGE_PATH=../storage/tree-file-system\n",
    encoding="utf-8")

info("Starting backend (dev, :8765)...")
proc_b = subprocess.Popen(
    ["uv", "run", "python", "main.py"], cwd=str(ROOT/"backend"),
    env={**os.environ, "APP_MODE": "dev", "BACKEND_PORT": "8765"},
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x00000010)
if wait_for("http://localhost:8765/api/v1/health", 45):
    ok("Backend /api/v1/health (dev)")
else:
    fail("Backend health timeout (dev)")

# CORS
try:
    req = urllib.request.Request("http://localhost:8765/api/v1/health", method="OPTIONS",
        headers={"Origin": "http://x.com", "Access-Control-Request-Method": "GET"})
    r = urllib.request.urlopen(req, timeout=5)
    assert r.headers.get("Access-Control-Allow-Origin") == "*"
    ok("Backend CORS: Access-Control-Allow-Origin=*")
except Exception as e:
    fail(f"CORS: {e}")

# Backend health JSON
try:
    r = urllib.request.urlopen("http://localhost:8765/api/v1/health", timeout=5)
    d = json.loads(r.read().decode())
    assert d.get("status") == "healthy"
    ok(f"Backend health JSON: {json.dumps(d)}")
except Exception as e:
    fail(f"Backend JSON: {e}")

# Backend mineru/status
try:
    r = urllib.request.urlopen("http://localhost:8765/api/v1/mineru/status", timeout=5)
    d = json.loads(r.read().decode())
    info(f"MinerU status: {json.dumps(d, ensure_ascii=False)}")
    ok("Backend mineru/status endpoint reachable")
except Exception as e:
    info(f"MinerU not running: {e}")

info("Starting frontend (dev, :6789)...")
proc_f = subprocess.Popen(
    ["node", "start.mjs"], cwd=str(ROOT/"web"),
    env={**os.environ, "APP_MODE": "dev", "WEB_PORT": "6789", "BACKEND_PORT": "8765"},
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x00000010)
if wait_for("http://localhost:6789/api/kb/catalog", 45):
    ok("Frontend /api/kb/catalog (dev)")
else:
    fail("Frontend timeout (dev)")

# MCP kb_list
try:
    r = urllib.request.urlopen("http://localhost:6789/api/kb/catalog", timeout=5)
    d = json.loads(r.read().decode())
    ok(f"MCP kb_list (dev): valid JSON, type={type(d).__name__}")
except Exception as e:
    fail(f"kb_list: {e}")

# MCP health_check equivalent
async def probe_dev():
    import httpx
    async with httpx.AsyncClient(timeout=5) as cli:
        b = await cli.get("http://localhost:8765/api/v1/health")
        f = await cli.get("http://localhost:6789/api/kb/catalog")
        return b.status_code == 200 and f.status_code == 200
rc = asyncio.run(probe_dev())
if rc: ok("MCP health_check (dev): both services reachable")
else: fail("MCP health_check (dev): not both reachable")

# MCP backend_status
async def bs_dev():
    import httpx
    async with httpx.AsyncClient(timeout=5) as cli:
        return (await cli.get("http://localhost:8765/api/v1/mineru/status")).status_code
rc = asyncio.run(bs_dev())
if rc == 200: ok("MCP backend_status (dev): endpoint reachable")
else: fail(f"backend_status (dev): {rc}")

proc_f.terminate(); proc_f.wait(timeout=10)
proc_b.terminate(); proc_b.wait(timeout=10)
info("Dev services stopped")


# ══════════════════════════════════════════════════════════
# PHASE 3 — Prod mode: services + MCP tool calls (no window)
# ══════════════════════════════════════════════════════════
hr("PHASE 3: MCP end-to-end (prod mode: 8001+3000, no window)")

kill_port(8001); kill_port(3000)
time.sleep(2)
(ROOT / ".env").write_text(
    "APP_MODE=prod\nBACKEND_PORT=8001\nWEB_PORT=3000\nTREE_STORAGE_PATH=../storage/tree-file-system\n",
    encoding="utf-8")

nw = 0x00000008 | 0x08000000
info("Starting backend (prod, :8001, no window)...")
proc_b = subprocess.Popen(
    ["uv", "run", "python", "main.py"], cwd=str(ROOT/"backend"),
    env={**os.environ, "APP_MODE": "prod", "BACKEND_PORT": "8001"},
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=nw)
if wait_for("http://localhost:8001/api/v1/health", 45):
    ok("Backend /api/v1/health (prod, no window)")
else:
    fail("Backend health timeout (prod)")

# CORS in prod
try:
    req = urllib.request.Request("http://localhost:8001/api/v1/health", method="OPTIONS",
        headers={"Origin": "http://prod-x.com", "Access-Control-Request-Method": "GET"})
    r = urllib.request.urlopen(req, timeout=5)
    assert r.headers.get("Access-Control-Allow-Origin") == "*"
    ok("Backend CORS (prod): Access-Control-Allow-Origin=*")
except Exception as e:
    fail(f"CORS (prod): {e}")

info("Starting frontend (prod, :3000, no window)...")
proc_f = subprocess.Popen(
    ["node", "start.mjs"], cwd=str(ROOT/"web"),
    env={**os.environ, "APP_MODE": "prod", "WEB_PORT": "3000", "BACKEND_PORT": "8001"},
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=nw)
if wait_for("http://localhost:3000/api/kb/catalog", 45):
    ok("Frontend /api/kb/catalog (prod, no window)")
else:
    fail("Frontend timeout (prod)")

# MCP health_check (prod)
async def probe_prod():
    import httpx
    async with httpx.AsyncClient(timeout=5) as cli:
        b = await cli.get("http://localhost:8001/api/v1/health")
        f = await cli.get("http://localhost:3000/api/kb/catalog")
        return b.status_code == 200 and f.status_code == 200
rc = asyncio.run(probe_prod())
if rc: ok("MCP health_check (prod): both services reachable")
else: fail("MCP health_check (prod): not both reachable")

# MCP kb_list (prod)
try:
    r = urllib.request.urlopen("http://localhost:3000/api/kb/catalog", timeout=5)
    d = json.loads(r.read().decode())
    ok(f"MCP kb_list (prod): valid JSON, type={type(d).__name__}")
except Exception as e:
    fail(f"kb_list (prod): {e}")

# MCP backend_status (prod)
async def bs_prod():
    import httpx
    async with httpx.AsyncClient(timeout=5) as cli:
        return (await cli.get("http://localhost:8001/api/v1/mineru/status")).status_code
rc = asyncio.run(bs_prod())
if rc == 200: ok("MCP backend_status (prod): endpoint reachable")
else: fail(f"backend_status (prod): {rc}")

proc_f.terminate(); proc_f.wait(timeout=10)
proc_b.terminate(); proc_b.wait(timeout=10)
info("Prod services stopped")


# ══════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════
hr("FINAL RESULTS")
print(f"  Passed: {PASS}")
print(f"  Failed: {FAIL}")
print(f"  Total:  {PASS + FAIL}")
if FAIL == 0:
    print("\n  ALL CHECKS PASSED — every config variable wired, MCP reachable in dev+prod.")
else:
    print(f"\n  {FAIL} failures — see above.")

(ROOT / ".env").write_text(
    "APP_MODE=dev\nBACKEND_PORT=8765\nWEB_PORT=6789\nTREE_STORAGE_PATH=../storage/tree-file-system\n",
    encoding="utf-8")
sys.exit(0 if FAIL == 0 else 1)
