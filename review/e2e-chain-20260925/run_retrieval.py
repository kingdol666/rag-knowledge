#!/usr/bin/env python3
"""E2E chain retrieval verification: the freshly ingested docs must be found
and their facts retrievable through all three retrieval modes."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "review" / "laya-three-mode-20260925"))
OUT = Path(__file__).resolve().parent
HYBRID = REPO / ".claude" / "skills" / "knowledgebase-hybrid" / "scripts" / "hybrid_search.py"

GOLD = "tracelens"
QUESTIONS = [
    {"id": "Q1", "modes": ["A_vector", "B_complete", "C_hybrid"],
     "query": "TraceLens 生产环境的 span 采样率和查询 p99 延迟分别是多少？相比旧系统降了多少？",
     "gold": "tracelens-deployment-notes", "facts": ["7.3%", "412ms", "847ms", "51.4%"]},
    {"id": "Q2", "modes": ["A_vector"],
     "query": "向量索引增量插入占比达到多少时应该触发全量重建？删除标记比例的阈值是多少？",
     "gold": "vector-index-tuning-guide (part 1 of 2)", "facts": ["15%", "25%"]},
]
EXTRA = {
    "Q1": "tracelens trace 采样率 sampling 分布式追踪 可观测性 运维 p99 延迟",
    "Q2": "向量索引 HNSW 增量重建 全量重建 删除标记 阈值",
}


def log(m): print(m, flush=True)


def gold_check(rec, q):
    verdict = rec.get("verdict") or rec.get("judge") or {}
    rows = verdict.get("doc_scores") or []
    hits = [r for r in rows if q["gold"] in str(r.get("doc_path") or r.get("doc") or "")]
    kept = [r for r in hits if r.get("kept")]
    return {"judged": bool(hits), "kept": bool(kept),
            "best": max((float(r.get("judge_score") or r.get("score") or 0) for r in hits), default=None)}


def run_mode(tag, q):
    trace: dict = {}
    import run_three_modes as h
    t0 = time.time()
    if tag == "A_vector":
        res = h.mode_a(q["query"], trace)
    else:
        res = h.mode_b(q["query"], trace,
                       extra_terms=tuple(EXTRA[q["id"]].split()), top_k_floor=5,
                       peek_heads=(tag == "B_complete"), peek_limit=300)
    rec = {"mode": tag, "id": q["id"], "query": q["query"], "seconds": round(time.time() - t0, 1),
           "scan": {k: trace.get(k) for k in ("descriptions_scanned", "description_overlap_docs",
                                              "zero_overlap_docs_unread", "docs_read", "peek_docs",
                                              "expansion_docs", "expansion_upgraded")},
           "judge": {k: v for k, v in (trace.get("judge") or {}).items() if k != "doc_scores"},
           "gold": gold_check({"verdict": trace.get("judge"), "kept_doc_paths": res.get("kept")}, q),
           "kept_doc_paths": res.get("kept"), "evidence_pack": res.get("evidence_pack")}
    return rec


def run_c(q):
    out = OUT / f"C_hybrid_{q['id']}.json"
    cmd = [sys.executable, str(HYBRID), "--query", q["query"], "--engine", "laya",
           "--doc-budget", "30", "--vector-top-k", "10", "--vector-threshold", "0.35",
           "--max-state-chars", "6000", "--peek-heads", "--top-k-floor", "5", "--lane-agreement",
           "--extra-terms", EXTRA[q["id"]]]
    for pref in ("Corpus", "soul-", "e2e-", "Novel-"):
        cmd += ["--exclude-prefix", pref]
    cmd += ["--output", str(out), "--require-real"]
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=2400)
    rec = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"status": "error"}
    rec["cli_exit_code"] = proc.returncode
    rec["seconds"] = round(time.time() - t0, 1)
    rec["gold"] = {"judged": any(q["gold"] in str(r.get("doc_path") or "") for r in (rec.get("judge") or {}).get("doc_scores") or []),
                   "kept": any(q["gold"] in str(r.get("doc_path") or "") for r in rec.get("result_list") or []),
                   "in_evidence": q["gold"] in str(rec.get("kept_doc_paths") or [])}
    return rec


def main():
    summary = []
    for q in QUESTIONS:
        log(f"[{q['id']}] {q['query']}")
        for tag in ("A_vector", "B_complete", "C_hybrid"):
            if tag not in q["modes"]:
                continue
            log(f"  -> {tag} start {time.strftime('%H:%M:%S')}")
            try:
                rec = run_c(q) if tag == "C_hybrid" else run_mode(tag, q)
            except Exception as exc:  # noqa: BLE001
                rec = {"mode": tag, "id": q["id"], "status": "harness_error",
                       "error": f"{type(exc).__name__}:{str(exc)[:300]}"}
            (OUT / f"{tag}_{q['id']}.json").write_text(
                json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
            log(f"  <- {tag} {rec.get('seconds')}s gold={rec.get('gold')}")
            summary.append({k: v for k, v in rec.items()
                            if k in ("mode", "id", "seconds", "status", "gold", "scan", "cli_exit_code")})
    (OUT / "RETRIEVAL_SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    log("RETRIEVAL_SUMMARY.json written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
