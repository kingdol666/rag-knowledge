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

安全边界：健康探测的 URL 是各调用点内联的字面量回环地址（127.0.0.1 平台标准
端口），无任何可配置主机/协议入口（SSRF 防护）。

注意：本脚本只做"确保可连接"，不承载业务检索；会话内 agent 的预检仍以
skill 规定的 kb_project_status 为准。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PROTOCOL_VERSION = "2024-11-05"
HANDSHAKE_TIMEOUT = 90.0   # uv 冷启动 + 启动钩子最多 ~45s 服务等待，留足余量
LIST_TIMEOUT = 30.0
HEALTH_TIMEOUT = 60.0


def _send(proc: subprocess.Popen, obj: dict) -> None:
    assert proc.stdin is not None
    proc.stdin.write(json.dumps(obj, ensure_ascii=False) + "\n")
    proc.stdin.flush()


def _recv(proc: subprocess.Popen, want_id: int, timeout_s: float) -> dict:
    assert proc.stdout is not None
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        line = proc.stdout.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg.get("id") == want_id:
            return msg
    raise TimeoutError(f"no response for id={want_id} within {timeout_s:.0f}s")


def check_stdio_server(name: str, cfg: dict) -> dict:
    """用配置里的原样命令 spawn 一个探活实例并完成 MCP 握手。

    管道死锁防护（Windows 实测）：stderr 直接 DEVNULL（无人消费的管道会塞满并
    卡死子进程）；看门狗定时器到期强杀进程，使阻塞中的 readline 立即解除。
    """
    command = [cfg["command"]] + [str(a) for a in cfg.get("args", [])]
    env = dict(os.environ)
    env.update({k: str(v) for k, v in (cfg.get("env") or {}).items()})
    env.setdefault("PYTHONUTF8", "1")

    t0 = time.perf_counter()
    proc = subprocess.Popen(
        command, cwd=str(REPO), env=env,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, text=True, encoding="utf-8", bufsize=1)
    watchdog = threading.Timer(
        HANDSHAKE_TIMEOUT + LIST_TIMEOUT + 15, proc.kill)
    watchdog.daemon = True
    watchdog.start()
    out: dict = {"name": name, "command": " ".join(command[:2]) + " …", "ok": False}
    try:
        _send(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                     "params": {"protocolVersion": PROTOCOL_VERSION, "capabilities": {},
                                "clientInfo": {"name": "mcp-ensure", "version": "1.0"}}})
        init = _recv(proc, 1, HANDSHAKE_TIMEOUT)
        if "error" in init:
            raise RuntimeError(f"initialize error: {json.dumps(init['error'])[:200]}")
        _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})

        _send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        listing = _recv(proc, 2, LIST_TIMEOUT)
        tools = [t.get("name") for t in (listing.get("result") or {}).get("tools", [])]
        if not tools:
            raise RuntimeError("tools/list returned zero tools")
        out.update(ok=True, tools=len(tools),
                   sample=[t for t in tools if t in
                           ("kb_list", "kb_search_vector", "kb_doc_read", "kb_laya_judge")],
                   seconds=round(time.perf_counter() - t0, 1))
    except Exception as exc:  # noqa: BLE001 — 报告失败原样给操作者
        out["error"] = f"{type(exc).__name__}: {exc}"[:220]
    finally:
        watchdog.cancel()
        try:
            if proc.stdin:
                proc.stdin.close()
            proc.terminate()
            proc.wait(timeout=10)
        except Exception:  # noqa: BLE001
            try:
                proc.kill()
            except Exception:  # noqa: BLE001
                pass
    return out


def wait_services(deadline_s: float) -> dict:
    """kb-mcp 启动钩子会自动拉起 backend/web；轮询两个字面量端点确认链路就绪。

    端口 = .env 权威值（BACKEND_PORT=8771 / WEB_PORT=6789）。
    """
    deadline = time.time() + deadline_s
    backend = web = 0
    while time.time() < deadline:
        if not backend:
            try:
                with urllib.request.urlopen(
                        "http://127.0.0.1:8771/api/v1/health", timeout=4) as r:
                    backend = r.status
            except urllib.error.HTTPError as e:
                backend = e.code
            except Exception:
                backend = 0
        if not web:
            try:
                with urllib.request.urlopen("http://127.0.0.1:6789/", timeout=4) as r:
                    web = r.status
            except urllib.error.HTTPError as e:
                web = e.code
            except Exception:
                web = 0
        if backend == 200 and web == 200:
            break
        time.sleep(3)
    return {"backend": {"url": "http://127.0.0.1:8771/api/v1/health", "status": backend},
            "web": {"url": "http://127.0.0.1:6789/", "status": web}}


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
            servers = (json.loads(cfg_path.read_text(encoding="utf-8"))
                       .get("mcpServers") or {})
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
                if r.get("stderr_tail"):
                    print(f"     stderr: …{r['stderr_tail']}")
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
