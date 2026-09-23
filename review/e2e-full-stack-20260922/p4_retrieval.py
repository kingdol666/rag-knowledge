"""P4 — multi-strategy retrieval E2E against the P3 test KB.

Reads p3_state.json for kb uuid/name. Covers: vector (scoped + cross-KB),
two-stage (BM25->graph->vector), batch-vector, web keyword search, and the
QDCVR honest-empty negative case.
Usage: python review/e2e-full-stack-20260922/p4_retrieval.py
"""
import ipaddress
import json
import os
import socket
import sys
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
WEB = "http://127.0.0.1:6789"

state = json.loads(HERE.joinpath("p3_state.json").read_text(encoding="utf-8"))
KB = state["kb_uuid"]
KB_NAME = state["kb_name"]
print("[i] test KB: " + KB_NAME + " (" + KB + ")")

# 1. vector search scoped — should hit AgentWorkShop doc
s, j = call_json("POST", BE + "/api/v1/search/vector",
                 {"query": "AgentWorkShop integration kb_agent chat API contract", "kb_id": KB, "top_k": 5})
hits = j.get("results") or []
top_paths = [h.get("doc_path") or h.get("path") or "" for h in hits[:3]]
check("vector scoped hit AgentWorkShop doc", s == 200 and j.get("success") and len(hits) >= 1
      and any("AgentWorkShop" in p for p in top_paths),
      "top=" + json.dumps(top_paths, ensure_ascii=False))

# 2. vector search cross-KB (kb_id="") — global semantic
s, j = call_json("POST", BE + "/api/v1/search/vector",
                 {"query": "MinerU OCR PDF parse pipeline", "kb_id": "", "top_k": 5})
check("vector cross-KB global", s == 200 and j.get("success") and len(j.get("results") or []) >= 1,
      "count=" + str(j.get("count")))

# 3. two-stage with graph expansion
s, j = call_json("POST", BE + "/api/v1/search/two-stage",
                 {"query": "kb-mcp MCP tools knowledge base operations", "kb_id": KB,
                  "stage1_top_k": 20, "stage2_top_k": 5, "enable_graph_expansion": True})
st1 = (j.get("stage1") or {}).get("candidate_count")
st2 = (j.get("stage2") or {}).get("results") or []
check("two-stage stage1+stage2", s == 200 and j.get("success") and (st1 or 0) >= 1 and len(st2) >= 1,
      f"stage1_candidates={st1} stage2={len(st2)}")

# 4. batch-vector
s, j = call_json("POST", BE + "/api/v1/search/batch-vector",
                 {"query_doc_paths": [KB_NAME + "/AgentWorkShop 集成指南.md"], "kb_id": KB, "top_k": 3})
check("batch-vector", s == 200 and j.get("success"), "keys=" + json.dumps(list((j.get("results") or {}).keys())[:3], ensure_ascii=False))

# 5. web keyword search (local file index) — param is `query`, response key is `hits`
s, j = call_json("GET", WEB + "/api/kb/search?query=" + quote("MinerU") + "&top_k=10")
n_kw = len(j.get("hits") or [])
s2, j2 = call_json("GET", WEB + "/api/kb/search?query=" + quote("AgentWorkShop") + "&top_k=10")
n_kw2 = len(j2.get("hits") or [])
check("web keyword search", s == 200 and n_kw >= 1 and n_kw2 >= 1,
      f"hits(MinerU)={n_kw} hits(AgentWorkShop)={n_kw2}")

# 6. negative: gibberish query -> honest empty (no inflated scores)
s, j = call_json("POST", BE + "/api/v1/search/vector",
                 {"query": "zzzqqx 混沌模糊量子咖啡杯 波粒二象性菠萝包 0xDEADBEEFCAFE", "kb_id": KB, "top_k": 5})
neg_hits = j.get("results") or []
max_score = max([float(h.get("score") or 0) for h in neg_hits], default=0)
check("negative query honest-empty", s == 200 and j.get("success") and (len(neg_hits) == 0 or max_score < 0.5),
      f"hits={len(neg_hits)} max_score={max_score:.3f}")

print()
failed = [n for n, ok, _ in results if not ok]
print("==== P4 retrieval summary: " + str(len(results) - len(failed)) + "/" + str(len(results)) + " passed ====")
sys.exit(1 if failed else 0)
