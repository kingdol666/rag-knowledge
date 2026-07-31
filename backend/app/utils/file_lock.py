"""跨进程文件锁 —— 修复 .knowledge-base.yml 跨进程读改写竞争。

背景：web(Nitro) 与 backend(FastAPI) 两个进程都会对同一 `.knowledge-base.yml`
做 read-modify-write（web 增删改文档/标签；backend 写回 vector_index/graph_index）。
进程内锁（web withKbLock / backend threading.Lock）无法互斥跨进程写，
并发 create + 自动索引写回会丢失条目（doc 在磁盘/树存在但 YAML 缺失）。

协议：O_EXCL 创建 `<target>.lock` 文件（写 PID+时间戳）→ 独占成功者执行
read-modify-write → finally 删除锁文件。竞争方以 20ms 间隔重试；
持有超过 ``stale_after`` 秒视为崩溃残留，可抢占。写目标用原子写（atomic_write_*）。
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Union

PathLike = Union[str, Path]

_DEFAULT_TIMEOUT = 15.0  # 秒：单次 YAML 操作应远小于此
_DEFAULT_STALE_AFTER = 30.0  # 秒：超过即视为崩溃残留，允许抢占
_RETRY_INTERVAL = 0.02  # 秒


class FileLockTimeoutError(TimeoutError):
    """获取锁超时。"""


class FileLock:
    """O_EXCL 锁文件互斥（跨进程、跨平台，Windows 可用）。"""

    def __init__(
        self,
        lock_path: PathLike,
        timeout: float = _DEFAULT_TIMEOUT,
        stale_after: float = _DEFAULT_STALE_AFTER,
    ) -> None:
        self.lock_path = Path(lock_path)
        self.timeout = timeout
        self.stale_after = stale_after
        self._acquired = False

    def acquire(self) -> "FileLock":
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                try:
                    os.write(fd, f"{os.getpid()} {time.time()}\n".encode("utf-8"))
                finally:
                    os.close(fd)
                self._acquired = True
                return self
            except FileExistsError:
                # 持有者崩溃后锁文件残留：超时即抢占
                try:
                    age = time.time() - self.lock_path.stat().st_mtime
                    if age > self.stale_after:
                        try:
                            self.lock_path.unlink()
                            continue
                        except FileNotFoundError:
                            continue
                except FileNotFoundError:
                    continue
                if time.monotonic() >= deadline:
                    raise FileLockTimeoutError(
                        f"Timed out acquiring lock: {self.lock_path}"
                    )
                time.sleep(_RETRY_INTERVAL)
            except PermissionError:
                # Windows：锁文件刚被创建、创建方尚未 close 时，O_EXCL 重开
                # 会抛共享违规 PermissionError（而非 FileExistsError）。
                # 与 FileExistsError 同样处理：短暂重试。
                if time.monotonic() >= deadline:
                    raise FileLockTimeoutError(
                        f"Timed out acquiring lock: {self.lock_path}"
                    )
                time.sleep(_RETRY_INTERVAL)

    def release(self) -> None:
        if self._acquired:
            try:
                self.lock_path.unlink()
            except FileNotFoundError:
                pass
            self._acquired = False

    def __enter__(self) -> "FileLock":
        return self.acquire()

    def __exit__(self, *exc) -> None:
        self.release()


def file_lock(
    lock_path: PathLike,
    timeout: float = _DEFAULT_TIMEOUT,
    stale_after: float = _DEFAULT_STALE_AFTER,
) -> FileLock:
    """获取 ``<lock_path>`` 上的跨进程互斥锁（上下文管理器）。"""
    return FileLock(lock_path, timeout=timeout, stale_after=stale_after)


def yaml_lock_path(yml_path: PathLike) -> Path:
    """YAML 文件对应的锁文件路径（同目录，.lock 后缀）。"""
    return Path(str(yml_path) + ".lock")
