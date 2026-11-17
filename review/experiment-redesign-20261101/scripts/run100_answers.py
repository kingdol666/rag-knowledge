# -*- coding: utf-8 -*-
"""Stage 7: fresh tiered-platform answers for BQ01-BQ10 (current fixed system).

Arm: platform chat API (engine=claude), kbEnhanced, pinned to the five
domain libraries — the same provenance family as the paper's P arm.
Grading: gold arXiv id presence, gold-keyword coverage (same kw lists as the
historical run), citation markers, false-abstain, latency/cost.
"""
from __future__ import annotations

import json
import re
import time
import urllib.request
from pathlib import Path

REPO = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge")
OUT = REPO / "review" / "_exp_rerun_20261114"
ANS = OUT / "answers_fresh"
ANS.mkdir(parents=True, exist_ok=True)
QA = REPO / "benchmark-suite" / "data" / "papers" / "qa_questions.json"
CHAT_URL = "http://127.0.0.1:6789/api/claude/chat"

LIBS = {
    "计算机与人工智能": "b1199132-e4d4-4305-8c2e-82dc1753b0ba",
    "自然科学与地球科学": "1e6199ea-f380-44e2-94fc-d431f0f9bb6b",
    "生命科学与医学": "b28f0a25-1e1d-40ad-96b8-61bd2b093a28",
    "工程与能源": "8fa4db59-adde-4d6d-9fdb-2c375400e631",
    "经济与社会": "f5770687-6b05-4a8d-8645-af31686ca87e",
}
LIB_IDS = list(LIBS.values())

HIST = json.loads((REPO / "benchmark-suite" / "results" /
                   "paper_report.json").read_text(encoding="utf-8"))


def get_token() -> str:
    cand = REPO / "storage" / "loop-auth.json"
    if cand.exists():
        try:
            tok = json.loads(cand.read_text(encoding="utf-8")).get("token", "")
            if tok:
                return tok
        except Exception:
            pass
    for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("MCP_AUTH_TOKEN="):
            return line.split("=", 1)[1].strip()
    return ""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())


def chat_once(prompt: str, engine: str = "claude", timeout_s: int = 600):
    body = {"prompt": prompt, "kbEnhanced": True, "kbIds": LIB_IDS,
            "engine": engine, "permissionMode": "default", "maxTurns": 24}
    t0 = time.time()
    http_code, payload, err = 0, {}, ""
    try:
        req = urllib.request.Request(CHAT_URL, method="POST",
                                     data=json.dumps(body).encode("utf-8"))
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {get_token()}")
        with OPENER.open(req, timeout=timeout_s) as resp:
            http_code = resp.status
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        err = f"{type(e).__name__}: {str(e)[:200]}"
    return {"http": http_code, "payload": payload,
            "wall_s": round(time.time() - t0, 1), "error": err}


def grade(answer: str, q: dict, kw_list: list) -> dict:
    low = answer.lower()
    gold = q["arxiv_id"]
    kw_hits = [k for k in kw_list if k.lower() in low]
    markers = re.findall(
        r"(arxiv:\d{4}\.\d{4,5}|\[\d{1,2}\]|§\d[\.\d]*|Table \d+|"
        r"part \d+ of \d+|Fig\.? \d+|\d{4}\.\d{4,5})", answer)
    abstain = bool(re.search(
        r"not[- ]found|没有找到|未找到|no supporting evidence|无法回答",
        low)) and len(answer) < 400
    return {
        "gold_id_in_answer": gold in answer,
        "kw_hits": len(kw_hits), "kw_total": len(kw_list),
        "kw_list_hit": kw_hits,
        "cited": bool(markers), "n_markers": len(markers),
        "markers_head": markers[:8],
        "false_abstain": abstain,
        "chars": len(answer),
    }


def main() -> int:
    qa = json.loads(QA.read_text(encoding="utf-8"))
    items = qa if isinstance(qa, list) else qa.get("questions") or []
    rows = []
    for i, q in enumerate(items, 1):
        qid = q["qid"]
        hist = HIST["per_question"][qid]
        kw_list = hist["cells"][0]["kw_list"]
        r = chat_once(q["question"])
        answer = str(r["payload"].get("answer") or "")
        p = r["payload"]
        g = grade(answer, q, kw_list)
        row = {
            "qid": qid, "arxiv": q["arxiv_id"], "question": q["question"],
            "http": r["http"], "error": r["error"],
            "wall_s": r["wall_s"],
            "latency_s": p.get("duration_ms", 0) / 1000 if p.get("duration_ms") else r["wall_s"],
            "turns": p.get("num_turns"), "cost_usd": p.get("total_cost_usd"),
            "success": p.get("success"),
            "answer": answer, "grade": g,
        }
        (ANS / f"{qid}.json").write_text(
            json.dumps(row, ensure_ascii=False, indent=1), encoding="utf-8")
        rows.append(row)
        print(f"[{i:02d}] {qid} http={r['http']} wall={r['wall_s']}s "
              f"gold_id={g['gold_id_in_answer']} kw={g['kw_hits']}/{g['kw_total']} "
              f"cited={g['cited']} chars={g['chars']}", flush=True)
        (OUT / "answers_fresh_summary.json").write_text(
            json.dumps([{k: v for k, v in r0.items() if k != "answer"}
                        for r0 in rows], ensure_ascii=False, indent=1),
            encoding="utf-8")
    n_id = sum(1 for r in rows if r["grade"]["gold_id_in_answer"])
    n_kw = sum(1 for r in rows
               if r["grade"]["kw_hits"] == r["grade"]["kw_total"])
    n_cited = sum(1 for r in rows if r["grade"]["cited"])
    print(f"\nFRESH TIERED SUMMARY: gold_id={n_id}/10 full_kw={n_kw}/10 "
          f"cited={n_cited}/10", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
