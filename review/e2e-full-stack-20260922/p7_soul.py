"""P7 — SOUL persona full lifecycle E2E (branch headline feature).

init -> bootstrap poll -> list/status/folder/persona-docs -> config update
-> learn (real harness, limit=1 rounds=1) -> memory drafts approve -> ask
-> qdcvr-ask -> router -> evaluate (4-dim) -> checkpoint -> cognition drafts
-> rollback -> export. A throwaway persona is created + deleted to validate
the delete path. The main persona is kept for P8/P9 (frontend needs it).

Usage: python review/e2e-full-stack-20260922/p7_soul.py [--fast]
  --fast: use harness=mock everywhere (no real LLM calls)
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
FAST = "--fast" in sys.argv
HARNESS = "mock" if FAST else ""


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


def poll_task(task_id, minutes=12, interval=10):
    """Poll GET /api/v1/soul/tasks/{id} until terminal; returns last payload."""
    deadline = time.time() + minutes * 60
    last = {}
    while time.time() < deadline:
        s, j = call_json("GET", BE + "/api/v1/soul/tasks/" + task_id, timeout=60)
        last = j or {}
        t = j.get("task") or j
        status = t.get("status") or ""
        if status in ("completed", "failed", "error", "cancelled", "done", "succeeded", "partial", "timeout"):
            return status, last
        print("    ... task " + task_id[:24] + " status=" + (status or "?"), flush=True)
        time.sleep(interval)
    return "timeout", last


BE = "http://127.0.0.1:8771"
WEB = "http://127.0.0.1:6789"
state = json.loads(HERE.joinpath("p3_state.json").read_text(encoding="utf-8"))
KB_NAME = state["kb_name"]
DOC_A = KB_NAME + "/平台架构总览.md"
stamp = time.strftime("%m%d-%H%M%S")

# ---- 0. settings + list baseline ----
s, j = call_json("GET", BE + "/api/v1/soul/settings")
check("soul settings", s == 200 and j.get("success", True), json.dumps(j, ensure_ascii=False)[:120])
s, j = call_json("GET", BE + "/api/v1/soul/list")
soul_list = j if isinstance(j, list) else (j.get("souls") or j.get("personas") or [])
before = len(soul_list)
check("soul list baseline", s == 200, "count=" + str(before) + " " + json.dumps(soul_list, ensure_ascii=False)[:100])

# ---- 1. throwaway persona: init + delete (validates both paths) ----
s, j = call_json("POST", WEB + "/api/soul/init",
                 {"name": "e2e-throwaway" + stamp[-6:], "harness": "mock"}, timeout=300)
thr_kb = j.get("kb_id") or ""
check("soul init (throwaway)", s == 200 and j.get("success", True) and bool(thr_kb),
      "kb_id=" + str(thr_kb) + " body=" + json.dumps(j, ensure_ascii=False)[:140])
if thr_kb:
    s, j = call_json("DELETE", BE + "/api/v1/soul/" + thr_kb + "?purge_experiences=false", timeout=120)
    check("soul delete (throwaway, checkpoint-first)", s == 200 and j.get("success", True),
          json.dumps(j, ensure_ascii=False)[:140])

# ---- 2. main persona init ----
s, j = call_json("POST", WEB + "/api/soul/init",
                 {"name": "e2e-tester-" + time.strftime("%H%M%S"), "kb_scope": ["*"],
                  "domain_labels": ["e2e", "platform-testing"], "harness": HARNESS or "omp"}, timeout=300)
soul_kb = j.get("kb_id") or ""
profile_task = j.get("profile_task_id") or ""
index_task = j.get("task_id") or ""
check("soul init (e2e-tester)", s == 200 and bool(soul_kb),
      "kb_id=" + str(soul_kb) + " profile_task=" + str(profile_task) + " index_task=" + str(index_task))
if not soul_kb:
    print("FATAL: no soul kb; aborting P7")
    sys.exit(1)
state["soul_kb"] = soul_kb
HERE.joinpath("p3_state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

for tid in (profile_task, index_task):
    if tid:
        status, payload = poll_task(tid, minutes=4, interval=5)
        check("soul bootstrap task " + tid[:16], status == "completed", "status=" + status + " " + json.dumps(payload, ensure_ascii=False)[:120])

# ---- 3. status / folder / persona-docs ----
s, j = call_json("GET", BE + "/api/v1/soul/" + soul_kb + "/status")
check("soul status", s == 200 and j.get("success", True), json.dumps(j, ensure_ascii=False)[:140])
s, j = call_json("GET", BE + "/api/v1/soul/" + soul_kb + "/folder")
check("soul folder (11-section view)", s == 200, json.dumps(j, ensure_ascii=False)[:140])
s, j = call_json("GET", BE + "/api/v1/soul/" + soul_kb + "/persona-docs")
docs_n = len(j.get("documents") or j.get("docs") or [])
check("soul persona-docs (4 constitution docs)", s == 200 and docs_n >= 4, "docs=" + str(docs_n))
s, j = call_json("GET", BE + "/api/v1/soul/list")
soul_list = j if isinstance(j, list) else (j.get("souls") or j.get("personas") or [])
names = json.dumps(soul_list, ensure_ascii=False)
check("soul list contains e2e-tester", "soul-e2e-tester" in names, names[:120])

# ---- 4. config update ----
s, j = call_json("PUT", BE + "/api/v1/soul/" + soul_kb + "/config",
                 {"domain_labels": ["e2e", "platform-testing", "rag"], "kb_scope": ["*"]})
check("soul config update", s == 200 and j.get("success", True), json.dumps(j, ensure_ascii=False)[:120])

# ---- 5. learn (real harness unless --fast) ----
s, j = call_json("POST", BE + "/api/v1/soul/" + soul_kb + "/learn",
                 {"doc_paths": [DOC_A], "limit": 1, "rounds": 1}, timeout=120)
learn_task = j.get("task_id") or ""
check("soul learn accepted", s == 200 and j.get("success", True) and bool(learn_task),
      "task_id=" + str(learn_task) + " " + json.dumps(j, ensure_ascii=False)[:140])
if learn_task:
    status, payload = poll_task(learn_task, minutes=14, interval=10)
    check("soul learn completed", status == "completed", "status=" + status + " " + json.dumps(payload, ensure_ascii=False)[:200])

# ---- 6. memory drafts -> approve ----
s, j = call_json("POST", BE + "/api/v1/soul/" + soul_kb + "/review-drafts",
                 {"draft_type": "memory", "action": "list"})
drafts = j.get("drafts") or []
check("soul memory drafts list", s == 200, "drafts=" + str(len(drafts)) + " " + json.dumps(j, ensure_ascii=False)[:120])
approved_any = False
for d in drafts:
    did = d.get("draft_id") or d.get("id") or ""
    if not did:
        continue
    s, j = call_json("POST", BE + "/api/v1/soul/" + soul_kb + "/review-drafts",
                     {"draft_type": "memory", "action": "approve", "draft_ids": [did]}, timeout=300)
    ok = s == 200 and j.get("success", True)
    approved_any = approved_any or ok
    if ok:
        check("soul memory draft approve", True, did + " " + json.dumps(j, ensure_ascii=False)[:120])
        break
if not approved_any and drafts:
    check("soul memory draft approve", False, "approve failed for all drafts")

# ---- 7. ask / qdcvr-ask / router ----
s, j = call_json("POST", BE + "/api/v1/soul/ask",
                 {"query": "这个平台的知识库入库流程是怎样的？", "soul_kb_id": soul_kb}, timeout=600)
ask = j.get("answer") or ""
check("soul ask (citations + pas)", s == 200 and len(ask) > 40,
      "pas=" + str(j.get("pas_score")) + " citations=" + str(len(j.get("citations") or [])) + " answer[:80]=" + ask[:80].replace("\n", " "))

s, j = call_json("POST", BE + "/api/v1/soul/qdcvr-ask",
                 {"query": "MinerU 解析 PDF 后如何入库？", "soul_kb_id": soul_kb, "top_k": 5}, timeout=600)
check("soul qdcvr-ask (evidence)", s == 200 and len(j.get("answer") or "") > 40,
      "evidence=" + str(j.get("evidence_count")) + " pas=" + str(j.get("pas_score")))

s, j = call_json("POST", BE + "/api/v1/soul/router", {"query": "帮我看看平台的架构设计"}, timeout=120)
check("soul router", s == 200 and j.get("success", True),
      "selected=" + str(j.get("selected_soul")) + " conf=" + str(j.get("route_confidence")))

# ---- 8. evaluate (4-dim) ----
s, j = call_json("POST", BE + "/api/v1/soul/" + soul_kb + "/evaluate", {}, timeout=600)
ev = j.get("evaluation") or j.get("scores") or j
check("soul evaluate (identity/values/thinking/language)", s == 200,
      json.dumps(ev, ensure_ascii=False)[:200])

# ---- 9. checkpoint ----
s, j = call_json("POST", BE + "/api/v1/soul/" + soul_kb + "/checkpoint", {}, timeout=120)
cp_id = j.get("checkpoint_id") or ""
check("soul checkpoint", s == 200 and bool(cp_id), "checkpoint_id=" + str(cp_id))

# ---- 10. cognition drafts (async) -> review ----
s, j = call_json("POST", BE + "/api/v1/soul/" + soul_kb + "/cognition-drafts", {}, timeout=120)
cg_task = j.get("task_id") or ""
check("soul cognition-drafts accepted", s == 200 and j.get("success", True), "task=" + str(cg_task))
if cg_task:
    poll_task(cg_task, minutes=6, interval=8)
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

# ---- 11. rollback to checkpoint ----
if cp_id:
    s, j = call_json("POST", BE + "/api/v1/soul/" + soul_kb + "/rollback",
                     {"checkpoint_id": cp_id}, timeout=120)
    check("soul rollback", s == 200 and j.get("success", True), json.dumps(j, ensure_ascii=False)[:140])

# ---- 12. export (LoRA JSONL) ----
s, j = call_json("POST", BE + "/api/v1/soul/" + soul_kb + "/export", {"min_score": 3.0, "limit": 100}, timeout=120)
check("soul export", s == 200 and j.get("success", True), json.dumps(j, ensure_ascii=False)[:160])

# ---- 13. training history ----
s, j = call_json("GET", BE + "/api/v1/soul/training/history?soul_kb_id=" + quote(soul_kb) + "&limit=5")
check("soul training history", s == 200, json.dumps(j, ensure_ascii=False)[:120])

print()
failed = [n for n, ok, _ in results if not ok]
print("==== P7 soul summary: " + str(len(results) - len(failed)) + "/" + str(len(results)) + " passed ====")
sys.exit(1 if failed else 0)
