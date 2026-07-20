"""
Project paths resolved from this module.
"""
from __future__ import annotations
from pathlib import Path

_THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = _THIS_FILE.parents[2]

CONFIG_PATH = PROJECT_ROOT / "config.yml"

_PARENT = PROJECT_ROOT.parent
SHARED_CONFIG_CANDIDATES = [
    _PARENT / "rag-knowledge" / "config.yml",
    _PARENT / "config.yml",
]
_SHARED = next((p for p in SHARED_CONFIG_CANDIDATES if p.is_file()), None)
SHARED_CONFIG_PATH = _SHARED

# .env file: check parent (rag-knowledge/) then self (backend/)
_ENV_CANDIDATES = [
    _PARENT / ".env",
    PROJECT_ROOT / ".env",
]
ENV_PATH = next((p for p in _ENV_CANDIDATES if p.is_file()), _PARENT / ".env")
ENV_EXAMPLE_PATH = _PARENT / ".env.example"


def resolve_path(relative: str | Path) -> Path:
    p = Path(relative)
    if p.is_absolute():
        return p
    return (PROJECT_ROOT / p).resolve()


# ── Storage Root (lazy, to avoid circular import with config) ──────────

_STORAGE_ROOT: Path | None = None


def get_storage_root() -> Path:
    """获取 web 端 tree-file-system 的绝对路径。

    用函数而非模块级常量来解决 paths.py ↔ config.py 之间的循环依赖。
    优先级: .env TREE_STORAGE_PATH > config.yml storage.tree_fs_root > 默认.
    """
    global _STORAGE_ROOT
    if _STORAGE_ROOT is not None:
        return _STORAGE_ROOT

    from app.config import config

    root = config.storage_tree_fs_root
    p = Path(root)
    if not p.is_absolute():
        # 相对路径基于主仓库根目录（backend/ 的父目录）
        p = PROJECT_ROOT.parent / p
    _STORAGE_ROOT = p.resolve()
    return _STORAGE_ROOT
