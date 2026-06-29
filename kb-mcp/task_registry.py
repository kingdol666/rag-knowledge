# -*- coding: utf-8 -*-
"""In-process background task registry for long-running parse jobs.

A PDF parse (PDF -> Markdown via MinerU OCR) can take minutes. If an MCP
tool awaits it directly, the tool response is blocked for that whole time,
which freezes the calling agent. Instead we hand the coroutine off to this
registry as a fire-and-forget asyncio task and return a ``task_id`` at once;
the agent polls ``parse_task_status(task_id)`` for the outcome.

Scope & lifetime
----------------
Storage is purely in-memory and lives for the lifetime of the MCP server
process (one process per agent session under stdio transport). State does
NOT survive a restart. A hard reference to every live ``asyncio.Task`` is
kept so the event-loop garbage collector never cancels a running parse.

Concurrency
-----------
The server runs a single event loop and all registry access happens on it,
so the plain dict operations here need no locking.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timezone

# Cap on how many *finished* records we retain, to bound memory use.
MAX_COMPLETED = 50

# task_id -> record dict (one entry per submitted job, running or done)
_records: dict[str, dict] = {}
# task_id -> asyncio.Task. Kept so the GC cannot collect a running task.
_handles: dict[str, asyncio.Task] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def submit(coro, kind: str, meta: dict | None = None) -> str:
    """Schedule *coro* on the running loop and return its task id instantly.

    Must be called from within a running event loop (i.e. inside an async
    MCP tool). The coroutine's return value is stored on the record under
    ``result``; any exception is captured into ``error``.
    """
    task_id = _new_id()
    record = {
        "task_id": task_id,
        "kind": kind,          # parse_pdf | parse_pdf_batch | parse_pdf_to_kb
        "status": "running",   # running | done | error
        "created_at": _now_iso(),
        "started_monotonic": time.monotonic(),
        "meta": meta or {},
        "result": None,
        "error": None,
    }
    _records[task_id] = record

    async def _runner():
        try:
            record["result"] = await coro
            record["status"] = "done"
        except Exception as e:  # surface any failure to the caller, never raise
            record["error"] = f"{type(e).__name__}: {e}"
            record["status"] = "error"
        finally:
            record["finished_at"] = _now_iso()
            _handles.pop(task_id, None)
            _reap_completed()

    _handles[task_id] = asyncio.create_task(_runner())
    return task_id


def get(task_id: str) -> dict | None:
    """Return the raw record for *task_id*, or ``None`` if unknown."""
    return _records.get(task_id)


def public_view(rec: dict | None) -> dict | None:
    """Project a record into a response-safe view (drops the internal clock)."""
    if rec is None:
        return None
    out = {
        "task_id": rec["task_id"],
        "kind": rec["kind"],
        "status": rec["status"],
        "created_at": rec["created_at"],
    }
    if rec["status"] == "running":
        out["elapsed_seconds"] = round(time.monotonic() - rec["started_monotonic"], 1)
    if rec.get("finished_at"):
        out["finished_at"] = rec["finished_at"]
    if rec["status"] in ("done", "error"):
        out["result"] = rec["result"] if rec["status"] == "done" else None
        out["error"] = rec.get("error")
    return out


def list_views(status: str = "") -> list[dict]:
    """Return public views for all tasks, optionally filtered by status."""
    views = [public_view(r) for r in _records.values()]
    if status:
        views = [v for v in views if v and v["status"] == status]
    return sorted([v for v in views if v], key=lambda v: v["created_at"])


def _reap_completed() -> None:
    """Drop the oldest finished records once we exceed MAX_COMPLETED."""
    done = [tid for tid, r in _records.items() if r["status"] in ("done", "error")]
    if len(done) <= MAX_COMPLETED:
        return
    done.sort(key=lambda tid: _records[tid].get("finished_at", ""))
    for tid in done[: len(done) - MAX_COMPLETED]:
        _records.pop(tid, None)
