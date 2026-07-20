"""路径安全 —— 阶段 0 (P0 #4 #7) 拦截路径遍历与绝对路径逃逸。

``resolve_within(candidate, root)`` 保证 candidate 解析后落在 root 子树内，
阻断：``..`` 遍历、绝对路径逃逸、UNC（``\\\\server\\share``）、NUL 字节、
Windows 大小写差异。

向后兼容：合法路径（root 子树内）行为不变；越界抛 ValueError，调用方转为
HTTP 422/403（而非原来的"任意目录写"）。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Union

PathLike = Union[str, Path]


def _is_within(resolved: str, root: str) -> bool:
    """大小写不敏感包含检查（Windows NTFS 不区分大小写）。

    ``resolved == root`` 或 ``resolved`` 以 ``root + sep`` 开头。
    """
    r = os.path.normcase(os.path.normpath(root)).rstrip("\\/")
    c = os.path.normcase(os.path.normpath(resolved))
    if c == r:
        return True
    return c.startswith(r + os.sep)


def is_path_within(path: PathLike, root: PathLike) -> bool:
    """校验**已解析**的路径是否在 root 子树内（大小写不敏感包含检查）。

    与 :func:`resolve_within` 的区别：本函数不做 join/normalize，只判断给定的
    绝对路径是否落在 root 内。用于业务逻辑已自行解析（如 ``resolve_path``）
    后的安全收敛，避免改变相对路径的基准。
    """
    return _is_within(str(path), str(root))


def resolve_within(candidate: PathLike, root: PathLike) -> str:
    """解析 candidate 并确保落在 root 子树内；越界抛 ValueError。"""
    s = str(candidate)
    if not s or "\x00" in s:
        raise ValueError("invalid path")
    # UNC (\\server\share) 拒绝；\\?\ 前缀（verbatim）允许但仍在 root 内校验
    if s.startswith("\\\\") and not s.startswith("\\\\?\\"):
        raise ValueError("UNC paths not allowed")
    resolved = os.path.normpath(os.path.join(str(root), s))
    if not _is_within(resolved, str(root)):
        raise ValueError(f"path outside allowed root: {candidate!r}")
    return resolved


def try_resolve_within(candidate: PathLike, root: PathLike) -> Optional[str]:
    """非抛异常版本：越界返回 None。"""
    try:
        return resolve_within(candidate, root)
    except ValueError:
        return None


def resolve_within_any_root(
    candidate: PathLike, roots: List[PathLike]
) -> Optional[str]:
    """多根校验：落在任一允许根内即返回解析路径，全部越界返回 None。"""
    s = str(candidate)
    if not s or "\x00" in s:
        return None
    if s.startswith("\\\\") and not s.startswith("\\\\?\\"):
        return None
    for root in roots:
        try:
            return resolve_within(s, root)
        except ValueError:
            continue
    return None
