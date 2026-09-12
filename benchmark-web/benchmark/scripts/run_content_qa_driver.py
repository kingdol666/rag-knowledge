#!/usr/bin/env python3
"""run_content_qa 的运行时包装: 用已验证的直连实现替换 api_post 后调 main.

背景: 本机代理/连接栈对模块内 api_post 存在间歇性空响应(200 + null/空体),
而同一进程内直连 urllib 请求稳定返回完整 JSON. 本包装不改被测脚本文件,
仅在运行时覆盖 api_post, 保证评测走的是稳定通道.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("run_content_qa", HERE / "run_content_qa.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def stable_api_post(path: str, data: dict, timeout: int = 600, tries: int = 5) -> dict:
    """直连实现: 逐请求边界校验 + 退避重试, 不经任何全局 opener 缓存."""
    url = mod.validate_base_url(mod.BASE + path)
    body = json.dumps(data).encode()
    last: Exception | None = None
    for attempt in range(1, tries + 1):
        req = urllib.request.Request(
            url, data=body,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {mod.TOKEN}"},
            method="POST",
            )
        opener = urllib.request.build_opener()  # 每次全新 opener, 杜绝连接复用
        try:
            with opener.open(req, timeout=timeout) as resp:
                raw = resp.read()
            parsed = json.loads(raw)
            if not isinstance(parsed, dict) or not parsed:
                raise ValueError(f"empty/null body (len={len(raw)})")
            return parsed
        except urllib.error.HTTPError as e:
            if e.code == 409:
                raise
            last = e
        except Exception as e:
            last = e
        time_sleep = min(30, 2 * attempt)
        import time as _time
        _time.sleep(time_sleep)
    raise last  # type: ignore[misc]


mod.api_post = stable_api_post
mod.TOKEN = os.environ.get("RAG_BENCH_TOKEN", "")
sys.argv = [str(HERE / "run_content_qa.py")] + sys.argv[1:]
mod.main()
