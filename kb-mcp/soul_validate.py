"""SOUL 工具层纯逻辑(无 mcp 依赖,可独立测试)。

包含: soul_name 校验(AC30a)、模板文档清单。
server.py 与测试共用,避免测试引入 FastMCP 依赖。
"""
from __future__ import annotations

import re

_TEMPLATE_DOCS = ["soul-definition.md", "values.md", "thinking-style.md", "memory-conventions.md"]


def soul_name_valid(name: str) -> str | None:
    """校验 soul_name;返回错误信息或 None。

    规则(AC30a): 长度 1-64;仅中英文/数字/下划线/连字符,首字符非连字符;
    拒绝 Windows 保留名(CON/PRN/AUX/NUL/COM\\d/LPT\\d);拒绝 <>:"/\\|?* 与 ..
    """
    if not name or len(name) > 64:
        return "长度 1-64"
    if not re.fullmatch(r"[\w\u4e00-\u9fff][\w\u4e00-\u9fff\-]{0,63}", name):
        return "仅允许中英文/数字/下划线/连字符,且首字符非连字符"
    base = name.split("-")[0].upper()
    # Windows 保留名: 任一路径段命中即拒绝(plan AC30a: soul-CON/soul-LPT3 等)
    for seg in name.split("-"):
        seg_u = seg.upper()
        if seg_u in {"CON", "PRN", "AUX", "NUL"} or re.fullmatch(r"COM\d|LPT\d", seg_u):
            return "Windows 保留名"
    if any(c in name for c in '<>:"/\\|?*') or ".." in name:
        return "包含非法字符或路径穿越"
    return None
