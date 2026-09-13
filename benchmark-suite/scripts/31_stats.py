#!/usr/bin/env python3
"""E2 · 配对统计显著性（修 TODO-7/F13/F14）.

对给定逐查询指标文件做方法间配对比较：
  - 每对比独立 bootstrap 95% CI（B=2000，配对重采样，percentile 法）→ per-comparison
  - Wilcoxon 符号秩（主检验，分布无关）+ 配对 t（对照）
  - Shapiro–Wilk 正态性检验（说明检验选择依据）
  - Holm–Bonferroni 多重校正（跨对比族），同时报告校正前后 p

用法: python scripts/31_stats.py <ablation_json> [more.json ...]
主对比: qdcvr_full vs 其余每个变体/方法；主指标: ndcg@10, recall@5, precision@5。
输出: results/run-*/stats_significance.json
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import numpy as np
from scipy import stats as sps

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import env_fingerprint, now_iso, set_run  # noqa: E402

METRICS = ("ndcg@10", "recall@5", "precision@5")
B = 2000
SEED = 0


def pick_ref(methods: list[str]) -> str:
    for cand in ("qdcvr_full", "qdcvr"):
        if cand in methods:
            return cand
    return methods[0]


def load_rows(path: Path) -> dict[str, dict[str, list]]:
    d = json.loads(path.read_text(encoding="utf-8"))
    rows = d["rows"]
    out: dict[str, dict[str, list]] = {}
    for method, per_q in rows.items():
        qids = [r["qid"] for r in per_q]
        out[method] = {m: [float(r[m]) for r in per_q] for m in METRICS}
        out[method]["__qids__"] = qids  # type: ignore[assignment]
    return out


def paired_bootstrap(x: list[float], y: list[float], b: int, rng: random.Random):
    diffs = [a - c for a, c in zip(x, y)]
    n = len(diffs)
    means = []
    for _ in range(b):
        s = [diffs[rng.randrange(n)] for _ in range(n)]
        means.append(sum(s) / n)
    means.sort()
    lo, hi = means[int(0.025 * b)], means[int(0.975 * b) - 1]
    return lo, hi


def holm(pvals: list[tuple[str, float]]) -> dict[str, float]:
    idx = sorted(range(len(pvals)), key=lambda i: pvals[i][1])
    m = len(pvals)
    out: dict[str, float] = {}
    prev = 0.0
    for rank, i in enumerate(idx):
        name, p = pvals[i]
        adj = min(max((m - rank) * p, prev), 1.0)
        out[name] = adj
        prev = adj
    return out


def main() -> int:
    outdir = set_run()
    files = [Path(a) for a in sys.argv[1:]] or sorted(
        Path(__file__).resolve().parent.parent.glob("results/run-*/ablation_scifact_1.json"))
    comparisons: list[dict] = []
    for f in files:
        data = load_rows(f)
        ref = pick_ref(list(data))
        methods = [m for m in data if m != ref]
        rng = random.Random(SEED)
        fam: list[tuple[str, float]] = []
        pending: list[dict] = []
        for m in methods:
            for metric in METRICS:
                a = data[ref][metric]
                b = data[m][metric]
                d = [x - y for x, y in zip(a, b)]
                if len(d) < 5:
                    continue
                sh = sps.shapiro(d)
                try:
                    w_stat, w_p = sps.wilcoxon(d)
                except ValueError:
                    w_stat, w_p = float("nan"), 1.0
                t_stat, t_p = sps.ttest_rel(a, b)
                sd = np.std(d, ddof=1)
                cohen_d = (np.mean(d) / sd) if sd > 0 else 0.0
                lo, hi = paired_bootstrap(a, b, B, rng)
                rec = {
                    "file": str(f), "comparison": f"{ref} vs {m}", "metric": metric,
                    "n": len(d), "mean_diff": round(float(np.mean(d)), 4),
                    "ci95_boot": [round(lo, 4), round(hi, 4)],
                    "wilcoxon_p": round(float(w_p), 5),
                    "paired_t_p": round(float(t_p), 5),
                    "cohen_d": round(float(cohen_d), 3),
                    "shapiro_p": round(float(sh.pvalue), 4),
                    "normal_at_0.05": bool(sh.pvalue > 0.05),
                }
                pending.append(rec)
                fam.append((f"{rec['comparison']}|{metric}", w_p))
        adj = holm(fam)
        for rec in pending:
            key = f"{rec['comparison']}|{rec['metric']}"
            rec["wilcoxon_p_holm"] = round(adj.get(key, float("nan")), 5)
            rec["significant_holm_0.05"] = bool(adj.get(key, 1.0) < 0.05)
            comparisons.append(rec)

    result = {"experiment": "E2 paired statistics (TODO-7/F13/F14)",
              "protocol": {"bootstrap_B": B, "seed": SEED, "primary_test":
                           "Wilcoxon signed-rank (distribution-free; n<=50)",
                           "multiplicity": "Holm-Bonferroni across all comparisons",
                           "normality": "Shapiro-Wilk on paired differences"},
              "comparisons": comparisons,
              "meta": {"generated": now_iso(), "env": env_fingerprint()}}
    out = outdir / "stats_significance.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"-> {out}")
    for c in comparisons:
        if c["metric"] == "ndcg@10":
            print(f"  {c['comparison']:26s} {c['metric']:12s} d={c['mean_diff']:+.4f} "
                  f"CI{c['ci95_boot']} p_w={c['wilcoxon_p']} "
                  f"p_holm={c['wilcoxon_p_holm']} sig={c['significant_holm_0.05']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
