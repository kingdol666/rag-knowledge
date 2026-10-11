# -*- coding: utf-8 -*-
"""laya-worker — 常驻判卷服务（plan 阶段 2）。

动机：kb-mcp 每次判卷 spawn 一个 GPU torch 子进程，模型加载占 10-12s/批，
且跨进程文件锁强制全局串行。本 worker 用 backend/.venv（MinerU 环境，含
laya SDK + torch）常驻进程加载模型一次，HTTP 队列串行消费——单批判卷
10-12s → 1-2s，文件锁的防显存耗尽语义由"单实例端口绑定 + 队列串行"接管。

运行（必须用 backend/.venv，kb-mcp 的 venv 没有 torch/laya）：
  backend/.venv/Scripts/python.exe kb-mcp/laya_worker.py [--port 8791]

端点：
  GET  /health → {"status","model_loaded","queue","port"}
  POST /judge  → body = 判卷 manifest（与 complete_recall --input 同构）
              → verdict JSON（与 complete_recall --output 同构，fail-closed）

单实例保证：端口绑定即锁——第二个实例绑定失败直接退出。
空闲退出：LAYA_WORKER_IDLE_EXIT=秒（默认 0=常驻），由调用方负责拉起。
"""
from __future__ import annotations

import argparse
import json
import queue
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LIBRARIAN_SCRIPTS = REPO / ".claude" / "skills" / "knowledgebase-librarian" / "scripts"
if str(LIBRARIAN_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(LIBRARIAN_SCRIPTS))

import complete_recall  # noqa: E402  (backend/.venv 内运行)

_WORK_Q: "queue.Queue[tuple[dict, queue.Queue]]" = queue.Queue()
_STATE = {"model_loaded": False, "last_error": "", "served": 0}
_CACHE: dict = {}          # 判卷结果持久缓存（plan 阶段 4）：单例进程 = 单例缓存
_CACHE_MAX = 512
_CACHE_HIT = {"n": 0}


def _cache_key(manifest: dict) -> str:
    import hashlib
    h = hashlib.sha256()
    h.update(str(manifest.get("query", "")).encode("utf-8"))
    h.update(str(manifest.get("criterion", "")).encode("utf-8"))
    h.update(str(manifest.get("threshold", "")).encode("utf-8"))
    for d in sorted(manifest.get("documents") or [],
                    key=lambda x: str(x.get("doc_path") or "")):
        h.update(str(d.get("kb_id", "")).encode("utf-8"))
        h.update(str(d.get("doc_path", "")).encode("utf-8"))
        h.update(str(len(d.get("content") or "")).encode("utf-8"))
    return h.hexdigest()[:32]


def _worker_loop() -> None:
    """串行消费判卷请求；首个请求触发模型加载（其后进程内缓存生效）。"""
    while True:
        manifest, out_q = _WORK_Q.get()
        try:
            ck = _cache_key(manifest)
            if ck in _CACHE:
                _CACHE_HIT["n"] += 1
                _CACHE[ck] = _CACHE.pop(ck)  # LRU touch
                out_q.put(("ok", _CACHE[ck]))
                continue
            verdict = complete_recall.run_manifest(manifest)
            if isinstance(verdict, dict) and verdict.get("jev"):
                _STATE["model_loaded"] = True
            if isinstance(verdict, dict) and (verdict.get("jev") or {}).get("status") == "ok":
                _CACHE[ck] = verdict
                if len(_CACHE) > _CACHE_MAX:
                    _CACHE.pop(next(iter(_CACHE)))
            _STATE["served"] += 1
            out_q.put(("ok", verdict))
        except Exception as exc:  # noqa: BLE001 — fail-closed，绝不隐式通过
            _STATE["last_error"] = str(exc)[:200]
            out_q.put(("error", {"status": "error", "real_engine": False,
                                 "survivors": [], "evidence_pack": "",
                                 "errors": [{"error": f"worker: {_STATE['last_error']}"}]}))
        finally:
            _WORK_Q.task_done()


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # noqa: N802 — 安静
        pass

    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        if self.path == "/health":
            self._send(200, {"status": "ok", "model_loaded": _STATE["model_loaded"],
                             "queue": _WORK_Q.qsize(), "served": _STATE["served"],
                             "cache": len(_CACHE), "cache_hits": _CACHE_HIT["n"],
                             "last_error": _STATE["last_error"]})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        if self.path != "/judge":
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            manifest = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            self._send(400, {"status": "error", "real_engine": False,
                             "errors": [{"error": f"bad manifest: {exc}"}]})
            return
        out_q: "queue.Queue" = queue.Queue()
        _WORK_Q.put((manifest, out_q))
        try:
            kind, verdict = out_q.get(timeout=600)
        except queue.Empty:
            self._send(504, {"status": "error", "real_engine": False,
                             "errors": [{"error": "worker_timeout_600s"}]})
            return
        self._send(200 if kind == "ok" else 500, verdict)


def _warmup() -> None:
    """启动即加载模型：一次小打分请求，把 ~10s 的首载成本移出第一批判卷。"""
    manifest = {
        "query": "warmup", "engine": "laya", "criterion": "evidence",
        "threshold": 0.5, "max_segment_chars": 1200, "max_evidence_chars": 2000,
        "documents": [{"kb_id": "warmup", "doc_path": "warmup.md",
                       "content": "warmup 预热文本。"}],
    }
    out_q: "queue.Queue" = queue.Queue()
    _WORK_Q.put((manifest, out_q))
    t0 = time.time()
    try:
        kind, verdict = out_q.get(timeout=300)
        print(f"[laya-worker] warmup {kind} in {time.time()-t0:.1f}s "
              f"(model_loaded={_STATE['model_loaded']})", flush=True)
    except queue.Empty:
        print("[laya-worker] warmup timeout", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int,
                    default=int(__import__("os").environ.get("LAYA_WORKER_PORT", "8791")))
    args = ap.parse_args()

    threading.Thread(target=_worker_loop, daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), _Handler)
    print(f"[laya-worker] listening on 127.0.0.1:{args.port} "
          f"(complete_recall from {LIBRARIAN_SCRIPTS})", flush=True)
    threading.Thread(target=_warmup, daemon=True).start()
    try:
        server.serve_forever()
    except OSError:
        print("[laya-worker] port bind failed — another instance owns it", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
