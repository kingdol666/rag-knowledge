#!/usr/bin/env python3
"""池化标注 (qrels) + IR 指标 — P0-5 的修法。

没有 qrels 就算不出 P@k / R@k / nDCG@k / MRR。本脚本：
  1) --build : 把**所有方法**每题 top-10 结果取并集，生成标注池模板
               （3 名标注者 × graded relevance 0/1/2/3；未标注默认 0，TREC 假设）
  2) --score : 读回人工标注，按方法计算 P@5 / R@10 / nDCG@10 / MRR，
               并按题目层（stratum）分桶报数

用法（在 benchmark-suite/ 下）
    python scripts/114_pool_qrels.py --build --run results/runs/run-2026...Z
    python scripts/114_pool_qrels.py --score --run results/runs/run-2026...Z \
        --questions data/papers/qa_v2.json
    # 标注池模板：qrels_pool.json（doc → {ann1,ann2,ann3}，值 0/1/2/3 或 null）

gains: graded 0-3；binary 相关 = grade>=2。
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE / "scripts"))
sys.path.insert(0, str(SUITE / "experiments"))

from baselines import src_of  # noqa: E402
from lib import resolve_run_dir  # noqa: E402

TOP = 10
REL_THRESHOLD = 2
ANN = ("ann1", "ann2", "ann3")


def _ranked_from_track(track: dict) -> list[str]:
    """Agent 轨的轨迹里抽取被检索/读取的文档 id（保序去重）。"""
    out, seen = [], set()
    for call in (track.get("tool_calls") or []):
        inp = call.get("input") or {}
        for key in ("doc_path", "path", "file_path", "kb_id"):
            v = inp.get(key)
            if isinstance(v, str) and v.strip():
                s = src_of(v)
                if s not in seen:
                    seen.add(s)
                    out.append(s)
    return out[:TOP]


def _collect(inputs: list[Path]) -> dict[str, dict[str, list[str]]]:
    """→ {qid: {method: [src, ...]}}"""
    data: dict[str, dict[str, list[str]]] = {}
    for f in inputs:
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        rows = doc.get("rows")
        if isinstance(rows, list):                       # baselines.json
            for r in rows:
                if r.get("ranked"):
                    data.setdefault(r["qid"], {})[r["method"]] = r["ranked"][:TOP]
            continue
        if isinstance(doc.get("track"), str):            # track_*.json
            rk = _ranked_from_track(doc)
            if rk:
                data.setdefault(doc["qid"], {})[doc["track"]] = rk
    return data


def build(run: Path, inputs: list[Path], out: str) -> None:
    data = _collect(inputs)
    pool: dict[str, dict[str, dict]] = {}
    for qid, by_method in sorted(data.items()):
        docs: list[str] = []
        for lst in by_method.values():
            for d in lst:
                if d and d not in docs:
                    docs.append(d)
        pool[qid] = {d: {a: None for a in ANN} for d in docs}
    dest = run / out
    dest.write_text(json.dumps(pool, ensure_ascii=False, indent=1), encoding="utf-8")
    sizes = [len(v) for v in pool.values()]
    print(f"[pool] {len(pool)} 题 · 池大小 min={min(sizes) if sizes else 0} "
          f"max={max(sizes) if sizes else 0} avg={sum(sizes)/max(1,len(sizes)):.1f}")
    print(f"[pool] 模板 → {dest}")
    print("下一步：3 名标注者对池内每个 doc 打 graded 0/1/2/3（未标注默认 0），"
          "再跑 --score。")


def _grade(labels: dict, doc: str) -> int:
    vals = [labels.get(doc, {}).get(a) for a in ANN]
    vals = [v for v in vals if isinstance(v, (int, float))]
    return round(sum(vals) / len(vals)) if vals else 0


def _dcg(gains: list[int]) -> float:
    return sum((2 ** g - 1) / math.log2(i + 2) for i, g in enumerate(gains))


def score(run: Path, pool: dict, data: dict, qstrat: dict, out: str) -> None:
    methods = sorted({m for bm in data.values() for m in bm})
    rows = []
    for qid, by_method in data.items():
        labels = pool.get(qid, {})
        for m, ranked in by_method.items():
            gains = [_grade(labels, d) for d in ranked[:TOP]]
            rel = [1 if g >= REL_THRESHOLD else 0 for g in gains]
            n_rel_pool = sum(1 for d in labels if _grade(labels, d) >= REL_THRESHOLD)
            p5 = sum(rel[:5]) / 5.0
            r10 = (sum(rel[:10]) / n_rel_pool) if n_rel_pool else 0.0
            ideal = sorted((_grade(labels, d) for d in labels), reverse=True)[:TOP]
            idcg = _dcg(ideal) or 1.0
            ndcg = _dcg(gains) / idcg
            mrr = next((1.0 / (i + 1) for i, r in enumerate(rel) if r), 0.0)
            rows.append({"qid": qid, "method": m, "stratum": qstrat.get(qid, "single"),
                         "P@5": round(p5, 4), "R@10": round(r10, 4),
                         "nDCG@10": round(ndcg, 4), "MRR": round(mrr, 4),
                         "n_rel_pool": n_rel_pool})

    agg = {}
    for m in methods:
        sub = [r for r in rows if r["method"] == m]
        if not sub:
            continue
        agg[m] = {k: round(sum(r[k] for r in sub) / len(sub), 4)
                  for k in ("P@5", "R@10", "nDCG@10", "MRR")}
        agg[m]["n"] = len(sub)
    by_stratum: dict[str, dict] = {}
    for m in methods:
        for s in sorted({r["stratum"] for r in rows if r["method"] == m}):
            sub = [r for r in rows if r["method"] == m and r["stratum"] == s]
            by_stratum.setdefault(m, {})[s] = {
                "n": len(sub),
                "nDCG@10": round(sum(r["nDCG@10"] for r in sub) / len(sub), 4)}

    payload = {"run": run.name, "top": TOP, "rel_threshold": REL_THRESHOLD,
               "per_method": agg, "by_stratum": by_stratum, "rows": rows}
    (run / out).write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                           encoding="utf-8")

    lines = ["# 池化 qrels IR 指标", "", f"Run: `{run.name}` · top={TOP} · "
             f"相关阈值 grade≥{REL_THRESHOLD}", "",
             "| method | n | P@5 | R@10 | nDCG@10 | MRR |",
             "|---|---:|---:|---:|---:|---:|"]
    for m in methods:
        g = agg.get(m)
        if g:
            lines.append(f"| {m} | {g['n']} | {g['P@5']} | {g['R@10']} | "
                         f"{g['nDCG@10']} | {g['MRR']} |")
    lines += ["", "## 分层 nDCG@10", "", "| method | stratum | n | nDCG@10 |",
              "|---|---|---:|---:|"]
    for m, d in by_stratum.items():
        for s, v in d.items():
            lines.append(f"| {m} | {s} | {v['n']} | {v['nDCG@10']} |")
    (run / out.replace(".json", ".md")).write_text("\n".join(lines), encoding="utf-8")
    print(f"[qrels] → {run / out}")
    for m in methods:
        if m in agg:
            g = agg[m]
            print(f"  {m:8} P@5={g['P@5']:.3f} R@10={g['R@10']:.3f} "
                  f"nDCG@10={g['nDCG@10']:.3f} MRR={g['MRR']:.3f}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="results/runs/<run_id> 目录")
    ap.add_argument("--inputs", default="",
                    help="逗号分隔的输入 JSON；默认读 run 目录下 baselines.json + track_*.json")
    ap.add_argument("--questions", default="", help="题集（取 stratum）")
    ap.add_argument("--pool", default="qrels_pool.json")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--out", default="qrels_scores.json")
    args = ap.parse_args()

    run = resolve_run_dir(args.run)
    if args.inputs:
        inputs = [(SUITE / p) if not Path(p).is_absolute() else Path(p)
                  for p in args.inputs.split(",") if p.strip()]
    else:
        inputs = ([run / "baselines.json"] if (run / "baselines.json").exists() else []) + \
                 sorted(run.glob("track_*.json"))

    if args.build:
        build(run, inputs, args.pool)
        return 0
    if args.score:
        pool = json.loads((run / args.pool).read_text(encoding="utf-8"))
        data = _collect(inputs)
        qstrat = {}
        if args.questions:
            raw = json.loads((SUITE / args.questions).read_text(encoding="utf-8"))
            qstrat = {q["qid"]: q.get("stratum", "single")
                      for q in raw.get("questions", [])}
        score(run, pool, data, qstrat, args.out)
        return 0
    ap.error("指定 --build 或 --score")


if __name__ == "__main__":
    sys.exit(main())
