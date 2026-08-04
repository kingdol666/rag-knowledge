"""SOUL 训练过程记录 — SQLite 持久化(训练历史 + 阶段事件流)。

设计:
- storage/soul-training.db(SQLite, 与 meditation.db 同模式, WAL)
- soul_training_runs: 一次训练运行(learn/learn-all/train-rl/审批)
  - id, soul_kb_id, task_id, kind, mode, started_at, finished_at,
    status(running|paused|done|error), rounds, questions, memories,
    docs, cost_usd, reward, report_json
- soul_training_events: 运行内阶段事件(每轮/每阶段一次)
  - id, run_id, ts, phase(scan|learn|reward|approve|info), payload_json
- 查询: history(soul) / run_detail(run_id) / latest_progress(task_id)

并发安全: 单连接 + WAL, 写操作串行化(threading.Lock);
所有写操作幂等(run_id 唯一约束, upsert 语义)。
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_STORAGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "storage"
_DB_PATH = _STORAGE_DIR / "soul-training.db"

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA busy_timeout=5000")
        _init_schema(_conn)
    return _conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS soul_training_runs (
            id TEXT PRIMARY KEY,
            soul_kb_id TEXT NOT NULL,
            task_id TEXT,
            kind TEXT NOT NULL,
            mode TEXT,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            status TEXT NOT NULL DEFAULT 'running',
            rounds INTEGER DEFAULT 0,
            questions INTEGER DEFAULT 0,
            memories INTEGER DEFAULT 0,
            docs INTEGER DEFAULT 0,
            cost_usd REAL DEFAULT 0,
            reward REAL,
            report_json TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_runs_soul ON soul_training_runs(soul_kb_id, started_at DESC);
        CREATE INDEX IF NOT EXISTS idx_runs_task ON soul_training_runs(task_id);

        CREATE TABLE IF NOT EXISTS soul_training_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            ts TEXT NOT NULL,
            phase TEXT NOT NULL,
            payload_json TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_events_run ON soul_training_events(run_id, id);
        """
    )
    conn.commit()


# ── 写 ────────────────────────────────────────────────────────────────

def start_run(soul_kb_id: str, kind: str, task_id: str | None = None,
              mode: str = "") -> str:
    """开启一条训练运行记录, 返回 run_id。"""
    run_id = _now_iso().replace(":", "").replace("-", "") + "-" + task_id[:6] if task_id else _now_iso()
    import uuid
    run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:12]}"
    with _lock:
        conn = _get_conn()
        conn.execute(
            "INSERT INTO soul_training_runs (id, soul_kb_id, task_id, kind, mode, started_at, status) "
            "VALUES (?, ?, ?, ?, ?, ?, 'running')",
            (run_id, soul_kb_id, task_id, kind, mode, _now_iso()),
        )
        conn.commit()
    return run_id


def log_event(run_id: str, phase: str, payload: dict | None = None) -> None:
    """记录阶段事件(轮次/进度/奖励)。"""
    with _lock:
        conn = _get_conn()
        conn.execute(
            "INSERT INTO soul_training_events (run_id, ts, phase, payload_json) VALUES (?, ?, ?, ?)",
            (run_id, _now_iso(), phase, json.dumps(payload or {}, ensure_ascii=False)),
        )
        conn.commit()


def update_progress(run_id: str, *, questions: int | None = None,
                    memories: int | None = None, docs: int | None = None,
                    rounds: int | None = None, cost_usd: float | None = None,
                    reward: float | None = None) -> None:
    """累加/更新运行指标。"""
    with _lock:
        conn = _get_conn()
        sets, args = [], []
        for col, val in (("questions", questions), ("memories", memories),
                         ("docs", docs), ("rounds", rounds),
                         ("cost_usd", cost_usd), ("reward", reward)):
            if val is not None:
                sets.append(f"{col} = COALESCE({col},0) + ?" if col in ("questions", "memories", "docs", "rounds", "cost_usd") else f"{col} = ?")
                args.append(val)
        if sets:
            args.append(run_id)
            conn.execute(f"UPDATE soul_training_runs SET {', '.join(sets)} WHERE id = ?", args)
            conn.commit()


def finish_run(run_id: str, status: str, report: dict | None = None) -> None:
    """结束运行(done/error/paused), 写入最终报告。"""
    with _lock:
        conn = _get_conn()
        conn.execute(
            "UPDATE soul_training_runs SET status = ?, finished_at = ?, report_json = ? WHERE id = ?",
            (status, _now_iso(), json.dumps(report or {}, ensure_ascii=False), run_id),
        )
        conn.commit()


def mark_paused(run_id: str) -> None:
    with _lock:
        conn = _get_conn()
        conn.execute("UPDATE soul_training_runs SET status = 'paused' WHERE id = ?", (run_id,))
        conn.commit()


def mark_resumed(run_id: str) -> None:
    with _lock:
        conn = _get_conn()
        conn.execute("UPDATE soul_training_runs SET status = 'running' WHERE id = ?", (run_id,))
        conn.commit()


# ── 读 ─────────────────────────────────────────────────────────────────

def list_runs(soul_kb_id: str = "", limit: int = 30) -> list[dict]:
    """最近训练运行历史(可过滤 soul)。"""
    with _lock:
        conn = _get_conn()
        if soul_kb_id:
            rows = conn.execute(
                "SELECT * FROM soul_training_runs WHERE soul_kb_id = ? ORDER BY started_at DESC LIMIT ?",
                (soul_kb_id, limit)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM soul_training_runs ORDER BY started_at DESC LIMIT ?", (limit,)).fetchall()
    cols = [d[0] for d in conn.execute("SELECT * FROM soul_training_runs LIMIT 0").description]
    return [_row_to_dict(r, cols) for r in rows]


def get_run(run_id: str) -> dict | None:
    with _lock:
        conn = _get_conn()
        row = conn.execute("SELECT * FROM soul_training_runs WHERE id = ?", (run_id,)).fetchone()
        if not row:
            return None
        cols = [d[0] for d in conn.execute("SELECT * FROM soul_training_runs LIMIT 0").description]
        return _row_to_dict(row, cols)


def get_run_events(run_id: str) -> list[dict]:
    with _lock:
        conn = _get_conn()
        rows = conn.execute(
            "SELECT id, run_id, ts, phase, payload_json FROM soul_training_events "
            "WHERE run_id = ? ORDER BY id", (run_id,)).fetchall()
    return [{"id": r[0], "run_id": r[1], "ts": r[2], "phase": r[3],
             "payload": json.loads(r[4]) if r[4] else {}} for r in rows]


def get_run_by_task(task_id: str) -> dict | None:
    with _lock:
        conn = _get_conn()
        row = conn.execute("SELECT * FROM soul_training_runs WHERE task_id = ? ORDER BY started_at DESC LIMIT 1",
                           (task_id,)).fetchone()
        if not row:
            return None
        cols = [d[0] for d in conn.execute("SELECT * FROM soul_training_runs LIMIT 0").description]
        return _row_to_dict(row, cols)


def _row_to_dict(row: sqlite3.Row | tuple, cols: list[str]) -> dict:
    return {c: row[i] for i, c in enumerate(cols)}
