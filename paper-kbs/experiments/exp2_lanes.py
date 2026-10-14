#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exp 2 — agentic end-to-end comparison through the platform chat API.

Arms (all via POST /api/claude/chat, engine=omp, non-stream):
  search    : pinned-KB vector fast lane   kbEnhanced=true, kbIds=[pin]
  librarian : all-KB hierarchical lane     kbEnhanced=true, kbIds=[]
  hybrid    : pinned KB + hybrid prompt    kbEnhanced=true, kbIds=[pin]
  bare      : no knowledge base            kbEnhanced=false

4 questions x 4 arms = 16 real agent runs. Per run we record wall time,
LLM turns, cost, answer, citation gold hit and fact-marker hits.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kbcommon import CHAT_URL, OPENER, QUESTIONS, RESULTS, get_token

HYBRID_SUFFIX = ("【混合检索模式】先用 kb_hybrid_search 混合检索（单次调用，服务端完成"
                 "向量+目录双车道合并与判卷）；若幸存证据不足以回答，再用 kb_search_vector"
                 " / kb_list → kb_get_documents 逐级补齐后才作答。")

REFUSAL_MARKERS = ("无法", "没有找到", "未找到", "未检索到", "没有检索到", "不存在",
                   "无法回答", "无法作答", "not found", "cannot answer",
                   "unable to answer", "no evidence")

OUT = RESULTS / "exp2_lanes"
ARMS = ["search", "librarian", "hybrid", "bare"]
TIMEOUT_S = 900
MAX_TURNS = 20


def is_refusal(answer: str) -> bool:
    """Refusal = hedging marker near the answer's opening (first 200 chars).
    Markers appearing mid-answer (e.g. 'EVA 无法像 POE 那样…') are not refusals."""
    head = answer[:200].lower()
    return any(m in head for m in REFUSAL_MARKERS)


def run_arm(arm: str, q: dict) -> dict:
    kb_ids = []
    kb_enhanced = True
    prompt = q["text"]
    if arm == "search":
        kb_ids = [q["pin_kb_id"]]
    elif arm == "hybrid":
        kb_ids = [q["pin_kb_id"]]
        prompt = f"{prompt} {HYBRID_SUFFIX}"
    elif arm == "bare":
        kb_enhanced = False
        prompt = (q["text"] + " 请仅凭你自己的知识回答，不要使用任何工具。"
                  "如果不确定，请明确说明。")
    body = {"prompt": prompt, "kbEnhanced": kb_enhanced, "kbIds": kb_ids,
            "engine": "omp", "permissionMode": "default",
            "maxTurns": MAX_TURNS}
    import urllib.request
    t0 = time.time()
    http, payload, err = 0, {}, ""
    for attempt in (1, 2):  # omp occasionally returns a 0-turn empty answer
        t0 = time.time()
        try:
            req = urllib.request.Request(CHAT_URL, method="POST",
                                         data=json.dumps(body).encode("utf-8"))
            req.add_header("Content-Type", "application/json")
            req.add_header("Authorization", f"Bearer {get_token()}")
            with OPENER.open(req, timeout=TIMEOUT_S) as resp:
                http = resp.status
                payload = json.loads(resp.read().decode("utf-8"))
            err = ""
        except Exception as e:  # noqa: BLE001
            err = f"{type(e).__name__}: {str(e)[:200]}"
        answer = str(payload.get("answer") or "")
        transient_err = bool(err) and ("504" in err or "Timeout" in err
                                       or "timed out" in err)
        zero_turn_flake = (not answer.strip()
                           and not (payload.get("num_turns") or 0))
        if attempt == 2 or not (transient_err or zero_turn_flake):
            break
        print(f"    [retry] {'transient transport error' if transient_err else 'empty 0-turn answer'}, "
              f"attempt {attempt}", flush=True)
    wall = round(time.time() - t0, 1)
    answer = str(payload.get("answer") or "")
    low = answer.lower()
    gold_hits = [g for g in q["gold_doc_substrings"] if g.lower() in low]
    fact_hits = [m for m in q["fact_markers"] if m in answer]
    return {
        "arm": arm, "qid": q["qid"], "http": http,
        "success": payload.get("success"), "error": err,
        "wall_s": wall, "duration_ms": payload.get("duration_ms"),
        "turns": payload.get("num_turns"), "cost_usd": payload.get("total_cost_usd"),
        "answer_chars": len(answer),
        "answer_head": answer[:600],
        "answer_full_len": len(answer),
        "doc_citation_hit": bool(gold_hits),
        "gold_hits": gold_hits,
        "fact_hits": fact_hits,
        "n_fact_hits": len(fact_hits),
        "refusal": is_refusal(answer) if answer else None,
        "session_id": payload.get("sessionId"),
    }


