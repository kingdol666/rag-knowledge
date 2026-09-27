#!/usr/bin/env python3
"""Three-mode skill-level retrieval test on the live KB with the real local Laya.

A vector+content gate  — knowledgebase-search script layer (harness mode_a):
                         kb_search_vector -> doc dedup -> reads -> jev_filter engine=laya
B complete-recall      — knowledgebase-librarian script layer (harness mode_b):
                         catalog scan -> reads -> jev_filter engine=laya
C parallel hybrid      — knowledgebase-hybrid skill CLI (hybrid_search.py) run as a
                         subprocess exactly as a user invokes it.

Same three questions as review/laya-three-mode-20260925 for comparability.
Read-only: no KB mutations. Transcripts + SUMMARY.json in this directory.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "review" / "laya-three-mode-20260925"))

OUT = REPO / "review" / "hybrid-skill-20260923"
OUT.mkdir(parents=True, exist_ok=True)
HYBRID = REPO / ".claude" / "skills" / "knowledgebase-hybrid" / "scripts" / "hybrid_search.py"

QUESTIONS = [
    {"id": "q1", "query": "How does InstructDS generate high-quality query-based dialogue summaries?",
     "gold": "2310.10981"},
    {"id": "q2", "query": "What datasets does MultiMedQA evaluate and how does Flan-PaLM perform on MedQA?",
     "gold": "2212.13138"},
    {"id": "q3", "query": "How should farmers allocate trap cropping investments to maximize yield?",
     "gold": "2508.05896"},
]
EXCLUDES = ["Corpus", "soul-", "e2e-", "Novel-"]


def log(msg: str) -> None:
    print(msg, flush=True)


def gold_rows(result: dict, gold: str) -> list[dict]:
    rows = (result.get("verdict") or result.get("judge") or {}).get("doc_scores") or []
    # harness verdicts key the path as "doc"; hybrid_search judge uses "doc_path"
    return [r for r in rows if gold in str(r.get("doc_path") or r.get("doc") or "")]


def summarize_gold(result: dict, gold: str) -> dict:
    rows = gold_rows(result, gold)
    if not rows:
        return {"gold_in_judged": False}
    best = max(rows, key=lambda r: float(r.get("judge_score") or r.get("score") or 0))
    kept_paths = result.get("kept_doc_paths") or [r.get("doc_path") for r in (result.get("result_list") or [])]
    kept_rows = [r for r in rows if r.get("kept")]
    ranked = sorted(rows, key=lambda r: -float(r.get("judge_score") or r.get("score") or 0))
    return {"gold_in_judged": True, "gold_kept": bool(kept_rows),
            "gold_score": best.get("judge_score") or best.get("score"),
            "gold_rank": ranked.index(best) + 1, "gold_parts": len(rows)}


def run_a(q: dict) -> dict:
    import run_three_modes as h
    trace: dict = {}
    t0 = time.time()
    res = h.mode_a(q["query"], trace)
    return {"mode": "A_vector", "id": q["id"], "query": q["query"], "seconds": round(time.time() - t0, 1),
            "docs_read": len(trace.get("docs_read") or []),
            "judge": trace.get("judge"), "kept_doc_paths": res.get("kept"),
            "evidence_pack": res.get("evidence_pack"), "_gold": summarize_gold(res, q["gold"])}


def run_b(q: dict) -> dict:
    import run_three_modes as h
    trace: dict = {}
    t0 = time.time()
    res = h.mode_b(q["query"], trace)
    return {"mode": "B_complete", "id": q["id"], "query": q["query"], "seconds": round(time.time() - t0, 1),
            "docs_read": (trace.get("catalog_branch") or {}).get("docs_read"),
            "lane": {k: v for k, v in trace.items() if k in
                     ("shelves", "descriptions_scanned", "catalog_branch_scan", "catalog_branch")},
            "judge": trace.get("judge"), "kept_doc_paths": res.get("kept"),
            "evidence_pack": res.get("evidence_pack"), "_gold": summarize_gold(res, q["gold"])}


def run_c(q: dict) -> dict:
    out = OUT / f"C_hybrid_{q['id']}.json"
    cmd = [sys.executable, str(HYBRID), "--query", q["query"], "--engine", "laya",
           "--doc-budget", "30", "--vector-top-k", "10", "--vector-threshold", "0.35",
           "--max-state-chars", "6000"]
    for pref in EXCLUDES:
        cmd += ["--exclude-prefix", pref]
    cmd += ["--output", str(out), "--require-real"]
    log(f"  C cmd: {' '.join(cmd[:6])} ...")
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=2400)
    wall = round(time.time() - t0, 1)
    result = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"status": "error"}
    result["cli_exit_code"] = proc.returncode
    result["cli_stderr_tail"] = (proc.stderr or "")[-400:]
    result["seconds_cli_wall"] = wall
    slim = {k: v for k, v in result.items() if k != "evidence_pack"}
    slim["evidence_pack_chars"] = len(result.get("evidence_pack") or "")
    slim["evidence_pack"] = result.get("evidence_pack")
    slim["mode"] = "C_hybrid"
    slim["id"] = q["id"]
    slim["_gold"] = summarize_gold(result, q["gold"])
    return slim


def main() -> int:
    summary = []
    for q in QUESTIONS:
        log(f"[{q['id']}] {q['query']}")
        for runner, tag in ((run_a, "A_vector"), (run_b, "B_complete"), (run_c, "C_hybrid")):
            log(f"  -> {tag} start {time.strftime('%H:%M:%S')}")
            try:
                rec = runner(q)
            except Exception as exc:  # noqa: BLE001 — record and continue
                rec = {"mode": tag, "id": q["id"], "status": "harness_error",
                       "error": f"{type(exc).__name__}:{str(exc)[:300]}"}
            path = OUT / f"{tag}_{q['id']}.json"
            path.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
            gold = rec.get("_gold") or {}
            log(f"  <- {tag} done {rec.get('seconds', rec.get('seconds_cli_wall'))}s "
                f"gold_in_judged={gold.get('gold_in_judged')} gold_kept={gold.get('gold_kept')} "
                f"gold_score={gold.get('gold_score')} -> {path.name}")
            summary.append({k: v for k, v in rec.items()
                            if k in ("mode", "id", "seconds", "seconds_cli_wall", "docs_read",
                                     "status", "cli_exit_code", "_gold")
                            or k in ("merge", "reread", "lanes")})
    (OUT / "SUMMARY.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    log("SUMMARY.json written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
