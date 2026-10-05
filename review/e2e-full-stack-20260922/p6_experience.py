"""P6 — experience system full lifecycle E2E on the P3 test KB.

init -> create -> list/read/update -> review -> apply -> extract(heuristic)
-> drafts -> approve -> search hit -> dashboard/stale/decay -> global-search
-> meditation config + mock-harness run + history.
Usage: python review/e2e-full-stack-20260922/p6_experience.py
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
print("[i] test KB: " + KB)


def find_id(j, prefix):
    """Walk a JSON payload and return the first string starting with prefix."""
    if isinstance(j, str):
        return j if j.startswith(prefix) else ""
    if isinstance(j, dict):
        for v in j.values():
            hit = find_id(v, prefix)
            if hit:
                return hit
    if isinstance(j, list):
        for v in j:
            hit = find_id(v, prefix)
            if hit:
                return hit
    return ""

# 1. init
s, j = call_json("POST", BE + "/api/v1/experience/" + KB + "/init")
check("experience init", s == 200 and j.get("success"), json.dumps(j, ensure_ascii=False)[:140])

# 2. create a real ops experience
s, j = call_json("POST", BE + "/api/v1/experience/" + KB, {
    "title": "MinerU 本地解析首次启动超时的处置经验",
    "scenario": "PDF 解析入库",
    "category": "troubleshooting",
    "problem": "冷启动 MinerU 本地引擎时首次解析请求超时，模型加载耗时被计入请求超时窗口。",
    "solution": "先调用 /api/v1/mineru/status 确认引擎状态，冷启动场景将客户端超时放宽到 1200s 以上；或先发一个 1 页小 PDF 预热。",
    "result": "success",
    "key_lessons": ["冷启动预热", "超时按模式区分", "解析前先探活"],
    "tags": ["mineru", "parse", "e2e"],
    "severity": "normal",
})
exp_id = find_id(j, "exp-")
check("experience create", s == 200 and j.get("success") and bool(exp_id), "exp_id=" + str(exp_id))

# 3. list + read + update
s, j = call_json("GET", BE + "/api/v1/experience/" + KB)
check("experience list", s == 200 and len(j.get("experiences") or []) >= 1, "count=" + str(len(j.get("experiences") or [])))
s, j = call_json("GET", BE + "/api/v1/experience/" + KB + "/" + exp_id)
check("experience read", s == 200 and (j.get("experience") or {}).get("title", "").startswith("MinerU"),
      json.dumps(j, ensure_ascii=False)[:120])
s, j = call_json("PUT", BE + "/api/v1/experience/" + KB + "/" + exp_id,
                 {"key_lessons": ["冷启动预热", "超时按模式区分", "解析前先探活", "解析产物走 save-parsed-files 落库"]})
check("experience update", s == 200 and j.get("success"), json.dumps(j, ensure_ascii=False)[:120])

# 4. review + apply (credibility path)
s, j = call_json("POST", BE + "/api/v1/experience/" + KB + "/" + exp_id + "/review",
                 {"reviewer": "e2e-full", "rating": 5, "comment": "verified in E2E run"})
check("experience review", s == 200 and j.get("success"), json.dumps(j, ensure_ascii=False)[:120])
s, j = call_json("POST", BE + "/api/v1/experience/" + KB + "/" + exp_id + "/apply",
                 {"user": "e2e-full", "context": "P3 PDF parse", "result": "success",
                  "notes": "applied preheat advice during ingest"})
check("experience apply", s == 200 and j.get("success"), json.dumps(j, ensure_ascii=False)[:120])

# 5. extract -> drafts -> approve
s, j = call_json("POST", BE + "/api/v1/experience/" + KB + "/extract",
                 {"doc_paths": [state["kb_name"] + "/平台架构总览.md"], "dry_run": False, "mode": "heuristic"}, timeout=120)
check("experience extract (heuristic -> draft pool)", s == 200 and j.get("success"),
      json.dumps(j, ensure_ascii=False)[:160])
s, j = call_json("GET", BE + "/api/v1/experience/" + KB + "/drafts")
drafts = j.get("drafts") or []
check("drafts list", s == 200 and len(drafts) >= 1, "drafts=" + str(len(drafts)))
approved = False
for d in drafts:
    did = d.get("draft_id") or d.get("id") or ""
    if not did:
        continue
    s, j = call_json("POST", BE + "/api/v1/experience/" + KB + "/drafts/" + did + "/approve", {})
    approved = s == 200 and j.get("success", True)
    if approved:
        check("draft approve (" + did[:18] + "...)", True, json.dumps(j, ensure_ascii=False)[:120])
        break
if not drafts:
    check("draft approve", False, "no drafts produced by heuristic extraction")

# 6. search: kb-scoped + global QDCVR — both return `experiences`
s, j = call_json("POST", BE + "/api/v1/experience/" + KB + "/search", {"query": "MinerU 解析超时", "top_k": 5})
hits = j.get("experiences") or j.get("results") or []
check("experience kb search hit", s == 200 and len(hits) >= 1, "hits=" + str(len(hits)))
s, j = call_json("POST", BE + "/api/v1/experience/global-search",
                 {"query": "PDF 解析冷启动怎么处理", "top_k": 5}, timeout=120)
ghits = j.get("experiences") or j.get("results") or []
check("experience global-search (QDCVR)", s == 200 and j.get("success") and len(ghits) >= 1,
      "hits=" + str(len(ghits)) + " " + json.dumps(j, ensure_ascii=False)[:120])

# 7. dashboard / stale / decay
s, j = call_json("GET", BE + "/api/v1/experience/" + KB + "/dashboard")
check("experience dashboard", s == 200 and j.get("success"), json.dumps(j, ensure_ascii=False)[:140])
s, j = call_json("GET", BE + "/api/v1/experience/" + KB + "/stale")
check("experience stale check", s == 200 and j.get("success"), json.dumps(j, ensure_ascii=False)[:100])
s, j = call_json("POST", BE + "/api/v1/experience/" + KB + "/decay")
check("experience apply decay", s == 200 and j.get("success"), json.dumps(j, ensure_ascii=False)[:100])

# 8. meditation: config -> mock run -> history
s, j = call_json("GET", BE + "/api/v1/meditation/config?kb_id=" + quote(KB))
check("meditation config get", s == 200 and j.get("success"), json.dumps(j, ensure_ascii=False)[:120])
s, j = call_json("PUT", BE + "/api/v1/meditation/config",
                 {"kb_id": KB, "config": {"enabled": True, "harness": "mock", "interval_hours": 12}})
check("meditation config put (harness=mock)", s == 200 and j.get("success"), json.dumps(j, ensure_ascii=False)[:120])
s, j = call_json("POST", BE + "/api/v1/meditation/run", {"kb_id": KB, "trigger": "manual", "harness": "mock"}, timeout=300)
run_ok = s in (200, 202) and j.get("success", True)
check("meditation run (mock harness)", run_ok, json.dumps(j, ensure_ascii=False)[:200])
s, j = call_json("GET", BE + "/api/v1/meditation/history?kb_id=" + quote(KB) + "&limit=5")
check("meditation history", s == 200 and j.get("success"), "runs=" + str(len(j.get("runs") or [])))
s, j = call_json("GET", BE + "/api/v1/meditation/status")
check("meditation status", s == 200 and j.get("success"), "keys=" + ",".join(list(j.keys())[:6]))

print()
failed = [n for n, ok, _ in results if not ok]
print("==== P6 experience summary: " + str(len(results) - len(failed)) + "/" + str(len(results)) + " passed ====")
sys.exit(1 if failed else 0)