def main() -> int:
    argv = sys.argv[1:]
    only = argv[0] if argv else ""
    global OUT
    if len(argv) > 1 and argv[1] == "rep2":
        OUT = RESULTS / "exp2_lanes_rep2"
    OUT.mkdir(parents=True, exist_ok=True)
    cat_cache = RESULTS / "kb_id_map.json"
    if cat_cache.exists():
        kbmap = json.loads(cat_cache.read_text(encoding="utf-8"))
    else:
        from kbcommon import McpClient
        mc = McpClient()
        cat = mc.call("kb_list", {"lightweight": True}, timeout=60)
        kbmap = {c["name"]: c["kb_id"] for c in cat["catalog"]}
        cat_cache.write_text(json.dumps(kbmap, ensure_ascii=False), encoding="utf-8")
    questions = [dict(q, pin_kb_id=kbmap[q["kb"]]) for q in QUESTIONS
                 if q["exp2"]]
    if only == "smoke":
        q = questions[0]
        r = run_arm("hybrid", q)
        print(json.dumps({k: v for k, v in r.items() if k != "answer_head"},
                         ensure_ascii=False, indent=1))
        print("HEAD:", r["answer_head"][:300])
        return 0

    for q in questions:
        for arm in ARMS:
            if only and only not in ("all",) and f"{arm}:{q['qid']}" != only:
                continue
            f = OUT / f"run_{arm}-{q['qid']}.json"
            if f.exists():
                print(f"[exp2] skip existing {f.name}", flush=True)
                continue
            print(f"[exp2] {arm} x {q['qid']} ...", flush=True)
            r = run_arm(arm, q)
            f.write_text(json.dumps({"run": r, "question": q["text"]},
                                    ensure_ascii=False, indent=1),
                         encoding="utf-8")
            print(f"[exp2]   -> wall={r['wall_s']}s turns={r['turns']} "
                  f"doc_hit={r['doc_citation_hit']} facts={r['n_fact_hits']}/"
                  f"{len(q['fact_markers'])} chars={r['answer_chars']} "
                  f"refusal={r['refusal']} err={r['error'][:60]}", flush=True)
            # clear orphan omp processes so the next run starts clean
            subprocess.run(["taskkill", "/F", "/IM", "omp.exe"],
                           capture_output=True)
            time.sleep(3)

    # summary
    rows = []
    for f in sorted(OUT.glob("run_*.json")):
        rows.append(json.loads(f.read_text(encoding="utf-8"))["run"])
    print("\n=== Exp2 summary ===")
    exp2_qs = {q["qid"]: q for q in QUESTIONS if q["exp2"]}
    total_markers = sum(len(q["fact_markers"]) for q in exp2_qs.values())
    summary = {}
    for arm in ARMS:
        rs = [r for r in rows if r["arm"] == arm]
        if not rs:
            continue
        walls = [r["wall_s"] for r in rs if r["wall_s"]]
        turns = [r["turns"] or 0 for r in rs]
        summary[arm] = {
            "n": len(rs),
            "doc_hit_rate": sum(1 for r in rs if r["doc_citation_hit"]) / len(rs),
            "fact_rate": sum(r["n_fact_hits"] for r in rs) / max(total_markers, 1),
            "wall_mean_s": round(sum(walls) / len(walls), 1) if walls else None,
            "turns_mean": round(sum(turns) / len(turns), 1) if turns else None,
            "refusals": sum(1 for r in rs if r["refusal"]),
        }
        s = summary[arm]
        print(f"{arm:<10} n={s['n']} doc_hit={s['doc_hit_rate']:.2f} "
              f"fact={s['fact_rate']:.2f} wall={s['wall_mean_s']}s "
              f"turns={s['turns_mean']} refusals={s['refusals']}")
    (OUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
