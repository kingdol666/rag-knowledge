# -*- coding: utf-8 -*-
"""
kb-mcp project service lifecycle — silent start + status.

All launches are HEADLESS on every platform and every mode (dev behaves
identically to prod): NO terminal / console window is ever opened.
stdout+stderr are redirected to the SAME shared log files that ragctl
(command/ragctl.js) and the Tauri desktop console (src-tauri) use, so logs
flow into one place regardless of which launcher started the services:

  backend → {project_root}/backend/logs/desktop-stdout.log
  web     → {project_root}/web/logs/desktop-stdout.log
  mineru  → {project_root}/backend/logs/mineru-api.log  (written by backend)

This module is the single kb-mcp-side source of truth for service lifecycle.
It backs:
  - the MCP tools `kb_project_start` / `kb_project_status` in server.py
  - the startup auto-launch (_startup_health_check_and_launch in server.py)

ragctl and the Tauri app are independent launchers that write to the same
log files, so all three surfaces (on-disk file, Tauri UI, `ragctl logs`)
stay in sync no matter who started the services.
"""
from __future__ import annotations

import os
import sys
import socket
import subprocess
import time
from pathlib import Path

try:
    import config as _config  # type: ignore
except Exception:  # pragma: no cover - config always present in-tree
    _config = None


# ── Paths ────────────────────────────────────────────────────────────────
_KB_MCP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = Path(os.environ.get("RAG_PROJECT_ROOT", _KB_MCP_DIR.parent)).resolve()
BACKEND_DIR = PROJECT_ROOT / "backend"
WEB_DIR = PROJECT_ROOT / "web"

# MUST stay in lock-step with src-tauri watch_log + ragctl LOG_PATHS.
LOG_PATHS = {
    "backend": BACKEND_DIR / "logs" / "desktop-stdout.log",
    "web": WEB_DIR / "logs" / "desktop-stdout.log",
    "mineru": BACKEND_DIR / "logs" / "mineru-api.log",
}

NEO4J_BOLT_PORT = 7687
NEO4J_HTTP_PORT = 7474


# ── Mode / port resolution ───────────────────────────────────────────────
def app_mode() -> str:
    """Active APP_MODE (env > .env > 'dev'). Matches .mcp.json + ragctl convention."""
    return os.environ.get("APP_MODE", "dev")


def _port_from_url(url: str, default: str) -> str:
    try:
        from urllib.parse import urlparse
        p = urlparse(url).port
        if p:
            return str(p)
    except Exception:
        pass
    return default


def _ports() -> dict:
    """Resolve backend + web ports. Prefer explicit env, then config URLs."""
    bport = (
        os.environ.get("BACKEND_PORT")
        or _port_from_url(getattr(_config, "BACKEND_URL", ""), "8765")
    )
    wport = (
        os.environ.get("WEB_PORT")
        or os.environ.get("FRONTEND_PORT")
        or _port_from_url(getattr(_config, "WEB_URL", ""), "6789")
    )
    return {"backend": int(bport), "web": int(wport)}


def _backend_url() -> str:
    return getattr(_config, "BACKEND_URL", f"http://localhost:{_ports()['backend']}")


def _web_url() -> str:
    return getattr(_config, "WEB_URL", f"http://localhost:{_ports()['web']}")


