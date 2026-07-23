#!/usr/bin/env python3
"""
Main entry point for RAG Knowledge Backend.

Startup contract (anti-zombie): before launching uvicorn we probe the chosen
port with a bare ``socket.bind``. If another process is actively LISTENING on
it, we print a clear error and ``sys.exit(1)`` — we never start a second
server that would fight the first one for the port (the historical source of
stale "zombie" backend processes on 8765). A port left in TIME_WAIT (a socket
that already closed) does *not* block the probe, so a clean restart right
after stopping the previous instance still works.
"""
import os
import socket
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from app.config import config

# Load root .env BEFORE anything else, so BACKEND_PORT / BACKEND_URL
# are visible to config.py properties and uvicorn port resolution.
_ROOT_DIR = Path(__file__).resolve().parent      # backend/
_PARENT_ENV = _ROOT_DIR.parent / ".env"           # rag-knowledge/.env
_SELF_ENV = _ROOT_DIR / ".env"                    # backend/.env
for env_path in (_PARENT_ENV, _SELF_ENV):
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)
        break


def _port_in_use(host: str, port: int) -> bool:
    """True iff some process is actively listening on ``host:port``.

    Uses a plain ``bind`` (no ``SO_REUSEADDR``) so that a genuinely listening
    socket fails to bind, while a leftover TIME_WAIT socket — which already
    closed and is not a real conflict — binds fine. This distinguishes "another
    server is running" (block) from "the previous instance just stopped"
    (allow).
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
    try:
        sock.bind((host, port))
    except OSError:
        return True
    finally:
        sock.close()
    return False


def main() -> int:
    # ── Step 0: 预下载 Embedding 模型 ──────────────────────────────────
    # 在服务器启动前，先确保 embedding 模型已下载到项目级 models_cache/。
    # 这样即使 HTTPS_PROXY 存在也能从本地缓存秒加载。
    # 下载失败不影响启动（向量搜索降级到 BM25）。
    try:
        from app.utils.download_model import ensure_model_downloaded  # type: ignore
        ensure_model_downloaded()
    except Exception as exc:
        print(f"[WARN] Embedding 模型预下载异常: {exc}")
        print("  → 向量搜索将在运行时降级到 BM25")

    host = config.server_host
    port = config.server_port  # env-aware single source: BACKEND_PORT env > config.yml > 8765

    print(f"Loaded configuration from config.yml [mode={config.app_mode}]")
    print(f"  Server host: {host}")
    print(f"  Server port: {port}")
    print(f"  CORS origins: {config.cors_origins}")

    # Anti-zombie guard: refuse to start if the port is already taken.
    if _port_in_use(host, port):
        print(
            f"\n[ERROR] Port {port} on {host} is already in use by another "
            f"process.\n"
            f"  Refusing to start a second backend (this prevents zombie "
            f"processes / port conflicts).\n"
            f"  → Stop the other process first, or set BACKEND_PORT=<free port>.",
            file=sys.stderr,
        )
        # Hint at what's holding it, if possible.
        try:
            import subprocess
            if sys.platform == "win32":
                r = subprocess.run(
                    ["netstat", "-ano"], capture_output=True, text=True, timeout=10
                )
                holders = [
                    line.strip() for line in r.stdout.splitlines()
                    if f":{port}" in line and "LISTENING" in line.upper()
                ]
                if holders:
                    print("  Holding process(es):", file=sys.stderr)
                    for line in holders:
                        print(f"    {line}", file=sys.stderr)
            else:
                # POSIX: prefer lsof, fall back to ss. Either may be absent.
                for cmd in (
                    ["lsof", "-iTCP:%s" % port, "-sTCP:LISTEN", "-n", "-P"],
                    ["ss", "-ltnp"],
                ):
                    try:
                        r = subprocess.run(
                            cmd, capture_output=True, text=True, timeout=10
                        )
                    except FileNotFoundError:
                        continue
                    holders = [
                        line.strip() for line in r.stdout.splitlines()
                        if f":{port}" in line
                    ]
                    if holders:
                        print("  Holding process(es):", file=sys.stderr)
                        for line in holders:
                            print(f"    {line}", file=sys.stderr)
                        break
        except Exception:
            pass
        return 1

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=config.app_mode == "dev",
        reload_dirs=[str(_ROOT_DIR / "app")] if config.app_mode == "dev" else None,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
