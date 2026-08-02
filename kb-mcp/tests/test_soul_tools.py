"""kb-mcp SOUL 工具纯逻辑测试(5.1)— 不依赖后端服务。

覆盖: soul_name 校验(AC30a: 保留名/路径穿越/非法字符)、模板文档清单。
"""
from __future__ import annotations

import pytest

from soul_validate import soul_name_valid as _soul_name_valid, _TEMPLATE_DOCS


class TestSoulNameValidation:
    @pytest.mark.parametrize("name", [
        "soul-材料学", "soul-ML", "soul-a1", "soul-测试-2", "soul-abc_def",
    ])
    def test_valid_names(self, name):
        assert _soul_name_valid(name) is None

    @pytest.mark.parametrize("name", [
        "soul-../../../etc",   # 路径穿越
        "soul-CON",            # Windows 保留名
        "soul-PRN", "soul-AUX", "soul-NUL", "soul-COM1", "soul-LPT3",
        "soul-a:b",            # 非法字符
        "soul-a/b", "soul-a\\b", "soul-a?b", "soul-a*b",
        "soul-..",             # 双点
        "-soul-x",             # 首字符连字符
        "",                    # 空
    ])
    def test_invalid_names(self, name):
        assert _soul_name_valid(name) is not None


class TestTemplateDocs:
    def test_four_persona_docs(self):
        assert _TEMPLATE_DOCS == [
            "soul-definition.md", "values.md",
            "thinking-style.md", "memory-conventions.md",
        ]
