#!/usr/bin/env python3
"""mcp_ensure — 作 业 前 确 保 kb-mcp 已 启 动 且 可 连 接 （幂等，标准前置检查）

对任何 harness（Claude Code / OMP / ZCode / chat API）作业前跑一次：

    python scripts/mcp_ensure.py                 # 校验项目 .mcp.json
    python scripts/mcp_ensure.py --config .omp/mcp.json --config .zcode/mcp.json

它做什么（start-then-execute；已启动则直接验证连接）：
  1. 读取 MCP 配置文件，取每个 server 的原样 spawn 命令（与 harness 启动时完全一致）；
  2. 用该命令 spawn 一个探活实例 → 真 MCP 握手（initialize → initialized → tools/list）
     → 确认工具清单可读 → 干净关闭（stdio server 本就按客户端会话各自 spawn，
     探活实例退出不影响服务链）；
  3. kb-mcp 的启动钩子会自动拉起 backend/web（若已启动则直接复用，幂等），
     脚本随后轮询两个健康端点，确认整条服务链就绪；
  4. 全绿 exit 0，任何一步失败 exit 1 并给出可执行的修复指引。

安全边界：健康探测仅允许来自环境或配置的回环 HTTP(S) 地址；禁用代理和重定向。
注意：执行本脚本会启动配置的 MCP 进程，kb-mcp 的启动钩子可能启动服务。

注意：本脚本只做"确保可连接"，不承载业务检索；会话内 agent 的预检仍以
skill 规定的 kb_project_status 为准。
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

try:
    import yaml
except ImportError:  # config.yml parsing is best-effort without PyYAML
    yaml = None

MAX_CONFIG_BYTES = 1024 * 1024
MAX_STDOUT_LINE = 1024 * 1024
MAX_STDOUT_TOTAL = 8 * 1024 * 1024
MAX_STDERR_BYTES = 64 * 1024
SAFE_DIAGNOSTICS = (
    (re.compile(r"timed?\s*out|timeout", re.I), "timeout"),
    (re.compile(r"enoent|not found|no such file|cannot find", re.I), "file or command not found"),
    (re.compile(r"eacces|permission denied", re.I), "permission denied"),
    (re.compile(r"mcp.*(?:fail|error|disconnect)", re.I), "MCP connection failure"),
    (re.compile(r"error|failed|exception", re.I), "startup error"),
)

REPO = Path(__file__).resolve().parents[1]
PROTOCOL_VERSION = "2024-11-05"
HANDSHAKE_TIMEOUT = 180.0  # peer wait + own launch + uv/OMP cold startup
LIST_TIMEOUT = 30.0
HEALTH_TIMEOUT = 60.0


def _send(proc: subprocess.Popen, obj: dict) -> None:
    assert proc.stdin is not None
    proc.stdin.write((json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8"))
    proc.stdin.flush()


def _sanitized_diagnostic(stderr_tail: bytes) -> list[str]:
    """Return bounded fixed categories only; never surface process text/secrets."""
    text = stderr_tail.decode("utf-8", errors="replace")[-MAX_STDERR_BYTES:]
    categories: list[str] = []
    for pattern, category in SAFE_DIAGNOSTICS:
        if pattern.search(text):
            categories.append(category)
    return categories[:5]


def _recv(proc: subprocess.Popen, want_id: int, timeout_s: float,
          stdout_queue: queue.Queue, state: dict) -> dict:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            item = stdout_queue.get(timeout=min(0.25, max(0.0, deadline - time.monotonic())))
        except queue.Empty:
            if proc.poll() is not None:
                break
            continue
        if item is None:
            break
        state["total"] += len(item)
        if state["total"] > MAX_STDOUT_TOTAL or len(item) > MAX_STDOUT_LINE:
            raise RuntimeError("MCP server exceeded bounded stdout limits")
        line = item.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg.get("id") == want_id:
            return msg
    raise TimeoutError(f"no response for id={want_id} within {timeout_s:.0f}s")


def _read_bounded_config(path: Path) -> dict:
    with path.open("rb") as stream:
        raw = stream.read(MAX_CONFIG_BYTES + 1)
    if len(raw) > MAX_CONFIG_BYTES:
        raise ValueError("configuration exceeds 1 MiB limit")
    parsed = json.loads(raw.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("configuration root must be an object")
    return parsed


def _configured_health_endpoints() -> dict:
    """Read loopback ports from env/config without permitting remote URLs."""
    env_path = REPO / ".env"
    env: dict[str, str] = {}
    try:
        if env_path.stat().st_size <= MAX_CONFIG_BYTES:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env[key.strip()] = value.strip().strip("\"'")
    except OSError:
        pass

    cfg: dict = {}
    try:
        config_path = REPO / "config.yml"
        if yaml and config_path.stat().st_size <= MAX_CONFIG_BYTES:
            cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception:  # invalid or unavailable YAML: fall back to env/defaults
        pass

    # Match kb-mcp/config.py: process environment wins per key, then .env.
    env.update(os.environ)
    mode = env.get("APP_MODE", "dev")
    section = (cfg.get("server") or {}).get(mode) or (cfg.get("server") or {}).get("dev") or {}
    backend_url = env.get("BACKEND_URL")
    backend_port = env.get("BACKEND_PORT")
    if not backend_url and backend_port:
        backend_url = f"http://127.0.0.1:{backend_port}"
    backend_url = backend_url or section.get("backend_url")
    if not backend_url:
        port = backend_port or section.get("backend_port", 8765)
        backend_url = f"http://127.0.0.1:{port}"
    web_url = env.get("WEB_URL")
    if not web_url:
        web_port = env.get("WEB_PORT") or env.get("FRONTEND_PORT")
        configured_url = section.get("frontend_url")
        if web_port:
            host = env.get("WEB_HOST") or "127.0.0.1"
            web_url = f"http://{host}:{web_port}"
        elif configured_url:
            web_url = str(configured_url)
        else:
            host = env.get("WEB_HOST") or "127.0.0.1"
            web_url = f"http://{host}:{section.get('frontend_port', 6789)}"

    result = {}
    for label, raw_url, suffix in (("backend", backend_url, "/api/v1/health"),
                                   ("web", web_url, "/")):
        parts = urlsplit(str(raw_url))
        try:
            port = parts.port
        except ValueError as exc:
            raise ValueError(f"invalid {label} endpoint port") from exc
        if parts.scheme not in ("http", "https") or parts.hostname not in ("localhost", "127.0.0.1", "::1"):
            raise ValueError(f"{label} health endpoint must use a loopback host and http(s)")
        if parts.username or parts.password or parts.query or parts.fragment:
            raise ValueError(f"{label} health endpoint contains unsupported components")
        authority = f"[{parts.hostname}]" if ":" in parts.hostname else parts.hostname
        if port:
            authority += f":{port}"
        base = f"{parts.scheme}://{authority}{parts.path.rstrip('/') if parts.path != '/' else ''}"
        result[label] = f"{base}{suffix}"
    return result


def _expand_config_value(value: object, variables: dict[str, str]) -> str:
    """Expand only environment-style variables used by MCP configs."""
    pattern = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)")
    return pattern.sub(lambda match: variables.get(match.group(1) or match.group(2), match.group(0)), str(value))


def check_stdio_server(name: str, cfg: dict) -> dict:
    """Spawn the configured stdio server and perform MCP initialize/tools/list."""
    if not isinstance(cfg, dict) or not isinstance(cfg.get("command"), str):
        return {"name": name, "ok": False, "error": "invalid stdio server configuration"}
    raw_env = cfg.get("env") or {}
    if not isinstance(raw_env, dict):
        return {"name": name, "ok": False, "error": "invalid MCP environment configuration"}
    variables = dict(os.environ)
    variables.setdefault("RAG_PROJECT_ROOT", str(REPO))
    config_env = {str(k): _expand_config_value(v, variables) for k, v in raw_env.items()}
    variables.update(config_env)
    command = [_expand_config_value(cfg["command"], variables)] + [
        _expand_config_value(a, variables) for a in cfg.get("args", [])
    ]
    env = dict(os.environ)
    env.update(config_env)
    env.setdefault("PYTHONUTF8", "1")
    # Both project .mcp.json and .omp/mcp.json run from the project root;
    # .omp is a configuration directory, not the server's working directory.
    cwd = str(REPO.resolve())

    t0 = time.perf_counter()
    try:
        proc = subprocess.Popen(
            command, cwd=cwd, env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, bufsize=0)
    except OSError as exc:
        return {"name": name, "ok": False,
                "error": "could not spawn configured MCP command",
                "diagnostics": ["file or command not found" if getattr(exc, "errno", None) == 2
                                else "permission denied" if getattr(exc, "errno", None) == 13
                                else "spawn failure"]}

    stdout_queue: queue.Queue = queue.Queue(maxsize=256)
    state = {"total": 0}
    stderr_tail = bytearray()
    stderr_lock = threading.Lock()

    def read_stdout() -> None:
        assert proc.stdout is not None
        try:
            while True:
                line = proc.stdout.readline(MAX_STDOUT_LINE + 1)
                if not line:
                    break
                try:
                    stdout_queue.put(line, timeout=1)
                except queue.Full:
                    break
        finally:
            try:
                stdout_queue.put_nowait(None)
            except queue.Full:
                try:
                    stdout_queue.get_nowait()
                    stdout_queue.put_nowait(None)
                except (queue.Empty, queue.Full):
                    pass

    def drain_stderr() -> None:
        assert proc.stderr is not None
        while True:
            chunk = proc.stderr.read(4096)
            if not chunk:
                return
            with stderr_lock:
                stderr_tail.extend(chunk)
                if len(stderr_tail) > MAX_STDERR_BYTES:
                    del stderr_tail[:-MAX_STDERR_BYTES]

    stdout_thread = threading.Thread(target=read_stdout, daemon=True)
    stderr_thread = threading.Thread(target=drain_stderr, daemon=True)
    stdout_thread.start()
    stderr_thread.start()
    watchdog = threading.Timer(HANDSHAKE_TIMEOUT + LIST_TIMEOUT + 15, proc.kill)
    watchdog.daemon = True
    watchdog.start()
    out: dict = {"name": name, "command": Path(command[0]).name, "ok": False}
    try:
        _send(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                     "params": {"protocolVersion": PROTOCOL_VERSION, "capabilities": {},
                                "clientInfo": {"name": "mcp-ensure", "version": "1.0"}}})
        init = _recv(proc, 1, HANDSHAKE_TIMEOUT, stdout_queue, state)
        if "error" in init:
            raise RuntimeError("initialize returned an MCP error")
        _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        _send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        listing = _recv(proc, 2, LIST_TIMEOUT, stdout_queue, state)
        tools = [t.get("name") for t in (listing.get("result") or {}).get("tools", [])
                 if isinstance(t, dict)]
        if not tools:
            raise RuntimeError("tools/list returned zero tools")
        out.update(ok=True, tools=len(tools),
                   sample=[t for t in tools if t in
                           ("kb_list", "kb_search_vector", "kb_doc_read", "kb_laya_judge")],
                   seconds=round(time.perf_counter() - t0, 1))
    except Exception as exc:  # noqa: BLE001 — keep diagnostics non-sensitive
        out["error"] = (str(exc) if isinstance(exc, (RuntimeError, TimeoutError))
                        else f"MCP handshake failed ({type(exc).__name__})")
        with stderr_lock:
            tail = bytes(stderr_tail)
        diagnostics = _sanitized_diagnostic(tail)
        if diagnostics:
            out["diagnostics"] = diagnostics
    finally:
        watchdog.cancel()
        try:
            if proc.stdin:
                proc.stdin.close()
        except OSError:
            pass
        if proc.poll() is None:
            proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)
        for stream in (proc.stdout, proc.stderr):
            if stream:
                stream.close()
    return out


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: object, fp: object, code: int, msg: str,
                         headers: object, newurl: str) -> None:
        return None


def wait_services(deadline_s: float) -> dict:
    """Wait for configured local service endpoints; remote hosts are rejected."""
    urls = _configured_health_endpoints()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    deadline = time.monotonic() + deadline_s
    statuses = {"backend": 0, "web": 0}
    while time.monotonic() < deadline:
        for label, url in urls.items():
            if statuses[label] == 200:
                continue
            try:
                with opener.open(url, timeout=min(4, max(0.01, deadline - time.monotonic()))) as response:
                    statuses[label] = response.status
            except urllib.error.HTTPError as exc:
                statuses[label] = exc.code
            except Exception:
                statuses[label] = 0
        if all(status == 200 for status in statuses.values()):
            break
        time.sleep(min(3, max(0, deadline - time.monotonic())))
    return {label: {"url": urls[label], "status": statuses[label]} for label in urls}


def main() -> int:
    ap = argparse.ArgumentParser(description="Ensure kb-mcp is started & connectable (idempotent)")
    ap.add_argument("--config", action="append", default=[],
                    help="MCP 配置文件（可重复）；默认项目 .mcp.json")
    ap.add_argument("--skip-services", action="store_true",
                    help="只验 MCP 握手，不等待 backend/web 健康端点")
    args = ap.parse_args()

    configs: list[Path] = [Path(p) for p in args.config] or [REPO / ".mcp.json"]
    all_ok = True

    print(f"[mcp-ensure] repo = {REPO}")
    for cfg_path in configs:
        if not cfg_path.is_absolute():
            cfg_path = REPO / cfg_path
        print(f"\n[mcp-ensure] config: {cfg_path}")
        if not cfg_path.exists():
            print("  ❌ 配置文件不存在")
            all_ok = False
            continue
        try:
            servers = _read_bounded_config(cfg_path).get("mcpServers") or {}
        except Exception as exc:  # noqa: BLE001
            print(f"  ❌ 配置解析失败: {exc}")
            all_ok = False
            continue
        if not servers:
            print("  ⚠️ 配置里没有 mcpServers 条目")
            all_ok = False
            continue
        for name, cfg in servers.items():
            r = check_stdio_server(name, cfg)
            if r["ok"]:
                sample = f" 关键工具: {r['sample']}" if r.get("sample") else ""
                print(f"  ✅ {name}: 握手+tools/list OK · {r['tools']} tools · "
                      f"{r['seconds']}s{sample}")
            else:
                print(f"  ❌ {name}: {r.get('error')}")
                if r.get("diagnostics"):
                    print(f"     diagnostics: {', '.join(r['diagnostics'])}")
                all_ok = False

    if not args.skip_services:
        print("\n[mcp-ensure] 服务链（kb-mcp 启动钩子应已自动拉起；已启动则直接复用）")
        svc = wait_services(HEALTH_TIMEOUT)
        for label, s in svc.items():
            mark = "✅" if s["status"] == 200 else "❌"
            print(f"  {mark} {label}: {s['url']} → HTTP {s['status']}")
            if s["status"] != 200:
                all_ok = False

    print(f"\n[mcp-ensure] {'✅ ALL GREEN — 可以开始作业' if all_ok else '❌ NOT READY — 先修复上述问题'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
