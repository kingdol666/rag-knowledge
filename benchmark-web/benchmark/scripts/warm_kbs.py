"""Warm every KB-* topic KB (BM25 keyword index cold-build happens on first
two-stage query per KB and can take minutes — must precede timed evals).

Usage: python scripts/warm_kbs.py   (token from RAG_BENCH_TOKEN or .env)
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent.parent.parent
BASE = os.environ.get("RAG_BENCH_URL", "http://127.0.0.1:8771").rstrip("/")
WEB = os.environ.get("RAG_BENCH_WEB_URL", "http://127.0.0.1:6790").rstrip("/")
LOCAL = {"localhost", "127.0.0.1", "::1"}


def assert_local_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Blocked scheme: {parsed.scheme}")
    if (parsed.hostname or "").lower() not in LOCAL:
        raise ValueError(f"Blocked non-local host: {parsed.hostname}")
    return url


def token() -> str:
    tok = os.environ.get("RAG_BENCH_TOKEN", "")
    if tok:
        return tok
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("MCP_AUTH_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"')
    return ""


def call(method: str, url: str, body: dict | None = None, timeout: int = 1800):
    assert_local_url(url)
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {token()}")
    data = None
    if body is not None:
        req.add_header("Content-Type", "application/json")
        data = json.dumps(body).encode("utf-8")
    with urllib.request.urlopen(req, data=data, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    if not token():
        print("no token")
        return 2
    cat = call("GET", f"{WEB}/api/kb/catalog", timeout=60)
    kbs = [(k.get("kbId") or k.get("id"), k.get("name"))
           for k in cat.get("knowledgeBases", [])
           if str(k.get("name", "")).startswith("KB-")]
    print(f"{len(kbs)} KB-* KBs, warming BM25 (first query per KB builds the index)...")
    failed = []
    for kb_id, name in kbs:
        t0 = time.time()
        try:
            call("POST", f"{BASE}/api/v1/search/two-stage",
                 {"query": "history", "kb_id": kb_id,
                  "stage1_top_k": 5, "stage2_top_k": 3}, timeout=1800)
            print(f"  {name}: warm in {time.time() - t0:.0f}s", flush=True)
        except Exception as e:
            print(f"  {name}: WARM FAIL {e}", flush=True)
            failed.append(name)
    if failed:
        print("failed:", failed)
        return 1
    print("all warm")
    return 0


if __name__ == "__main__":
    sys.exit(main())