# ── Probes ───────────────────────────────────────────────────────────────
def port_listening(port: int, host: str = "127.0.0.1", timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _http_ok(url: str, timeout: float = 3.0) -> tuple[bool, str]:
    """Probe an HTTP endpoint. Returns (ok, detail). trust_env=False avoids
    HTTPS_PROXY hijacking localhost (per project convention)."""
    try:
        import httpx
        with httpx.Client(timeout=timeout, trust_env=False) as c:
            r = c.get(url)
            return (r.status_code == 200, f"HTTP {r.status_code}")
    except Exception as e:
        return (False, str(e)[:140])


def _pid_on_port(port: int) -> int | None:
    """Best-effort PID lookup for the process listening on `port`."""
    try:
        if sys.platform == "win32":
            out = subprocess.run(
                ["cmd", "/c", f"netstat -ano | findstr :{port} | findstr LISTENING"],
                capture_output=True, text=True, timeout=5,
                **_run_silent_args(),
            ).stdout
            line = out.strip().splitlines()
            if line:
                return int(line[0].split()[-1])
        else:
            out = subprocess.run(
                ["sh", "-c", f"lsof -ti:{port} 2>/dev/null || ss -tlnp 2>/dev/null | grep ':{port}'"],
                capture_output=True, text=True, timeout=5,
            ).stdout
            if out.strip():
                return int(out.strip().splitlines()[0].split()[0])
    except Exception:
        pass
    return None


# ── Executable resolution ────────────────────────────────────────────────
def _which(name: str) -> str:
    """Resolve the FULL PATH to an executable (uv/node) so we can spawn it
    directly via CreateProcess without a shell.

    Search order:
      1. ``shutil.which`` (honors PATH + PATHEXT)
      2. Common install dirs that aren't always on PATH in fresh terminals:
         - uv:  ``~/.local/bin`` (standalone installer), ``~/.cargo/bin`` (cargo)
         - node: ``%APPDATA%\\npm``, ``%ProgramFiles%\\nodejs``
      3. Bare name + ``.exe`` fallback (lets the OS try one last time)

    Returns the resolved path or the bare name so the caller always gets a
    usable string.
    """
    from shutil import which as _shutil_which

    found = _shutil_which(name)
    if found:
        return found

    home = Path.home()
    if sys.platform == "win32":
        exe = f"{name}.exe"
        candidates = [
            home / ".local" / "bin" / exe,                 # modern uv
            home / ".cargo" / "bin" / exe,                 # legacy uv (cargo)
            home / "AppData" / "Roaming" / "npm" / exe,    # node/npm global
            home / "AppData" / "Local" / "Programs" / name / exe,
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "nodejs" / exe,
        ]
    else:
        candidates = [
            home / ".local" / "bin" / name,
            home / ".cargo" / "bin" / name,
            Path("/usr/local/bin") / name,
            Path("/usr/bin") / name,
        ]
    for c in candidates:
        try:
            if c.is_file():
                return str(c)
        except OSError:
            continue

    # Last resort: bare name (+ .exe on Windows); CreateProcess will search PATH.
    return f"{name}.exe" if sys.platform == "win32" else name


# ── Silent launch ────────────────────────────────────────────────────────
def _silent_flags() -> dict:
    """Always-headless subprocess flags — no console/GUI window ever, dev AND
    prod, every OS.

    Windows strategy (defense in depth — three independent layers):
      1. ``CREATE_NO_WINDOW`` — console-subsystem process with a HIDDEN console.
         Children INHERIT this hidden console, so they never call
         ``AllocConsole()`` to make a new visible one. (MUST NOT be combined
         with ``DETACHED_PROCESS``: per MSDN, ``CREATE_NO_WINDOW`` is *ignored*
         when ``DETACHED_PROCESS`` is also set, and ``DETACHED_PROCESS`` alone
         risks child processes allocating a fresh visible console.)
      2. ``CREATE_NEW_PROCESS_GROUP`` — isolates Ctrl-C so the launcher's signal
         handling never cascades into the service.
      3. ``STARTUPINFO(STARTF_USESHOWWINDOW, SW_HIDE)`` — if the binary is
         GUI-subsystem or spawns a windowed helper, force-hide the window.

    POSIX: ``start_new_session`` detaches from the controlling terminal.
    """
    if sys.platform == "win32":
        flags = 0
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            flags |= subprocess.CREATE_NO_WINDOW
        if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
            flags |= subprocess.CREATE_NEW_PROCESS_GROUP
        si = subprocess.STARTUPINFO()  # type: ignore[attr-defined]
        si.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 0)
        si.wShowWindow = 0  # SW_HIDE
        return {"creationflags": flags, "startupinfo": si}
    return {"start_new_session": True}


def _run_silent_args() -> dict:
    """Kwargs for ``subprocess.run`` so status probes (netstat/lsof/taskkill)
    never flash a console window on Windows. Combine with capture_output=True."""
    if sys.platform == "win32":
        flags = 0
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            flags |= subprocess.CREATE_NO_WINDOW
        si = subprocess.STARTUPINFO()  # type: ignore[attr-defined]
        si.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 0)
        si.wShowWindow = 0  # SW_HIDE
        return {"creationflags": flags, "startupinfo": si}
    return {}


