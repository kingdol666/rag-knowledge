#!/usr/bin/env python3
"""Channel 1 — harness 对外 API 流式检索流程测试 2026-10-12.

与 exp --chatmodes 完全相同的问题集(cm1/cm2/cm3, 直接 import 保证逐字一致)
和完全相同的模式表达(A: kbIds=[pin]; B: kbIds=[]; C: kbIds=[pin]+混合后缀),
但走 stream=True 抓真实检索流程: 每个工具调用的时刻/入参/结果返回时刻.

产物: review/retrieval-e2e-20261012/c1_<mode>-<qid>.json + summary.json
断点续跑: 已存在 JSON 跳过.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "benchmark-suite" / "experiments"))
from dev_smoke import OPENER, guard_url  # noqa: E402
from chat_mode_arms import HYBRID_SUFFIX, QUESTIONS, _is_refusal  # noqa: E402

HERE = Path(__file__).resolve().parent
WEB = "http://127.0.0.1:6789"
BACKEND = "http://127.0.0.1:8771"
AUTH_PATH = REPO / "storage" / "fulltest-auth.json"
AUTH = json.loads(AUTH_PATH.read_text(encoding="utf-8"))
TOK = AUTH["token"]

TIMEOUT_S = 600.0


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(HERE / "progress.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def verify_token() -> bool:
    guard_url(f"{BACKEND}/api/v1/auth/verify")
    req = urllib.request.Request(
        f"{BACKEND}/api/v1/auth/verify", method="POST",
        data=json.dumps({"token": TOK}).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    try:
        with OPENER.open(req, timeout=20) as resp:
            return resp.status == 200
    except urllib.error.HTTPError:
        return False


def refresh_token() -> str:
    """login + create API token, persist to storage/fulltest-auth.json."""
    guard_url(f"{BACKEND}/api/v1/auth/login")
    req = urllib.request.Request(
        f"{BACKEND}/api/v1/auth/login", method="POST",
        data=json.dumps({"username": AUTH["user"], "password": AUTH["pwd"]}).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    with OPENER.open(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    # token create 需要登录态; 登录返回里通常带一个可用凭证字段, 逐字段探测
    bearer = data.get("access_token") or data.get("token") or ""
    if not bearer:
        raise RuntimeError(f"login returned no bearer: {list(data.keys())}")
    guard_url(f"{BACKEND}/api/v1/auth/tokens")
    req2 = urllib.request.Request(
        f"{BACKEND}/api/v1/auth/tokens", method="POST",
        data=json.dumps({"name": f"retrieval-e2e-{time.strftime('%m%d-%H%M')}"}).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {bearer}"})
    with OPENER.open(req2, timeout=20) as resp2:
        tok = json.loads(resp2.read().decode("utf-8"))
    new_tok = tok.get("token") or tok.get("api_token") or tok.get("key") or ""
    if not new_tok:
        raise RuntimeError(f"token create returned no key: {list(tok.keys())}")
    AUTH["token"] = new_tok
    globals()["TOK"] = new_tok
    AUTH_PATH.write_text(json.dumps(AUTH, ensure_ascii=False, indent=1), encoding="utf-8")
    return new_tok


def _input_head(inp: dict) -> str:
    try:
        s = json.dumps(inp, ensure_ascii=False)
    except Exception:  # noqa: BLE001
        s = str(inp)
    return s[:220]


def stream_run(mode: str, q: dict) -> dict:
    prompt = q["text"]
    kb_ids = [q["pin"]] if mode in ("A", "C") else []
    if mode == "C":
        prompt = f"{prompt} {HYBRID_SUFFIX}"
    body = {
        "prompt": prompt, "kbEnhanced": True, "kbIds": kb_ids,
        "engine": "claude", "permissionMode": "default",
        "maxTurns": 18, "timeout_ms": int(TIMEOUT_S * 1000), "stream": True,
    }
    rec: dict = {
        "channel": "harness-api-stream", "mode": mode, "qid": q["qid"],
        "expect": q["expect"], "kbIds": kb_ids, "prompt_head": prompt[:300],
        "engine": "claude", "permissionMode": "default",
    }
    t0 = time.time()
    events: list = []
    done_msg: dict | None = None
    buf = ""
    try:
        guard_url(f"{WEB}/api/claude/chat")
        r = urllib.request.Request(
            f"{WEB}/api/claude/chat", method="POST",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {globals()['TOK']}"})
        with OPENER.open(r, timeout=TIMEOUT_S + 60) as resp:
            rec["http"] = resp.status
            for raw in resp:
                buf += raw.decode("utf-8", "replace")
                while "\n\n" in buf:
                    frame, buf = buf.split("\n\n", 1)
                    ev_name, ev_data = "", ""
                    for ln in frame.splitlines():
                        if ln.startswith("event: "):
                            ev_name = ln[7:].strip()
                        elif ln.startswith("data: "):
                            ev_data = ln[6:]
                    if not ev_name and ev_data:
                        ev_name = "message"
                    if not ev_name:
                        continue
                    try:
                        d = json.loads(ev_data)
                    except Exception:  # noqa: BLE001
                        continue
                    ent: dict = {"t": round(time.time() - t0, 1), "event": ev_name}
                    msg = d.get("message") if isinstance(d.get("message"), dict) else {}
                    mtype = d.get("type") or msg.get("type")
                    ent["mtype"] = mtype
                    if ev_name == "meta":
                        ent["engine"] = d.get("engine")
                        ent["model"] = d.get("model")
                    elif ev_name == "done":
                        done_msg = d
                        ent["subtype"] = d.get("subtype")
                    elif ev_name == "error":
                        ent["error"] = str(d.get("error"))[:200]
                    else:
                        blk = msg.get("content") if msg else d.get("content")
                        if isinstance(blk, list):
                            uses = [{"id": b.get("tool_use_id") or b.get("id"),
                                     "name": b.get("name"),
                                     "input": _input_head(b.get("input") or {})}
                                    for b in blk
                                    if isinstance(b, dict) and b.get("type") == "tool_use"]
                            res = [{"id": b.get("tool_use_id"),
                                    "chars": len(json.dumps(b.get("content") or "", ensure_ascii=False))}
                                   for b in blk
                                   if isinstance(b, dict) and b.get("type") == "tool_result"]
                            if uses:
                                ent["tool_uses"] = uses
                            if res:
                                ent["tool_results"] = res
                            txt = sum(len(b.get("text") or "") for b in blk
                                      if isinstance(b, dict) and b.get("type") == "text")
                            if txt:
                                ent["text_chars"] = txt
                    events.append(ent)
    except urllib.error.HTTPError as e:
        rec["http"] = e.code
        rec["error"] = e.read().decode("utf-8", "replace")[:300]
    except Exception as e:  # noqa: BLE001
        rec["http"] = None
        rec["error"] = f"{type(e).__name__}: {str(e)[:250]}"
    rec["wall_s"] = round(time.time() - t0, 1)
    rec["n_events"] = len(events)
    rec["timeline"] = events
    if done_msg:
        rec["answer"] = str(done_msg.get("result") or done_msg.get("answer") or "")
        rec["num_turns"] = done_msg.get("num_turns")
        rec["duration_ms"] = done_msg.get("duration_ms")
        rec["cost_usd"] = done_msg.get("total_cost_usd")
        rec["session_id"] = done_msg.get("sessionId") or done_msg.get("session_id")
    else:
        rec["answer"] = ""

    # ── 工具时间线: tool_use→tool_result 配对出每工具耗时 ──
    pending: dict = {}
    spans: list = []
    for e in events:
        for u in e.get("tool_uses") or []:
            pending[u["id"]] = {"name": u["name"], "input": u["input"], "t0": e["t"]}
        for rr in e.get("tool_results") or []:
            u = pending.pop(rr["id"], None)
            if u:
                spans.append({"tool": u["name"], "input": u["input"],
                              "t_start": u["t0"], "t_end": e["t"],
                              "dur_s": round(e["t"] - u["t0"], 1),
                              "result_chars": rr["chars"]})
    rec["tool_spans"] = spans
    rec["tool_sequence"] = [s["tool"] for s in spans]
    rec["retrieval_tools_s"] = round(sum(s["dur_s"] for s in spans), 1)
    rec["answer_chars"] = len(rec.get("answer") or "")

    # ── 质量门 (与 exp chatmodes 同一口径) ──
    low = (rec.get("answer") or "").lower()
    markers = [m for m in q["answer_markers"] if m in low]
    rec["answer_markers_hit"] = markers
    if q["expect"] == "found":
        rec["gate_passed"] = rec.get("http") == 200 and bool(rec.get("answer")) and bool(markers)
    else:
        rec["refusal"] = _is_refusal(rec.get("answer") or "")
        rec["gate_passed"] = rec.get("http") == 200 and bool(rec.get("answer")) and rec["refusal"]
    return rec


def main() -> int:
    if not verify_token():
        log("token 401 → 重新铸造…")
        try:
            refresh_token()
            log(f"新 token: {TOK[:16]}…")
        except Exception as e:  # noqa: BLE001
            log(f"重铸失败: {e}")
            return 2
    modes = ("A", "B", "C")
    qids = ("cm1", "cm2", "cm3")
    rows = []
    for mode in modes:
        for qid in qids:
            q = QUESTIONS[qid]
            out = HERE / f"c1_{mode}-{qid}.json"
            if out.exists():
                log(f"跳过已存在 {out.name}")
                r = json.loads(out.read_text(encoding="utf-8"))
                rows.append(r)
                continue
            log(f"▶ mode {mode} × {qid} ({q['expect']}) 开始…")
            r = stream_run(mode, q)
            out.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
            seq = ",".join(r["tool_sequence"][:10])
            log(f"  → wall={r['wall_s']}s http={r.get('http')} gate="
                f"{'✅' if r['gate_passed'] else '❌'} turns={r.get('num_turns')} "
                f"tools=[{seq}] ans={r['answer_chars']}ch")
            rows.append(r)
    n_pass = sum(1 for r in rows if r.get("gate_passed"))
    (HERE / "channel1_summary.json").write_text(
        json.dumps({"rows": [{k: r.get(k) for k in (
            "mode", "qid", "expect", "http", "wall_s", "duration_ms", "num_turns",
            "cost_usd", "answer_chars", "answer_markers_hit", "refusal",
            "gate_passed", "tool_sequence", "retrieval_tools_s", "session_id")}
            for r in rows]}, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"通道1完成: 门禁 {n_pass}/{len(rows)}")
    return 0 if n_pass == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
