#!/usr/bin/env python3
"""chat API stream/non-stream retrieval test client (2026-09-28).

Security posture: target is the literal loopback dev endpoint, host and port
fixed as string/number literals below (no host input, no redirects possible —
http.client never follows them). Same posture as scripts/mcp_call.py.

Usage:
  python test_chat_api.py nonstream   # stream:false — final JSON only + timing
  python test_chat_api.py stream      # stream:true  — SSE timeline + final answer
"""
import json
import sys
import time
import http.client
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
AI_INFRA_KB = "5bc21b9b-2a05-470a-9cd6-eaafedfb87a2"  # AI 基础设施
QUESTION = "向量检索召回率劣化的排查思路是什么？什么条件下应该触发索引全量重建？"


def token() -> str:
    for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("MCP_AUTH_TOKEN="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("MCP_AUTH_TOKEN not in .env")


def body(stream, all_kb: bool = False) -> dict:
    """stream=None → omit the field entirely (tests the API default)."""
    b = {
        "prompt": QUESTION,
        "kbEnhanced": True,
        "kbIds": [] if all_kb else [AI_INFRA_KB],
        "engine": "claude",
        "permissionMode": "default",
        "timeout_ms": 480000,
    }
    if stream is not None:
        b["stream"] = stream
    return b


def post(payload: dict, timeout: float = 360.0):
    # host/port are the literals "127.0.0.1" / 6789 — fixed loopback target
    conn = http.client.HTTPConnection("127.0.0.1", 6789, timeout=timeout)
    conn.request("POST", "/api/claude/chat", body=json.dumps(payload),
                 headers={"Content-Type": "application/json",
                          "Authorization": f"Bearer {token()}"})
    return conn


def run_nonstream(all_kb: bool = False, stream=None) -> None:
    t0 = time.time()
    resp = post(body(stream, all_kb)).getresponse()
    raw = resp.read().decode("utf-8")
    wall = time.time() - t0
    print(f"HTTP {resp.status} · client wall {wall:.1f}s")
    try:
        print(json.dumps(json.loads(raw), ensure_ascii=False, indent=1)[:6000])
    except json.JSONDecodeError:
        print(raw[:2000])


def run_stream() -> None:
    t0 = time.time()
    resp = post(body(True)).getresponse()
    print(f"HTTP {resp.status} · headers at {time.time()-t0:.2f}s")
    events, first_at, done_msg, done_at = {}, None, None, None
    event = None
    for raw in resp:
        line = raw.decode("utf-8", "replace").rstrip("\r\n")
        if line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            at = time.time() - t0
            if first_at is None and event == "data":
                first_at = at
            events[event] = events.get(event, 0) + 1
            if event == "done":
                done_msg = json.loads(line[5:].strip())
                done_at = at
                break
    wall = time.time() - t0
    fs = f"{first_at:.1f}" if first_at is not None else "-"
    ds = f"{done_at:.1f}" if done_at is not None else "-"
    print(f"SSE events {events} · first data {fs}s · done {ds}s · total {wall:.1f}s")
    if done_msg:
        ans = done_msg.get("result") or ""
        print(f"--- final answer (done.result, {len(ans)} chars) ---")
        print(ans[:3500])
        print(f"--- meta: duration_ms={done_msg.get('duration_ms')} num_turns={done_msg.get('num_turns')} cost=${done_msg.get('total_cost_usd')} model={done_msg.get('model')} ---")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "default"
    all_kb = len(sys.argv) > 2 and sys.argv[2] == "all"
    if mode == "nonstream":          # explicit stream:false
        run_nonstream(all_kb, stream=False)
    elif mode == "default":          # stream field OMITTED — API default
        run_nonstream(all_kb, stream=None)
    else:                            # stream — explicit stream:true SSE
        run_stream()
