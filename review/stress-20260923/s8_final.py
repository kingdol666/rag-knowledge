"""S8 — final: resource delta + post-stress functional sanity + cleanup cascade.

Usage: backend/.venv/Scripts/python.exe review/stress-20260923/s8_final.py
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, "review/stress-20260923")
from stress_lib import (BE, WEB, HERE, HEADERS, check, client, proc_stats,
                        pid_on_port, report)  # noqa: E402

state = json.loads(HERE.joinpath("stress_state.json").read_text(encoding="utf-8"))
KB = state["kb_uuid"]
KB_NAME = state["kb_name"]

# ---- 1. resource delta ----
be_pid = pid_on_port(8771)
web_pid = pid_on_port(6789)
be_now = proc_stats(be_pid)
web_now = proc_stats(web_pid)
be_t0 = state.get("be_stats_t0") or {}
web_t0 = state.get("web_stats_t0") or {}
be_cpu_delta = be_now.get("cpu_s", 0) - be_t0.get("cpu_s", 0)
web_cpu_delta = web_now.get("cpu_s", 0) - web_t0.get("cpu_s", 0)
print(f"[i] backend pid={be_pid} rss {be_t0.get('rss_mb','?')}->{be_now.get('rss_mb','?')}MB "
      f"cpu +{be_cpu_delta:.0f}s", flush=True)
print(f"[i] web     pid={web_pid} rss {web_t0.get('rss_mb','?')}->{web_now.get('rss_mb','?')}MB "
      f"cpu +{web_cpu_delta:.0f}s", flush=True)
check("backend alive (not gone)", "gone" not in be_now, str(be_now))
check("web alive (not gone)", "gone" not in web_now, str(web_now))
check("backend RSS < 4GB (no runaway)", 0 < be_now.get("rss_mb", 9e9) < 4096,
      f"rss={be_now.get('rss_mb')}MB")

# ---- 2. post-stress functional sanity ----
with client() as c:
    r = c.get(BE + "/api/v1/health", timeout=15)
    check("sanity: backend healthy", r.status_code == 200 and r.json()["vector"]["ready"], r.text[:100])
    r = c.post(BE + "/api/v1/search/vector",
               json={"query": "STRESSMARK-persona-06", "kb_id": KB, "top_k": 3},
               headers=HEADERS, timeout=60)
    body = json.dumps(r.json(), ensure_ascii=False)
    check("sanity: stress KB still searchable", "persona-06" in body, body[:120])
    r = c.post(BE + "/api/v1/search/two-stage",
               json={"query": "retrieval embedding chunking", "kb_id": "", "stage1_top_k": 20, "stage2_top_k": 5},
               headers=HEADERS, timeout=60)
    check("sanity: two-stage global works", r.status_code == 200, f"code={r.status_code}")
    r = c.get(WEB + "/api/health/stats", headers=HEADERS, timeout=60)
    st = r.json()
    check("sanity: web stats healthy", st.get("status") == "healthy",
          f"kbs={st['storage']['kb_count']} docs={st['storage']['doc_count']} nodes={st['graph']['node_count']}")
    r = c.get(WEB + "/api/kb/agent/meta", headers=HEADERS, timeout=30)
    check("sanity: agent meta responds", r.status_code == 200, f"code={r.status_code}")

# ---- 3. cleanup stress KB with cascade verification ----
with client() as c:
    r = c.get(WEB + "/api/health/stats", headers=HEADERS, timeout=60)
    before = r.json()
    r = c.request("DELETE", WEB + "/api/kb/delete", json={"kbId": KB}, headers=HEADERS, timeout=120)
    check("cleanup: delete stress KB", r.status_code == 200 and r.json().get("success"),
          r.text[:120])
    time.sleep(10)
    r = c.get(WEB + "/api/health/stats", headers=HEADERS, timeout=60)
    after = r.json()
    d_kbs = after["storage"]["kb_count"] - before["storage"]["kb_count"]
    d_docs = after["storage"]["doc_count"] - before["storage"]["doc_count"]
    d_nodes = after["graph"]["node_count"] - before["graph"]["node_count"]
    check("cleanup cascade: counts dropped", d_kbs == -1 and d_docs <= -21,
          f"d_kbs={d_kbs} d_docs={d_docs} d_nodes={d_nodes} coverage={after['vector']['coverage_pct']}%")
    p = Path(__import__("os").path.join(str(HERE.parent.parent), "storage", "tree-file-system", KB_NAME))
    check("cleanup cascade: disk removed", not p.exists(), str(p))

print()
sys.exit(report("S8 final"))
