#!/usr/bin/env python3
"""双轨流水线预检 — 把 TEST-PLAN §0/§7 的手工纪律变成跑前防呆（只报错，不删数据）.

用法:
  python scripts/00_preflight.py            # 健康检查 + 残留 KB 探测
  python scripts/00_preflight.py R          # 额外执行 Track R 的前置断言(Hotpot 九库空态)

检查项(全部非破坏性 —— 发现问题只 fail-loud 并给出处置指引, 绝不自动删除):
  1. backend  /api/v1/health → healthy (默认 http://localhost:8771)
  2. web      /            → 200    (默认 http://localhost:6789; 6790 是死代理陷阱⑲)
  3. MCP_AUTH_TOKEN 可解析(环境变量或仓库 .env)
  4. omp 可执行(E16 作答/判分 Agent 依赖)
  5. (R) KB-Hotpot-* 九库必须为空态 —— 非空时 60_hotpot_build 会复用旧库
     并累积 "(1)" 改名副本, 全局 balance 的 stage1 候选池被实验残留挤占后
     two_stage/qdcvr 通道会静默归零(TEST-PLAN §7.3, 已实测发生)。
     实验残留名单: KB-Ops-Eval-*/KB-Exp-Ops/KB-UserDemo/UserDemo-*/VerifyDemo-*。
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE / "scripts"))
from lib import BACKEND, WEB  # noqa: E402

HOTPOT_PREFIX = "KB-Hotpot-"
LEFTOVER_PREFIXES = ("KB-Ops-Eval-", "KB-Exp-Ops", "KB-UserDemo",
                     "UserDemo-", "VerifyDemo-")
# 预检目标只允许本机服务 —— 显式 scheme + 环回主机白名单后再请求(SSRF 加固)。
ALLOWED_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _fetch(url: str, timeout: float = 8.0) -> tuple[int, str]:
    parts = urlparse(url)
    if parts.scheme not in ("http", "https"):
        raise ValueError(f"blocked scheme: {parts.scheme!r} ({url})")
    if (parts.hostname or "").lower() not in ALLOWED_HOSTS:
        raise ValueError(f"blocked non-loopback host: {parts.hostname!r} ({url})")
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(200).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""


def _token() -> str:
    if os.environ.get("RAG_BENCH_TOKEN"):
        return os.environ["RAG_BENCH_TOKEN"]
    env = SUITE.parent / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("MCP_AUTH_TOKEN="):
                return line.split("=", 1)[1].strip()
    return ""


def _kb_catalog() -> list[dict]:
    """经 web 层拿知识库目录（与 60_hotpot_build 同一入口）。"""
    tok = _token()
    req = urllib.request.Request(
        f"{WEB}/api/kb/catalog",
        headers={"Authorization": f"Bearer {tok}"} if tok else {})
    parts = urlparse(f"{WEB}/api/kb/catalog")
    if parts.scheme not in ("http", "https"):
        raise ValueError(f"blocked scheme: {parts.scheme!r}")
    if (parts.hostname or "").lower() not in ALLOWED_HOSTS:
        raise ValueError(f"blocked non-loopback host: {parts.hostname!r}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8")).get("knowledgeBases") or []


def _storage_doc_counts() -> dict[str, int]:
    """KB 名 → 存储 md 文件数。catalog API 的 doc_count 字段不可靠(实测为 null),
    直接数 storage/tree-file-system/<KB>/*.md 是物理事实。"""
    root = SUITE.parent / "storage" / "tree-file-system"
    counts: dict[str, int] = {}
    if not root.is_dir():
        return counts
    for kb_dir in root.iterdir():
        if kb_dir.is_dir():
            counts[kb_dir.name] = sum(1 for _ in kb_dir.rglob("*.md"))
    return counts


def main() -> int:
    track = sys.argv[1] if len(sys.argv) > 1 else ""
    problems: list[str] = []
    warnings: list[str] = []

    # 1. backend
    try:
        code, body = _fetch(f"{BACKEND}/api/v1/health")
    except Exception as e:  # noqa: BLE001
        code, body = 0, str(e)
    if code == 200 and "healthy" in body:
        print(f"  [OK] backend {BACKEND} healthy")
    else:
        problems.append(f"backend {BACKEND} 未就绪 (HTTP {code}) — 先 ragctl up --mode dev")

    # 2. web
    try:
        code, _ = _fetch(WEB)
    except Exception as e:  # noqa: BLE001
        code = 0
    if code == 200:
        print(f"  [OK] web {WEB} responding")
    else:
        problems.append(f"web {WEB} 未就绪 (HTTP {code}) — 检查端口(6790 是死代理陷阱⑲)")

    # 3. token
    if _token():
        print("  [OK] MCP_AUTH_TOKEN 可解析")
    else:
        problems.append("MCP_AUTH_TOKEN 缺失(环境变量或仓库 .env)")

    # 4. omp
    if shutil.which("omp"):
        print("  [OK] omp 可执行(作答/判分 Agent)")
    else:
        warnings.append("omp 不在 PATH —— Track R 的 E16 作答/判分阶段将失败;"
                        " Track F 的冥想/判分阶段将失败")

    # 5. track-specific KB state
    if track.upper().startswith("R"):
        try:
            kbs = _kb_catalog()
        except Exception as e:  # noqa: BLE001
            problems.append(f"知识库目录读取失败(web 层): {e}")
            kbs = []
        counts = _storage_doc_counts()
        hotpot = [k for k in kbs if str(k.get("name", "")).startswith(HOTPOT_PREFIX)]
        nonempty = [f"{name}({counts.get(name, 0)}篇)"
                    for name in (str(k.get("name")) for k in hotpot)
                    if counts.get(name, 0) > 0]
        if hotpot and not any(counts.get(str(k.get("name")), 0) for k in hotpot):
            print(f"  [OK] KB-Hotpot-* 空态 ({len(hotpot)} 个库)")
        elif nonempty:
            problems.append(
                "KB-Hotpot-* 非空: " + ", ".join(nonempty)
                + " → 先 python scripts/00_reset_env.py 或手工清空九库再跑 R3"
                  " (TEST-PLAN §7.3: 非空起步会静默归零/累积副本)")
        else:
            warnings.append("未发现 KB-Hotpot-* 库 — R3 会由 60_hotpot_build 新建(正常, 首跑耗时较长)")
        leftover = [k["name"] for k in kbs
                    if any(str(k.get("name", "")).startswith(p)
                           for p in LEFTOVER_PREFIXES)]
        if leftover:
            warnings.append("实验残留 KB 在库: " + ", ".join(leftover)
                            + " → 会挤占全局 balance 候选池, 建议 00_reset_env.py 后重跑")
        else:
            print("  [OK] 无实验残留 KB")

    for w in warnings:
        print(f"  [WARN] {w}")
    if problems:
        print("\n✗ 预检未通过:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("\n✓ 预检通过 — 可以开始跑轨")
    return 0


if __name__ == "__main__":
    sys.exit(main())
