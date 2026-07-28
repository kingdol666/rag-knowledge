"""Meditation DB — SQLite storage for meditation signals and run records.

Independent from the chat DB to avoid coupling/locks.
Uses WAL mode for cross-process safety.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_DB_PATH: Path | None = None
_local = threading.local()


def _get_db_path() -> Path:
    global _DB_PATH
    if _DB_PATH is not None:
        return _DB_PATH
    from app.utils.paths import PROJECT_ROOT
    storage = PROJECT_ROOT.parent / "storage"
    storage.mkdir(parents=True, exist_ok=True)
    _DB_PATH = storage / "meditation.db"
    return _DB_PATH


def _get_conn() -> sqlite3.Connection:
    """Get a thread-local SQLite connection in WAL mode."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(str(_get_db_path()), check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        _local.conn = conn
    return conn


def init_db() -> None:
    """Create tables if they don't exist. Safe to call multiple times."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS meditation_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            kb_id TEXT NOT NULL,
            question_text TEXT NOT NULL,
            retrieved_docs TEXT DEFAULT '[]',
            assistant_answer TEXT,
            resolved INTEGER DEFAULT 0,
            user_feedback INTEGER DEFAULT -1,
            experience_derived INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_signals_kb ON meditation_signals(kb_id, experience_derived);
        CREATE INDEX IF NOT EXISTS idx_signals_session ON meditation_signals(session_id);

        CREATE TABLE IF NOT EXISTS meditation_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kb_id TEXT NOT NULL,
            harness TEXT NOT NULL,
            trigger TEXT DEFAULT 'scheduled',
            started_at TEXT NOT NULL,
            finished_at TEXT,
            status TEXT DEFAULT 'running',
            pid INTEGER,
            exit_code INTEGER,
            cost_usd REAL DEFAULT 0,
            experiences_created INTEGER DEFAULT 0,
            drafts_created INTEGER DEFAULT 0,
            signals_processed INTEGER DEFAULT 0,
            report_json TEXT DEFAULT '{}',
            error TEXT,
            agent_stdout_tail TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_runs_kb ON meditation_runs(kb_id);
        CREATE INDEX IF NOT EXISTS idx_runs_status ON meditation_runs(status);
    """)
    conn.commit()
    logger.info("Meditation DB initialized at %s", _get_db_path())


# ── Signal CRUD ────────────────────────────────────────────────────────

def save_signal(session_id: str, kb_id: str, question_text: str,
                retrieved_docs: list[str] | None = None,
                assistant_answer: str = "",
                resolved: bool = False) -> int:
    """Insert a meditation signal. Returns the new row id."""
    conn = _get_conn()
    docs_json = json.dumps(retrieved_docs or [], ensure_ascii=False)
    cur = conn.execute(
        """INSERT INTO meditation_signals
           (session_id, kb_id, question_text, retrieved_docs, assistant_answer, resolved)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (session_id, kb_id, question_text, docs_json, assistant_answer, 1 if resolved else 0),
    )
    conn.commit()
    return cur.lastrowid


def get_pending_signals(kb_id: str = "", days: int = 7, limit: int = 50) -> list[dict]:
    """Get unprocessed signals, optionally filtered by KB."""
    conn = _get_conn()
    if kb_id:
        rows = conn.execute(
            """SELECT * FROM meditation_signals
               WHERE experience_derived = 0 AND kb_id = ?
                 AND created_at >= datetime('now', ?)
               ORDER BY created_at DESC LIMIT ?""",
            (kb_id, f"-{days} days", limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT * FROM meditation_signals
               WHERE experience_derived = 0
                 AND created_at >= datetime('now', ?)
               ORDER BY created_at DESC LIMIT ?""",
            (f"-{days} days", limit),
        ).fetchall()
    return [dict(r) for r in rows]


