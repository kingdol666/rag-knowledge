"""P7b — SOUL lifecycle continuation: async learn -> approve -> ask/qdcvr/router
-> evaluate -> checkpoint -> cognition -> rollback -> export -> training history.

Reuses soul-e2e-tester created by p7_soul.py (soul_kb in p3_state.json).
Usage: python review/e2e-full-stack-20260922/p7b_soul_resume.py
"""
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
results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("[PASS] " if cond else "[FAIL] ") + name + ("  -- " + detail if detail else ""), flush=True)


def call_json(method, url, body=None, token=TOKEN, timeout=300):
    guard_url(url)
    req = urllib.request.Request(url, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data=data, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8", "replace"))
        except Exception:
            return e.code, {}


def poll_task(task_id, minutes=16, interval=10):
    deadline = time.time() + minutes * 60
    last = {}
    while time.time() < deadline:
        s, j = call_json("GET", BE + "/api/v1/soul/tasks/" + task_id, timeout=60)
        last = j or {}
        t = j.get("task") or j
        status = t.get("status") or ""
        if status in ("completed", "failed", "error", "cancelled", "done", "succeeded", "timeout", "partial"):
            return status, last
        print("    ... " + task_id[:20] + " status=" + (status or "?") + " " + json.dumps(t.get("progress") or "", ensure_ascii=False)[:80], flush=True)
        time.sleep(interval)
    return "timeout", last


BE = "http://127.0.0.1:8771"
state = json.loads(HERE.joinpath("p3_state.json").read_text(encoding="utf-8"))
soul_kb = state.get("soul_kb") or ""
KB_NAME = state["kb_name"]
DOC_A = KB_NAME + "/平台架构总览.md"
print("[i] soul persona: " + soul_kb)
if not soul_kb:
    print("FATAL: no soul_kb in state")
    sys.exit(1)

# ---- 5b. async learn ----
s, j = call_json("POST", BE + "/api/v1/soul/" + soul_kb + "/learn",
                 {"doc_paths": [DOC_A], "limit": 1, "rounds": 1, "async_mode": True}, timeout=90)
learn_task = j.get("task_id") or ""
check("soul learn async accepted", s == 200 and j.get("success", True) and bool(learn_task),
      "task_id=" + str(learn_task) + " " + json.dumps(j, ensure_ascii=False)[:140])
if learn_task:
    status, payload = poll_task(learn_task, minutes=16, interval=10)
    check("soul learn completed", status in ("completed", "done"), "status=" + status + " " + json.dumps(payload, ensure_ascii=False)[:240])

# ---- status after learn ----
s, j = call_json("GET", BE + "/api/v1/soul/" + soul_kb + "/status")
st = j.get("status") or j
check("soul status after learn", s == 200, json.dumps(st, ensure_ascii=False)[:200])

# ---- 6. memory drafts -> approve ----
s, j = call_json("POST", BE + "/api/v1/soul/" + soul_kb + "/review-drafts",
                 {"draft_type": "memory", "action": "list"})
drafts = j.get("drafts") or []
check("soul memory drafts list", s == 200, "drafts=" + str(len(drafts)) + " " + json.dumps(j, ensure_ascii=False)[:140])
approved = False
for d in drafts:
    did = d.get("draft_id") or d.get("id") or ""
    if not did:
        continue
    s, j = call_json("POST", BE + "/api/v1/soul/" + soul_kb + "/review-drafts",
                     {"draft_type": "memory", "action": "approve", "draft_ids": [did]}, timeout=180)
    ok = s == 200 and j.get("success", True)
    if ok:
        approved = True
        check("soul memory draft approve", True, did + " " + json.dumps(j, ensure_ascii=False)[:120])
        break
if drafts and not approved:
    check("soul memory draft approve", False, "all approves failed")

# ---- 7. ask / qdcvr-ask / router ----
s, j = call_json("POST", BE + "/api/v1/soul/ask",
                 {"query": "这个平台的知识库入库流程是怎样的？", "soul_kb_id": soul_kb}, timeout=600)
ask = j.get("answer") or ""
check("soul ask (persona answer)", s == 200 and len(ask) > 40,
      "pas=" + str(j.get("pas_score")) + " citations=" + str(len(j.get("citations") or [])) + " answer[:90]=" + ask[:90].replace(chr(10), " "))

s, j = call_json("POST", BE + "/api/v1/soul/qdcvr-ask",
                 {"query": "MinerU 解析 PDF 后如何入库？", "soul_kb_id": soul_kb, "top_k": 5}, timeout=600)
check("soul qdcvr-ask (evidence)", s == 200 and len(j.get("answer") or "") > 40,
      "evidence=" + str(j.get("evidence_count")) + " pas=" + str(j.get("pas_score")))

s, j = call_json("POST", BE + "/api/v1/soul/router", {"query": "帮我看看平台的架构设计"}, timeout=120)
check("soul router", s == 200 and j.get("success", True),
      "selected=" + str(j.get("selected_soul")) + " conf=" + str(j.get("route_confidence")))

# ---- 8. evaluate (4-dim) ----
s, j = call_json("POST", BE + "/api/v1/soul/" + soul_kb + "/evaluate", {}, timeout=600)
check("soul evaluate (identity/values/thinking/language)", s == 200,
      json.dumps(j, ensure_ascii=False)[:220])

# ---- 9. checkpoint ----
s, j = call_json("POST", BE + "/api/v1/soul/" + soul_kb + "/checkpoint", {}, timeout=120)
cp_id = j.get("checkpoint_id") or ""
check("soul checkpoint", s == 200 and bool(cp_id), "checkpoint_id=" + str(cp_id))

# ---- 10. cognition drafts (async) -> reject-first review ----
s, j = call_json("POST", BE + "/api/v1/soul/" + soul_kb + "/cognition-drafts", {}, timeout=120)
cg_task = j.get("task_id") or ""
check("soul cognition-drafts accepted", s == 200 and j.get("success", True), "task=" + str(cg_task))
if cg_task:
    poll_task(cg_task, minutes=8, interval=8)
s, j = call_json("POST", BE + "/api/v1/soul/" + soul_kb + "/review-drafts",
                 {"draft_type": "cognition", "action": "list"})
cg_drafts = j.get("drafts") or []
check("soul cognition drafts list", s == 200, "drafts=" + str(len(cg_drafts)))
for d in cg_drafts[:1]:
    did = d.get("draft_id") or d.get("id") or ""
    if did:
        s, j = call_json("POST", BE + "/api/v1/soul/" + soul_kb + "/review-drafts",
                         {"draft_type": "cognition", "action": "reject", "draft_ids": [did]}, timeout=120)
        check("soul cognition draft reject", s == 200 and j.get("success", True), did)

# ---- 11. rollback ----
if cp_id:
    s, j = call_json("POST", BE + "/api/v1/soul/" + soul_kb + "/rollback",
                     {"checkpoint_id": cp_id}, timeout=120)
    check("soul rollback", s == 200 and j.get("success", True), json.dumps(j, ensure_ascii=False)[:140])

# ---- 12. export ----
s, j = call_json("POST", BE + "/api/v1/soul/" + soul_kb + "/export", {"min_score": 3.0, "limit": 100}, timeout=120)
check("soul export", s == 200 and j.get("success", True), json.dumps(j, ensure_ascii=False)[:160])

# ---- 13. training history ----
s, j = call_json("GET", BE + "/api/v1/soul/training/history?soul_kb_id=" + quote(soul_kb) + "&limit=5")
check("soul training history", s == 200, json.dumps(j, ensure_ascii=False)[:140])

print()
failed = [n for n, ok, _ in results if not ok]
print("==== P7b soul-resume summary: " + str(len(results) - len(failed)) + "/" + str(len(results)) + " passed ====")
sys.exit(1 if failed else 0)
