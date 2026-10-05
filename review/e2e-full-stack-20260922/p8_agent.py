"""P8 — AgentWorkShop integration APIs E2E.

meta -> agent/chat sync(mock + claude) -> agent/chat async(task poll)
-> native-search (QDCVR) -> claude/chat SSE (kbEnhanced) -> HITL deny+allow
-> history persistence + replay.

Usage: python review/e2e-full-stack-20260922/p8_agent.py [--no-llm]
  --no-llm skips the real-LLM legs (claude engine calls).
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
NO_LLM = "--no-llm" in sys.argv


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


def call_json(method, url, body=None, token=TOKEN, timeout=300):
    guard_url(url)
    req = urllib.request.Request(url, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data=data, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8", "replace"))
        except Exception:
            return e.code, {}


def sse_chat(body, on_event=None, timeout_s=420):
    """POST /api/claude/chat and consume the SSE stream. Returns (events, done_payload)."""
    guard_url(WEB + "/api/claude/chat")
    req = urllib.request.Request(WEB + "/api/claude/chat", method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "text/event-stream")
    req.add_header("Authorization", "Bearer " + TOKEN)
    events = []
    done = {}
    with urllib.request.urlopen(req, data=json.dumps(body).encode(), timeout=timeout_s) as resp:
        buf = b""
        start = time.time()
        while time.time() - start < timeout_s:
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
                if etype == "done":
                    done = payload
                    return events, done
                if etype == "error":
                    done = payload
                    return events, done
    return events, done


WEB = "http://127.0.0.1:6789"
BE = "http://127.0.0.1:8771"
state = json.loads(HERE.joinpath("p3_state.json").read_text(encoding="utf-8"))
KB = state["kb_uuid"]

# ---- 1. meta discovery ----
s, j = call_json("GET", WEB + "/api/kb/agent/meta")
check("agent meta discovery", s == 200 and j.get("success", True),
      "keys=" + ",".join(list(j.keys())[:8]))

# ---- 2. sync chat with mock harness (contract validation) ----
s, j = call_json("POST", WEB + "/api/kb/agent/chat",
                 {"prompt": "Reply with the single word: pong", "harness": "mock", "mode": "sync"}, timeout=120)
check("agent chat sync (mock)", s == 200 and j.get("success") and bool(j.get("reply")),
      "reply[:60]=" + (j.get("reply") or "")[:60] + " tools=" + str(j.get("tools_used")))

# ---- 3. invalid prompt validation ----
s, j = call_json("POST", WEB + "/api/kb/agent/chat", {"prompt": ""}, timeout=30)
check("agent chat empty prompt -> 400", s == 400, f"status={s}")

if not NO_LLM:
    # ---- 4. sync chat with claude harness (real retrieval over ingested docs) ----
    t0 = time.time()
    s, j = call_json("POST", WEB + "/api/kb/agent/chat",
                     {"prompt": "在知识库里检索「AgentWorkShop 集成指南」这篇文档，告诉我 kb_agent chat API 的同步响应包含哪些字段？必须先检索再回答。",
                      "harness": "claude", "mode": "sync", "timeout_ms": 420000}, timeout=480)
    dur = time.time() - t0
    reply = j.get("reply") or ""
    tools = j.get("tools_used") or []
    check("agent chat sync (claude, real retrieval)", s == 200 and j.get("success") and len(reply) > 30,
          f"dur={dur:.0f}s tools={tools} reply[:100]={reply[:100].replace(chr(10), ' ')}")
    check("agent chat used retrieval tools", len(tools) >= 1, "tools_used=" + str(tools))

    # ---- 5. async mode + task poll ----
    s, j = call_json("POST", WEB + "/api/kb/agent/chat",
                     {"prompt": "用一句话说明这个知识库平台是做什么的。", "harness": "claude", "mode": "async"}, timeout=60)
    task_id = j.get("task_id") or ""
    check("agent chat async accepted", s == 200 and j.get("success") and bool(task_id),
          "task_id=" + str(task_id) + " poll=" + str(j.get("poll")))
    if task_id:
        final = {}
        for _ in range(60):
            s2, j2 = call_json("GET", WEB + "/api/kb/agent/tasks/" + task_id, timeout=60)
            final = j2
            st = (j2.get("task") or j2).get("status")
            if st in ("completed", "failed"):
                break
            time.sleep(5)
        st = (final.get("task") or final).get("status")
        check("agent async task completed", st == "completed", "status=" + str(st) + " " + json.dumps(final, ensure_ascii=False)[:160])

    # ---- 6. native-search (QDCVR one-shot) ----
    t0 = time.time()
    s, j = call_json("POST", WEB + "/api/kb/native-search",
                     {"query": "平台支持哪些检索策略？vector two-stage QDCVR", "kb_ids": [KB], "timeout_ms": 280000}, timeout=320)
    dur = time.time() - t0
    check("native-search QDCVR", s == 200 and j.get("success") and len(j.get("answer") or "") > 30,
          f"dur={dur:.0f}s tools={j.get('tools_used')} answer[:100]=" + (j.get("answer") or "")[:100].replace(chr(10), " "))

    # ---- 7. claude/chat SSE with kbEnhanced ----
    sess = {"id": ""}
    ev_types = []

    def on_ev(p):
        etype = p.get("type") or ""
        ev_types.append(etype)
        if etype == "system" and p.get("session_id"):
            sess["id"] = p["session_id"]

    events, done = sse_chat({
        "prompt": "请检索知识库中「平台架构总览」文档，用三句话概括平台的三个服务分别是什么。",
        "kbEnhanced": True, "kbIds": [KB], "engine": "claude", "maxTurns": 20,
    }, on_event=on_ev)
    check("claude chat SSE stream (kbEnhanced)", len(events) >= 2 and ("done" in ev_types),
          "events=" + str(len(events)) + " types=" + ",".join(sorted(set(ev_types))))
    final_msg = json.dumps(done, ensure_ascii=False)
    check("claude chat SSE result content", bool(done), "done[:160]=" + final_msg[:160])

    # ---- 8. HITL deny + allow legs ----
    hitl_target = str(ROOT.joinpath("storage", "tmp", "e2e-hitl-deny.txt"))
    marker = "E2E-HITL-" + time.strftime("%H%M%S")

    def hitl_leg(fname, allow):
        events = []
        pending = {}
        done_l = {}

        def cb(p):
            if p.get("type") == "permission_request":
                pending["payload"] = p
            if p.get("type") == "done":
                done_l["p"] = p

        body = {
            "prompt": "Create a file named " + fname + " in the current working directory containing exactly: " + marker,
            "engine": "claude", "permissionMode": "default", "maxTurns": 10, "cwd": str(ROOT.joinpath("storage", "tmp")),
        }
        result = {}

        def run_stream():
            try:
                result["events"], result["done"] = sse_chat(body, on_event=cb, timeout_s=300)
            except Exception as e:  # noqa: BLE001
                result["error"] = repr(e)

        th = threading.Thread(target=run_stream, daemon=True)
        th.start()
        for _ in range(120):
            if "payload" in pending:
                break
            time.sleep(1)
        th.join(timeout=1)
        if "payload" not in pending:
            return None, "no permission_request emitted", pending, done_l
        pl = pending["payload"]
        ans = call_json("POST", WEB + "/api/claude/permission",
                        {"sessionId": pl.get("sessionId"), "toolUseId": pl.get("toolUseId"),
                         "behavior": "allow" if allow else "deny"}, timeout=60)
        th.join(timeout=240)
        return ans, None, pending, done_l

    fname_deny = "e2e-hitl-deny-" + marker + ".txt"
    ans, err, pending, done_l = hitl_leg(fname_deny, allow=False)
    if err:
        check("HITL deny leg", False, err + " events=" + str(len(done_l.get("p", {}))))
    else:
        deny_path = ROOT.joinpath("storage", "tmp", fname_deny)
        check("HITL deny leg (no file created)", (ans or {}).get("success", True) and not deny_path.exists(),
              "answer=" + json.dumps(ans or {}, ensure_ascii=False)[:80] + " file_exists=" + str(deny_path.exists()))

    fname_allow = "e2e-hitl-allow-" + marker + ".txt"
    ans2, err2, pending2, done_l2 = hitl_leg(fname_allow, allow=True)
    if err2:
        check("HITL allow leg", False, err2)
    else:
        allow_path = ROOT.joinpath("storage", "tmp", fname_allow)
        created = allow_path.exists()
        if not created:
            time.sleep(3)
            created = allow_path.exists()
        check("HITL allow leg (file created)", (ans2 or {}).get("success", True) and created,
              "answer=" + json.dumps(ans2 or {}, ensure_ascii=False)[:80] + " file_exists=" + str(created))

    # ---- 9. history persistence + replay ----
    if sess["id"]:
        s, j = call_json("GET", WEB + "/api/claude/history/" + sess["id"], timeout=60)
        msgs = j.get("messages") or []
        check("chat history replay", s == 200 and len(msgs) >= 2, "messages=" + str(len(msgs)))
        s, j = call_json("GET", WEB + "/api/claude/history?engine=claude", timeout=60)
        check("chat history list", s == 200, json.dumps(j, ensure_ascii=False)[:100])
    else:
        check("chat history replay", False, "no session id captured from SSE")

print()
failed = [n for n, ok, _ in results if not ok]
print("==== P8 agent-integration summary: " + str(len(results) - len(failed)) + "/" + str(len(results)) + " passed ====")
sys.exit(1 if failed else 0)
