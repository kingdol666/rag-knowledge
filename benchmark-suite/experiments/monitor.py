"""System resource monitor (optional; degrades gracefully).

Samples the process tree's CPU / RSS (and GPU memory when pynvml is present)
around one run, in a background thread. If `psutil` is not installed the monitor
reports `available: false` instead of failing — the platform's own metrics
(latency / tokens / cost / tool calls) are always recorded regardless.

Install once to enable system metrics:
    pip install psutil            # CPU + RSS
    pip install nvidia-ml-py      # + GPU memory
"""
from __future__ import annotations

import os
import threading
import time


class SystemMonitor:
    def __init__(self, interval: float = 0.4):
        self.interval = interval
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._samples: list[dict] = []
        self._psutil = None
        self._nvml = None
        try:
            import psutil  # type: ignore
            self._psutil = psutil
        except Exception:  # noqa: BLE001
            pass
        try:
            import pynvml  # type: ignore
            pynvml.nvmlInit()
            self._nvml = pynvml
        except Exception:  # noqa: BLE001
            pass

    @property
    def available(self) -> bool:
        return self._psutil is not None or self._nvml is not None

    def _tree(self):
        ps = self._psutil
        try:
            procs = [ps.Process(os.getpid())]
            procs += procs[0].children(recursive=True)
            return procs
        except Exception:  # noqa: BLE001
            return []

    def _sample(self) -> dict:
        s: dict = {}
        if self._psutil is not None:
            cpu = 0.0
            rss = 0
            for p in self._tree():
                try:
                    cpu += p.cpu_percent(interval=None)
                    rss += p.memory_info().rss
                except Exception:  # noqa: BLE001
                    continue
            s["cpu_pct"] = round(cpu, 1)
            s["rss_mb"] = round(rss / 1024 / 1024, 1)
        if self._nvml is not None:
            try:
                used = []
                for i in range(self._nvml.nvmlDeviceGetCount()):
                    h = self._nvml.nvmlDeviceGetHandleByIndex(i)
                    used.append(self._nvml.nvmlDeviceGetMemoryInfo(h).used)
                s["gpu_mem_mb"] = round(sum(used) / 1024 / 1024, 1)
            except Exception:  # noqa: BLE001
                pass
        return s

    def _loop(self) -> None:
        # prime cpu_percent so the first real sample is meaningful
        for p in self._tree():
            try:
                p.cpu_percent(interval=None)
            except Exception:  # noqa: BLE001
                pass
        while not self._stop.wait(self.interval):
            s = self._sample()
            if s:
                self._samples.append(s)

    def start(self) -> None:
        self._samples = []
        self._stop.clear()
        if not self.available:
            return
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> dict:
        t_end = time.perf_counter()
        if self._thread:
            self._stop.set()
            self._thread.join(timeout=2)
            self._thread = None
        if not self.available:
            return {"available": False,
                    "note": "psutil not installed (pip install psutil)"}
        out: dict = {"available": True, "n_samples": len(self._samples)}
        for key, agg in (("cpu_pct", "max"), ("rss_mb", "max"), ("gpu_mem_mb", "max")):
            vals = [s[key] for s in self._samples if key in s]
            if vals:
                out[f"{key}_peak"] = max(vals)
                out[f"{key}_avg"] = round(sum(vals) / len(vals), 1)
        if not self._samples:
            out["note"] = "no samples captured (run too short for the interval)"
        _ = t_end
        return out
