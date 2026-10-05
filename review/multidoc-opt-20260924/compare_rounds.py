#!/usr/bin/env python3
"""Compare rounds: python compare_rounds.py round1 [round2 ...]
Recomputes gold tracking from raw transcripts (driver key bugs excluded) and
prints one table per round + a round-over-round delta for B/C modes."""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
GOLDS = {
    "T1": ["2310.10981"],
    "T2": ["2502.00306", "2402.12317", "2411.18583"],
    "T3": ["2508.05896"],
    "T4": ["2503.21676"],
    "T5": [],
}
MODES = ["A_vector", "B_complete", "C_hybrid"]


def gold_stats(rec: dict, golds: list[str]) -> dict:
    verdict = rec.get("verdict") or rec.get("judge") or {}
    rows = verdict.get("doc_scores") or []
    kept_paths = rec.get("kept_doc_paths") or rec.get("kept") or []
    out = {}
    for gid in golds:
        rows_g = [r for r in rows if gid in str(r.get("doc_path") or r.get("doc") or "")]
        best = max(rows_g, key=lambda r: float(r.get("judge_score") or r.get("score") or 0)) if rows_g else None
        out[gid] = {"judged": bool(rows_g),
                    "kept": any(r.get("kept") for r in rows_g),
                    "in_evidence": any(gid in str(p) for p in kept_paths),
                    "score": (best.get("judge_score") or best.get("score")) if best else None}
    return out


def round_table(round_dir: Path) -> list[dict]:
    rows = []
    for qid, golds in GOLDS.items():
        for mode in MODES:
            path = round_dir / f"{mode}_{qid}.json"
            if not path.exists():
                continue
            rec = json.loads(path.read_text(encoding="utf-8"))
            verdict = rec.get("verdict") or rec.get("judge") or {}
            g = gold_stats(rec, golds)
            kept_n = len(rec.get("kept_doc_paths") or rec.get("kept") or [])
            rows.append({"qid": qid, "mode": mode, "secs": rec.get("seconds") or rec.get("seconds_cli_wall"),
                         "status": rec.get("status"), "backend": verdict.get("backend"),
                         "real": verdict.get("real_engine"),
                         "judged_docs": len(verdict.get("doc_scores") or []),
                         "kept_docs": kept_n,
                         "golds": g,
                         "kept_summary": "/".join("K" if g2.get("kept") else ("j" if g2.get("judged") else "-")
                                                  for g2 in g.values())})
    return rows


def main() -> int:
    all_rows = {}
    for rn in sys.argv[1:]:
        rd = BASE / rn
        if not rd.is_dir():
            print(f"skip {rn}: no dir")
            continue
        rows = round_table(rd)
        all_rows[rn] = rows
        print(f"\n===== {rn} =====")
        print(f"{'q':4}{'mode':12}{'secs':>7}{'judged':>8}{'kept':>6}  golds(K=kept,j=judged-only,-=miss)  backend/real")
        for r in rows:
            print(f"{r['qid']:4}{r['mode']:12}{r['secs'] or 0:>7}{r['judged_docs']:>8}{r['kept_docs']:>6}  {r['kept_summary']:20}  {r.get('backend')}/{r.get('real')}")
    if len(all_rows) >= 2:
        rounds = list(all_rows)
        base, cur = all_rows[rounds[0]], all_rows[rounds[-1]]
        print(f"\n===== delta {rounds[0]} -> {rounds[-1]} (B/C gold kept) =====")
        bmap = {(r["qid"], r["mode"]): r for r in base}
        for r in cur:
            if r["mode"] == "A_vector":
                continue
            b = bmap.get((r["qid"], r["mode"]))
            if not b:
                continue
            gk_cur = sum(1 for g in r["golds"].values() if g.get("kept"))
            gk_base = sum(1 for g in b["golds"].values() if g.get("kept"))
            mark = "improved" if gk_cur > gk_base else ("regressed" if gk_cur < gk_base else "same")
            print(f"  {r['qid']} {r['mode']:11} golds_kept {gk_base} -> {gk_cur}  [{mark}]  secs {b['secs']} -> {r['secs']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
