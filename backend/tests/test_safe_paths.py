"""路径安全回归测试 (P0 #4 #7) — 阻断路径遍历/绝对路径逃逸/UNC/NUL。

覆盖：合法相对路径通过、绝对路径逃逸被拒、UNC 拒、NUL 拒、遍历拒、
多根校验、try/is_within 辅助函数。
"""
from __future__ import annotations

import os

import pytest

from app.utils.paths import PROJECT_ROOT
from app.utils.safe_paths import (
    is_path_within,
    resolve_within,
    resolve_within_any_root,
    try_resolve_within,
)


class TestResolveWithin:
    def test_legal_relative(self):
        r = resolve_within("output/test", PROJECT_ROOT)
        assert is_path_within(r, PROJECT_ROOT)

    def test_reject_absolute_system_path(self):
        with pytest.raises(ValueError):
            resolve_within(r"C:\Windows\System32\evil", PROJECT_ROOT)

    def test_reject_traversal_escape(self):
        # 从 PROJECT_ROOT 向上逃逸
        with pytest.raises(ValueError):
            resolve_within("../../../../etc/passwd", PROJECT_ROOT)

    @pytest.mark.skipif(os.name != "nt", reason="Windows UNC semantics")
    def test_reject_unc(self):
        with pytest.raises(ValueError):
            resolve_within(r"\\server\share\evil", PROJECT_ROOT)

    def test_reject_nul_byte(self):
        with pytest.raises(ValueError):
            resolve_within("safe\x00evil", PROJECT_ROOT)

    def test_reject_empty(self):
        with pytest.raises(ValueError):
            resolve_within("", PROJECT_ROOT)

    def test_try_resolve_within(self):
        assert try_resolve_within("output/test", PROJECT_ROOT) is not None
        assert try_resolve_within(r"C:\Windows\System32", PROJECT_ROOT) is None

    def test_resolve_within_any_root_hit(self):
        # 落在 PROJECT_ROOT 内
        assert resolve_within_any_root("output/test", [PROJECT_ROOT]) is not None

    def test_resolve_within_any_root_all_miss(self):
        # 全部根都越界
        assert (
            resolve_within_any_root(
                r"C:\Windows\System32\evil", [PROJECT_ROOT, PROJECT_ROOT.parent]
            )
            is None
        )

    def test_is_path_within(self):
        assert is_path_within(PROJECT_ROOT / "sub" / "x", PROJECT_ROOT)
        assert not is_path_within(r"C:\Windows", PROJECT_ROOT)

    def test_is_path_within_root_itself(self):
        # 根自身算"在内"
        assert is_path_within(PROJECT_ROOT, PROJECT_ROOT)
