"""P8b — retry the three concurrency-affected legs: native-search, SSE done-wait, HITL.

Runs alone (no parallel training) with generous windows.
Usage: python review/e2e-full-stack-20260922/p8b_retry.py
"""
import ipaddress
import json
import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
HERE = Path(os.path.dirname(os.path.abspath(__file__)))
ALLOWED_HOSTS = {"127.0.0.1", "localhost"}
ALLOWED_PORTS = {8771, 6789}


def guard_url(url: str) -> None:
    p = urlparse(url)
    if p.scheme != "http" or p.hostname not in ALLOWED_HOSTS:
        raise ValueError("blocked target: " + repr(url))
    if p.port not in ALLOWED_PORTS:
        raise ValueError("blocked target: " + repr(url))
    ip = socket.gethostbyname(p.hostname)
    if ipaddress.ip_address(ip) != ipaddress.ip_address("127.0.0.1"):
        raise ValueError("DNS rebinding blocked: " + url)


def load_token() -> str:
    for line in ROOT.joinpath(".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("MCP_AUTH_TOKEN="):
            return line.split("=", 1)[1].strip()
    return ""


TOKEN = load_token()
results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("[PASS] " if cond else "[FAIL] ") + name + ("  -- " + detail if detail else ""), flush=True)


def call_json(method, url, body=None, timeout=420):
    guard_url(url)
    req = urllib.request.Request(url, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", "Bearer " + TOKEN)
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data=data, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8", "replace"))
        except Exception:
            return e.code, {}


def sse_chat(body, on_event=None, window_s=560):
    guard_url("http://127.0.0.1:6789/api/claude/chat")
    req = urllib.request.Request("http://127.0.0.1:6789/api/claude/chat", method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "text/event-stream")
    req.add_header("Authorization", "Bearer " + TOKEN)
    events = []
    done = {}
    with urllib.request.urlopen(req, data=json.dumps(body).encode(), timeout=window_s) as resp:
        buf = b""
        start = time.time()
        while time.time() - start < window_s:
            chunk = resp.read1(4096) if hasattr(resp, "read1") else resp.read(1)
            if not chunk:
                break
            buf += chunk
            while b"\n\n" in buf:
                block, buf = buf.split(b"\n\n", 1)
                text = block.decode("utf-8", "replace").strip()
                if not text:
                    continue
                data_lines = [l[5:].strip() for l in text.splitlines() if l.startswith("data:")]
                if not data_lines:
                    continue
                try:
                    payload = json.loads("\n".join(data_lines))
                except ValueError:
                    payload = {"_raw": "\n".join(data_lines)[:200]}
                etype = payload.get("type") or ""
                events.append(payload)
                if on_event:
                    on_event(payload)
                if etype in ("done", "error"):
                    done = payload
                    return events, done
    return events, done


WEB = "http://127.0.0.1:6789"
state = json.loads(HERE.joinpath("p3_state.json").read_text(encoding="utf-8"))
KB = state["kb_uuid"]

# ---- 1. native-search retry (alone, bigger window) ----
t0 = time.time()
s, j = call_json("POST", WEB + "/api/kb/native-search",
                 {"query": "平台支持哪些检索策略？vector two-stage QDCVR", "kb_ids": [KB], "timeout_ms": 420000}, timeout=460)
dur = time.time() - t0
check("native-search QDCVR (retry)", s == 200 and j.get("success") and len(j.get("answer") or "") > 30,
      f"dur={dur:.0f}s tools={len(j.get('tools_used') or [])} answer[:120]=" + (j.get("answer") or "")[:120].replace(chr(10), " "))

# ---- 2. SSE kbEnhanced retry with longer window ----
ev_types = []
sess = {"id": ""}

def on_ev(p):
    etype = p.get("type") or ""
    ev_types.append(etype)
    if etype == "system" and p.get("session_id"):
        sess["id"] = p["session_id"]

t0 = time.time()
events, done = sse_chat({
    "prompt": "请检索知识库中「平台架构总览」文档，用三句话概括平台的三个服务分别是什么。",
    "kbEnhanced": True, "kbIds": [KB], "engine": "claude", "maxTurns": 15,
}, on_event=on_ev, window_s=560)
dur = time.time() - t0
check("claude chat SSE kbEnhanced (retry)", "done" in ev_types and bool(done),
      f"dur={dur:.0f}s events={len(events)} types={sorted(set(ev_types))}")
final_txt = json.dumps(done, ensure_ascii=False)
check("SSE done payload has result", ("result" in done or len(final_txt) > 50), final_txt[:160])

# ---- 3. HITL deny + allow ----
def hitl_leg(fname, allow, marker):
    pending = {}

    def cb(p):
        if p.get("type") == "permission_request":
            pending["p"] = p

    body = {
        "prompt": "Create a file named " + fname + " in the current working directory containing exactly: " + marker,
        "engine": "claude", "permissionMode": "default", "maxTurns": 10,
        "cwd": str(ROOT.joinpath("storage", "tmp")),
    }
    out = {}

    def run():
        try:
            out["events"], out["done"] = sse_chat(body, on_event=cb, window_s=420)
        except Exception as e:  # noqa: BLE001
            out["err"] = repr(e)

    th = threading.Thread(target=run, daemon=True)
    th.start()
    for _ in range(180):
        if "p" in pending:
            break
        time.sleep(1)
    if "p" not in pending:
        th.join(timeout=2)
        return None, "no permission_request in 180s", (out.get("events") or [])
    pl = pending["p"]
    ans = call_json("POST", WEB + "/api/claude/permission",
                    {"sessionId": pl.get("sessionId"), "toolUseId": pl.get("toolUseId"),
                     "behavior": "allow" if allow else "deny"}, timeout=60)
    th.join(timeout=380)
    return ans, None, (out.get("events") or [])


marker = "E2E-HITL-" + time.strftime("%H%M%S")
fname_deny = "e2e-hitl-deny-" + marker + ".txt"
ans, err, evs = hitl_leg(fname_deny, allow=False, marker=marker)
if err:
    check("HITL deny leg", False, err + " events=" + str(len(evs)))
else:
    p = ROOT.joinpath("storage", "tmp", fname_deny)
    check("HITL deny leg (no file)", (ans or {}).get("success", True) and not p.exists(),
          "ans=" + json.dumps(ans or {}, ensure_ascii=False)[:80])

fname_allow = "e2e-hitl-allow-" + marker + ".txt"
ans2, err2, evs2 = hitl_leg(fname_allow, allow=True, marker=marker)
if err2:
    check("HITL allow leg", False, err2 + " events=" + str(len(evs2)))
else:
    p2 = ROOT.joinpath("storage", "tmp", fname_allow)
    created = p2.exists()
    if not created:
        time.sleep(3)
        created = p2.exists()
    check("HITL allow leg (file created)", (ans2 or {}).get("success", True) and created,
          "ans=" + json.dumps(ans2 or {}, ensure_ascii=False)[:80])

print()
failed = [n for n, ok, _ in results if not ok]
print("==== P8b retry summary: " + str(len(results) - len(failed)) + "/" + str(len(results)) + " passed ====")
sys.exit(1 if failed else 0)
