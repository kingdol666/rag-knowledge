"""S5 — streams & tasks concurrency: 5 parallel mock SSE chats (isolation) +
25 async mock agent tasks (registry under concurrency).

Usage: backend/.venv/Scripts/python.exe review/stress-20260923/s4_streams.py
"""
import json
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, "review/stress-20260923")
from stress_lib import WEB, OPENER, check, guard_url, report  # noqa: E402
from stress_lib import TOKEN  # noqa: E402


def sse_chat(prompt: str, engine: str = "mock", window_s: float = 120):
    guard_url(WEB + "/api/claude/chat")
    req = urllib.request.Request(WEB + "/api/claude/chat", method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "text/event-stream")
    req.add_header("Authorization", "Bearer " + TOKEN)
    body = {"prompt": prompt, "engine": engine, "maxTurns": 5}
    events = []
    done = {}
    sess = ""
    with OPENER.open(req, data=json.dumps(body).encode(), timeout=window_s) as resp:
        buf = b""
        cur_event = ""
        t0 = time.time()
        while time.time() - t0 < window_s:
            chunk = resp.read1(4096) if hasattr(resp, "read1") else resp.read(1)
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                text = line.decode("utf-8", "replace").rstrip("\r")
                if text == "":
                    cur_event = ""
                    continue
                if text.startswith("event:"):
                    cur_event = text[6:].strip()
                    continue
                if not text.startswith("data:"):
                    continue
                try:
                    payload = json.loads(text[5:].strip())
                except ValueError:
                    continue
                etype = payload.get("type") or cur_event or ""
                if cur_event in ("done", "error"):
                    etype = cur_event  # SSE header is authoritative for terminal frames
                events.append(etype)
                if payload.get("session_id"):
                    sess = payload["session_id"]
                elif (payload.get("message") or {}).get("session_id"):
                    sess = payload["message"]["session_id"]
                if etype in ("done", "error", "result"):
                    done = {"type": etype, "payload": payload}
                    return events, done, sess
    return events, done, sess


# ---- 1. five parallel mock SSE chats ----
print("[i] 5 parallel mock SSE chats ...", flush=True)
results = [None] * 5
t0 = time.perf_counter()


def one_chat(i: int):
    marker = f"stress-sse-{i}"
    events, done, sess = sse_chat("Reply with the marker word only: " + marker)
    return i, len(events), done.get("type"), sess, time.perf_counter() - t0


with ThreadPoolExecutor(max_workers=5) as ex:
    for r in ex.map(one_chat, range(5)):
        results[r[0]] = r

sessions = [r[3] for r in results]
dones = [r[2] for r in results]
check("5 parallel SSE all reached done", all(d in ("done", "result") for d in dones),
      f"dones={dones} durs={[round(r[4],1) for r in results]}")
check("5 parallel SSE sessions unique (no cross-talk)", len(set(sessions)) == 5 and all(sessions),
      f"sessions={[s[:8] for s in sessions]}")

# ---- 2. 25 async mock agent tasks ----
print("[i] 25 async mock agent tasks ...", flush=True)
t0 = time.perf_counter()
task_ids = []


def fire_async(i: int):
    guard_url(WEB + "/api/kb/agent/chat")
    req = urllib.request.Request(WEB + "/api/kb/agent/chat", method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", "Bearer " + TOKEN)
    body = {"prompt": "one-word reply: ok" + str(i), "harness": "mock", "mode": "async"}
    with OPENER.open(req, data=json.dumps(body).encode(), timeout=60) as r:
        j = json.loads(r.read().decode("utf-8", "replace"))
    return j.get("task_id") or "", j.get("success", False)


with ThreadPoolExecutor(max_workers=10) as ex:
    fired = list(ex.map(fire_async, range(25)))
dt_fire = time.perf_counter() - t0
task_ids = [t for t, ok in fired if ok and t]
check("25 async agent tasks accepted", len(task_ids) == 25,
      f"accepted={len(task_ids)}/25 fire_dur={dt_fire:.1f}s")

# poll all to terminal
final_status = {}
deadline = time.time() + 180
pending = set(task_ids)
while pending and time.time() < deadline:
    for tid in list(pending):
        guard_url(WEB + "/api/kb/agent/tasks/" + tid)
        req = urllib.request.Request(WEB + "/api/kb/agent/tasks/" + tid)
        req.add_header("Authorization", "Bearer " + TOKEN)
        try:
            with OPENER.open(req, timeout=30) as r:
                j = json.loads(r.read().decode("utf-8", "replace"))
            st = (j.get("task") or j).get("status")
            if st in ("completed", "failed"):
                final_status[tid] = st
                pending.discard(tid)
        except Exception:  # noqa: BLE001
            pass
    if pending:
        time.sleep(2)
n_completed = sum(1 for v in final_status.values() if v == "completed")
check("25/25 async tasks completed", n_completed == 25,
      f"completed={n_completed}/25 poll_window={'done' if not pending else 'timeout'}")

sys.exit(report("S5 streams+tasks"))
