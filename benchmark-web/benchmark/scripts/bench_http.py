#!/usr/bin/env python3
"""基准脚本共享出站 HTTP 客户端 — 集中实施 SSRF 边界.

边界规则: 仅 http(s); 本机回环(localhost/127.0.0.1/::1)直接放行（本基准的合法靶机是
本机 rag-knowledge 服务）; 其余目标默认拒绝, 设 RAG_BENCH_ALLOW_REMOTE=1 后仅放行
https API 端点, 且禁止解析到链路本地/云元数据地址。
"""
from __future__ import annotations

import ipaddress
import json
import os
import socket
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def validated_url(url: str, extra_hosts: set[str] | None = None) -> str:
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        raise ValueError(f"仅允许 http/https: {url}")
    host = (p.hostname or "").lower()
    allow = _LOCAL_HOSTS | (extra_hosts or set())
    if host not in allow:
        if (p.scheme != "https"
                and os.environ.get("RAG_BENCH_ALLOW_REMOTE") != "1"):
            raise ValueError(f"非白名单目标被拒绝: {host} (白名单={sorted(allow)}, "
                             f"远程 https 需 RAG_BENCH_ALLOW_REMOTE=1)")
        for ai in socket.getaddrinfo(host, None):
            addr = ipaddress.ip_address(ai[4][0])
            if addr.is_link_local or str(addr) == "169.254.169.254":
                raise ValueError(f"目标解析到受限地址: {url}")
    return url


def _open_fresh(req, timeout: int):
    """每次请求新建 opener — 本机连接栈在负载下会对复用连接返回 200+空体/null,
    fresh opener 杜绝该问题(实测修复, 见 docs/benchmark-audit-2026-09-12.md)."""
    return urllib.request.build_opener().open(req, timeout=timeout)


def _post_raw(url: str, payload: dict, headers: dict, timeout: int) -> dict:
    last: Exception | None = None
    for attempt in range(3):
        req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                     headers=headers, method="POST")
        try:
            with _open_fresh(req, timeout) as resp:
                raw = resp.read()
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise ValueError(f"null/empty body (len={len(raw)})")
            return parsed
        except urllib.error.HTTPError as e:
            if e.code in (401, 409, 429) or e.code >= 500:
                last = e          # 瞬态: 退避重试
            else:
                raise
        except Exception as e:  # noqa: BLE001
            last = e
        time.sleep(2 * (attempt + 1))
    raise last  # type: ignore[misc]


def _get_raw(url: str, headers: dict, timeout: int) -> dict:
    last: Exception | None = None
    for attempt in range(3):
        req = urllib.request.Request(url, headers=headers)
        try:
            with _open_fresh(req, timeout) as resp:
                raw = resp.read()
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise ValueError(f"null/empty body (len={len(raw)})")
            return parsed
        except urllib.error.HTTPError as e:
            if e.code in (401, 429) or e.code >= 500:
                last = e
            else:
                raise
        except Exception as e:  # noqa: BLE001
            last = e
        time.sleep(2 * (attempt + 1))
    raise last  # type: ignore[misc]


def post_json(base: str, path: str, payload: dict, token: str = "",
              timeout: int = 90, extra_headers: dict | None = None) -> dict:
    url = validated_url(base.rstrip("/") + path)
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if extra_headers:
        headers.update(extra_headers)
    return _post_raw(url, payload, headers, timeout)


def get_json(base: str, path: str, token: str = "", timeout: int = 60) -> dict:
    url = validated_url(base.rstrip("/") + path)
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return _get_raw(url, headers, timeout)
