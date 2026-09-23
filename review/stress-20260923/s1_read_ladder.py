"""S1 — concurrent READ ladder: 5/15/30 workers at 3/6/9 RPS, mixed endpoints.

Endpoints mixed by weight: health, catalog, search/stats, vector search (25%),
two-stage (20%), graph stats, soul list, experience list, web kb search.
Usage: backend/.venv/Scripts/python.exe review/stress-20260923/s1_read_ladder.py
"""
import json
import sys
import time

sys.path.insert(0, "review/stress-20260923")
from stress_lib import BE, WEB, HEADERS, check, fmt, report, run_paced  # noqa: E402

state = json.loads(__import__("pathlib").Path("review/stress-20260923/stress_state.json").read_text(encoding="utf-8"))


def mk(method, url, body=None):
    def fn(c):
        r = c.request(method, url, json=body, headers=HEADERS, timeout=30.0)
        return r.status_code
    return fn


def web_fn(c):
    r = c.get(WEB + "/api/kb/search?query=MinerU&top_k=10", headers=HEADERS, timeout=30.0)
    return r.status_code


fns = [
    (mk("GET", BE + "/api/v1/health"), 0.05),
    (mk("GET", WEB + "/api/kb/catalog"), 0.10),
    (mk("GET", BE + "/api/v1/search/stats"), 0.10),
    (mk("POST", BE + "/api/v1/search/vector", {"query": "MinerU OCR PDF parse pipeline", "kb_id": "", "top_k": 5}), 0.25),
    (mk("POST", BE + "/api/v1/search/two-stage", {"query": "platform architecture three services", "kb_id": "", "stage1_top_k": 20, "stage2_top_k": 5}), 0.20),
    (mk("GET", BE + "/api/v1/graph/stats"), 0.10),
    (mk("GET", BE + "/api/v1/soul/list"), 0.05),
    (mk("GET", BE + "/api/v1/experience/aw-industrial"), 0.10),
    (web_fn, 0.05),
]
# expand weights into a round-robin pool of ~40 slots
pool = []
for fn, w in fns:
    pool.extend([fn] * max(1, int(w * 40)))

ladder = [(5, 3.0), (15, 6.0), (30, 9.0)]
all_ok = True
for workers, rps in ladder:
    print(f"\n[i] ladder step: workers={workers} target={rps} RPS for 30s ...", flush=True)
    rec = run_paced(pool, 30.0, workers, rps)
    s = rec.summary()
    print(fmt(f"read-ladder w={workers} @{rps}rps", s), flush=True)
    ok = s["n"] >= 20 and s["err_rate"] < 0.02 and s["codes"].get(200, 0) / max(s["n"], 1) > 0.95
    all_ok = all_ok and ok
    time.sleep(3)

check("S1 read ladder clean (no errors, >95% 200)", all_ok,
      "see per-step STAT lines above")
sys.exit(report("S1 read-ladder"))
