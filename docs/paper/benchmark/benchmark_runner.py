#!/usr/bin/env python3
"""
QDCVR Benchmark Execution Framework — CIKM 2027
================================================
Executes all 18 experiments from SYSTEM-BENCHMARK-PLAN.md v6.0.
Outputs: JSON results, LaTeX tables, PNG figures.

Usage: python benchmark_runner.py [--exp EXP_NUM] [--all]
"""
from __future__ import annotations

import json
import time
import os
import sys
import math
import statistics
from pathlib import Path
from datetime import datetime, timezone
from typing import Any
from dataclasses import dataclass, field, asdict
from collections import defaultdict

import requests
import numpy as np

# ── Configuration ──────────────────────────────────────────────────────────
BACKEND_URL = os.environ.get("RAG_BACKEND_URL", "http://localhost:8765")
API_PREFIX = "/api/v1"
BENCHMARK_ROOT = Path(__file__).resolve().parent if "__file__" in dir() else Path("docs/paper/benchmark")
RESULTS_DIR = BENCHMARK_ROOT / "results"
DATASETS_DIR = BENCHMARK_ROOT / "datasets"
QRELS_DIR = BENCHMARK_ROOT / "qrels"
FIGURES_DIR = BENCHMARK_ROOT / "figures"
TABLES_DIR = BENCHMARK_ROOT / "paper-tables"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
DATASETS_DIR.mkdir(parents=True, exist_ok=True)
QRELS_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
TABLES_DIR.mkdir(parents=True, exist_ok=True)

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)


# ── API Client ─────────────────────────────────────────────────────────────
class QDCVRClient:
    """Thin HTTP wrapper over the backend API + MCP tool call simulation."""

    def __init__(self, base_url: str = BACKEND_URL):
        self.base = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.timeout = (10, 60)

    def _get(self, path: str, **params) -> dict:
        r = self.session.get(f"{self.base}{API_PREFIX}{path}", params=params)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, json_data: dict = None) -> dict:
        r = self.session.post(f"{self.base}{API_PREFIX}{path}", json=json_data or {})
        r.raise_for_status()
        return r.json()

    def health(self) -> dict:
        return self._get("/health")

    # KB operations
    def kb_list(self, lightweight: bool = False) -> list:
        return self._get("/kb/list", lightweight=lightweight)

    def kb_get_documents(self, kb_id: str) -> list:
        return self._get(f"/kb/{kb_id}/documents")

    # Search
    def search_vector(self, query: str, kb_id: str = "", top_k: int = 5,
                      score_threshold: float = 0.0, balance_kbs: bool = False) -> dict:
        return self._post("/search/vector", {
            "query": query, "kb_id": kb_id, "top_k": top_k,
            "score_threshold": score_threshold, "balance_kbs": balance_kbs,
        })

    def search_two_stage(self, query: str, kb_id: str = "", top_k: int = 5,
                         balance_kbs: bool = False, verify_content: bool = True) -> dict:
        return self._post("/search/two-stage", {
            "query": query, "kb_id": kb_id, "top_k": top_k,
            "balance_kbs": balance_kbs, "verify_content": verify_content,
        })

    # Graph
    def graph_cross_kb_documents(self, min_kbs: int = 2, limit: int = 50) -> dict:
        return self._get("/graph/cross-kb-documents", min_kbs=min_kbs, limit=limit)

    def graph_stats(self) -> dict:
        return self._get("/graph/stats")


# ── Metrics ─────────────────────────────────────────────────────────────────
@dataclass
class RetrievalMetrics:
    """All standard IR metrics for one method on one query set."""
    p_at_1: float = 0.0
    p_at_3: float = 0.0
    p_at_5: float = 0.0
    r_at_5: float = 0.0
    ndcg_at_5: float = 0.0
    mrr: float = 0.0
    map_score: float = 0.0
    fpr: float = 0.0
    candidates: int = 0
    latency_ms: float = 0.0
    n_queries: int = 0


