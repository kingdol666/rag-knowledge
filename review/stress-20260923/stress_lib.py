"""Stress-test shared library for the rag-knowledge platform.

SSRF-hardened: guard_url allows loopback 8771/6789 only. Token from .env,
never printed. Uses httpx (backend venv) with trust_env=False (proxy pitfall).
Usage: import from sibling phase scripts run by backend/.venv/Scripts/python.exe.
"""
import os
import statistics
import threading
import time
import urllib.request
from pathlib import Path

import httpx


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = urllib.request.build_opener(_NoRedirect)

ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
HERE = Path(os.path.dirname(os.path.abspath(__file__)))
BE = "http://127.0.0.1:8771"
WEB = "http://127.0.0.1:6789"
ALLOWED_HOSTS = {"127.0.0.1", "localhost"}
ALLOWED_PORTS = {8771, 6789}


def guard_url(url: str) -> None:
    from urllib.parse import urlparse
    p = urlparse(url)
    if p.scheme != "http" or p.hostname not in ALLOWED_HOSTS:
        raise ValueError("blocked target: " + repr(url))
    if p.port not in ALLOWED_PORTS:
        raise ValueError("blocked target: " + repr(url))


def load_token() -> str:
    for line in ROOT.joinpath(".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("MCP_AUTH_TOKEN="):
            return line.split("=", 1)[1].strip()
    return ""


TOKEN = load_token()
HEADERS = {"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"}


def client(limit: int = 64) -> httpx.Client:
    return httpx.Client(trust_env=False, timeout=httpx.Timeout(60.0),
                        limits=httpx.Limits(max_connections=limit, max_keepalive_connections=limit))


class Rec:
    """Thread-safe latency recorder."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.lat: list[float] = []
        self.codes: dict[int, int] = {}
        self.errs: list[str] = []

    def add(self, dt: float, code: int = 0, err: str = "") -> None:
        with self.lock:
            self.lat.append(dt)
            self.codes[code] = self.codes.get(code, 0) + 1
            if err:
                self.errs.append(err[:120])

    @property
    def n(self) -> int:
        return len(self.lat)

    def summary(self) -> dict:
        with self.lock:
            xs = sorted(self.lat)
            codes = dict(self.codes)
        if not xs:
            return {"n": 0}
        q = lambda p: xs[min(len(xs) - 1, int(len(xs) * p))]  # noqa: E731
        return {
            "n": len(xs), "rps": round(len(xs) / max(sum(xs) / len(xs), 1e-9), 1),
            "p50_ms": round(q(0.50) * 1000, 1), "p90_ms": round(q(0.90) * 1000, 1),
            "p95_ms": round(q(0.95) * 1000, 1), "p99_ms": round(q(0.99) * 1000, 1),
            "max_ms": round(xs[-1] * 1000, 1), "codes": codes,
            "err_rate": round(len(self.errs) / len(xs), 4),
        }


def hammer(rec: Rec, stop: threading.Event, fn) -> None:
    """Worker loop: call fn(client) repeatedly until stop is set."""
    c = client()
    try:
        while not stop.is_set():
            t0 = time.perf_counter()
            try:
                code = fn(c)
                rec.add(time.perf_counter() - t0, code)
            except Exception as e:  # noqa: BLE001
                rec.add(time.perf_counter() - t0, 0, repr(e)[:120])
    finally:
        c.close()


def paced_hammer(rec: Rec, stop: threading.Event, fn, target_rps: float, workers: int) -> None:
    """Worker loop with global pacing: whole pool emits ~target_rps req/s."""
    interval = workers / target_rps
    c = client()
    try:
        while not stop.is_set():
            t0 = time.perf_counter()
            try:
                code = fn(c)
                rec.add(time.perf_counter() - t0, code)
            except Exception as e:  # noqa: BLE001
                rec.add(time.perf_counter() - t0, 0, repr(e)[:120])
            dt = time.perf_counter() - t0
            if dt < interval:
                time.sleep(interval - dt)
    finally:
        c.close()


def run_paced(fns: list, duration_s: float, workers: int, target_rps: float) -> Rec:
    rec = Rec()
    stop = threading.Event()
    threads = []
    for i in range(workers):
        fn = fns[i % len(fns)]
        t = threading.Thread(target=paced_hammer, args=(rec, stop, fn, target_rps, workers), daemon=True)
        t.start()
        threads.append(t)
    time.sleep(duration_s)
    stop.set()
    for t in threads:
        t.join(timeout=15)
    return rec


def run_load(fns: list, duration_s: float, max_workers: int) -> Rec:
    """Run a mix of request lambdas across workers for duration_s."""
    rec = Rec()
    stop = threading.Event()
    threads = []
    for i in range(max_workers):
        fn = fns[i % len(fns)]
        t = threading.Thread(target=hammer, args=(rec, stop, fn), daemon=True)
        t.start()
        threads.append(t)
    time.sleep(duration_s)
    stop.set()
    for t in threads:
        t.join(timeout=15)
    return rec


def fmt(name: str, s: dict) -> str:
    if s.get("n", 0) == 0:
        return f"[----] {name}: no samples"
    return (f"[STAT] {name}: n={s['n']} codes={s['codes']} p50={s['p50_ms']}ms "
            f"p95={s['p95_ms']}ms p99={s['p99_ms']}ms max={s['max_ms']}ms err={s['err_rate']}")


RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(cond), detail))
    print(("[PASS] " if cond else "[FAIL] ") + name + ("  -- " + detail if detail else ""), flush=True)


def report(phase: str) -> int:
    failed = [n for n, ok, _ in RESULTS if not ok]
    print()
    print(f"==== {phase}: {len(RESULTS) - len(failed)}/{len(RESULTS)} passed ====")
    return 1 if failed else 0


def pid_on_port(port: int) -> int:
    import subprocess
    out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True,
                         encoding="gbk", errors="replace").stdout
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[0] == "TCP" and parts[3] == "LISTENING" and parts[1].endswith(":" + str(port)):
            return int(parts[4])
    return 0


def proc_stats(pid: int) -> dict:
    """RSS (MB) + total CPU seconds via PowerShell (sampled)."""
    import subprocess
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"$p=Get-Process -Id {pid} -ErrorAction SilentlyContinue; "
         "if($p){ '{0:.1f} {1:.2f}'.format($p.WorkingSet64/1MB, $p.TotalProcessorTime.TotalSeconds) } else { 'gone' }"],
        capture_output=True, text=True, encoding="gbk", errors="replace").stdout.strip()
    if out and out != "gone":
        rss, cpu = out.split()
        return {"rss_mb": float(rss), "cpu_s": float(cpu)}
    return {"rss_mb": 0.0, "cpu_s": 0.0, "gone": True}


def summary_line(rec: Rec) -> str:
    s = rec.summary()
    return fmt("mixed", s)
