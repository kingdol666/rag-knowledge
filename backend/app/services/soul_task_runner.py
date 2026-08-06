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
        "kind": kind,            # soul_learn | soul_learn_all | soul_review | soul_train_rl
        "status": "running",     # running | paused | done | error
        "created_at": _now_iso(),
        "started_monotonic": time.monotonic(),
        "meta": meta or {},
        "progress": None,
        "result": None,
        "error": None,
        # 详细事件缓冲(前端实时可视化每个模型的输出)
        "events": [],
        # 暂停/继续门: 任务协程在每轮边界 await gate.wait(),
        # pause 时 gate 未置位 → 协程停在轮次之间(LLM 调用不被打断)
        "gate": asyncio.Event(),
    }
    record["gate"].set()
    _records[task_id] = record

    # 自动注册 task→soul 映射(WebSocket 广播按 soul_kb_id 路由)
    soul_id = (meta or {}).get("soul_kb_id") or ""
    if soul_id:
        try:
            from app.services.soul_training_ws import ws_manager
            ws_manager.register_task(task_id, soul_id)
        except Exception:
            pass

    async def _runner() -> None:
        try:
            # 支持同步/异步 progress_cb: 每轮边界等待暂停门
            record["result"] = await coro_factory(task_id)
            record["status"] = "done"
            _ws_broadcast(task_id, "done", {"result": record["result"],
                                              "status": "done"})
        except asyncio.CancelledError:
            record["status"] = "error"
            record["error"] = "cancelled"
            _ws_broadcast(task_id, "error", {"error": "cancelled",
                                               "status": "error"})
        except Exception as e:  # 任何失败都落到 record, 不向调用方抛
            record["error"] = f"{type(e).__name__}: {e}"
            record["status"] = "error"
            _ws_broadcast(task_id, "error", {"error": record["error"],
                                               "status": "error"})
        finally:
            record["finished_at"] = _now_iso()
            _handles.pop(task_id, None)
            # 解除 task → soul 映射(延迟, 让最后一批广播送达)
            _trim()
            from app.services.soul_training_ws import ws_manager
            ws_manager.unregister_task(task_id)

    _handles[task_id] = asyncio.create_task(_runner())
    _reap_stale()
    return task_id


def pause_soul_task(task_id: str) -> bool:
    """暂停运行中任务(在下一轮边界生效)。返回是否成功。"""
    rec = _records.get(task_id)
    if not rec or rec["status"] not in ("running", "paused"):
        return False
    if rec["status"] == "running":
        rec["gate"].clear()
        rec["status"] = "paused"
    return True


def resume_soul_task(task_id: str) -> bool:
    """继续已暂停任务。返回是否成功。"""
    rec = _records.get(task_id)
    if not rec or rec["status"] != "paused":
        return False
    rec["gate"].set()
    rec["status"] = "running"
    return True


async def gated_progress_cb(task_id: str) -> Any:
    """构造暂停门包装的 progress_cb(每轮边界检查暂停/继续)。

    用法: progress_cb=gated_progress_cb(task_id) 传给 learn_*/train_rl;
    内部: await gate → 若 paused 则 status=paused(通知前端) →
    继续等待 resume → status=running → 调用 update_progress。
    返回的包装函数同时兼容同步/异步调用方。
    """
    rec = _records.get(task_id)

    async def _cb(progress: dict) -> None:
        if rec is None:
            return
        # 暂停门: paused 时阻塞直到 resume
        if not rec["gate"].is_set():
            rec["status"] = "paused"
            if rec.get("progress") != progress:
                rec["progress"] = progress
            await rec["gate"].wait()
            if rec["status"] == "paused":
                rec["status"] = "running"
        update_progress(task_id, progress)

    return _cb


def update_progress(task_id: str, progress: dict) -> None:
    """任务协程内部进度上报(仅 running 状态可写)。

    同时通过 WebSocket 实时推送到订阅了对应 SOUL 的前端客户端。
    """
    rec = _records.get(task_id)
    if rec and rec["status"] == "running":
        rec["progress"] = progress
        # WebSocket 实时广播
        _ws_broadcast(task_id, "progress", {"progress": progress,
                                              "status": rec["status"]})

_MAX_EVENTS = 500  # 事件缓冲上限(超出丢弃最旧, 避免内存膨胀)

def append_event(task_id: str, event: dict) -> None:
    """向任务的事件缓冲追加一条详细事件(前端实时可视化)。

    同时通过 WebSocket 实时推送到订阅了对应 SOUL 的前端客户端。
    """
    rec = _records.get(task_id)
    if rec and rec["status"] == "running":
        rec["events"].append(event)
        if len(rec["events"]) > _MAX_EVENTS:
            rec["events"] = rec["events"][-_MAX_EVENTS:]
        # WebSocket 实时广播详细事件
        _ws_broadcast(task_id, "event", {"event": event})


def _ws_broadcast(task_id: str, event_type: str, data: dict) -> None:
    """fire-and-forget WebSocket 广播(非阻塞, 失败不影响训练)。

    直接从 task_soul_map 解析 soul_kb_id 并构造完整 payload 后调度广播。
    不使用 broadcast_task_event(避免 unregister 后 broadcast_task_event 找不到映射)。
    """
    try:
        loop = asyncio.get_running_loop()
        from app.services.soul_training_ws import ws_manager
        soul_kb_id = ws_manager._task_soul_map.get(task_id)
        if not soul_kb_id:
            return
        payload = {
            "type": event_type,
            "ts": _now_iso(),
            "soul_kb_id": soul_kb_id,
            "task_id": task_id,
            **data,
        }
        loop.create_task(ws_manager.broadcast(soul_kb_id, payload))
    except RuntimeError:
        pass  # 无 running loop, 跳过
    except Exception:
        pass  # 广播失败不影响训练


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
    if rec.get("events"):
        out["events"] = rec["events"]
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
