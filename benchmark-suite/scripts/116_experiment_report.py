#!/usr/bin/env python3
"""实验报告生成 — 汇总 run 目录下所有工件为一份 REPORT.md + report.json。

只做汇整，**不做任何评价性改写**；数字一律来自落盘工件；没有的写"未测量"。

读取（存在即用）
  <run>/baselines.json        6 个 baseline 的逐题结果
  <run>/track_*.json          Agent 轨（a/a2/b/c）逐题结果
  <run>/qrels_scores.json     池化 IR 指标（114 产出）
  <run>/stats.json            显著性（115 产出）
  <run>/judge.json            L2 judge 结果 {rows:[{qid,method,correct,quality}]}
  <run>/run_manifest.json     provenance

用法（在 benchmark-suite/ 下）
    python scripts/116_experiment_report.py --run results/runs/run-2026...Z
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE / "scripts"))
from lib import resolve_run_dir  # noqa: E402


def _load(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _collect(run: Path) -> dict[str, list[dict]]:
    """→ {method: [row, ...]}"""
    by: dict[str, list[dict]] = defaultdict(list)
    b = _load(run / "baselines.json")
    if b:
        for r in b.get("rows", []):
            if r.get("method"):
                by[r["method"]].append(r)
    for f in sorted(run.glob("track_*.json")):
        d = _load(f)
        if isinstance(d, dict) and d.get("track"):
            by[d["track"]].append(d)
    return by


def _avg(rows: list[dict], key: str):
    vals = [r.get(key) for r in rows if isinstance(r.get(key), (int, float))]
    return round(sum(vals) / len(vals), 4) if vals else None


def build(run: Path) -> tuple[str, dict]:
    by = _collect(run)
    qrels = _load(run / "qrels_scores.json") or {}
    stats = _load(run / "stats.json") or {}
    judge = _load(run / "judge.json") or {}
    manifest = _load(run / "run_manifest.json") or {}

    jrows: dict[str, list[dict]] = defaultdict(list)
    for r in judge.get("rows", []):
        m = r.get("method") or r.get("track")
        if m:
            jrows[m].append(r)

    methods = sorted(set(by) | set(jrows) | set(qrels.get("per_method", {})))
    table = {}
    for m in methods:
        rows = by.get(m, [])
        qm = (qrels.get("per_method") or {}).get(m, {})
        jr = jrows.get(m, [])
        entry = {
            "n": len(rows) or qm.get("n"),
            "avg_latency_s": _avg(rows, "latency_s"),
            "avg_cost_usd": _avg(rows, "total_cost_usd"),
            "avg_tools": _avg(rows, "tool_call_count"),
            "tokens_out": sum((r.get("tokens") or {}).get("output") or 0 for r in rows) or None,
            "judge_acc": (round(sum(1 for r in jr if r.get("correct") in (1, True)) / len(jr), 3)
                          if jr else None),
            "judge_quality": (round(sum(r.get("quality", 0) for r in jr) / len(jr), 2)
                              if jr else None),
            "P@5": qm.get("P@5"), "R@10": qm.get("R@10"),
            "nDCG@10": qm.get("nDCG@10"), "MRR": qm.get("MRR"),
        }
        table[m] = entry

    L = [f"# 实验报告 — `{run.name}`", ""]
    prov = {k: manifest.get(k) for k in
            ("git_commit", "config_hash", "prompt_version", "seed", "max_turns",
             "tracks", "questions", "shuffled")}
    L += ["## Provenance", "",
          "| 项 | 值 |", "|---|---|"] + \
         [f"| {k} | `{v}` |" for k, v in prov.items() if v is not None] + [""]

    L += ["## 主表（方法 × 指标）", "",
          "| method | n | judge acc | quality | P@5 | R@10 | nDCG@10 | MRR | "
          "时延 s | 成本 $ | 工具数 |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for m in methods:
        e = table[m]
        def f(x, d="—"):
            return d if x is None else (f"{x}" if isinstance(x, int) else f"{x:.3f}"
                                        if isinstance(x, float) else str(x))
        L.append(f"| {m} | {f(e['n'],'—')} | {f(e['judge_acc'])} | "
                 f"{f(e['judge_quality'])} | {f(e['P@5'])} | {f(e['R@10'])} | "
                 f"{f(e['nDCG@10'])} | {f(e['MRR'])} | {f(e['avg_latency_s'])} | "
                 f"{f(e['avg_cost_usd'])} | {f(e['avg_tools'])} |")

    if qrels.get("by_stratum"):
        L += ["", "## 分层 nDCG@10", "", "| method | stratum | n | nDCG@10 |",
              "|---|---|---:|---:|"]
        for m, d in qrels["by_stratum"].items():
            for s, v in d.items():
                L.append(f"| {m} | {s} | {v['n']} | {v['nDCG@10']} |")

    if stats:
        L += ["", f"## 显著性（metric={stats.get('metric')}，ref=`{stats.get('ref')}`）", "",
              "| method | mean | sd | n | Δ vs ref | CI95 | p_holm | 显著 |",
              "|---|---:|---:|---:|---:|---|---:|:--:|"]
        for m, d in stats.get("descriptives", {}).items():
            c = stats.get("comparisons", {}).get(m, {})
            L.append(f"| {m} | {d['mean']} | {d['sd']} | {d['n']} | "
                     f"{c.get('mean_diff','—')} | {c.get('ci95','—')} | "
                     f"{c.get('p_holm','—')} | "
                     f"{'✅' if c.get('significant_0.05') else '—'} |")
        pw = stats.get("power", {})
        L += ["", f"> power: n={pw.get('n_pairs')} 配对，"
                  f"MDE(d)≈{pw.get('min_detectable_effect_d')} @80%。"]

    missing = [k for k, v in {
        "judge.json (L2 正确性)": judge,
        "qrels_scores.json (IR 指标)": qrels,
        "stats.json (显著性)": stats}.items() if not v]
    if missing:
        L += ["", "## 未测量项（如实标注）", ""] + [f"- {m}" for m in missing]

    L += ["", "---", "",
          "*数字均来自本 run 目录工件；缺项写“未测量”，未做任何评价性改写。*"]

    report = {"run": run.name, "provenance": prov, "table": table,
              "qrels_by_stratum": qrels.get("by_stratum"),
              "stats": stats or None, "missing": missing}
    return "\n".join(L), report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", default="REPORT.md")
    args = ap.parse_args()
    run = resolve_run_dir(args.run)
    if not run.exists():
        print(f"[report] 目录不存在: {run}")
        return 1
    md, payload = build(run)
    (run / args.out).write_text(md, encoding="utf-8")
    (run / "report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                                     encoding="utf-8")
    print(f"[report] → {run / args.out}")
    if payload["missing"]:
        print(f"[report] 未测量: {', '.join(payload['missing'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
