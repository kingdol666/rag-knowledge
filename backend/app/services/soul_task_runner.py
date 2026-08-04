"""后端内存任务注册表 — 长时间作业(训练/审批)异步执行 + 进度追踪。

与 kb-mcp 层 task_registry 同构(独立实现, 后端进程内运行):
- submit_soul_task 在事件循环上调度协程, 立即返回 task_id
- 任务协程通过 update_progress(task_id, {...}) 上报中间进度
- GET /api/v1/soul/tasks/{task_id} 暴露 {status, progress, result, error}

设计: 提交的是 coroutine 工厂 (task_id) -> coroutine, 使任务协程能拿到
自己的 task_id 用于进度上报。
"""
from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

MAX_RECORDS = 100        # 保留记录上限(超出丢弃最旧完成记录)
RUNNING_TTL = 4 * 3600   # 运行超时(秒): 训练最长可达 ~2h, 给足余量

_records: dict[str, dict] = {}
_handles: dict[str, asyncio.Task] = {}

CoroFactory = Callable[[str], Awaitable[Any]]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def submit_soul_task(coro_factory: CoroFactory, kind: str,
                     meta: dict | None = None) -> str:
    """调度 coro_factory(task_id) 在事件循环上运行, 立即返回 task_id。

    任务协程可调用 ``update_progress(task_id, progress)`` 上报中间进度;
    异常被捕获写入 record["error"], status -> error, 永不向上抛。
    """
    task_id = _new_id()
    record: dict[str, Any] = {
        "task_id": task_id,
        "kind": kind,            # soul_learn | soul_learn_all | soul_review
        "status": "running",     # running | done | error
        "created_at": _now_iso(),
        "started_monotonic": time.monotonic(),
        "meta": meta or {},
        "progress": None,
        "result": None,
        "error": None,
    }
    _records[task_id] = record

    async def _runner() -> None:
        try:
            record["result"] = await coro_factory(task_id)
            record["status"] = "done"
        except Exception as e:  # 任何失败都落到 record, 不向调用方抛
            record["error"] = f"{type(e).__name__}: {e}"
            record["status"] = "error"
        finally:
            record["finished_at"] = _now_iso()
            _handles.pop(task_id, None)
            _trim()

    _handles[task_id] = asyncio.create_task(_runner())
    _reap_stale()
    return task_id


def update_progress(task_id: str, progress: dict) -> None:
    """任务协程内部进度上报(仅 running 状态可写)。"""
    rec = _records.get(task_id)
    if rec and rec["status"] == "running":
        rec["progress"] = progress


def get_soul_task(task_id: str) -> dict | None:
    return _records.get(task_id)


def public_task_view(rec: dict | None) -> dict | None:
    """响应安全视图(去掉内部单调时钟)。"""
    if rec is None:
        return None
    out: dict[str, Any] = {
        "task_id": rec["task_id"],
        "kind": rec["kind"],
        "status": rec["status"],
        "created_at": rec["created_at"],
        "meta": rec.get("meta") or {},
    }
    if rec["status"] == "running":
        out["elapsed_seconds"] = round(time.monotonic() - rec["started_monotonic"], 1)
    if rec.get("finished_at"):
        out["finished_at"] = rec["finished_at"]
    if rec.get("progress"):
        out["progress"] = rec["progress"]
    if rec["status"] in ("done", "error"):
        out["result"] = rec["result"] if rec["status"] == "done" else None
        out["error"] = rec.get("error")
    return out


def list_soul_tasks(status: str = "") -> list[dict]:
    views = [public_task_view(r) for r in _records.values()]
    if status:
        views = [v for v in views if v and v["status"] == status]
    return sorted([v for v in views if v], key=lambda v: v["created_at"])


def _reap_stale() -> None:
    """取消超时任务; 超过并发上限时取消最旧运行任务。"""
    now = time.monotonic()
    for tid, r in list(_records.items()):
        if r["status"] != "running":
            continue
        if now - r["started_monotonic"] > RUNNING_TTL:
            handle = _handles.pop(tid, None)
            if handle and not handle.done():
                handle.cancel()
            r["status"] = "error"
            r["error"] = f"task timed out after {RUNNING_TTL}s"
            r["finished_at"] = _now_iso()


def _trim() -> None:
    """超过 MAX_RECORDS 时丢弃最旧的已完成记录。"""
    done = sorted(
        [(tid, r) for tid, r in _records.items() if r["status"] != "running"],
        key=lambda x: x[1]["created_at"],
    )
    overflow = len(_records) - MAX_RECORDS
    for tid, _ in done[:max(0, overflow)]:
        _records.pop(tid, None)
