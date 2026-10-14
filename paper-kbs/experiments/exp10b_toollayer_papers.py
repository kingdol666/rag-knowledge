#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exp 10b — tool layer on the second corpus (10 English arXiv gold papers).

Run AFTER exp10_ingest_papers.py. Reruns the tool-layer comparison on a
domain-shifted corpus: the ten benchmark-suite gold questions, gold = the
question's own paper (gold_hit on the arXiv id in the document path).
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kbcommon import RESULTS, McpClient, gold_hit, norm_path  # noqa: E402
from exp1_retrieval import (BM25Okapi, load_corpus, rank_bm25, rank_dense,
                            rank_graph, rank_hybrid, rank_rrf,
                            rank_twostage, tokenize)  # noqa: E402

RRF_K = 60
TOP_K = 5


def main() -> int:
    qs = json.loads((RESULTS.parents[2] / "benchmark-suite" / "data"
                     / "papers" / "qa_questions.json").read_text(
        encoding="utf-8"))["questions"]
    state = json.loads((RESULTS / "exp10_ingest_state.json").read_text(
        encoding="utf-8"))
    kb_id = state["kb_id"]
    mc = McpClient()

    # corpus = only the second-corpus KB's documents (fresh fetch, no cache)
    cat = mc.call("kb_list", {"lightweight": True}, timeout=60)
    docs = []
    for kb in cat["catalog"]:
        if kb["kb_id"] != kb_id:
            continue
        d = mc.call("kb_get_documents",
                    {"kb_id": kb_id, "lightweight": True}, timeout=120)
        for row_ in d.get("catalog", []):
            rd = mc.call("kb_doc_read",
                         {"kb_id": kb_id, "doc_path": row_["doc_path"],
                          "max_chars": 60000}, timeout=120)
            content = rd.get("content") or rd.get("text") or ""
            docs.append({"kb_id": kb_id,
                         "kb_name": kb.get("name"),
                         "doc_path": norm_path(row_["doc_path"]),
                         "name": row_.get("name") or Path(row_["doc_path"]).name,
                         "content": content})
    print(f"second-corpus docs: {len(docs)}", flush=True)
    bm25 = BM25Okapi([tokenize(d["content"]) for d in docs])

    rows = []
    for q in qs:
        text = q["question"]
        gold_sub = [q["arxiv_id"]]
        t0 = time.time()
        bm25_rank = rank_bm25(bm25, docs, text)
        dense_rank = rank_dense(mc, text)
        rrf_rank = rank_rrf(bm25_rank, dense_rank)
        graph_rank = rank_graph(mc, text)
        twostage_rank = rank_twostage(mc, text)
        lat = round(time.time() - t0, 3)
        fusion_rank, _ = rank_hybrid(mc, text, enable_judge=False)
        judged_rank, jscores = rank_hybrid(mc, text, enable_judge=True)
        lat_h = round(time.time() - t0 - lat, 3)
        judged_order = sorted(jscores, key=lambda p: -jscores[p]) if jscores else []
        filter_order = [p for p in fusion_rank if p in jscores] if jscores else []
        row = {"qid": q["qid"], "paper": q["paper"], "latency_s": lat,
               "hybrid_latency_s": lat_h,
               "n_candidates": len(fusion_rank),
               "n_kept": len(jscores or {})}
        for name, ranked in (("bm25", bm25_rank), ("dense", dense_rank),
                             ("rrf", rrf_rank), ("graph", graph_rank),
                             ("twostage", twostage_rank),
                             ("fusion_only", fusion_rank),
                             ("judged", judged_order),
                             ("filter_only", filter_order)):
            hits, best = gold_hit(ranked, gold_sub, TOP_K)
            row[name] = {"hit": hits > 0, "best_rank": best}
        rows.append(row)
        print(f"[exp10b] {q['qid']} {q['paper'][:28]}: bm25={row['bm25']['hit']} "
              f"dense={row['dense']['hit']} judged={row['judged']['hit']} "
              f"filter={row['filter_only']['hit']} "
              f"fusion={row['fusion_only']['hit']}", flush=True)

    summary = {}
    for name in ("bm25", "dense", "rrf", "graph", "twostage",
                 "fusion_only", "judged", "filter_only"):
        summary[name] = {
            "hit@5": sum(r[name]["hit"] for r in rows) / len(rows)}
        print(f"{name:<12} hit@5={summary[name]['hit@5']:.2f}")
    out = RESULTS / "exp10_papers_toollayer.json"
    out.write_text(json.dumps({"kb_id": kb_id, "n_docs": len(docs),
                               "rows": rows, "summary": summary},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
