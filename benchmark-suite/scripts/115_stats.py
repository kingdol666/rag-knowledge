#!/usr/bin/env python3
"""统计显著性 — P1-6 / TODO-20 的修法（纯 python，无 scipy 依赖）。

做四件事：
  1) 每方法 n / mean / SD（跨 run 聚合）
  2) 逐题配对 → Wilcoxon signed-rank（含并列校正 + 连续性校正）
  3) Holm 多重比较校正
  4) bootstrap 95% CI（配对均值差）+ 效应量（rank-biserial r）+ power statement

输入（二选一）
  --runs d1,d2,...   每个目录下读 --file（默认 judge.json），
                     期望 {"rows":[{"qid","method","correct"|"quality",...}]}
  --input rows.json  直接给 {"rows":[{"qid","method","run","value"}]}

用法（在 benchmark-suite/ 下）
    python scripts/115_stats.py --runs results/runs/run-A,results/runs/run-B \
        --metric correct --ref bm25 --out stats.json
    python scripts/115_stats.py --input results/runs/run-A/rows.json --ref rerank
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
Z = 1.959963984540054   # 1.96
Z_POWER = 0.8416212335729143  # 0.84 (80% power)


def _phi(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _rankdata(xs: list[float]) -> list[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def wilcoxon(diffs: list[float]) -> tuple[float, float, float]:
    """→ (W+, p, rank_biserial_r)。零差被丢弃（标准做法）。"""
    d = [x for x in diffs if x != 0]
    n = len(d)
    if n == 0:
        return 0.0, 1.0, 0.0
    ranks = _rankdata([abs(x) for x in d])
    wp = sum(r for r, x in zip(ranks, d) if x > 0)
    wm = sum(r for r, x in zip(ranks, d) if x < 0)
    mu = n * (n + 1) / 4.0
    tie = sum(t ** 3 - t for t in Counter(abs(x) for x in d).values())
    var = n * (n + 1) * (2 * n + 1) / 24.0 - tie / 48.0
    if var <= 0:
        return wp, 1.0, (wp - wm) / (wp + wm) if (wp + wm) else 0.0
    sigma = math.sqrt(var)
    z = (wp - mu)
    z -= 0.5 * (1 if z > 0 else -1)          # continuity correction
    z /= sigma
    p = 2 * (1 - _phi(abs(z)))
    r = (wp - wm) / (wp + wm) if (wp + wm) else 0.0
    return wp, min(1.0, p), r


def bootstrap_ci(diffs: list[float], n_boot: int = 5000,
                 seed: int = 0) -> tuple[float, float]:
    if not diffs:
        return 0.0, 0.0
    rnd = random.Random(seed)
    n = len(diffs)
    means = []
    for _ in range(n_boot):
        s = sum(diffs[rnd.randrange(n)] for _ in range(n)) / n
        means.append(s)
    means.sort()
    lo = means[int(0.025 * n_boot)]
    hi = means[int(0.975 * n_boot)]
    return round(lo, 4), round(hi, 4)


def holm(pvals: dict[str, float]) -> dict[str, float]:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    adj, running = {}, 0.0
    for i, (k, p) in enumerate(items):
        val = min(1.0, (m - i) * p)
        running = max(running, val)
        adj[k] = round(running, 5)
    return adj


def _load_rows(args) -> list[dict]:
    rows: list[dict] = []
    if args.input:
        doc = json.loads((SUITE / args.input).read_text(encoding="utf-8"))
        return doc["rows"]
    for d in args.runs.split(","):
        d = d.strip()
        if not d:
            continue
        p = Path(d)
        p = p if p.is_absolute() else SUITE / d
        f = p / args.file
        if not f.exists():
            print(f"[warn] 缺少 {f}，跳过")
            continue
        doc = json.loads(f.read_text(encoding="utf-8"))
        rid = doc.get("run_id") or p.name
        for r in doc.get("rows", []):
            v = r.get(args.metric)
            if v is None:
                continue
            rows.append({"qid": r.get("qid"), "method": r.get("method") or r.get("track"),
                         "run": rid, "value": float(v)})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="", help="逗号分隔的 run 目录")
    ap.add_argument("--input", default="", help="预构建 rows.json")
    ap.add_argument("--file", default="judge.json")
    ap.add_argument("--metric", default="correct")
    ap.add_argument("--ref", default="", help="参照方法（默认取均值最高者）")
    ap.add_argument("--out", default="stats.json")
    args = ap.parse_args()

    rows = _load_rows(args)
    if not rows:
        print("[stats] 没有可用数据")
        return 1

    # 每题每方法先跨 run 求均值 → 再配对比较
    per_q: dict[tuple, list[float]] = defaultdict(list)
    for r in rows:
        per_q[(r["qid"], r["method"])].append(r["value"])
    qmean: dict[tuple, float] = {k: sum(v) / len(v) for k, v in per_q.items()}

    methods = sorted({m for _, m in qmean})
    desc = {}
    for m in methods:
        vals = [v for (q, mm), v in qmean.items() if mm == m]
        mu = sum(vals) / len(vals) if vals else 0.0
        sd = (math.sqrt(sum((x - mu) ** 2 for x in vals) / (len(vals) - 1))
              if len(vals) > 1 else 0.0)
        desc[m] = {"n": len(vals), "mean": round(mu, 4), "sd": round(sd, 4)}

    ref = args.ref or max(desc, key=lambda m: desc[m]["mean"])
    qids = sorted({q for q, _ in qmean})
    comparisons = {}
    pvals = {}
    for m in methods:
        if m == ref:
            continue
        diffs = [qmean[(q, m)] - qmean[(q, ref)] for q in qids
                 if (q, m) in qmean and (q, ref) in qmean]
        w, p, r = wilcoxon(diffs)
        lo, hi = bootstrap_ci(diffs)
        mean_diff = sum(diffs) / len(diffs) if diffs else 0.0
        comparisons[m] = {"vs": ref, "n_pairs": len(diffs),
                          "mean_diff": round(mean_diff, 4),
                          "median_diff": round(sorted(diffs)[len(diffs)//2], 4) if diffs else 0.0,
                          "wilcoxon_W": round(w, 2), "p_raw": round(p, 5),
                          "ci95": [lo, hi], "rank_biserial_r": round(r, 3)}
        pvals[m] = p
    adj = holm(pvals) if pvals else {}
    for m, a in adj.items():
        comparisons[m]["p_holm"] = a
        comparisons[m]["significant_0.05"] = bool(a < 0.05)

    # power statement: n 对配对下，80% power 能检出的最小标准化效应
    n_pairs = len(qids)
    mde = (Z + Z_POWER) / math.sqrt(n_pairs) if n_pairs else None

    out = {"metric": args.metric, "ref": ref, "n_questions": n_pairs,
           "n_runs": len({r["run"] for r in rows}),
           "descriptives": desc, "comparisons": comparisons,
           "power": {"n_pairs": n_pairs,
                     "min_detectable_effect_d": round(mde, 3) if mde else None,
                     "alpha": 0.05, "power": 0.8,
                     "note": "配对 Wilcoxon；MDE 为标准化效应量近似"}}
    (SUITE / "results" / args.out).write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"[stats] ref={ref} · n_questions={n_pairs} · "
          f"n_runs={out['n_runs']}")
    for m in methods:
        d = desc[m]
        print(f"  {m:8} mean={d['mean']:.3f} sd={d['sd']:.3f} n={d['n']}")
    for m, c in comparisons.items():
        print(f"  {m:8} vs {ref}: Δ={c['mean_diff']:+.3f} "
              f"CI95={c['ci95']} p_holm={c.get('p_holm')} "
              f"r={c['rank_biserial_r']}")
    if mde:
        print(f"  power: n={n_pairs} pairs → MDE(d)≈{mde:.2f} @80% power")
    return 0


if __name__ == "__main__":
    sys.exit(main())