def mark_signals_derived(signal_ids: list[int]) -> None:
    """Mark signals as processed (experience_derived=1)."""
    if not signal_ids:
        return
    conn = _get_conn()
    placeholders = ",".join("?" * len(signal_ids))
    conn.execute(
        f"UPDATE meditation_signals SET experience_derived = 1 WHERE id IN ({placeholders})",
        signal_ids,
    )
    conn.commit()


def update_signal_feedback(signal_id: int, feedback: int) -> bool:
    """Update user feedback on a signal (-1=none, 0=down, 1=up)."""
    conn = _get_conn()
    cur = conn.execute(
        "UPDATE meditation_signals SET user_feedback = ? WHERE id = ?",
        (feedback, signal_id),
    )
    conn.commit()
    return cur.rowcount > 0


def list_signals(kb_id: str = "", days: int = 7, limit: int = 100) -> list[dict]:
    """List signals, optionally filtered."""
    conn = _get_conn()
    if kb_id:
        rows = conn.execute(
            """SELECT * FROM meditation_signals
               WHERE kb_id = ? AND created_at >= datetime('now', ?)
               ORDER BY created_at DESC LIMIT ?""",
            (kb_id, f"-{days} days", limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT * FROM meditation_signals
               WHERE created_at >= datetime('now', ?)
               ORDER BY created_at DESC LIMIT ?""",
            (f"-{days} days", limit),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Run CRUD ───────────────────────────────────────────────────────────

def create_run(kb_id: str, harness: str, trigger: str = "scheduled",
               pid: int | None = None) -> int:
    """Create a new meditation run record. Returns the run id."""
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        """INSERT INTO meditation_runs
           (kb_id, harness, trigger, started_at, status, pid)
           VALUES (?, ?, ?, ?, 'running', ?)""",
        (kb_id, harness, trigger, now, pid),
    )
    conn.commit()
    return cur.lastrowid


def update_run(run_id: int, **kwargs: Any) -> None:
    """Update fields on a meditation run."""
    if not kwargs:
        return
    conn = _get_conn()
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values())
    conn.execute(
        f"UPDATE meditation_runs SET {sets} WHERE id = ?",
        values + [run_id],
    )
    conn.commit()


def finish_run(run_id: int, status: str = "completed",
               experiences_created: int = 0, drafts_created: int = 0,
               signals_processed: int = 0, error: str = "",
               report_json: str = "{}", agent_stdout_tail: str = "",
               exit_code: int | None = None) -> None:
    """Mark a run as finished with final stats."""
    now = datetime.now(timezone.utc).isoformat()
    update_run(
        run_id,
        finished_at=now, status=status,
        experiences_created=experiences_created,
        drafts_created=drafts_created,
        signals_processed=signals_processed,
        error=error, report_json=report_json,
        agent_stdout_tail=agent_stdout_tail,
        exit_code=exit_code,
    )


def get_run(run_id: int) -> dict | None:
    """Get a single run record."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM meditation_runs WHERE id = ?", (run_id,)).fetchone()
    return dict(row) if row else None


def list_runs(kb_id: str = "", limit: int = 20) -> list[dict]:
    """List recent meditation runs, optionally filtered by KB."""
    conn = _get_conn()
    if kb_id:
        rows = conn.execute(
            "SELECT * FROM meditation_runs WHERE kb_id = ? ORDER BY started_at DESC LIMIT ?",
            (kb_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM meditation_runs ORDER BY started_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_running_count(kb_id: str = "") -> int:
    """Count currently running meditations."""
    conn = _get_conn()
    if kb_id:
        row = conn.execute(
            "SELECT COUNT(*) as c FROM meditation_runs WHERE status = 'running' AND kb_id = ?",
            (kb_id,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT COUNT(*) as c FROM meditation_runs WHERE status = 'running'",
        ).fetchone()
    return row["c"] if row else 0


def close() -> None:
    """Close the thread-local connection."""
    conn = getattr(_local, "conn", None)
    if conn is not None:
        conn.close()
        _local.conn = None
