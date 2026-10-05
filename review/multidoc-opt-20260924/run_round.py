#!/usr/bin/env python3
"""Multi-scenario three-mode retrieval test (A vector / B librarian / C hybrid CLI).

Usage: python run_round.py round1|round2
Questions are scenario-designed: T1 enumeration (instance criterion), T2 multi-doc
synthesis, T3 paraphrase (zero description overlap), T4 part-targeting, T5 not-in-library.
Same scripts as the skill layers: A/B via librarian harness flows (jev_filter engine=laya),
C via the knowledgebase-hybrid CLI exactly as a user invokes it.
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
ROUND = sys.argv[1] if len(sys.argv) > 1 else "round1"
OUT = OUT / ROUND
OUT.mkdir(parents=True, exist_ok=True)

QUESTIONS = [
    {"id": "T1", "scenario": "enumeration/instance",
     "query": "Which evaluation datasets and baseline methods does InstructDS compare against in its experiments?",
     "golds": ["2310.10981"]},
    {"id": "T2", "scenario": "multi-doc synthesis",
     "query": "What weaknesses or risks of retrieval-augmented generation does the library identify, and what improvements or defenses does it propose?",
     "golds": ["2502.00306", "2402.12317", "2411.18583"]},
    {"id": "T3", "scenario": "paraphrase zero-overlap",
     "query": "How should a farmer split planting area between decoy plants and the main crop to control insect pests without pesticides and keep the harvest high?",
     "golds": ["2508.05896"]},
    {"id": "T4", "scenario": "part targeting",
     "query": "Where does the library discuss hallucinations in the paper on how language models learn facts, and what does it say about when hallucinations start?",
     "golds": ["2503.21676"]},
    {"id": "T5", "scenario": "not-in-library",
     "query": "What does the library say about federated learning for privacy-preserving machine learning training?",
     "golds": []},
]
EXCLUDES = ["Corpus", "soul-", "e2e-", "Novel-"]

# Round 2 optimization stack: agent-supplied bilingual Phase-0 keywords (the
# query and the descriptions often live in different languages), head-peek
# scan over unpicked zero-overlap docs (no blind spot by construction), and a
# global top-K judge floor protecting question-critical mid-score docs.
ROUND2 = {
    "top_k_floor": 5,
    "peek_heads": True,
    "peek_limit": 300,
    "extra_terms": {
        "T1": "instructds instructive dialogue summarization evaluation datasets baselines experiments 对话摘要 数据集 实验 评估 基线",
        "T2": "rag retrieval-augmented generation 检索增强生成 weaknesses risks defenses membership inference privacy 幻觉 检索",
        "T3": "trap cropping 诱虫作物 pest 害虫 allocation 配比 yield 产量 insecticide 农药 decoy 诱捕 投资优化",
        "T4": "language models facts 语言模型 事实 hallucinations 幻觉 learning dynamics 学习动态 training",
        "T5": "federated learning 联邦学习 privacy-preserving 隐私 distributed training 分布式训练",
    },
}
CFG = ROUND2 if ROUND == "round2" else {}


def log(msg: str) -> None:
    print(msg, flush=True)


def gold_stats(result: dict, golds: list[str]) -> dict:
    verdict = result.get("verdict") or result.get("judge") or {}
    rows = verdict.get("doc_scores") or []
    # harness modes return {"kept": [...]}; hybrid returns {"kept_doc_paths": [...]}
    kept_paths = result.get("kept_doc_paths") or result.get("kept") or []
    out = {}
    for gid in golds:
        rows_g = [r for r in rows if gid in str(r.get("doc_path") or r.get("doc") or "")]
        best = max(rows_g, key=lambda r: float(r.get("judge_score") or r.get("score") or 0)) if rows_g else None
        out[gid] = {"judged": bool(rows_g),
                    "kept": any(r.get("kept") for r in rows_g),
                    "in_evidence": any(gid in str(p) for p in kept_paths),
                    "score": (best.get("judge_score") or best.get("score")) if best else None}
    out["_summary"] = {
        "golds_total": len(golds),
        "golds_judged": sum(1 for g in golds if out[g]["judged"]),
        "golds_kept": sum(1 for g in golds if out[g]["kept"]),
        "golds_in_evidence": sum(1 for g in golds if out[g]["in_evidence"]),
    }
    return out


def run_a(q: dict) -> dict:
    import run_three_modes as h
    trace: dict = {}
    t0 = time.time()
    res = h.mode_a(q["query"], trace, top_k_floor=CFG.get("top_k_floor", 0))
    return {"mode": "A_vector", "id": q["id"], "scenario": q["scenario"], "query": q["query"],
            "seconds": round(time.time() - t0, 1), "docs_read": len(trace.get("docs_read") or []),
            "judge": trace.get("judge"), "kept_doc_paths": res.get("kept"),
            "evidence_pack": res.get("evidence_pack"), "_gold": gold_stats(res, q["golds"])}


def run_b(q: dict) -> dict:
    import run_three_modes as h
    trace: dict = {}
    t0 = time.time()
    res = h.mode_b(q["query"], trace,
                   extra_terms=tuple(str(CFG.get("extra_terms", {}).get(q["id"], "")).split()),
                   top_k_floor=CFG.get("top_k_floor", 0), peek_heads=CFG.get("peek_heads", False),
                   peek_limit=CFG.get("peek_limit", 300))
    scan = {k: trace.get(k) for k in ("shelves_scanned", "descriptions_scanned",
                                      "description_overlap_docs", "stem_completion_docs",
                                      "zero_overlap_docs_unread", "docs_read",
                                      "peek_docs", "peek_seconds", "peek_empty")}
    return {"mode": "B_complete", "id": q["id"], "scenario": q["scenario"], "query": q["query"],
            "seconds": round(time.time() - t0, 1), "scan": scan,
            "judge": trace.get("judge"), "kept_doc_paths": res.get("kept"),
            "evidence_pack": res.get("evidence_pack"), "_gold": gold_stats(res, q["golds"])}


def run_c(q: dict) -> dict:
    out = OUT / f"C_hybrid_{q['id']}.json"
    cmd = [sys.executable, str(HYBRID), "--query", q["query"], "--engine", "laya",
           "--doc-budget", "30", "--vector-top-k", "10", "--vector-threshold", "0.35",
           "--max-state-chars", "6000"]
    for pref in EXCLUDES:
        cmd += ["--exclude-prefix", pref]
    cmd += ["--output", str(out), "--require-real"]
    if CFG:
        cmd += ["--top-k-floor", str(CFG["top_k_floor"]), "--peek-heads",
                "--peek-limit", str(CFG["peek_limit"]), "--lane-agreement"]
        et = str(CFG.get("extra_terms", {}).get(q["id"], "")).strip()
        if et:
            cmd += ["--extra-terms", et]
    log(f"  C subprocess start")
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=2400)
    wall = round(time.time() - t0, 1)
    result = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"status": "error"}
    result["cli_exit_code"] = proc.returncode
    result["seconds_cli_wall"] = wall
    result["mode"] = "C_hybrid"
    result["id"] = q["id"]
    result["scenario"] = q["scenario"]
    result["query"] = q["query"]
    result["_gold"] = gold_stats(result, q["golds"])
    return result


def main() -> int:
    summary = []
    for q in QUESTIONS:
        log(f"[{q['id']}/{q['scenario']}] {q['query'][:80]}")
        for runner, tag in ((run_a, "A_vector"), (run_b, "B_complete"), (run_c, "C_hybrid")):
            log(f"  -> {tag} start {time.strftime('%H:%M:%S')}")
            try:
                rec = runner(q)
            except Exception as exc:  # noqa: BLE001
                rec = {"mode": tag, "id": q["id"], "status": "harness_error",
                       "error": f"{type(exc).__name__}:{str(exc)[:300]}"}
            path = OUT / f"{tag}_{q['id']}.json"
            path.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
            gs = (rec.get("_gold") or {}).get("_summary") or {}
            log(f"  <- {tag} {rec.get('seconds', rec.get('seconds_cli_wall'))}s "
                f"golds_judged={gs.get('golds_judged')}/{gs.get('golds_total')} "
                f"kept={gs.get('golds_kept')} evidence={gs.get('golds_in_evidence')}")
            summary.append({k: v for k, v in rec.items()
                            if k in ("mode", "id", "scenario", "seconds", "seconds_cli_wall",
                                     "status", "cli_exit_code", "_gold", "scan")
                            or k in ("merge", "reread", "lanes")})
    (OUT / "SUMMARY.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    log("SUMMARY.json written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
