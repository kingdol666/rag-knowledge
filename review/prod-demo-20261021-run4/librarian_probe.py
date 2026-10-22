#!/usr/bin/env python3
"""Librarian-lane deep test (ralph run 4, US-305).

Drives the production full-library ladder — POST /api/claude/chat with
kbEnhanced=true and kbIds=[] — so the injected instruction is the librarian
spine itself: kb_list -> shelf selection -> kb_get_documents description
sweep -> batched kb_laya_judge -> kb_doc_read survivors -> answer / honest
not-found.  Three questions (lookup / enumerative / verified-absent), each
with the FULL tool trajectory captured from the SSE stream so the layer-by-
layer behaviour can be judged, not just the final answer.

SSRF-hardened: fixed loopback targets via dev_smoke.guard_url/OPENER.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from dev_smoke import OPENER, guard_url  # noqa: E402

CHAT = "http://127.0.0.1:6789/api/claude/chat"


def token() -> str:
    for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("MCP_AUTH_TOKEN="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("no token")


QUESTIONS = [
    {
        "qid": "LIB1-lookup",
        "text": ("How does InstructDS generate high-quality query-based dialogue "
                 "summaries? (InstructDS dialogue summarization, query-based "
                 "instruction tuning data synthesis)"),
        "expect": "found",
        "gold": ["2310.10981", "instructds"],
    },
    {
        "qid": "LIB2-enumerative",
        "text": ("Which papers in this knowledge base study precipitation extremes "
                 "under climate change? List each paper and its main finding."),
        "expect": "found",
        "gold": ["1503.07557", "precipitation"],
    },
    {
        "qid": "LIB3-absent",
        "text": "What is the traditional home recipe for Sichuan pickled vegetables (泡菜), including salt ratios and fermentation days?",
        "expect": "refusal",
        "gold": [],
    },
]

OUT = Path(__file__).resolve().parent


def run_one(q: dict, tok: str, max_turns: int = 24, timeout_s: int = 420) -> dict:
    guard_url(CHAT)
    payload = {"prompt": q["text"], "cwd": str(REPO), "engine": "claude",
               "maxTurns": max_turns, "stream": True,
               "kbEnhanced": True, "kbIds": []}
    req = urllib.request.Request(CHAT, method="POST",
                                 data=json.dumps(payload).encode("utf-8"))
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "text/event-stream")
    req.add_header("Authorization", f"Bearer {tok}")

    t0 = time.perf_counter()
    tools: list[dict] = []
    texts: list[str] = []
    result_frame: dict | None = None
    try:
        resp = OPENER.open(req, timeout=timeout_s)
        for raw in resp:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            body = line[5:].strip()
            try:
                msg = json.loads(body)
            except json.JSONDecodeError:
                continue
            mtype = msg.get("type")
            if mtype == "assistant":
                for b in (msg.get("message") or {}).get("content", []):
                    if b.get("type") == "tool_use":
                        args = b.get("input") or {}
                        keep = {k: str(v)[:110] for k, v in args.items()
                                if k in ("query", "kb_id", "doc_path", "pattern",
                                         "documents", "max_chars", "lightweight", "view")}
                        tools.append({"name": b.get("name"), "args": keep})
                    elif b.get("type") == "text" and b.get("text"):
                        texts.append(str(b["text"]))
            elif mtype == "result":
                result_frame = msg
    except urllib.error.HTTPError as e:
        return {"qid": q["qid"], "error": f"http {e.code}: {e.read().decode('utf-8', 'replace')[:300]}",
                "wall_s": round(time.perf_counter() - t0, 1)}
    except Exception as e:
        return {"qid": q["qid"], "error": str(e)[:300],
                "wall_s": round(time.perf_counter() - t0, 1)}

    wall = round(time.perf_counter() - t0, 1)
    answer = str((result_frame or {}).get("result") or "".join(texts)).strip()
    blob = answer.lower()
    if q["expect"] == "found":
        ok = any(g.lower() in blob for g in q["gold"])
        verdict = "PASS-gold" if ok else "FAIL-no-gold"
    else:
        refusal = any(k in blob for k in ("not found", "not_found", "no evidence",
                                          "not in", "cannot find", "无法", "没有任何",
                                          "不存在", "未找到", "没有找到", "不含",
                                          "未收录", "没有收录",
                                          "no content", "no recipe",
                                          "nothing retrieved", "verified absence"))
        fabricated = ("盐" in answer and "发酵" in answer and "天" in answer
                      and "not found" not in blob and "未找到" not in blob
                      and "not_found" not in blob)
        ok = refusal and not fabricated
        verdict = "PASS-honest-refusal" if ok else ("FAIL-fabrication" if fabricated else "FAIL-no-refusal")
    return {
        "qid": q["qid"], "expect": q["expect"], "verdict": verdict,
        "wall_s": wall,
        "duration_ms": (result_frame or {}).get("duration_ms"),
        "num_turns": (result_frame or {}).get("num_turns"),
        "cost_usd": (result_frame or {}).get("total_cost_usd"),
        "tool_trajectory": tools,
        "tool_counts": _counts(tools),
        "ladder_summary": _ladder(tools),
        "answer": answer,
        "answer_chars": len(answer),
    }


def _counts(tools: list[dict]) -> dict:
    c: dict[str, int] = {}
    for t in tools:
        n = str(t.get("name", "")).split("__")[-1]
        c[n] = c.get(n, 0) + 1
    return c


def _ladder(tools: list[dict]) -> str:
    """Compress the trajectory into the librarian spine stages actually visited."""
    stages = []
    for t in tools:
        n = str(t.get("name", "")).split("__")[-1]
        if n == "kb_list" and "L:kb_list" not in stages:
            stages.append("L:kb_list")
        elif n == "kb_get_documents" and "L:descriptions" not in stages:
            stages.append("L:descriptions")
        elif n == "kb_laya_judge" and "L:judge" not in stages:
            stages.append("L:judge")
        elif n == "kb_doc_read" and "L:read" not in stages:
            stages.append("L:read")
        elif n in ("kb_search_vector", "kb_search_two_stage") and "L:vector(!!off-lane)" not in stages:
            stages.append("L:vector(!!off-lane)")
        elif n == "kb_search" and "L:keyword(!!off-lane)" not in stages:
            stages.append("L:keyword(!!off-lane)")
    return " -> ".join(stages) if stages else "(no KB tools)"


def main() -> int:
    tok = token()
    out = {"timestamp_utc": datetime.now(timezone.utc).isoformat(),
           "lane": "librarian (kbEnhanced=true, kbIds=[])", "runs": []}
    for q in QUESTIONS:
        print(f"--- {q['qid']} ...", flush=True)
        r = run_one(q, tok)
        out["runs"].append(r)
        print(f"    verdict={r.get('verdict')} wall={r.get('wall_s')}s "
              f"ladder={r.get('ladder_summary')}", flush=True)
    (OUT / "librarian_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    passed = sum(1 for r in out["runs"] if str(r.get("verdict", "")).startswith("PASS"))
    print(f"\nLIBRARIAN LANE: {passed}/{len(out['runs'])} PASS")
    return 0 if passed == len(out["runs"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