def start_service(name: str, mode: str | None = None) -> dict:
    """Silently launch one service (backend|web). Headless + logged.

    Does NOT wait for readiness — returns pid + log path immediately.
    Truncates the shared log file on start (matches ragctl + Tauri).
    """
    mode = mode or app_mode()
    if name == "backend":
        if not BACKEND_DIR.exists():
            return {"success": False, "service": name, "error": f"backend dir not found: {BACKEND_DIR}"}
        uv_bin = _which("uv")
        cmd = [uv_bin, "run", "python", "main.py"]
        cwd = str(BACKEND_DIR)
    elif name == "web":
        if not WEB_DIR.exists():
            return {"success": False, "service": name, "error": f"web dir not found: {WEB_DIR}"}
        node_bin = _which("node")
        cmd = [node_bin, "start.mjs"]
        cwd = str(WEB_DIR)
    else:
        return {"success": False, "service": name, "error": f"unknown service: {name} (backend|web)"}

    log_path = LOG_PATHS[name]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = open(log_path, "w", encoding="utf-8", errors="replace")  # truncate on start
    try:
        env = {
            **os.environ,
            "APP_MODE": mode,
            "PYTHONUTF8": "1",
            "PYTHONUNBUFFERED": "1",
        }
        # Pin ports so web proxies to the correct backend even when .env differs.
        ports = _ports()
        env["BACKEND_PORT"] = str(ports["backend"])
        env["WEB_PORT"] = str(ports["web"])
        env["FRONTEND_PORT"] = str(ports["web"])
        env["BACKEND_URL"] = f"http://localhost:{ports['backend']}"
        proc = subprocess.Popen(
            cmd, cwd=cwd, env=env,
            stdin=subprocess.DEVNULL,
            stdout=log, stderr=subprocess.STDOUT,
            **_silent_flags(),
        )
        return {
            "success": True, "service": name, "pid": proc.pid, "mode": mode,
            "cmd": " ".join(cmd), "cwd": cwd, "log_path": str(log_path),
            "note": "silent launch (no terminal window); poll kb_project_status for readiness",
        }
    except FileNotFoundError as e:
        return {"success": False, "service": name, "error": f"executable not found: {e.filename or e}"}
    finally:
        log.close()


def start_neo4j() -> dict:
    """Start Neo4j via docker compose (optional — requires Docker). Silent."""
    compose = PROJECT_ROOT / "docker-compose.yml"
    if not compose.exists():
        return {"success": False, "service": "neo4j", "error": "docker-compose.yml not found"}
    try:
        subprocess.Popen(
            ["docker", "compose", "up", "-d", "neo4j"],
            cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            **_silent_flags(),
        )
        return {"success": True, "service": "neo4j", "note": "docker compose up -d neo4j (detached, silent)"}
    except FileNotFoundError:
        return {"success": False, "service": "neo4j", "error": "docker not found on PATH"}


def _preflight_problems() -> list[str]:
    """Detect an un-set-up project so kb_project_start fails fast with an
    actionable message instead of (a) silently triggering a multi-GB torch
    download via `uv run` auto-sync, or (b) crashing `node start.mjs` because
    web/node_modules is missing. Empty list = good to go."""
    problems = []
    if not (PROJECT_ROOT / ".env").exists():
        problems.append(
            ".env missing (config file). ragctl setup creates it from .env.example."
        )
    if not (BACKEND_DIR / "app" / "main.py").exists():
        problems.append(
            "backend/ directory missing. Run: ragctl setup"
        )
    elif not (BACKEND_DIR / ".venv").exists() and not (BACKEND_DIR / "uv.lock").exists():
        problems.append(
            "backend dependencies not installed (no .venv/uv.lock). ragctl setup runs `uv sync`."
        )
    if not (WEB_DIR / "package.json").exists():
        problems.append(
            "web/ directory missing. Run: ragctl setup"
        )
    elif not (WEB_DIR / "node_modules").exists():
        problems.append(
            "web dependencies not installed (no node_modules). ragctl setup runs `npm install`."
        )
    return problems


def preflight() -> dict:
    """Return whether the project is ready to start services, plus any problems.
    Exposed so callers (MCP tool, agent) can check before attempting a launch."""
    problems = _preflight_problems()
    return {
        "ready_to_start": not problems,
        "problems": problems,
        "fix": (
            "Run `ragctl setup` (one-click: uv + deps + model + .env), "
            "or invoke the knowledgebase-init skill for a guided wizard."
            if problems else ""
        ),
        "setup_command": "node command/ragctl.js setup",
    }


