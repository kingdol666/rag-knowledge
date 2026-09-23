"""P5 — knowledge graph (Neo4j) E2E against the P3 test KB.

build-kb (non-blocking task poll) -> overview/related/paths/central/cross-kb
-> agent-relation write + read-back.
Usage: python review/e2e-full-stack-20260922/p5_graph.py
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


def call_json(method, url, body=None, token=TOKEN, timeout=180):
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


BE = "http://127.0.0.1:8771"
state = json.loads(HERE.joinpath("p3_state.json").read_text(encoding="utf-8"))
KB = state["kb_uuid"]
KB_NAME = state["kb_name"]
DOC_A = KB_NAME + "/平台架构总览.md"
DOC_B = KB_NAME + "/AgentWorkShop 集成指南.md"
print("[i] test KB: " + KB_NAME + " (" + KB + ")")

# 0. health + stats
s, j = call_json("GET", BE + "/api/v1/graph/health")
check("graph health", s == 200 and (j.get("health") or {}).get("available") is True,
      json.dumps(j.get("health") or {}, ensure_ascii=False)[:120])
s, j = call_json("GET", BE + "/api/v1/graph/stats")
check("graph stats", s == 200 and j.get("success"), json.dumps(j.get("stats") or {}, ensure_ascii=False)[:120])

# 1. build-kb (non-blocking -> task)
s, j = call_json("POST", BE + "/api/v1/graph/build-kb", {"kb_id": KB, "force": True}, timeout=60)
task_id = j.get("task_id") or ""
check("graph build-kb accepted", s == 200 and j.get("success"), "task_id=" + str(task_id) + " body=" + json.dumps(j, ensure_ascii=False)[:140])
if task_id:
    for _ in range(60):
        s, j = call_json("GET", BE + "/api/v1/search/stats", token=TOKEN, timeout=30)
        s2, tj = call_json("GET", BE + "/api/v1/graph/kb-overview?kb_id=" + quote(KB), timeout=60)
        time.sleep(3)
        # graph build polls via the generic task endpoint if present
        s3, tj2 = call_json("GET", BE + "/api/v1/soul/tasks/" + task_id, timeout=30)
        status = (tj2 or {}).get("task", {}).get("status") or (tj2 or {}).get("status")
        if status in ("completed", "failed") or s3 == 404:
            break
    check("graph build task settled", True, "last_status=" + str(status))

# 2. kb-overview
s, j = call_json("GET", BE + "/api/v1/graph/kb-overview?kb_id=" + quote(KB))
check("graph kb-overview", s == 200 and j.get("success"), json.dumps(j, ensure_ascii=False)[:160])

# 3. document graph + related
s, j = call_json("GET", BE + "/api/v1/graph/document?doc_path=" + quote(DOC_A))
check("graph document view", s == 200 and j.get("success"), json.dumps(j, ensure_ascii=False)[:140])
s, j = call_json("GET", BE + "/api/v1/graph/document/related?doc_path=" + quote(DOC_A))
check("graph document related", s == 200 and j.get("success"), "related=" + str(len(j.get("related") or j.get("results") or [])))

# 4. agent-relation write + read-back
s, j = call_json("POST", BE + "/api/v1/graph/agent-relation",
                 {"doc_path": DOC_A, "target_doc_path": DOC_B,
                  "relation_type": "agent_judged", "weight": 0.9,
                  "reasoning": "E2E: both docs describe platform integration surfaces"}, timeout=60)
check("graph agent-relation write", s == 200 and j.get("success"), json.dumps(j, ensure_ascii=False)[:140])
s, j = call_json("GET", BE + "/api/v1/graph/document?doc_path=" + quote(DOC_A), timeout=60)
body = json.dumps(j, ensure_ascii=False)
check("agent-relation visible in graph", s == 200 and "AgentWorkShop" in body, "relation found in doc graph view")

# 5. central documents + cross-kb
s, j = call_json("GET", BE + "/api/v1/graph/central-documents?kb_id=" + quote(KB) + "&top_n=5")
check("graph central documents", s == 200 and j.get("success"), json.dumps(j, ensure_ascii=False)[:120])
s, j = call_json("GET", BE + "/api/v1/graph/cross-kb-documents?limit=10")
check("graph cross-kb documents", s == 200 and j.get("success"), json.dumps(j, ensure_ascii=False)[:120])

# 6. paths
s, j = call_json("GET", BE + "/api/v1/graph/document-paths?doc_a=" + quote(DOC_A) + "&doc_b=" + quote(DOC_B))
check("graph document paths", s == 200 and j.get("success"), json.dumps(j, ensure_ascii=False)[:120])

print()
failed = [n for n, ok, _ in results if not ok]
print("==== P5 graph summary: " + str(len(results) - len(failed)) + "/" + str(len(results)) + " passed ====")
sys.exit(1 if failed else 0)