def compute_metrics(results: list[dict], ground_truths: list[set], total_candidates: int = 0) -> RetrievalMetrics:
    """
    results: list of {doc_id, score, kb_id} per query
    ground_truths: list of set of relevant doc_ids per query
    """
    n = len(results)
    if n == 0:
        return RetrievalMetrics()

    p1s, p3s, p5s, r5s, ndcgs, mrrs, aps, fprs, lats, cands = [], [], [], [], [], [], [], [], [], []

    for i in range(n):
        res = results[i]
        gt = ground_truths[i]
        top_k = res.get("results", [])[:5]
        k = len(top_k)

        # Precision
        hits_at_k = [1 if r.get("doc_id") in gt or r.get("doc_path", "") in gt else 0 for r in top_k]
        p1s.append(hits_at_k[0] if k >= 1 else 0)
        p3s.append(sum(hits_at_k[:min(3, k)]) / min(3, k) if k > 0 else 0)
        p5s.append(sum(hits_at_k) / k if k > 0 else 0)

        # Recall@5
        r5s.append(len([h for h in hits_at_k if h]) / max(len(gt), 1))

        # nDCG@5
        dcg = sum(h / math.log2(i + 2) for i, h in enumerate(hits_at_k[:5]))
        idcg = sum(1 / math.log2(i + 2) for i in range(min(len(gt), 5)))
        ndcgs.append(dcg / idcg if idcg > 0 else 0)

        # MRR
        rr = 0.0
        for rank, h in enumerate(hits_at_k[:5]):
            if h:
                rr = 1.0 / (rank + 1)
                break
        mrrs.append(rr)

        # MAP
        ap = 0.0
        num_hits = 0
        for rank, h in enumerate(hits_at_k[:5]):
            if h:
                num_hits += 1
                ap += num_hits / (rank + 1)
        aps.append(ap / max(len(gt), 1))

        # FPR (domain mismatch)
        correct_kb = res.get("correct_kb", "")
        wrong_domains = sum(1 for r in top_k if r.get("kb_id", "") != correct_kb)
        fprs.append(wrong_domains / k if k > 0 else 0.0)

        # Latency
        lats.append(res.get("latency_ms", 0))
        cands.append(total_candidates if total_candidates else res.get("candidates", 0))

    return RetrievalMetrics(
        p_at_1=statistics.mean(p1s),
        p_at_3=statistics.mean(p3s),
        p_at_5=statistics.mean(p5s),
        r_at_5=statistics.mean(r5s),
        ndcg_at_5=statistics.mean(ndcgs),
        mrr=statistics.mean(mrrs),
        map_score=statistics.mean(aps),
        fpr=statistics.mean(fprs),
        candidates=int(statistics.mean(cands)) if cands else 0,
        latency_ms=statistics.mean(lats),
        n_queries=n,
    )


def paired_ttest(values_a: list[float], values_b: list[float]) -> dict:
    """Paired t-test between two methods' per-query scores."""
    from scipy import stats as scipy_stats
    t_stat, p_val = scipy_stats.ttest_rel(values_a, values_b)
    d = (statistics.mean(values_a) - statistics.mean(values_b)) / max(
        math.sqrt((statistics.variance(values_a) + statistics.variance(values_b)) / 2), 1e-10
    )
    return {"t_statistic": float(t_stat), "p_value": float(p_val), "cohens_d": float(d)}


def bootstrap_ci(values: list[float], n_boot: int = 10000, alpha: float = 0.05) -> tuple:
    """Bootstrap 95% CI for mean."""
    means = []
    n = len(values)
    for _ in range(n_boot):
        sample = np.random.choice(values, size=n, replace=True)
        means.append(float(np.mean(sample)))
    return float(np.percentile(means, 100 * alpha / 2)), float(np.percentile(means, 100 * (1 - alpha / 2)))


# ── Result Saving ───────────────────────────────────────────────────────────
def save_result(exp_name: str, data: dict) -> Path:
    path = RESULTS_DIR / f"{exp_name}.json"
    data["_timestamp"] = datetime.now(timezone.utc).isoformat()
    data["_exp_name"] = exp_name
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str))
    print(f"  ✓ Saved {path.name}")
    return path


# ── Latex Table Generators ──────────────────────────────────────────────────
def latex_table(data: list[dict], columns: list[str], caption: str, label: str) -> str:
    """Generate a LaTeX table from metric data."""
    header = " & ".join(columns)
    rows = []
    for row in data:
        vals = []
        for col in columns:
            v = row.get(col, row.get(col.lower(), "—"))
            if isinstance(v, float):
                vals.append(f"{v:.3f}")
            else:
                vals.append(str(v))
        rows.append(" & ".join(vals))
    body = " \\\\\n    ".join(rows)
    return f"""\\begin{{table}}[ht]
\\centering
\\caption{{{caption}}}
\\label{{{label}}}
\\begin{{tabular}}{{{'c' * len(columns)}}}
\\toprule
{header} \\\\
\\midrule
{body} \\\\
\\bottomrule
\\end{{tabular}}
\\end{{table}}
"""


print("✅ Benchmark framework initialized.")
print(f"   Backend: {BACKEND_URL}")
print(f"   Results: {RESULTS_DIR}")
print(f"   Datasets: {DATASETS_DIR}")