def start_project(
    backend: bool = True,
    web: bool = True,
    neo4j: bool = False,
    mode: str = "",
    wait: bool = False,
    timeout: int = 45,
) -> dict:
    """Silently start project services. Headless on every OS/mode.

    Args:
        backend: start the FastAPI backend (default True)
        web: start the Nuxt web server (default True)
        neo4j: start Neo4j via docker compose (default False; needs Docker)
        mode: override APP_MODE ("dev"|"prod"); "" = use current env
        wait: if True, block until backend+web HTTP-healthy or timeout
        timeout: max seconds to wait when wait=True

    Fails fast with an actionable `preflight` block if the project hasn't been
    set up yet (missing .env / submodules / deps) — so the caller never waits
    on a silent multi-GB download or a crash.
    """
    pf = preflight()
    if not pf["ready_to_start"]:
        return {
            "success": False,
            "error": "project not set up — services cannot start cleanly",
            "preflight": pf,
            "hint": "Run ragctl setup first, then retry kb_project_start.",
        }

    m = mode or app_mode()
    ports = _ports()
    launched = []

    def _already(svc: str, port: int) -> bool:
        if port_listening(port):
            launched.append({"success": True, "service": svc,
                             "note": f"already listening on port {port} — skipped"})
            return True
        return False

    if backend and not _already("backend", ports["backend"]):
        launched.append(start_service("backend", m))
    if web and not _already("web", ports["web"]):
        launched.append(start_service("web", m))
    if neo4j:
        if port_listening(NEO4J_BOLT_PORT):
            launched.append({"success": True, "service": "neo4j",
                             "note": f"already listening on port {NEO4J_BOLT_PORT} — skipped"})
        else:
            launched.append(start_neo4j())

    waited = _wait_ready(timeout=timeout) if wait else None
    return {
        "success": True,
        "mode": m,
        "headless": True,
        "launched": launched,
        "wait": waited,
        "status": project_status(),
    }


# ── Readiness wait + full status ─────────────────────────────────────────
def _wait_ready(timeout: int = 45) -> dict:
    """Poll backend+web health until both ok or timeout. Blocking."""
    deadline = time.time() + timeout
    b_url, w_url = _backend_url(), _web_url()
    start = time.time()
    while time.time() < deadline:
        b_ok, _ = _http_ok(f"{b_url}/api/v1/health", timeout=2)
        w_ok, _ = _http_ok(f"{w_url}/api/kb/catalog", timeout=2)
        if b_ok and w_ok:
            return {"ready": True, "elapsed_s": round(time.time() - start)}
        time.sleep(2)
    return {"ready": False, "timeout_s": timeout, "elapsed_s": round(time.time() - start)}


def project_status() -> dict:
    """Full project service status — ports listening + HTTP health + pids + log paths + MinerU."""
    ports = _ports()
    b_url, w_url = _backend_url(), _web_url()
    mode = app_mode()

    # backend
    b_listen = port_listening(ports["backend"])
    if b_listen:
        b_ok, b_detail = _http_ok(f"{b_url}/api/v1/health")
    else:
        b_ok, b_detail = False, "port not listening"

    # web
    w_listen = port_listening(ports["web"])
    if w_listen:
        w_ok, w_detail = _http_ok(f"{w_url}/api/kb/catalog")
    else:
        w_ok, w_detail = False, "port not listening"

    # neo4j
    n_bolt = port_listening(NEO4J_BOLT_PORT)
    n_http = port_listening(NEO4J_HTTP_PORT)

    # mineru — only meaningful when backend is up
    mineru: dict = {"available": False, "detail": "backend down"}
    if b_ok:
        m_ok, m_detail = _http_ok(f"{b_url}/api/v1/mineru/status", timeout=5)
        mineru = {"available": m_ok, "detail": m_detail}

    services = {
        "backend": {
            "port": ports["backend"], "port_listening": b_listen,
            "http_ok": b_ok, "detail": b_detail,
            "pid": _pid_on_port(ports["backend"]),
            "url": b_url, "log_path": str(LOG_PATHS["backend"]),
        },
        "web": {
            "port": ports["web"], "port_listening": w_listen,
            "http_ok": w_ok, "detail": w_detail,
            "pid": _pid_on_port(ports["web"]),
            "url": w_url, "log_path": str(LOG_PATHS["web"]),
        },
        "neo4j": {
            "bolt_port": NEO4J_BOLT_PORT, "bolt_listening": n_bolt,
            "http_port": NEO4J_HTTP_PORT, "http_listening": n_http,
            "log_path": "(docker-managed)",
        },
        "mineru": mineru,
    }
    ready = b_ok and w_ok
    return {
        "success": True,
        "ready": ready,
        "app_mode": mode,
        "project_root": str(PROJECT_ROOT),
        "services": services,
        "summary": (
            f"backend {'UP' if b_ok else 'DOWN'}(:{ports['backend']}) · "
            f"web {'UP' if w_ok else 'DOWN'}(:{ports['web']}) · "
            f"neo4j {'UP' if n_bolt else 'down'}(:{NEO4J_BOLT_PORT}) · "
            f"mineru {'up' if mineru['available'] else 'n/a'}"
        ),
    }


