"""Shared helpers for the E2E OMP+AWS acceptance run (2026-10-01).

URL policy: every base URL is a module-level literal, validated with the
repo-standard guard_url (loopback-only) before any request — same pattern as
benchmark-suite/experiments/chat_mode_arms.py.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
from dev_smoke import OPENER, guard_url  # noqa: E402

OUT = Path(__file__).resolve().parent
CHAT = "http://127.0.0.1:6789/api/claude/chat"
AGENT_CHAT = "http://127.0.0.1:6789/api/kb/agent/chat"
AGENT_TASK = "http://127.0.0.1:6789/api/kb/agent/tasks"
AW = "http://127.0.0.1:3996"
WEB = "http://127.0.0.1:6789"
BACKEND = "http://127.0.0.1:8771"

KB_CS = "b1199132-e4d4-4305-8c2e-82dc1753b0ba"    # 计算机与人工智能
KB_LIFE = "b28f0a25-1e1d-40ad-96b8-61bd2b093a28"  # 生命科学与医学


def token() -> str:
    d = json.loads((REPO / "storage" / "loop-auth.json").read_text(encoding="utf-8"))
    return d["token"]


def _save(rec: dict, tag: str) -> None:
    (OUT / f"{tag}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1),
                                     encoding="utf-8")


def _request_json(url: str, method: str, body=None, headers=None,
                  timeout_s: float = 60.0):
    guard_url(url)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, method=method, data=data,
                                 headers={"Content-Type": "application/json",
                                          **(headers or {})})
    with OPENER.open(req, timeout=timeout_s) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


def chat(prompt: str, *, engine: str = "omp", kb_ids=None, kb_enhanced: bool = True,
         max_turns: int = 18, timeout_s: float = 480.0, tag: str = "call",
         permission_mode: str = "default") -> dict:
    """One non-stream chat-API call; persists the full evidence JSON."""
    body = {"prompt": prompt, "engine": engine, "kbEnhanced": kb_enhanced,
            "maxTurns": max_turns, "permissionMode": permission_mode,
            "timeout_ms": int(timeout_s * 1000), "stream": False}
    if kb_ids:
        body["kbIds"] = kb_ids
    t0 = time.time()
    rec: dict = {"tag": tag, "engine": engine, "request": body}
    try:
        status, payload = _request_json(CHAT, "POST", body,
                                        {"Authorization": f"Bearer {token()}"},
                                        timeout_s)
        rec.update({"http": status, "wall_s": round(time.time() - t0, 1),
                    "response": payload,
                    "answer": str(payload.get("answer") or ""),
                    "num_turns": payload.get("num_turns"),
                    "cost_usd": payload.get("total_cost_usd"),
                    "session_id": payload.get("sessionId")})
    except urllib.error.HTTPError as e:
        rec.update({"http": e.code, "wall_s": round(time.time() - t0, 1),
                    "error": e.read().decode("utf-8", "replace")[:300]})
    except Exception as e:  # noqa: BLE001 - 记录后继续
        rec.update({"http": None, "wall_s": round(time.time() - t0, 1),
                    "error": f"{type(e).__name__}: {str(e)[:300]}"})
    _save(rec, tag)
    return rec


def agent_chat(prompt: str, *, mode: str = "async", timeout_s: float = 540.0,
               tag: str = "agent") -> dict:
    """POST web /api/kb/agent/chat (the exact surface the AWS plugin calls)."""
    body = {"prompt": prompt, "timeout_ms": int(timeout_s * 1000), "mode": mode}
    t0 = time.time()
    rec: dict = {"tag": tag, "mode": mode, "request_prompt": prompt[:200]}
    try:
        status, payload = _request_json(AGENT_CHAT, "POST", body,
                                        {"Authorization": f"Bearer {token()}"},
                                        timeout_s + 30)
        rec.update({"http": status, "wall_s": round(time.time() - t0, 1),
                    "response": payload})
        if mode == "sync":
            rec["reply"] = str(payload.get("reply") or "")
        else:
            rec["task_id"] = payload.get("task_id")
    except urllib.error.HTTPError as e:
        rec.update({"http": e.code, "wall_s": round(time.time() - t0, 1),
                    "error": e.read().decode("utf-8", "replace")[:300]})
    except Exception as e:  # noqa: BLE001
        rec.update({"http": None, "wall_s": round(time.time() - t0, 1),
                    "error": f"{type(e).__name__}: {str(e)[:300]}"})
    _save(rec, tag)
    return rec


def agent_task(task_id: str, *, timeout_s: float = 540.0, tag: str = "task") -> dict:
    """Poll GET /api/kb/agent/tasks/:id until completed/failed."""
    deadline = time.time() + timeout_s
    last: dict = {}
    while time.time() < deadline:
        try:
            status_code, payload = _request_json(
                AGENT_TASK + "/" + task_id, "GET", None,
                {"Authorization": f"Bearer {token()}"}, 30)
            last = payload
        except Exception as e:  # noqa: BLE001
            last = {"error": str(e)[:200]}
        status = str(last.get("status") or "")
        if status in ("completed", "failed", "error"):
            rec = {"tag": tag, "task_id": task_id, "status": status,
                   "final": last}
            _save(rec, tag)
            return rec
        time.sleep(6)
    rec = {"tag": tag, "task_id": task_id, "status": "timeout", "final": last}
    _save(rec, tag)
    return rec


def catalog() -> list:
    """GET web /api/kb/catalog → knowledgeBases list."""
    guard_url(WEB + "/api/kb/catalog")
    req = urllib.request.Request(WEB + "/api/kb/catalog",
                                 headers={"Authorization": f"Bearer {token()}"})
    with OPENER.open(req, timeout=20) as r:
        d = json.loads(r.read().decode("utf-8"))
    return d.get("knowledgeBases", [])


def refusal(answer: str) -> bool:
    low = (answer or "").lower()
    markers = ("无法", "没有找到", "未找到", "未检索到", "没有检索到", "不存在",
               "无法回答", "无法作答", "无法据此", "not found", "no document",
               "cannot answer", "unable to answer", "no evidence", "cannot find",
               "not covered", "outside the corpus", "not in the library")
    return any(m in low for m in markers)
