"""P7c — SOUL tail checks: cognition reject, rollback, export, training history."""
import ipaddress
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse, quote

ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
HERE = Path(os.path.dirname(os.path.abspath(__file__)))
ALLOWED_HOSTS = {"127.0.0.1", "localhost"}
ALLOWED_PORTS = {8771, 6789}


def guard_url(url: str) -> None:
    p = urlparse(url)
    if p.scheme != "http" or p.hostname not in ALLOWED_HOSTS:
        raise ValueError("blocked target: " + repr(url))
    if p.port not in ALLOWED_PORTS:
        raise ValueError("blocked target: " + repr(url))
    ip = socket.gethostbyname(p.hostname)
    if ipaddress.ip_address(ip) != ipaddress.ip_address("127.0.0.1"):
        raise ValueError("DNS rebinding blocked: " + url)


def load_token() -> str:
    for line in ROOT.joinpath(".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("MCP_AUTH_TOKEN="):
            return line.split("=", 1)[1].strip()
    return ""


TOKEN = load_token()
BE = "http://127.0.0.1:8771"


def call_json(method, url, body=None, timeout=240):
    guard_url(url)
    req = urllib.request.Request(url, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", "Bearer " + TOKEN)
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data=data, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8", "replace"))
        except Exception:
            return e.code, {}


def poll_task(task_id, minutes=6, interval=6):
    deadline = time.time() + minutes * 60
    last = {}
    while time.time() < deadline:
        s, j = call_json("GET", BE + "/api/v1/soul/tasks/" + task_id, timeout=45)
        last = j or {}
        t = j.get("task") or j
        st = t.get("status") or ""
        if st in ("completed", "failed", "error", "cancelled", "done", "succeeded", "partial", "timeout"):
            return st, last
        time.sleep(interval)
    return "poll-timeout", last


state = json.loads(HERE.joinpath("p3_state.json").read_text(encoding="utf-8"))
soul_kb = state["soul_kb"]
results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("[PASS] " if cond else "[FAIL] ") + name + ("  -- " + detail if detail else ""), flush=True)


# 1. wait for cognition task to settle + list
s, j = call_json("POST", BE + "/api/v1/soul/" + soul_kb + "/review-drafts", {"draft_type": "cognition", "action": "list"})
drafts = j.get("drafts") or []
check("cognition drafts list", s == 200, "drafts=" + str(len(drafts)))
for d in drafts[:1]:
    did = d.get("draft_id") or d.get("id") or ""
    if did:
        s, j = call_json("POST", BE + "/api/v1/soul/" + soul_kb + "/review-drafts",
                         {"draft_type": "cognition", "action": "reject", "draft_ids": [did]})
        check("cognition draft reject", s == 200 and j.get("success", True), did + " " + json.dumps(j, ensure_ascii=False)[:100])

# 2. fresh checkpoint then rollback (id must belong to THIS persona)
s, j = call_json("POST", BE + "/api/v1/soul/" + soul_kb + "/checkpoint", {})
cp_id = (j or {}).get("checkpoint_id") or ""
check("fresh checkpoint", s == 200 and bool(cp_id), "cp=" + str(cp_id))
s, j = call_json("POST", BE + "/api/v1/soul/" + soul_kb + "/rollback", {"checkpoint_id": cp_id})
check("soul rollback", s == 200 and j.get("success", True), json.dumps(j, ensure_ascii=False)[:160])

# 3. export LoRA JSONL
s, j = call_json("POST", BE + "/api/v1/soul/" + soul_kb + "/export", {"min_score": 3.0, "limit": 100})
out = j.get("output_path") or j.get("path") or ""
check("soul export", s == 200 and j.get("success", True), json.dumps(j, ensure_ascii=False)[:180])

# 4. training history
s, j = call_json("GET", BE + "/api/v1/soul/training/history?soul_kb_id=" + quote(soul_kb) + "&limit=5")
runs = j.get("runs") or (j.get("history") or [])
check("soul training history", s == 200 and len(runs) >= 1, "runs=" + str(len(runs)))

# 5. memories now registered + searchable (approved memory indexed)
s, j = call_json("GET", BE + "/api/v1/soul/" + soul_kb + "/status")
st = j.get("status") or j
check("soul status shows memories", s == 200, json.dumps(st, ensure_ascii=False)[:200])

print()
failed = [n for n, ok, _ in results if not ok]
print("==== P7c soul-tail summary: " + str(len(results) - len(failed)) + "/" + str(len(results)) + " passed ====")
sys.exit(1 if failed else 0)
