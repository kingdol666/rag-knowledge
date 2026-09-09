# -*- coding: utf-8 -*-
"""kb-mcp pytest 共享 fixtures。

历史缺陷修复(2026-09-09): test_mcp_full_suite.py 的全部用例依赖 `client`
fixture, 但 conftest.py 从未提交, 导致 26 个 E2E 用例一直无法运行
(fixture 'client' not found)。现补齐。

注意: test_mcp_full_suite 是真 E2E——会创建/删除真实测试知识库, 需要服务在跑。
"""
import asyncio
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("APP_MODE", "dev")

from kb_client.client import KbClient  # noqa: E402
from config import WEB_URL, BACKEND_URL  # noqa: E402


@pytest.fixture
async def client():
    async with KbClient(web_url=WEB_URL, backend_url=BACKEND_URL) as c:
        yield c
