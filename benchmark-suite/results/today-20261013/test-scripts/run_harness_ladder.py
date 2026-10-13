#!/usr/bin/env python3
"""对外 harness API（POST /api/claude/chat）真实问题逐级检索实测：
mode B（kbEnhanced=true, kbIds=[]，全库逐级车道，服务端抑制向量工具）。
两题串行：transformer是什么 / 红烧肉怎么做。
每题抓完整 SSE 工具时间线（时刻/工具/入参/返回大小）+ 最终回答。
SSRF 边界：目标主机/端口为字面量回环地址，与 scripts/mcp_call.py 同款防护。"""
import json, sys, threading, time, queue
import http.client
from pathlib import Path

REPO = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge")
# 回环字面量——唯一允许的目标（SSRF 防护：主机端口不在任何变量中）
CHAT_HOST, CHAT_PORT = "127.0.0.1", 6789
assert f"http://{CHAT_HOST}:{CHAT_PORT}" == "http://127.0.0.1:6789"

QUESTIONS = [
    {"qid": "s1-tomato", "text": "番茄炒蛋怎么做？"},
    {"qid": "s2-transformer-power", "text": "transformer 变压器在电力系统中如何选型？"},
    {"qid": "s3-lora", "text": "如何用 LoRA 微调大语言模型？"},
    {"qid": "s4-zephyr7", "text": "Zephyr-7 无线充电协议的帧结构是什么？"},
]
TIMEOUT_S = 600


def stream_run(q: dict, tok: str) -> dict:
    body = {"prompt": q["text"], "kbEnhanced": True, "kbIds": [], "engine": "claude",
            "permissionMode": "default", "maxTurns": 18, "timeout_ms": TIMEOUT_S * 1000, "stream": True}
    t0 = time.time()
    events, done, buf = [], None, ""
    conn = http.client.HTTPConnection(CHAT_HOST, CHAT_PORT, timeout=TIMEOUT_S + 60)
    conn.request("POST", "/api/claude/chat", body=json.dumps(body).encode("utf-8"),
                 headers={"Content-Type": "application/json",
                          "Authorization": f"Bearer {tok}"})
    resp = conn.getresponse()
    http_status = resp.status
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
            except Exception:
                continue
            ent = {"t": round(time.time() - t0, 1), "event": ev_name}
            msg = d.get("message") if isinstance(d.get("message"), dict) else {}
            if ev_name == "done":
                done = d
            blk = msg.get("content") if msg else d.get("content")
            if isinstance(blk, list):
                uses = [{"name": b.get("name"),
                         "input": json.dumps(b.get("input") or {}, ensure_ascii=False)[:200]}
                        for b in blk if isinstance(b, dict) and b.get("type") == "tool_use"]
                res = [{"chars": len(json.dumps(b.get("content") or "", ensure_ascii=False))}
                       for b in blk if isinstance(b, dict) and b.get("type") == "tool_result"]
                if uses:
                    ent["uses"] = uses
                if res:
                    ent["res"] = res
            events.append(ent)
    wall = round(time.time() - t0, 1)
    answer = str((done or {}).get("result") or (done or {}).get("answer") or "")
    seq = []
    sizes = [r["chars"] for e in events for r in e.get("res", [])]
    si = 0
    for e in events:
        for u in e.get("uses", []):
            cs = sizes[si] if si < len(sizes) else None
            si += 1
            seq.append({"t": e["t"], "tool": u["name"], "input": u["input"], "result_chars": cs})
    return {"qid": q["qid"], "prompt": q["text"], "http": http_status, "wall_s": wall,
            "turns": (done or {}).get("num_turns"), "cost_usd": (done or {}).get("total_cost_usd"),
            "duration_ms": (done or {}).get("duration_ms"),
            "answer": answer, "answer_chars": len(answer),
            "max_tool_result_chars": max((s["result_chars"] or 0) for s in seq) if seq else 0,
            "tool_timeline": seq, "n_events": len(events)}


def main() -> int:
    AUTH = json.loads((REPO / "storage" / "fulltest-auth.json").read_text(encoding="utf-8"))
    TOK = AUTH["token"]
    out_all = []
    for q in QUESTIONS:
        print("=" * 76)
        print(f"问题[{q['qid']}]: {q['text']}")
        print("=" * 76)
        rec = stream_run(q, TOK)
        out_all.append(rec)
        print(f"HTTP {rec['http']} · wall {rec['wall_s']}s · turns {rec['turns']} · "
              f"cost ${rec['cost_usd']} · 回答 {rec['answer_chars']} chars · "
              f"最大单次工具返回 {rec['max_tool_result_chars']} chars")
        print("工具时间线:")
        for s in rec["tool_timeline"]:
            print(f"  t+{s['t']:6.1f}s  {s['tool']:30s} {s['input'][:120]}")
            print(f"{'':12s}↳ 返回 {s['result_chars']} chars")
        print("\n回答:")
        print(rec["answer"][:1200])
        print()
        (REPO / "tmp" / f"harness_ladder_{q['qid']}.json").write_text(
            json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    print("artifacts: per-qid JSON artifacts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
