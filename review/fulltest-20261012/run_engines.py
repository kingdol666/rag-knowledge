#!/usr/bin/env python3
"""All-harness acceptance 2026-10-12 — 每个可用引擎:
  A. 一轮带工具调用的对话(API, bypassPermissions) → sessionId 非空 + 回答非空
  B. resume 第二轮 → 同一 session 行增长(不碎裂) + 上下文连续
  C. HITL(stream=true, default 档): mock 脚本审批 / dsh 原生 request_permission
产物: review/fulltest-20261012/eng_<engine>_<tag>.json
断点续跑: 已存在 JSON 跳过。
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from dev_smoke import OPENER, guard_url  # noqa: E402

WEB = "http://127.0.0.1:6789"
TOK = json.loads((REPO / "storage" / "fulltest-auth.json").read_text(encoding="utf-8"))["token"]

TOOL_PROMPT = "列出当前目录下名叫 web 的文件夹里有什么文件。用你的文件/终端工具实际执行,不要凭记忆回答。"


def req_json(method: str, url: str, body=None, timeout: float = 60.0):
    guard_url(url)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    r = urllib.request.Request(url, method=method, data=data,
                               headers={"Content-Type": "application/json",
                                        "Authorization": f"Bearer {TOK}"})
    with OPENER.open(r, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def log(msg: str):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(HERE / "progress.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def save(tag: str, rec: dict):
    (HERE / f"{tag}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1),
                                      encoding="utf-8")


def chat(engine: str, prompt: str, tag: str, *, resume: str = "",
         permission_mode: str = "bypassPermissions", timeout_s: float = 300.0) -> dict:
    t0 = time.time()
    body = {"prompt": prompt, "engine": engine, "kbEnhanced": False,
            "maxTurns": 12, "permissionMode": permission_mode,
            "timeout_ms": int(timeout_s * 1000), "stream": False}
    if resume:
        body["resume"] = resume
    rec: dict = {"tag": tag, "engine": engine, "prompt_head": prompt[:120]}
    try:
        payload = req_json("POST", f"{WEB}/api/claude/chat", body, timeout_s + 30)
        rec.update({"answer": str(payload.get("answer") or ""),
                    "session_id": payload.get("sessionId"),
                    "num_turns": payload.get("num_turns"),
                    "duration_ms": payload.get("duration_ms"),
                    "stop_reason": payload.get("stopReason") or payload.get("stop_reason"),
                    "is_error": payload.get("isError")})
    except urllib.error.HTTPError as e:
        rec["error"] = e.read().decode("utf-8", "replace")[:300]
    except Exception as e:  # noqa: BLE001
        rec["error"] = f"{type(e).__name__}: {str(e)[:200]}"
    rec["wall_s"] = round(time.time() - t0, 1)
    save(tag, rec)
    log(f"  {tag}: wall={rec['wall_s']}s sid={rec.get('session_id')} "
        f"ans={len(rec.get('answer') or '')}ch "
        f"{'ERR=' + str(rec.get('error'))[:150] if rec.get('error') else ''}")
    return rec


# ── HITL: stream=true + 捕获 permission_request + POST 决策 ──

def hitl_roundtrip(engine: str, prompt: str, tag: str, approve: bool = True,
                   timeout_s: float = 180.0) -> dict:
    import ssl  # noqa: F401  (OPENER handles it)
    t0 = time.time()
    body = {"prompt": prompt, "engine": engine, "kbEnhanced": False,
            "maxTurns": 10, "permissionMode": "default",
            "timeout_ms": int(timeout_s * 1000), "stream": True}
    guard_url(f"{WEB}/api/claude/chat")
    r = urllib.request.Request(f"{WEB}/api/claude/chat", method="POST",
                               data=json.dumps(body).encode("utf-8"),
                               headers={"Content-Type": "application/json",
                                        "Authorization": f"Bearer {TOK}"})
    rec: dict = {"tag": tag, "engine": engine, "approve": approve}
    perm_req = None
    done_msg = None
    buf = ""
    perm_answered = False
    try:
        with OPENER.open(r, timeout=timeout_s + 60) as resp:
            def read_stream_and_answer():
                nonlocal perm_req, done_msg, buf, perm_answered
                for raw in resp:
                    buf += raw.decode("utf-8", "replace")
                    while "\n\n" in buf:
                        frame, buf = buf.split("\n\n", 1)
                        ev, data = "", ""
                        for ln in frame.splitlines():
                            if ln.startswith("event: "):
                                ev = ln[7:].strip()
                            elif ln.startswith("data: "):
                                data += ln[6:]
                        if not data:
                            continue
                        try:
                            d = json.loads(data)
                        except Exception:
                            continue
                        if ev == "permission_request" and not perm_answered:
                            perm_req = d
                            rec["perm_tool"] = d.get("toolName")
                            rec["perm_options"] = [o.get("optionId") if isinstance(o, dict) else o
                                                    for o in (d.get("options") or [])][:6]
                            # 审批决策
                            decision = ("allow", d.get("options", [{}])[0].get("optionId", "allow_once") if approve else None)
                            payload = {"sessionId": d.get("sessionId") or "",
                                       "toolUseId": d.get("toolUseId"),
                                       "behavior": decision[0]}
                            if approve and isinstance(d.get("options"), list) and d["options"]:
                                payload["optionId"] = d["options"][0].get("optionId")
                            try:
                                req_json("POST", f"{WEB}/api/claude/permission",
                                         {"sessionId": d.get("sessionId") or "",
                                          "toolUseId": d.get("toolUseId"),
                                          "behavior": "allow" if approve else "deny",
                                          **({"optionId": d["options"][0]["optionId"]}
                                             if approve and isinstance(d.get("options"), list) and d["options"] else {})},
                                         timeout=30)
                                log(f"  {tag}: permission {'ALLOW' if approve else 'DENY'} 已提交")
                            except Exception as e:  # noqa: BLE001
                                rec["perm_post_error"] = str(e)[:150]
                            perm_answered = True
                        elif ev == "done":
                            done_msg = d
                            return
            read_stream_and_answer()
    except urllib.error.HTTPError as e:
        rec["error"] = e.read().decode("utf-8", "replace")[:300]
    except Exception as e:  # noqa: BLE001
        rec["error"] = f"{type(e).__name__}: {str(e)[:200]}"
    if done_msg:
        rec["answer"] = str(done_msg.get("result") or done_msg.get("answer") or "")
    rec["got_permission_request"] = perm_req is not None
    rec["wall_s"] = round(time.time() - t0, 1)
    save(tag, rec)
    log(f"  {tag}: perm_req={rec['got_permission_request']} tool={rec.get('perm_tool')} "
        f"wall={rec['wall_s']}s ans={len(rec.get('answer') or '')}ch "
        f"{'ERR=' + str(rec.get('error'))[:120] if rec.get('error') else ''}")
    return rec


ENGINES = {
    # engine: (工具提示词, 是否做 resume 第二轮)
    "mock": ("请随便回应即可", True),
    "codex": (TOOL_PROMPT, True),
    "pi": (TOOL_PROMPT, True),
    "copilot": (TOOL_PROMPT, False),
    "dsh": (TOOL_PROMPT, True),
    "hermes": (TOOL_PROMPT, True),
}


def main() -> int:
    only = set(sys.argv[1:]) or None
    log(f"=== 引擎验收启动: {', '.join(ENGINES)} ===")
    for eng, (prompt, do_resume) in ENGINES.items():
        if only and eng not in only:
            continue
        t1 = f"eng_{eng}_turn1"
        if (HERE / f"{t1}.json").exists():
            log(f"-- {t1} 已存在, 跳过")
            rec = json.loads((HERE / f"{t1}.json").read_text(encoding="utf-8"))
        else:
            log(f"── {eng} turn1 开始")
            rec = chat(eng, prompt, t1)
        sid = rec.get("session_id") or ""
        if do_resume and sid and only is None or (do_resume and sid):
            t2 = f"eng_{eng}_turn2"
            if not (HERE / f"{t2}.json").exists():
                log(f"── {eng} turn2 (resume={sid[:18]}…) 开始")
                chat(eng, "我上一条问题问的是什么?请原样复述问题的前 20 个字。", t2, resume=sid)
        # HITL: mock(脚本) 与 dsh(原生 ACP)
        if eng in ("mock", "dsh"):
            th = f"eng_{eng}_hitl"
            if not (HERE / f"{th}.json").exists():
                log(f"── {eng} HITL roundtrip 开始")
                if eng == "mock":
                    hitl_roundtrip(eng, "[hitl-demo] 请写入 demo.txt", th, approve=True)
                else:
                    hitl_roundtrip(eng, TOOL_PROMPT, th, approve=True)
    log("=== 引擎验收执行完毕 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
