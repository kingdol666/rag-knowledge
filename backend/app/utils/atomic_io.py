"""原子写 —— 阶段 0 (P0 #2 #3) 数据完整性基石。

策略：同目录 temp 文件 → fsync → ``os.replace``（Windows/POSIX 均原子）。
崩溃发生在任意时刻，目标文件要么是旧内容要么是新内容，永不截断/空。
temp 文件用 ``.{name}.{pid}.{rand}.tmp`` 前缀，可被孤儿扫描清理。

向后兼容：对调用方透明（语义同 ``Path.write_text``）。
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Union

PathLike = Union[str, Path]


def _replace_with_retry(
    src: str, dst: str, retries: int = 6, delay: float = 0.03
) -> None:
    """``os.replace`` 带短重试。

    Windows 上当目标文件刚被另一进程/线程替换（句柄未完全释放）时，
    ``os.replace`` 可能抛 ``PermissionError`` [WinError 5]（共享违规）。
    这是瞬态冲突，短重试即可解决，避免并发写误报失败。
    """
    import time

    last_err: Exception | None = None
    for i in range(retries):
        try:
            os.replace(src, dst)
            return
        except PermissionError as e:  # Windows 共享违规 / 目标被占
            last_err = e
            time.sleep(delay * (i + 1))
        except OSError:
            raise
    assert last_err is not None
    raise last_err


def atomic_write_text(path: PathLike, data: str, encoding: str = "utf-8") -> None:
    """原子写文本。同目录 temp → fsync → os.replace。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{p.name}.", suffix=".tmp", dir=str(p.parent))
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        _replace_with_retry(tmp, str(p))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def atomic_write_bytes(path: PathLike, data: bytes) -> None:
    """原子写字节。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{p.name}.", suffix=".tmp", dir=str(p.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        _replace_with_retry(tmp, str(p))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def atomic_write_yaml(path: PathLike, data: str) -> None:
    """原子写 YAML（调用方先 ``yaml.safe_dump`` 成 str 再传入）。等价 atomic_write_text。"""
    atomic_write_text(path, data)