# ── Version / Update (delegates to ragctl.js — single source of truth) ───
def _ragctl_js() -> Path:
    return PROJECT_ROOT / "command" / "ragctl.js"


def _extract_json_blob(text: str):
    """Extract a top-level JSON object from mixed human+JSON stdout.

    ragctl prints a human header then a JSON object when --json is set.
    A naive rfind('{') hits nested objects and fails — prefer a full-line
    JSON object, then balanced-brace scan.
    """
    if not text:
        return None
    import json as _json

    try:
        return _json.loads(text)
    except Exception:
        pass

    # Prefer a line that is itself a complete JSON object
    for line in reversed(text.splitlines()):
        s = line.strip()
        if s.startswith("{") and s.endswith("}"):
            try:
                return _json.loads(s)
            except Exception:
                continue

    # Balanced-brace scan from each '{'
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        depth = 0
        in_str = False
        escape = False
        for j in range(i, len(text)):
            c = text[j]
            if in_str:
                if escape:
                    escape = False
                elif c == "\\":
                    escape = True
                elif c == '"':
                    in_str = False
                continue
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[i : j + 1]
                    try:
                        return _json.loads(candidate)
                    except Exception:
                        break
    return None


def _run_ragctl(args: list[str], timeout: int = 180) -> dict:
    """Run `node command/ragctl.js <args>` and return structured result.

    Prefers --json output when the subcommand supports it. Never raises —
    returns {success, exit_code, stdout, stderr, data?} so MCP tools stay
    resilient under network / git failures.
    """
    js = _ragctl_js()
    if not js.exists():
        return {
            "success": False,
            "error": f"ragctl.js not found at {js}",
            "hint": "Are you inside a full rag-knowledge checkout?",
        }
    node = _which("node")
    try:
        proc = subprocess.run(
            [node, str(js), *args],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
            **_run_silent_args(),
        )
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"ragctl {' '.join(args)} timed out after {timeout}s"}
    except FileNotFoundError:
        return {"success": False, "error": "node not found on PATH — install Node.js ≥18"}
    except Exception as e:
        return {"success": False, "error": f"failed to run ragctl: {e}"}

    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    data = _extract_json_blob(stdout)

    return {
        "success": proc.returncode == 0,
        "exit_code": proc.returncode,
        "stdout": stdout[-4000:] if stdout else "",
        "stderr": stderr[-2000:] if stderr else "",
        "data": data,
        "command": f"node command/ragctl.js {' '.join(args)}",
    }


def project_version(local_only: bool = False) -> dict:
    """Return local VERSION + optional remote GitHub comparison via ragctl version --json."""
    args = ["version", "--json"]
    if local_only:
        args.append("--local")
    result = _run_ragctl(args, timeout=30)
    if result.get("data"):
        return {"success": True, **result["data"], "via": "ragctl"}
    # Fallback: read VERSION file directly if ragctl failed
    ver_file = PROJECT_ROOT / "VERSION"
    local_ver = ver_file.read_text(encoding="utf-8").strip() if ver_file.exists() else "0.0.0"
    return {
        "success": result.get("success", False),
        "local": {"version": local_ver, "project_root": str(PROJECT_ROOT)},
        "remote": None,
        "update_available": None,
        "error": result.get("error") or result.get("stderr") or "ragctl version failed",
        "via": "fallback",
    }


def project_update(
    check_only: bool = False,
    force: bool = False,
    no_deps: bool = False,
    restart: bool = False,
) -> dict:
    """Check GitHub for a newer version and optionally pull it via ragctl update.

    Args:
        check_only: dry-run — report only, never pull
        force: pull even if versions look equal / dirty worktree
        no_deps: after pull, skip `ragctl deps`
        restart: after pull, run `ragctl up --force`
    """
    args = ["update", "--json", "--yes"]
    if check_only:
        args.append("--check")
    if force:
        args.append("--force")
    if no_deps:
        args.append("--no-deps")
    if restart:
        args.append("--restart")
    # Pull can take a while (network + submodule + optional deps)
    timeout = 60 if check_only else 600
    result = _run_ragctl(args, timeout=timeout)
    payload = {
        "success": result.get("success", False),
        "check_only": check_only,
        "command": result.get("command"),
        "exit_code": result.get("exit_code"),
    }
    if result.get("data"):
        payload.update(result["data"])
    else:
        payload["stdout"] = result.get("stdout")
        payload["stderr"] = result.get("stderr")
        if result.get("error"):
            payload["error"] = result["error"]
    return payload
