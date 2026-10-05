#!/usr/bin/env python3
"""Chat-API driver for the three-mode retrieval test (2026-09-26).

POSTs retrieval prompts to the web chat API (OMP engine), consumes the SSE
stream (which now closes on `event: done` after the D4 fix), extracts the
final result text, and saves transcript + answer per run.

SSRF-hardened: every URL passes guard_url() — http scheme, loopback host
allowlist, fixed port allowlist, and a DNS-rebinding check — mirroring
scripts/dev_smoke.py.
"""
from __future__ import annotations

import ipaddress
import json
import os
import socket
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
from dev_smoke import load_token  # noqa: E402

WEB = "http://127.0.0.1:6789"
ALLOWED_HOSTS = {"127.0.0.1", "localhost"}
ALLOWED_PORTS = {6789}
OUT = Path(__file__).resolve().parent


def guard_url(url: str) -> None:
    """SSRF guard: this driver may only talk to the local web dev server."""
    p = urlparse(url)
    if p.scheme != "http" or p.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"blocked target (scheme/host): {url!r}")
    if p.port not in ALLOWED_PORTS:
        raise ValueError(f"blocked target (port): {url!r}")
    ip = socket.gethostbyname(p.hostname)
    if ipaddress.ip_address(ip) != ipaddress.ip_address("127.0.0.1"):
        raise ValueError(f"DNS rebinding blocked: {url!r} -> {ip}")


def _extract_text(obj: dict) -> str:
    if isinstance(obj.get("result"), str) and obj["result"].strip():
        return obj["result"]
    content = obj.get("content") or (obj.get("message") or {}).get("content")
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content
                         if isinstance(b, dict) and b.get("type") == "text")
    if isinstance(content, str):
        return content
    return ""


def run_chat(prompt: str, tag: str, *, engine: str = "omp",
             permission_mode: str = "bypassPermissions",
             timeout_ms: int = 900_000, max_turns: int = 60,
             read_timeout: int = 300) -> dict:
    guard_url(WEB + "/api/claude/chat")
    payload = {"prompt": prompt, "cwd": str(REPO), "engine": engine,
               "permissionMode": permission_mode, "maxTurns": max_turns,
               "timeout_ms": timeout_ms}
    req = urllib.request.Request(
        WEB + "/api/claude/chat", method="POST",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": "Bearer " + load_token(),
                 "Content-Type": "application/json"})
    t0 = time.time()
    data_lines: list[str] = []
    hard_deadline = timeout_ms / 1000 + 120
    with urllib.request.urlopen(req, timeout=read_timeout) as r:
        for raw in r:
            line = raw.decode("utf-8", "replace").strip()
            if line.startswith("data:"):
                data_lines.append(line[5:].strip())
            if time.time() - t0 > hard_deadline:
                break
    seconds = round(time.time() - t0, 1)
    result_text = ""
    for dl in data_lines:
        try:
            obj = json.loads(dl)
        except Exception:
            continue
        if isinstance(obj, dict) and obj.get("type") == "result":
            result_text = _extract_text(obj) or result_text
    (OUT / f"{tag}.transcript.txt").write_text("\n\n".join(data_lines), encoding="utf-8")
    (OUT / f"{tag}.answer.md").write_text(result_text or "(no result extracted)",
                                          encoding="utf-8")
    status = {"tag": tag, "seconds": seconds, "data_events": len(data_lines),
              "has_result": bool(result_text), "answer_chars": len(result_text)}
    (OUT / f"{tag}.status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=1), encoding="utf-8")
    print("RUN_DONE " + json.dumps(status, ensure_ascii=False), flush=True)
    return status


if __name__ == "__main__":
    tag = sys.argv[1]
    prompt = sys.argv[2]
    mt = int(sys.argv[3]) if len(sys.argv) > 3 else 60
    run_chat(prompt, tag, max_turns=mt)
