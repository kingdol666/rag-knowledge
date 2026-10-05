"""S0 — preflight + single-thread latency baseline (10 endpoints x 15 rounds).

Usage: backend/.venv/Scripts/python.exe review/stress-20260923/s0_baseline.py
"""
import json
import sys
import time

sys.path.insert(0, "review/stress-20260923")
from stress_lib import BE, WEB, RESULTS, check, client, proc_stats, pid_on_port, report  # noqa: E402

import httpx  # noqa: E402

STAMP = time.strftime("%m%d-%H%M%S")
KB_NAME = "stress-" + STAMP
state = {"kb_name": KB_NAME, "stamp": STAMP}

# preflight
with client() as c:
    r = c.get(BE + "/api/v1/health")
    j = r.json()
    check("backend healthy + vector ready", r.status_code == 200 and j["vector"]["ready"], json.dumps(j))
    r = c.get(BE + "/api/v1/graph/health", headers={"Authorization": "Bearer " + __import__("stress_lib").TOKEN})
    check("graph available", r.status_code == 200 and r.json()["health"]["available"], r.text[:120])
    r = c.get(WEB + "/api/health/stats", headers={"Authorization": "Bearer " + __import__("stress_lib").TOKEN})
    st = r.json()
    check("web stats reachable", r.status_code == 200 and st.get("status") == "healthy",
          f"kbs={st['storage']['kb_count']} docs={st['storage']['doc_count']} nodes={st['graph']['node_count']}")
    state["base_kbs"] = st["storage"]["kb_count"]
    state["base_docs"] = st["storage"]["doc_count"]
    state["base_nodes"] = st["graph"]["node_count"]

be_pid = pid_on_port(8771)
web_pid = pid_on_port(6789)
state["be_pid"], state["web_pid"] = be_pid, web_pid
state["be_stats_t0"] = proc_stats(be_pid)
state["web_stats_t0"] = proc_stats(web_pid)
print(f"[i] backend pid={be_pid} rss={state['be_stats_t0']['rss_mb']}MB cpu={state['be_stats_t0']['cpu_s']}s", flush=True)
print(f"[i] web     pid={web_pid} rss={state['web_stats_t0']['rss_mb']}MB cpu={state['web_stats_t0']['cpu_s']}s", flush=True)

# latency baseline: 10 endpoints x 15 rounds sequential
TOKEN = __import__("stress_lib").TOKEN
H = {"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"}
endpoints = [
    ("BE health", "GET", BE + "/api/v1/health", None),
    ("BE catalog", "GET", WEB + "/api/kb/catalog", None),
    ("BE search/stats", "GET", BE + "/api/v1/search/stats", None),
    ("BE vector search", "POST", BE + "/api/v1/search/vector", {"query": "MinerU OCR PDF parse", "kb_id": "", "top_k": 5}),
    ("BE two-stage", "POST", BE + "/api/v1/search/two-stage", {"query": "platform architecture services", "kb_id": "", "stage1_top_k": 20, "stage2_top_k": 5}),
    ("BE graph stats", "GET", BE + "/api/v1/graph/stats", None),
    ("BE experience list", "GET", BE + "/api/v1/experience/" + "aw-industrial", None),
    ("BE soul list", "GET", BE + "/api/v1/soul/list", None),
    ("BE meditation status", "GET", BE + "/api/v1/meditation/status", None),
    ("WEB kb search", "GET", WEB + "/api/kb/search?query=MinerU&top_k=10", None),
]
with client() as c:
    for name, method, url, body in endpoints:
        lat = []
        for _ in range(15):
            t0 = time.perf_counter()
            try:
                r = c.request(method, url, json=body, headers=H, timeout=30.0)
                dt = time.perf_counter() - t0
                lat.append(dt)
                code = r.status_code
            except Exception as e:  # noqa: BLE001
                dt = time.perf_counter() - t0
                lat.append(dt)
                code = 0
                check(f"baseline {name}", False, repr(e)[:100])
                break
        xs = sorted(lat)
        med = xs[len(xs) // 2] * 1000
        p95 = xs[int(len(xs) * 0.95) - 1] * 1000
        print(f"[BASE] {name:22s} median={med:7.1f}ms  p95={p95:7.1f}ms  code={code}", flush=True)

from pathlib import Path  # noqa: E402
Path("review/stress-20260923/stress_state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
sys.exit(report("S0 baseline"))
