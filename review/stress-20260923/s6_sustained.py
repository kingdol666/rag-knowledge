"""S6+S7 — 6-minute sustained mixed load (latency drift across 3 windows) +
rate-limit boundary burst (429 semantics + window recovery).

Usage: backend/.venv/Scripts/python.exe review/stress-20260923/s6_sustained.py
"""
import json
import sys
import threading
import time

sys.path.insert(0, "review/stress-20260923")
from stress_lib import BE, WEB, HEADERS, check, fmt, report, run_paced, Rec  # noqa: E402


def mk(method, url, body=None):
    def fn(c):
        r = c.request(method, url, json=body, headers=HEADERS, timeout=45.0)
        return r.status_code
    return fn


def web_fn(c):
    return c.get(WEB + "/api/kb/search?query=MinerU&top_k=10", headers=HEADERS, timeout=45.0).status_code


fns = [
    (mk("POST", BE + "/api/v1/search/vector", {"query": "MinerU OCR PDF parse pipeline", "kb_id": "", "top_k": 5}), 0.25),
    (mk("POST", BE + "/api/v1/search/two-stage", {"query": "platform architecture services", "kb_id": "", "stage1_top_k": 20, "stage2_top_k": 5}), 0.20),
    (mk("GET", WEB + "/api/kb/catalog"), 0.10),
    (mk("GET", BE + "/api/v1/search/stats"), 0.10),
    (mk("GET", BE + "/api/v1/graph/stats"), 0.10),
    (mk("GET", BE + "/api/v1/experience/aw-industrial"), 0.10),
    (mk("GET", BE + "/api/v1/soul/list"), 0.05),
    (web_fn, 0.05),
    (mk("GET", BE + "/api/v1/health"), 0.05),
]
pool = []
for fn, w in fns:
    pool.extend([fn] * max(1, int(w * 40)))

# ---- S6: 3 windows x 2 min at 4 RPS, 8 workers ----
windows = []
for w_i in range(3):
    rec = run_paced(pool, 120.0, 8, 4.0)
    s = rec.summary()
    windows.append(s)
    print(fmt(f"S6 window{w_i+1} (2min @4rps)", s), flush=True)

w1, w3 = windows[0], windows[2]
drift_ok = (w3["n"] >= 300 and w3["err_rate"] < 0.02
            and w3["codes"].get(200, 0) / max(w3["n"], 1) > 0.95)
check("S6 sustained 6min: throughput held + no errors", drift_ok,
      f"win1 n={w1['n']} p50={w1['p50_ms']} p95={w1['p95_ms']} | win3 n={w3['n']} p50={w3['p50_ms']} p95={w3['p95_ms']}")
degradation = (w3["p50_ms"] / max(w1["p50_ms"], 0.1))
check("S6 latency drift p50 win3/win1 < 3x", degradation < 3.0, f"drift={degradation:.2f}x")

# ---- S7: rate-limit burst on a non-exempt light endpoint ----
# /api/v1/health is exempt; use /api/v1/soul/list (reads config, non-exempt).
state = json.loads(__import__("pathlib").Path("review/stress-20260923/stress_state.json").read_text(encoding="utf-8"))
print("\n[i] S7 burst: 50 threads x unlimited on /api/v1/soul/list for 12s ...", flush=True)
rec = Rec()
stop = threading.Event()


def _burst_worker(rec, stop, fn):
    from stress_lib import client
    c = client()
    while not stop.is_set():
        t0 = time.perf_counter()
        try:
            code = fn(c)
            rec.add(time.perf_counter() - t0, code)
        except Exception as e:  # noqa: BLE001
            rec.add(time.perf_counter() - t0, 0, repr(e)[:100])
    c.close()


def burst_fn(c):
    return c.get(BE + "/api/v1/soul/list", headers=HEADERS, timeout=15.0).status_code


threads = []
t_burst0 = time.time()
for _ in range(50):
    t = threading.Thread(target=_burst_worker, args=(rec, stop, burst_fn), daemon=True)
    t.start()
    threads.append(t)

time.sleep(12)
stop.set()
for t in threads:
    t.join(timeout=10)
s = rec.summary()
print(fmt("S7 burst 12s", s), flush=True)
n429 = s["codes"].get(429, 0)
check("S7 burst triggers 429 (limit enforced)", n429 > 0 and s["n"] > 600,
      f"total={s['n']} 429s={n429} 200s={s['codes'].get(200, 0)}")
check("S7 burst RPS far above configured limit (600/60s)", s["n"] / 12 > 30,
      f"effective={s['n']/12:.0f} rps")

# recovery: wait for the 60s window to slide
print("[i] waiting 70s for rate-limit window recovery ...", flush=True)
time.sleep(70)
from stress_lib import client as _client  # noqa: E402
with _client() as c:
    r = c.get(BE + "/api/v1/soul/list", headers=HEADERS, timeout=30)
    check("S7 window recovery -> 200", r.status_code == 200, f"code={r.status_code}")
    r = c.get(BE + "/api/v1/health", timeout=15)
    check("S7 health still fine after burst", r.status_code == 200, f"code={r.status_code}")

sys.exit(report("S6+S7 sustained+ratelimit"))
