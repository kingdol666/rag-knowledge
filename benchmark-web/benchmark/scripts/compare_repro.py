"""Compare two benchmark eval JSON runs — reproducibility checker (read-only).

Usage: python scripts/compare_repro.py <run1.json> <run2.json> [--tol 0.0]

Deterministic metrics (p1/p5/mrr/ndcg5/routing/fpr/acc...) must match exactly
for a frozen corpus; latency_ms is allowed to drift (reports it separately).
Exit 0 = reproducible within tolerance.
"""
from __future__ import annotations

import json
import sys

METRIC_KEYS = {"p1", "p5", "mrr", "ndcg5", "routing", "fpr", "acc3", "acc2",
               "fpr_pct", "correct_precision", "correct_recall", "correct_f1",
               "n_eval", "n_excluded_no_corpus"}
LATENCY_KEYS = {"latency_ms", "elapsed_s"}


def flat(d: dict, prefix: str = "") -> dict:
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flat(v, key + "."))
        elif isinstance(v, list):
            out[key] = json.dumps(v, sort_keys=True, ensure_ascii=False)
        else:
            out[key] = v
    return out


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    tol = 0.0
    if "--tol" in sys.argv:
        tol = float(sys.argv[sys.argv.index("--tol") + 1])
    a = flat(json.load(open(sys.argv[1], encoding="utf-8")))
    b = flat(json.load(open(sys.argv[2], encoding="utf-8")))

    metric_diffs, latency_diffs, only_a, only_b = [], [], [], []
    for k in sorted(set(a) | set(b)):
        va, vb = a.get(k), b.get(k)
        if k.endswith("timestamp") or k in ("started", "generated_at"):
            continue  # wall-clock fields are expected to differ
        if va is None:
            only_b.append(k)
        elif vb is None:
            only_a.append(k)
        elif any(k.endswith(m) for m in METRIC_KEYS) or k in METRIC_KEYS:
            if va != vb:
                if isinstance(va, (int, float)) and isinstance(vb, (int, float)) \
                        and abs(float(va) - float(vb)) <= tol:
                    continue
                metric_diffs.append((k, va, vb))
        elif k in LATENCY_KEYS or "latency" in k:
            latency_diffs.append((k, va, vb))
        elif va != vb:
            metric_diffs.append((k, va, vb))

    print(f"comparing: {sys.argv[1]}  vs  {sys.argv[2]}  (tol={tol})")
    for k, va, vb in latency_diffs:
        print(f"  [latency drift, expected] {k}: {va} -> {vb}")
    for k, va, vb in metric_diffs:
        print(f"  [METRIC DIFF] {k}: {va} -> {vb}")
    for k in only_a:
        print(f"  [only in run1] {k} = {a[k]}")
    for k in only_b:
        print(f"  [only in run2] {k} = {b[k]}")

    ok = not metric_diffs and not only_a and not only_b
    print("VERDICT:", "REPRODUCIBLE (metrics identical; latency excluded)" if ok
          else f"DRIFT ({len(metric_diffs)} metric diffs)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
