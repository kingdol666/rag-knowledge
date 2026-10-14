#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exp 3 — abstention probes + cut-margin replay + judge-rank analysis.

Part A (machine level): 4 out-of-corpus queries through kb_search_vector and
kb_hybrid_search(judge on). The honesty contract predicts: few/no candidates,
all judge scores < 0.5, empty kept/reads.
Part B (offline replay): from the 16 logged 12-candidate judge score sets,
replay relative-cut margins (best-margin, top-5 floor) and report gold
retention + kept-set size per margin.
Part C (judge rank): per-run rank of the gold document(s) within the judged
candidate ordering.
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kbcommon import QUESTIONS, RESULTS, McpClient, norm_path

RES = RESULTS

OOD_QUERIES = [
    {"qid": "O1", "text": "锂离子电池热失控的处置步骤是什么？",
     "topic": "lithium battery thermal runaway"},
    {"qid": "O2", "text": "儿童疫苗接种时间表是怎样安排的？",
     "topic": "child vaccination schedule"},
    {"qid": "O3", "text": "Python 多进程和多线程的区别是什么？",
     "topic": "Python multiprocessing vs threading"},
    {"qid": "O4", "text": "注塑模具排气槽的设计规范是什么？",
     "topic": "injection mold vent design"},
]


def part_a(mc: McpClient) -> list[dict]:
    out = []
    for q in OOD_QUERIES:
        row = {"qid": q["qid"], "topic": q["topic"]}
        v = mc.call("kb_search_vector",
                    {"query": q["text"], "top_k": 10, "score_threshold": 0.0},
                    timeout=120)
        vs = [x["score"] for x in v.get("results", [])]
        row["vector_top_score"] = round(max(vs), 3) if vs else None
        row["vector_above_0.35"] = sum(1 for s in vs if s >= 0.35)
        h = mc.call("kb_hybrid_search",
                    {"query": q["text"], "candidate_cap": 12,
                     "enable_judge": True}, timeout=300)
        kept = (h.get("cut", {}) or {}).get("kept", []) or []
        reads = h.get("reads") or []
        row["merge_n"] = ((h.get("merge") or {}).get("merged"))
        row["kept_n"] = len(kept) if isinstance(kept, list) else kept
        row["kept_scores"] = [round(float(k.get("score") or 0), 3)
                              for k in kept] if isinstance(kept, list) else []
        row["reads_n"] = len(reads) if isinstance(reads, list) else reads
        row["elapsed_s"] = h.get("elapsed_s")
        out.append(row)
        print(f"[probe] {q['qid']} {q['topic']}: vector_top={row['vector_top_score']} "
              f">0.35:{row['vector_above_0.35']} kept={row['kept_n']} "
              f"reads={row['reads_n']}", flush=True)
    return out


def part_b(rows: list[dict]) -> dict:
    """Replay the relative cut (keep >= best-margin, top-5 floor) offline."""
    from kbcommon import QUESTIONS
    qg = {q["qid"]: q["gold_doc_substrings"] for q in QUESTIONS}
    margins = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35]
    stats = {m: {"gold_kept": 0, "gold_pool": 0, "kept_sizes": []}
             for m in margins}
    for r in rows:
        if r.get("method") != "qdcvr_hybrid" or "judge_scores" not in r:
            continue
        scores = sorted(r["judge_scores"]["all"].values(), reverse=True)
        if not scores:
            continue
        best = scores[0]
        golds = qg[r["qid"]]
        gold_scores = [s for p, s in r["judge_scores"]["all"].items()
                       if any(g.lower() in p.lower() for g in golds)]
        for m in margins:
            keep = [s for s in scores if s >= best - m]
            if len(keep) < 5:
                keep = scores[:5]
            stats[m]["kept_sizes"].append(len(keep))
            stats[m]["gold_pool"] += len(gold_scores)
            stats[m]["gold_kept"] += sum(1 for gs in gold_scores if gs >= best - m or gs in scores[:5])
    out = {}
    for m in margins:
        st = stats[m]
        out[m] = {"gold_kept": st["gold_kept"], "gold_pool": st["gold_pool"],
                  "mean_kept": round(statistics.mean(st["kept_sizes"]), 1)}
        print(f"[replay] margin {m:.2f}: gold kept "
              f"{st['gold_kept']}/{st['gold_pool']}, mean kept set "
              f"{out[m]['mean_kept']}", flush=True)
    return out


def part_c(rows: list[dict]) -> list[dict]:
    from kbcommon import QUESTIONS
    qg = {q["qid"]: q["gold_doc_substrings"] for q in QUESTIONS}
    out = []
    for r in rows:
        if r.get("method") != "qdcvr_hybrid" or "judge_scores" not in r:
            continue
        order = sorted(r["judge_scores"]["all"].items(),
                       key=lambda kv: -kv[1])
        golds = qg[r["qid"]]
        ranks = [i + 1 for i, (p, _) in enumerate(order)
                 if any(g.lower() in p.lower() for g in golds)]
        out.append({"qid": r["qid"], "n_cand": len(order), "gold_ranks": ranks})
        print(f"[rank] {r['qid']}: n={len(order)} gold_ranks={ranks}",
              flush=True)
    return out


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    mc = McpClient()
    print("== Part A: out-of-corpus abstention probes ==", flush=True)
    probes = part_a(mc)
    rows = json.loads((RES / "exp1_retrieval.json").read_text(
        encoding="utf-8"))["rows"]
    print("== Part B: cut-margin replay ==", flush=True)
    replay = part_b(rows)
    print("== Part C: gold rank within judged candidates ==", flush=True)
    ranks = part_c(rows)
    (RES / "exp3_abstention.json").write_text(json.dumps(
        {"probes": probes, "cut_replay": replay, "gold_ranks": ranks},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote results/exp3_abstention.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
