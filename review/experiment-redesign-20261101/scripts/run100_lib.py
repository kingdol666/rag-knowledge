# -*- coding: utf-8 -*-
"""Shared helpers for the 2026-11-14 100-paper re-ingest + tiered retrieval rerun.

Transport mirrors scripts/mcp_call.py (SSE JSON-RPC to resident kb-mcp :8000).
All paths are absolute and correct for the current checkout.
"""
from __future__ import annotations

import http.client
import json
import queue
import threading
import urllib.request
from pathlib import Path

REPO = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge")
OUTDIR = REPO / "review" / "_exp_rerun_20261114"
OUTDIR.mkdir(parents=True, exist_ok=True)
PDF_DIR = REPO / "benchmark-suite" / "data" / "papers"
STATE = REPO / "paper-kbs" / "experiments" / "results" / "exp10_ingest_state.json"

LIBS = {
    "计算机与人工智能": "b1199132-e4d4-4305-8c2e-82dc1753b0ba",
    "自然科学与地球科学": "1e6199ea-f380-44e2-94fc-d431f0f9bb6b",
    "生命科学与医学": "b28f0a25-1e1d-40ad-96b8-61bd2b093a28",
    "工程与能源": "8fa4db59-adde-4d6d-9fdb-2c375400e631",
    "经济与社会": "f5770687-6b05-4a8d-8645-af31686ca87e",
}


class Mcp:
    """Persistent SSE JSON-RPC client for kb-mcp at 127.0.0.1:8000."""

    def __init__(self, host="127.0.0.1", port=8000, timeout=660.0):
        self.host, self.port, self.timeout = host, port, timeout
        self._q: "queue.Queue[str]" = queue.Queue()
        self._t = threading.Thread(target=self._reader, daemon=True)
        self._t.start()
        self._ep = None
        deadline = time.time() + 30
        while self._ep is None and time.time() < deadline:
            time.sleep(0.2)
        if self._ep is None:
            raise RuntimeError("SSE endpoint not ready")

    def _reader(self):  # noqa: ANN202
        conn = http.client.HTTPConnection(self.host, self.port, timeout=600)
        conn.request("GET", "/sse", headers={"Accept": "text/event-stream"})
        resp = conn.getresponse()
        event, data = None, []
        while True:
            line = resp.fp.readline()
            if not line:
                break
            s = line.decode("utf-8", "replace").rstrip("\r\n")
            if s == "":
                if event == "endpoint" and data:
                    self._ep = data[0]
                elif event == "message" and data:
                    self._q.put("\n".join(data))
                event, data = None, []
            elif s.startswith("event:"):
                event = s[6:].strip()
            elif s.startswith("data:"):
                data.append(s[5:].strip())

    def call(self, tool: str, args: dict, timeout: float | None = None):
        import uuid

        rid = str(uuid.uuid4())
        body = json.dumps({
            "jsonrpc": "2.0", "id": rid, "method": "tools/call",
            "params": {"name": tool, "arguments": args},
        }, ensure_ascii=False).encode("utf-8")
        parsed = urllib.parse.urlsplit(self._ep)
        conn = http.client.HTTPConnection(self.host, self.port,
                                          timeout=timeout or self.timeout)
        conn.request("POST", parsed.path + ("?" + parsed.query if parsed.query else ""),
                     body=body,
                     headers={"Content-Type": "application/json"})
        conn.getresponse().read()
        deadline = time.time() + (timeout or self.timeout)
        while time.time() < deadline:
            try:
                raw = self._q.get(timeout=1.0)
            except queue.Empty:
                continue
            try:
                msg = json.loads(raw)
            except Exception:
                continue
            if str(msg.get("id")) == rid:
                content = msg.get("result", {}).get("content") or []
                text = "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
                try:
                    return json.loads(text, strict=False)
                except Exception:
                    return {"_raw": text}
        raise TimeoutError(f"MCP call timed out: {tool}")


import time  # noqa: E402
import urllib.parse  # noqa: E402


def get_token() -> str:
    cand = REPO / "storage" / "loop-auth.json"
    if cand.exists():
        try:
            tok = json.loads(cand.read_text(encoding="utf-8")).get("token", "")
            if tok:
                return tok
        except Exception:
            pass
    for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("MCP_AUTH_TOKEN="):
            return line.split("=", 1)[1].strip()
    return ""
