#!/usr/bin/env python3
"""Three-mode retrieval + answer-source comparison with pre-registered gold.

Q1 gold : AI 基础设施/tracelens-deployment-notes.md
          facts: 采样率 7.3%（目标 7.5%）；p99 847ms -> 412ms（降 51.4%）
Q2 gold : AI 基础设施/vector-index-tuning-guide (part 1 of 2).md（第 5 节）
          facts: 增量占比 15% 触发全量重建；删除标记比例 25% 阈值
          (经验 exp-c2a2 也含两数字，属合法来源但非 gold 文档)

Every mode's answer must be synthesized STRICTLY from that mode's evidence pack.
"""
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

QUESTIONS = [
    {"id": "Q1",
     "query": "TraceLens 生产环境的 span 采样率和查询 p99 延迟分别是多少？相比旧系统降了多少？",
     "gold_path": "AI 基础设施/tracelens-deployment-notes.md",
     "gold_facts": ["采样率 7.3%", "p99 847ms → 412ms", "降幅 51.4%"],
     "extra": "tracelens trace 采样率 sampling 分布式追踪 可观测性 运维 p99 延迟"},
    {"id": "Q2",
     "query": "向量索引增量插入占比达到多少时应该触发全量重建？删除标记比例的阈值是多少？",
     "gold_path": "AI 基础设施/vector-index-tuning-guide (part 1 of 2).md",
     "gold_facts": ["增量 15% 触发全量重建", "删除标记 25% 阈值"],
     "extra": "向量索引 HNSW 增量重建 全量重建 删除标记 阈值"},
]
EXCLUDES = ("Corpus", "soul-", "e2e-", "Novel-")


def log(m):
    print(m, flush=True)


def norm(p):
    return str(p or "").replace("\\", "/")


def gold_status(rec, q):
    verdict = rec.get("verdict") or rec.get("judge") or {}
    rows = verdict.get("doc_scores") or []
    kept_paths = [norm(p) for p in (rec.get("kept_doc_paths") or rec.get("kept") or [])]
    gp = norm(q["gold_path"])
    rows_g = [r for r in rows if gp.lower() in norm(r.get("doc_path") or r.get("doc") or "").lower()]
    best = max((float(r.get("judge_score") or r.get("score") or 0) for r in rows_g), default=None)
    return {"judged": bool(rows_g), "kept": any(gp.lower() in p.lower() for p in kept_paths),
            "in_evidence": any(gp.lower() in p.lower() for p in kept_paths), "best": best,
            "kept_paths": kept_paths}


def run_a(q):
    import run_three_modes as h
    trace = {}
    t0 = time.time()
    res = h.mode_a(q["query"], trace, top_k_floor=5)
    return {"mode": "A_vector", "seconds": round(time.time() - t0, 1),
            "judge": {k: v for k, v in (trace.get("judge") or {}).items() if k != "doc_scores"},
            "gold": gold_status({"verdict": trace.get("judge"), "kept": res.get("kept")}, q),
            "kept_doc_paths": res.get("kept"), "evidence_pack": res.get("evidence_pack", "")}


def run_b(q):
    import run_three_modes as h
    trace = {}
    t0 = time.time()
    res = h.mode_b(q["query"], trace, extra_terms=tuple(q["extra"].split()),
                   top_k_floor=5, peek_heads=True, peek_limit=300)
    verdict = trace.get("judge") or {}
    rec = {"mode": "B_librarian", "seconds": round(time.time() - t0, 1),
           "judge": {k: v for k, v in verdict.items() if k != "doc_scores"},
           "gold": gold_status({"verdict": verdict, "kept": res.get("kept")}, q),
           "kept_doc_paths": res.get("kept"), "evidence_pack": res.get("evidence_pack", "")}
    rel = verdict.get("doc_scores") or []
    rec["gold_judge_rows"] = [(norm(r.get("doc") or r.get("doc_path")), r.get("judge_score"), r.get("kept"))
                              for r in rel if norm(q["gold_path"]).lower() in norm(r.get("doc") or r.get("doc_path") or "").lower()]
    return rec


def run_c(q):
    out = OUT / f"C_hybrid_{q['id']}.json"
    cmd = [sys.executable, str(HYBRID), "--query", q["query"], "--engine", "laya",
           "--doc-budget", "30", "--vector-top-k", "10", "--vector-threshold", "0.35",
           "--max-state-chars", "6000", "--peek-heads", "--top-k-floor", "5", "--lane-agreement",
           "--extra-terms", q["extra"]]
    for pref in EXCLUDES:
        cmd += ["--exclude-prefix", pref]
    cmd += ["--output", str(out), "--require-real"]
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=2400)
    rec = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"status": "error"}
    rec["cli_exit_code"] = proc.returncode
    rec["seconds"] = round(time.time() - t0, 1)
    rec["gold"] = gold_status(rec, q)
    return {k: rec.get(k) for k in ("mode", "status", "seconds", "real_engine", "cli_exit_code",
                                    "gold", "kept_doc_paths", "evidence_pack")} | {"mode": "C_hybrid"}


def main():
    for q in QUESTIONS:
        log(f"[{q['id']}] {q['query']}  gold={q['gold_path']}")
        for tag in ("A_vector", "B_librarian", "C_hybrid"):
            log(f"  -> {tag} start {time.strftime('%H:%M:%S')}")
            try:
                rec = {"A_vector": run_a, "B_librarian": run_b, "C_hybrid": run_c}[tag](q)
            except Exception as exc:  # noqa: BLE001
                rec = {"mode": tag, "status": "harness_error",
                       "error": f"{type(exc).__name__}:{str(exc)[:300]}"}
            rec["id"] = q["id"]
            (OUT / f"{tag}_{q['id']}.json").write_text(
                json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
            g = rec.get("gold") or {}
            log(f"  <- {tag} {rec.get('seconds')}s gold judged={g.get('judged')} "
                f"kept={g.get('kept')} evidence={g.get('in_evidence')} best={g.get('best')}")
    log("ALL DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
