#!/usr/bin/env python3
"""Post-process the three-mode transcripts: recompute gold tracking (harness
verdicts use the "doc" key, hybrid judge uses "doc_path") and rebuild
SUMMARY.json. Also writes ANALYSIS.json with the cross-mode comparison."""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
GOLDS = {"q1": "2310.10981", "q2": "2212.13138", "q3": "2508.05896"}
MODES = ["A_vector", "B_complete", "C_hybrid"]


def gold_stats(path: Path, gold: str) -> dict:
    d = json.loads(path.read_text(encoding="utf-8"))
    verdict = d.get("verdict") or d.get("judge") or {}
    rows = [r for r in (verdict.get("doc_scores") or [])
            if gold in str(r.get("doc_path") or r.get("doc") or "")]
    kept_paths = d.get("kept_doc_paths") or []
    kept_rows = [r for r in rows if r.get("kept")]
    best = max(rows, key=lambda r: float(r.get("judge_score") or r.get("score") or 0)) if rows else None
    ranked = sorted(rows, key=lambda r: -float(r.get("judge_score") or r.get("score") or 0)) if rows else []
    out = {
        "gold_in_judged": bool(rows), "gold_kept": bool(kept_rows),
        "gold_score": (best.get("judge_score") or best.get("score")) if best else None,
        "gold_rank": (ranked.index(best) + 1) if best else None,
        "gold_parts": len(rows),
        "gold_parts_kept": len(kept_rows),
        "gold_in_evidence": any(gold in str(p) for p in kept_paths),
    }
    d["_gold"] = out
    path.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main() -> int:
    summary, analysis = [], []
    for qid, gold in GOLDS.items():
        for mode in MODES:
            path = OUT / f"{mode}_{qid}.json"
            if not path.exists():
                continue
            d = json.loads(path.read_text(encoding="utf-8"))
            g = gold_stats(path, gold)
            judge = d.get("verdict") or d.get("judge") or {}
            row = {"q": qid, "mode": mode,
                   "secs": d.get("seconds") or d.get("seconds_cli_wall"),
                   "status": d.get("status"), "cli_exit_code": d.get("cli_exit_code"),
                   "backend": judge.get("backend"), "real_engine": judge.get("real_engine"),
                   "engine": judge.get("engine"),
                   "relative_cut": judge.get("relative_cut"),
                   "global_best": judge.get("global_best"),
                   "total_judged": judge.get("total_judged") or len(judge.get("doc_scores") or []),
                   **g}
            summary.append(row)
            if mode == "C_hybrid":
                row["merge"] = d.get("merge")
                row["reread"] = {k: v for k, v in (d.get("reread") or {}).items()}
                row["lanes"] = d.get("lanes")
            analysis.append(row)
    (OUT / "SUMMARY.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
