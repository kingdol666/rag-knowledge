#!/usr/bin/env python3
r"""164_paper_claims_probe.py —— 为改写 sec4 正文论断取数（只读）。

回答四个问题：
  1) 三轨延迟的 min/median/max（替换论文的「116/48/41 s」与「±35 s 方差」）
  2) 成本是否真的分得开（A vs B 的逐题配对差 + t 检验）
  3) 本轮究竟是那一题把关键词判丢的（替换「B 轨 cathodes 复数」这个例子）
  4) 一题内 A 轨的工具调用构成（说明平台为什么更贵：多步阅读）
"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
RESULTS = SUITE / "results"
LABEL = {"a2": "A", "b": "B", "c": "C"}


def main() -> int:
    rep = json.loads((RESULTS / "paper_report.json").read_text(encoding="utf-8"))
    print(f"run {rep['meta']['run_id']} · 题集 {rep['meta'].get('qfile')}")
    rows = []
    for qid, blob in rep["per_question"].items():
        for c in blob["cells"]:
            rows.append({**c, "qid": qid})

    print("\n[1] 延迟分布（s）")
    for t in ("a2", "b", "c"):
        xs = sorted(float(r["latency_s"]) for r in rows if r["track"] == t)
        print(f"  {LABEL[t]}: min {xs[0]:.1f} · median {st.median(xs):.1f} · "
              f"mean {st.mean(xs):.1f} · max {xs[-1]:.1f} · "
              f"p90 {xs[int(0.9 * (len(xs) - 1))]:.1f}")

    print("\n[2] 成本（$/题，逐题配对）")
    by = {t: {r["qid"]: float(r["cost_usd"]) for r in rows if r["track"] == t}
          for t in ("a2", "b", "c")}
    for t in ("a2", "b", "c"):
        xs = sorted(by[t].values())
        print(f"  {LABEL[t]}: mean ${st.mean(xs):.4f} · median ${st.median(xs):.4f} · "
              f"min ${xs[0]:.3f} · max ${xs[-1]:.3f} · 合计 ${sum(xs):.3f}")
    d = [by["a2"][q] - by["b"][q] for q in by["a2"]]
    n = len(d)
    md = st.mean(d)
    sd = st.stdev(d) if n > 1 else 0.0
    se = sd / (n ** 0.5) if n else 0.0
    t_stat = md / se if se else float("inf")
    print(f"  配对差 A-B: mean ${md:+.4f} · sd ${sd:.4f} · t {t_stat:+.2f} "
          f"(df {n - 1}) · A 更贵的题数 {sum(1 for x in d if x > 0)}/{n}")

    print("\n[3] 关键词判丢的题（word-boundary 保守判分）")
    for r in rows:
        kt, kh = r.get("kw_total"), r.get("kw_hits")
        if kt and kh is not None and kh < kt:
            miss = [k for k in (r.get("kw_list") or []) if k not in (r.get("kw_found") or [])]
            print(f"  {LABEL[r['track']]}/{r['qid']}: {kh}/{kt} · 命中 {r.get('kw_found')} · "
                  f"未命中 {miss or r.get('kw_list')}")
    hits = {r["qid"]: r for r in rows if r["track"] == "b"}
    print("  B 轨 BQ08 明细:", json.dumps(
        {k: hits["BQ08"].get(k) for k in ("kw_total", "kw_hits", "kw_list", "kw_found")},
        ensure_ascii=False))

    print("\n[4] 一题内工具构成（样例：A 轨最贵/最便宜各一题）")
    tdir = None
    for p in (RESULTS / "runs").glob("run-*"):
        if p.name == rep["meta"]["run_id"]:
            tdir = p
    if tdir:
        a2 = {r["qid"]: float(r["cost_usd"]) for r in rows if r["track"] == "a2"}
        for qid in (max(a2, key=a2.get), min(a2, key=a2.get)):
            f = tdir / f"track_a2_{qid}.json"
            if not f.exists():
                continue
            cell = json.loads(f.read_text(encoding="utf-8"))
            names = [str(t.get("name") or t.get("tool") or "?")
                     for t in (cell.get("tool_calls") or [])]
            print(f"  A/{qid} ${a2[qid]:.3f} · {len(names)} 次调用: {names}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
