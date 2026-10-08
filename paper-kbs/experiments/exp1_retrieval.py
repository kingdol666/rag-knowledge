#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exp 1 — machine-level retrieval comparison on the production KBs.

Methods (all invoked through the platform's real interfaces):
  bm25          : in-process jieba+BM25Okapi over the 42 document full texts
                  (classic lexical baseline; index build time reported).
  dense         : MCP kb_search_vector (BGE-M3 dense retrieval).
  rrf           : reciprocal-rank fusion of the bm25 and dense rankings (k=60).
  graph         : MCP kb_graph_search (Neo4j keyword lookup over graph nodes).
  twostage      : MCP kb_search_two_stage (BM25+graph candidate pool -> dense refine).
  hybrid_nojudge: MCP kb_hybrid_search enable_judge=false (fusion + cut only).
  qdcvr_hybrid  : MCP kb_hybrid_search enable_judge=true (full QDCVR pipeline).

Output: results/exp1_retrieval.json + console table.
"""
from __future__ import annotations

import json
import math
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kbcommon import (QUESTIONS, RESULTS, McpClient, gold_hit, norm_path)

TOP_K = 5
RRF_K = 60
WARMUP_QUERY = "光伏组件层压工艺"


# ---------------------------------------------------------------- BM25 core
def tokenize(text: str) -> list[str]:
    import jieba
    return [t for t in jieba.lcut(text) if t.strip()]


class BM25Okapi:
    """Standard Okapi BM25 (k1=1.5, b=0.75), same formula as rank_bm25."""

    def __init__(self, corpus_tokens: list[list[str]], k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.N = len(corpus_tokens)
        self.avgdl = sum(len(c) for c in corpus_tokens) / max(self.N, 1)
        self.doc_len = [len(c) for c in corpus_tokens]
        self.tf = [{} for _ in corpus_tokens]
        df: dict[str, int] = {}
        for i, toks in enumerate(corpus_tokens):
            for t in toks:
                self.tf[i][t] = self.tf[i].get(t, 0) + 1
            for t in set(toks):
                df[t] = df.get(t, 0) + 1
        self.idf = {t: math.log(1 + (self.N - n + 0.5) / (n + 0.5))
                    for t, n in df.items()}

    def scores(self, query_tokens: list[str]) -> list[float]:
        out = []
        for i in range(self.N):
            s, dl = 0.0, self.doc_len[i]
            for t in query_tokens:
                f = self.tf[i].get(t, 0)
                if not f:
                    continue
                s += self.idf.get(t, 0) * f * (self.k1 + 1) / (
                    f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
            out.append(s)
        return out


def load_corpus(mc: McpClient) -> tuple[list[dict], float]:
    """Fetch all doc full texts via MCP kb_doc_read. Returns (docs, fetch_s)."""
    cache = RESULTS / "corpus_cache.json"
    if cache.exists():
        docs = json.loads(cache.read_text(encoding="utf-8"))
        return docs, 0.0
    cat = mc.call("kb_list", {"lightweight": True}, timeout=60)
    docs = []
    t0 = time.time()
    for kb in cat["catalog"]:
        d = mc.call("kb_get_documents",
                    {"kb_id": kb["kb_id"], "lightweight": True}, timeout=60)
        for row in d.get("catalog", []):
            rd = mc.call("kb_doc_read",
                         {"kb_id": kb["kb_id"], "doc_path": row["doc_path"],
                          "max_chars": 60000}, timeout=60)
            content = rd.get("content") or rd.get("text") or ""
            docs.append({"kb_id": kb["kb_id"], "kb_name": kb["name"],
                         "doc_path": norm_path(row["doc_path"]),
                         "name": row.get("name") or Path(row["doc_path"]).name,
                         "content": content})
    dt = round(time.time() - t0, 2)
    cache.write_text(json.dumps(docs, ensure_ascii=False), encoding="utf-8")
    return docs, dt


# ---------------------------------------------------------------- methods
def rank_bm25(bm25, docs, query):
    q = tokenize(query)
    scores = bm25.scores(q)
    order = sorted(range(len(docs)), key=lambda i: -scores[i])
    return [docs[i]["doc_path"] for i in order[:10]]


def rank_dense(mc, query):
    r = mc.call("kb_search_vector",
                {"query": query, "top_k": 10, "score_threshold": 0.0},
                timeout=120)
    seen, out = set(), []
    for x in r.get("results", []):
        p = norm_path(x["doc_path"])
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def rank_rrf(bm25_rank, dense_rank):
    scores: dict[str, float] = {}
    for rank_list in (bm25_rank, dense_rank):
        for i, p in enumerate(rank_list):
            scores[p] = scores.get(p, 0.0) + 1.0 / (RRF_K + i + 1)
    return [p for p, _ in sorted(scores.items(), key=lambda kv: -kv[1])][:10]


def rank_graph(mc, query):
    """kb_graph_search is a Cypher CONTAINS match on node name/path — call it
    once per distinctive jieba keyword and merge by best rank (a fair use of
    the tool as documented)."""
    import jieba.analyse
    kws = jieba.analyse.extract_tags(query, topK=3)
    best: dict[str, int] = {}
    for kw in kws:
        try:
            r = mc.call("kb_graph_search",
                        {"keyword": kw, "node_type": "all", "limit": 10},
                        timeout=60)
        except Exception:  # noqa: BLE001
            continue
        for i, d in enumerate(r.get("documents", []) or []):
            p = norm_path(d.get("doc_path") or d.get("path")
                          or d.get("name") or "")
            if p and (p not in best or i + 1 < best[p]):
                best[p] = i + 1
    return [p for p, _ in sorted(best.items(), key=lambda kv: kv[1])][:10]


def rank_twostage(mc, query):
    r = mc.call("kb_search_two_stage",
                {"query": query, "stage1_top_k": 20, "stage2_top_k": 5},
                timeout=120)
    seen, out = set(), []
    for x in (r.get("stage2", {}) or {}).get("results", []):
        p = norm_path(x.get("doc_path") or x.get("path") or "")
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return out


def rank_hybrid(mc, query, enable_judge: bool):
    """Returns (ranked_paths, judge_scores or None).

    enable_judge=False -> the server skips scoring, so cut.kept is empty;
    the fusion ranking (agreed-first, then vector top8, catalog top4) is
    reported by the server itself as merge.judged_candidates — that is the
    honest 'hybrid fusion without content verification' ranking.
    enable_judge=True  -> cut.kept is the judge-scored, relatively cut,
    re-ranked list; per-doc judge scores are captured for the inflation
    analysis.
    """
    r = mc.call("kb_hybrid_search",
                {"query": query, "candidate_cap": 12, "enable_judge": enable_judge},
                timeout=300)
    if enable_judge:
        kept = (r.get("cut", {}) or {}).get("kept", []) or []
        paths = [norm_path(k["doc_path"]) for k in kept]
        scores = {norm_path(k["doc_path"]): float(k.get("score") or 0)
                  for k in kept}
        return paths, scores
    cand = (r.get("merge", {}) or {}).get("judged_candidates", []) or []
    return [norm_path(p) for p in cand], None


METHODS = ["bm25", "dense", "rrf", "graph", "twostage",
           "fusion_only", "qdcvr_hybrid"]


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    mc = McpClient()
    print("[exp1] loading corpus via MCP ...", flush=True)
    docs, fetch_s = load_corpus(mc)
    print(f"[exp1] corpus: {len(docs)} docs, fetch {fetch_s}s", flush=True)
    t0 = time.time()
    bm25 = BM25Okapi([tokenize(d["content"]) for d in docs])
    bm25_build_s = round(time.time() - t0, 2)
    print(f"[exp1] BM25 index built in {bm25_build_s}s", flush=True)

    # warm-up calls (model load, resident worker, first-touch caches)
    rank_bm25(bm25, docs, WARMUP_QUERY)
    rank_dense(mc, WARMUP_QUERY)
    rank_graph(mc, WARMUP_QUERY)
    rank_twostage(mc, WARMUP_QUERY)
    rank_hybrid(mc, WARMUP_QUERY, enable_judge=False)
    rank_hybrid(mc, WARMUP_QUERY, enable_judge=True)
    print("[exp1] warm-up done", flush=True)

    rows = []
    for q in QUESTIONS:
        for method in METHODS:
            t0 = time.time()
            try:
                judge_scores = None
                if method == "bm25":
                    ranked = rank_bm25(bm25, docs, q["text"])
                elif method == "dense":
                    ranked = rank_dense(mc, q["text"])
                elif method == "rrf":
                    ranked = rank_rrf(rank_bm25(bm25, docs, q["text"]),
                                      rank_dense(mc, q["text"]))
                elif method == "graph":
                    ranked = rank_graph(mc, q["text"])
                elif method == "twostage":
                    ranked = rank_twostage(mc, q["text"])
                elif method == "fusion_only":
                    ranked, _ = rank_hybrid(mc, q["text"], enable_judge=False)
                else:
                    ranked, judge_scores = rank_hybrid(mc, q["text"],
                                                       enable_judge=True)
            except Exception as e:  # noqa: BLE001
                rows.append({"method": method, "qid": q["qid"],
                             "error": f"{type(e).__name__}: {str(e)[:200]}"})
                print(f"[exp1] {method} x {q['qid']} ERROR {e}", flush=True)
                continue
            lat = round(time.time() - t0, 3)
            hits, best = gold_hit(ranked, q["gold_doc_substrings"], TOP_K)
            n_gold = len(q["gold_doc_substrings"])
            row = {"method": method, "qid": q["qid"], "latency_s": lat,
                   "hit@5": hits > 0, "recall@5": hits / n_gold,
                   "best_rank": best,
                   "mrr": (1.0 / best) if best else 0.0,
                   "ranked_top5": ranked[:TOP_K],
                   "n_ranked": len(ranked)}
            if judge_scores is not None:
                gold_scores = [s for p, s in judge_scores.items()
                               if any(g.lower() in p.lower()
                                      for g in q["gold_doc_substrings"])]
                non_scores = [s for p, s in judge_scores.items()
                              if not any(g.lower() in p.lower()
                                         for g in q["gold_doc_substrings"])]
                row["judge_scores"] = {
                    "gold": gold_scores,
                    "nongold_mean": (round(sum(non_scores) / len(non_scores), 4)
                                     if non_scores else None),
                    "nongold_max": (round(max(non_scores), 4)
                                    if non_scores else None),
                    "all": judge_scores}
            rows.append(row)
            print(f"[exp1] {method:<14} {q['qid']} lat={lat:>6}s "
                  f"hit={hits>0} recall={row['recall@5']:.2f} rank={best}",
                  flush=True)
            (RESULTS / "exp1_retrieval.json").write_text(
                json.dumps({"corpus_docs": len(docs), "bm25_build_s": bm25_build_s,
                            "corpus_fetch_s": fetch_s, "rows": rows},
                           ensure_ascii=False, indent=1), encoding="utf-8")

    # summary
    print("\n=== Exp1 summary (mean over 8 questions) ===")
    summary = {}
    for m in METHODS:
        rs = [r for r in rows if r["method"] == m and "error" not in r]
        if not rs:
            continue
        summary[m] = {
            "hit@5": sum(r["hit@5"] for r in rs) / len(rs),
            "recall@5": sum(r["recall@5"] for r in rs) / len(rs),
            "mrr": sum(r["mrr"] for r in rs) / len(rs),
            "latency_mean": round(statistics.mean(r["latency_s"] for r in rs), 3),
            "latency_p50": round(statistics.median(r["latency_s"] for r in rs), 3),
        }
        s = summary[m]
        print(f"{m:<14} hit@5={s['hit@5']:.2f} recall@5={s['recall@5']:.2f} "
              f"mrr={s['mrr']:.3f} lat_mean={s['latency_mean']}s "
              f"lat_p50={s['latency_p50']}s")
    (RESULTS / "exp1_summary.json").write_text(
        json.dumps({"n_questions": len(QUESTIONS), "summary": summary,
                    "corpus_docs": len(docs), "bm25_build_s": bm25_build_s},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
