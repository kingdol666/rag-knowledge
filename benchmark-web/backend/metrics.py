"""Standard IR metrics for the benchmark comparison.

These are the textbook definitions, computed only when the caller supplies
ground truth. Without ground truth the API reports *observable* quantities
(latency, score distribution, inter-method overlap) and says so — it never
derives a precision figure from a similarity score, which would look like a
metric without being one.
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Sequence


def _ranked_ids(hits: Sequence, key: str = "doc_id") -> list[str]:
    """Pull the evaluated identity out of each hit, order preserved."""
    out = []
    for hit in hits:
        if isinstance(hit, dict):
            out.append(str(hit.get(key) or hit.get("chunk_id") or ""))
        else:
            out.append(str(getattr(hit, key, "") or getattr(hit, "chunk_id", "")))
    return out


def precision_at_k(ranked: Sequence[str], relevant: set[str], k: int) -> float:
    """Fraction of the top ``k`` results that are relevant."""
    if k <= 0 or not ranked:
        return 0.0
    top = ranked[:k]
    return sum(1 for item in top if item in relevant) / k


def recall_at_k(ranked: Sequence[str], relevant: set[str], k: int) -> float:
    """Fraction of all relevant items found within the top ``k``."""
    if not relevant:
        return 0.0
    top = ranked[:k]
    return sum(1 for item in top if item in relevant) / len(relevant)


def hit_at_k(ranked: Sequence[str], relevant: set[str], k: int) -> int:
    """1 when at least one relevant item appears in the top ``k``."""
    return int(any(item in relevant for item in ranked[:k]))


def reciprocal_rank(ranked: Sequence[str], relevant: set[str]) -> float:
    """1/rank of the first relevant hit (0 when there is none)."""
    for i, item in enumerate(ranked, start=1):
        if item in relevant:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked: Sequence[str], relevant: set[str], k: int) -> float:
    """Normalised discounted cumulative gain with binary relevance."""
    if not relevant or k <= 0:
        return 0.0
    dcg = sum(1.0 / math.log2(i + 1)
              for i, item in enumerate(ranked[:k], start=1) if item in relevant)
    ideal = sum(1.0 / math.log2(i + 1) for i in range(1, min(k, len(relevant)) + 1))
    return dcg / ideal if ideal else 0.0


def evaluate(hits: Sequence, relevant: Iterable[str], ks: Sequence[int] = (1, 3, 5, 10),
             key: str = "doc_id") -> dict[str, float]:
    """Compute the full metric set for one ranked list against ground truth."""
    relevant_set = {str(r) for r in relevant}
    ranked = _ranked_ids(hits, key)
    metrics: dict[str, float] = {}
    for k in ks:
        metrics[f"precision@{k}"] = round(precision_at_k(ranked, relevant_set, k), 4)
        metrics[f"recall@{k}"] = round(recall_at_k(ranked, relevant_set, k), 4)
        metrics[f"hit@{k}"] = float(hit_at_k(ranked, relevant_set, k))
    metrics["ndcg@10"] = round(ndcg_at_k(ranked, relevant_set, 10), 4)
    metrics["mrr"] = round(reciprocal_rank(ranked, relevant_set), 4)
    metrics["relevant_total"] = float(len(relevant_set))
    return metrics


def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    """Overlap of two result sets — how much two methods actually agree."""
    left, right = set(a), set(b)
    if not left and not right:
        return 1.0
    return round(len(left & right) / len(left | right), 4)


def score_summary(hits: Sequence) -> dict[str, float]:
    """Describe a score distribution without inventing a quality metric."""
    scores = [float(h["score"] if isinstance(h, dict) else h.score) for h in hits]
    if not scores:
        return {"count": 0, "mean_score": 0.0, "max_score": 0.0,
                "min_score": 0.0, "spread": 0.0}
    return {
        "count": len(scores),
        "mean_score": round(sum(scores) / len(scores), 4),
        "max_score": round(max(scores), 4),
        "min_score": round(min(scores), 4),
        "spread": round(max(scores) - min(scores), 4),
    }
