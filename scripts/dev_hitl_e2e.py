"""HITL end-to-end test over the real chat SSE pipeline (engine=claude, SDK canUseTool).

Leg DENY: prompt asks claude to Write zz-hitl-e2e.txt; deny the permission
request; assert the file was NOT created.
Leg ALLOW: same prompt; approve; assert the file WAS created; then delete it.
SSRF-hardened: guard_url() pins targets to the loopback dev servers.
Exits 1 on any FAIL. Usage: python scripts/dev_hitl_e2e.py
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from dev_smoke import OPENER, guard_url  # noqa: E402  (loopback SSRF guard)

TARGET = os.path.join(ROOT, "zz-hitl-e2e.txt")
U_CHAT = "http://127.0.0.1:6789/api/claude/chat"
U_PERM = "http://127.0.0.1:6789/api/claude/permission"

RESULTS = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append(ok)
    tag = "PASS" if ok else "FAIL"
    print(f"[{tag}] {name}" + (f" -- {detail}" if detail else ""), flush=True)


def load_token() -> str:
    with open(os.path.join(ROOT, "storage", "smoke-e2e-token.txt"),
              encoding="utf-8") as f:
        return f.read().strip()


def sse_chat(token: str, prompt: str, on_permission, timeout_s: int = 240):
    """Run one chat turn; returns (assistant_texts, result_dict, perm_events)."""
    payload = {
        "prompt": prompt,
        "cwd": ROOT,
        "engine": "claude",
        "permissionMode": "default",
        "maxTurns": 6,
    }
    guard_url(U_CHAT)
    req = urllib.request.Request(U_CHAT, method="POST",
                                 data=json.dumps(payload).encode("utf-8"))
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "text/event-stream")
    req.add_header("Authorization", f"Bearer {token}")

    texts, result, perms = [], {}, []
    cur_event, cur_data = "", ""
    deadline = time.time() + timeout_s
    with OPENER.open(req, timeout=timeout_s) as resp:
        while time.time() < deadline:
            try:
                raw = resp.readline()
            except (TimeoutError, OSError):
                break  # socket read timeout — stream went silent
            if not raw:
                break
            line = raw.decode("utf-8", "replace").rstrip("\r\n")
            if line.startswith("event:"):
                cur_event, cur_data = line[6:].strip(), ""
                continue
            if not line.startswith("data:"):
                continue
            cur_data = line[5:].strip()
            if not cur_data:
                continue
            try:
                msg = json.loads(cur_data)
            except Exception:
                cur_event = ""  # consumed
                continue
            was_perm = (cur_event == "permission_request"
                        or msg.get("type") == "permission_request")
            cur_event = ""  # an event: header applies to exactly one data line
            if was_perm:
                perms.append(msg)
                print(f"       perm-event: {json.dumps(msg, ensure_ascii=False)[:220]}",
                      flush=True)
                decision = on_permission(msg)
                ack = post_permission(token, msg.get("sessionId", msg.get("session_id", "")),
                                      msg.get("toolUseId", ""), decision)
                print(f"       perm-post ack: {json.dumps(ack, ensure_ascii=False)[:200]}",
                      flush=True)
            mtype = msg.get("type")
            if mtype == "assistant":
                for blk in (msg.get("message") or {}).get("content", []):
                    if blk.get("type") == "text" and blk.get("text"):
                        texts.append(blk["text"])
            if mtype == "result":
                result = msg
                break
    return texts, result, perms


def post_permission(token: str, session_id: str, tool_use_id: str,
                    behavior: str) -> dict:
    payload = {"sessionId": session_id, "toolUseId": tool_use_id,
               "behavior": behavior,
               "message": f"HITL-E2E: {behavior} by automated test"}
    guard_url(U_PERM)
    req = urllib.request.Request(U_PERM, method="POST",
                                 data=json.dumps(payload).encode("utf-8"))
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with OPENER.open(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:1500]
        print(f"       [debug] sent payload: {json.dumps(payload, ensure_ascii=False)[:300]}",
              flush=True)
        print(f"       [debug] HTTP {e.code} body: {body}", flush=True)
        return {"success": False, "http_status": e.code, "error": body}


def main() -> int:
    token = load_token()
    prompt = ("Create a file named zz-hitl-e2e.txt in the current working "
              "directory containing exactly HITL-TEST. Use the Write tool. "
              "Do nothing else.")

    def deny(_msg):
        return "deny"

    def allow(_msg):
        return "allow"

    # ---------- leg 1: DENY ----------
    if os.path.exists(TARGET):
        os.remove(TARGET)
    texts, result, perms = sse_chat(token, prompt, deny)
    check("DENY: permission_request emitted", len(perms) >= 1,
          f"perms={len(perms)} result_type={result.get('type')}")
    check("DENY: stream reached result", result.get("type") == "result",
          f"got={result.get('type')}")
    check("DENY: file NOT created", not os.path.exists(TARGET),
          "file exists after deny!" if os.path.exists(TARGET) else "")
    print(f"       deny-leg assistant: {(texts[-1][:100] if texts else '(none)')}",
          flush=True)

    # ---------- leg 2: ALLOW ----------
    if os.path.exists(TARGET):
        os.remove(TARGET)
    texts2, result2, perms2 = sse_chat(token, prompt, allow)
    check("ALLOW: permission_request emitted", len(perms2) >= 1, f"perms={len(perms2)}")
    check("ALLOW: stream reached result", result2.get("type") == "result",
          f"got={result2.get('type')}")
    created = os.path.exists(TARGET)
    check("ALLOW: file created", created,
          "" if created else "file missing after allow!")
    if created:
        with open(TARGET, encoding="utf-8") as f:
            content = f.read().strip()
        check("ALLOW: file content correct", "HITL-TEST" in content,
              f"content={content[:60]!r}")
        os.remove(TARGET)
        print("       allow-leg cleanup: zz-hitl-e2e.txt removed", flush=True)

    failed = RESULTS.count(False)
    print(f"\n==== HITL e2e summary: {len(RESULTS) - failed} passed, "
          f"{failed} failed ====", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
