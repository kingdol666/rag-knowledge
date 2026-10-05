"""P8c — corrected SSE parser (honors `event:` header lines) re-runs:
SSE kbEnhanced done-detection + HITL deny/allow legs.

Root cause of prior FAILs: server emits SSE `event:` headers; the previous
parser only read the data-JSON `type` field.
Usage: python review/e2e-full-stack-20260922/p8c_sse_hitl.py
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
WEB = "http://127.0.0.1:6789"
results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("[PASS] " if cond else "[FAIL] ") + name + ("  -- " + detail if detail else ""), flush=True)


def post_json(url, body, timeout=90):
    guard_url(url)
    req = urllib.request.Request(url, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", "Bearer " + TOKEN)
    with urllib.request.urlopen(req, data=json.dumps(body).encode(), timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def sse_chat(body, on_event=None, window_s=600):
    """Parse SSE properly: `event: <name>` headers + data JSON `type` both count."""
    guard_url(WEB + "/api/claude/chat")
    req = urllib.request.Request(WEB + "/api/claude/chat", method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "text/event-stream")
    req.add_header("Authorization", "Bearer " + TOKEN)
    events = []
    done = {}
    with urllib.request.urlopen(req, data=json.dumps(body).encode(), timeout=window_s) as resp:
        buf = b""
        cur_event = ""
        start = time.time()
        while time.time() - start < window_s:
            chunk = resp.read1(4096) if hasattr(resp, "read1") else resp.read(1)
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                text = line.decode("utf-8", "replace").rstrip("\r")
                if text == "":
                    cur_event = ""
                    continue
                if text.startswith("event:"):
                    cur_event = text[6:].strip()
                    continue
                if not text.startswith("data:"):
                    continue
                data_str = text[5:].strip()
                try:
                    payload = json.loads(data_str)
                except ValueError:
                    payload = {"_raw": data_str[:200]}
                etype = payload.get("type") or cur_event or ""
                if cur_event in ("done", "error"):
                    etype = cur_event  # SSE header is authoritative for terminal frames
                payload["_sse_event"] = cur_event
                events.append(payload)
                if on_event:
                    on_event(payload, etype)
                if etype in ("done", "error", "result"):
                    if etype in ("done", "error", "result"):
                        done = payload
                        return events, done
    return events, done


state = json.loads(HERE.joinpath("p3_state.json").read_text(encoding="utf-8"))
KB = state["kb_uuid"]

# ---- 1. SSE kbEnhanced with correct parser ----
ev_types = []
sess = {"id": ""}


def on_ev(p, et):
    ev_types.append(et)
    if et == "system" and (p.get("session_id") or (p.get("message") or {}).get("session_id")):
        sess["id"] = p.get("session_id") or (p.get("message") or {}).get("session_id")


t0 = time.time()
events, done = sse_chat({
    "prompt": "请检索知识库中「平台架构总览」文档，用三句话概括平台的三个服务分别是什么。",
    "kbEnhanced": True, "kbIds": [KB], "engine": "claude", "maxTurns": 15,
    "permissionMode": "bypassPermissions",  # machine-to-machine leg: no human to approve MCP reads
}, on_event=on_ev, window_s=600)
dur = time.time() - t0
check("SSE kbEnhanced reaches done", ("done" in ev_types or "result" in ev_types),
      f"dur={dur:.0f}s events={len(events)} types={sorted(set(ev_types))}")
result_obj = done.get("result") or done
result_txt = json.dumps(result_obj, ensure_ascii=False)
check("SSE result content mentions services", ("后端" in result_txt or "backend" in result_txt.lower() or "服务" in result_txt),
      result_txt[:200])
if sess["id"]:
    h = post_json("GET", WEB + "/api/claude/history/" + sess["id"]) if False else None
# history check for this session
if sess["id"]:
    guard_url(WEB + "/api/claude/history/" + sess["id"])
    req = urllib.request.Request(WEB + "/api/claude/history/" + sess["id"])
    req.add_header("Authorization", "Bearer " + TOKEN)
    with urllib.request.urlopen(req, timeout=60) as r:
        hj = json.loads(r.read().decode("utf-8", "replace"))
    check("history replay of kbEnhanced session", len(hj.get("messages") or []) >= 2,
          "messages=" + str(len(hj.get("messages") or [])))

# ---- 2. HITL legs ----
def hitl_leg(fname, allow, marker):
    pending = {}

    def cb(p, et):
        if et == "permission_request":
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
    for _ in range(150):
        if "p" in pending:
            break
        time.sleep(1)
    if "p" not in pending:
        th.join(timeout=2)
        return None, "no permission_request in 150s", out
    pl = pending["p"]
    ans = post_json(WEB + "/api/claude/permission",
                    {"sessionId": pl.get("sessionId"), "toolUseId": pl.get("toolUseId"),
                     "behavior": "allow" if allow else "deny"})
    th.join(timeout=380)
    return ans, None, out


marker = "E2E-HITL-" + time.strftime("%H%M%S")
fname_deny = "e2e-hitl-deny-" + marker + ".txt"
ans, err, out = hitl_leg(fname_deny, allow=False, marker=marker)
if err:
    check("HITL deny leg", False, err)
else:
    # the model may resolve the file at repo root even with cwd set; check both
    candidates = [ROOT.joinpath("storage", "tmp", fname_deny), ROOT.joinpath(fname_deny)]
    created_any = any(p.exists() for p in candidates)
    check("HITL deny leg (permission approved-by-api, file NOT created)",
          (ans or {}).get("success", True) and not created_any,
          "ans=" + json.dumps(ans or {}, ensure_ascii=False)[:80])

fname_allow = "e2e-hitl-allow-" + marker + ".txt"
ans2, err2, out2 = hitl_leg(fname_allow, allow=True, marker=marker)
if err2:
    check("HITL allow leg", False, err2)
else:
    candidates2 = [ROOT.joinpath("storage", "tmp", fname_allow), ROOT.joinpath(fname_allow)]
    created = any(p.exists() for p in candidates2)
    if not created:
        time.sleep(3)
        created = any(p.exists() for p in candidates2)
    content_ok = False
    for p in candidates2:
        if p.exists():
            content_ok = marker in p.read_text(encoding="utf-8", errors="replace")
    check("HITL allow leg (file created with content)", (ans2 or {}).get("success", True) and created and content_ok,
          "ans=" + json.dumps(ans2 or {}, ensure_ascii=False)[:80])

print()
failed = [n for n, ok, _ in results if not ok]
print("==== P8c corrected-SSE summary: " + str(len(results) - len(failed)) + "/" + str(len(results)) + " passed ====")
sys.exit(1 if failed else 0)
