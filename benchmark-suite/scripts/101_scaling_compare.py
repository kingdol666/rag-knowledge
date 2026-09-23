#!/usr/bin/env python3
"""扩展性实验对照报告 — 汇总 results/scaling/ 下多快照 JSON, 产出对照表与结论.

判定(固定题集 old50/bq10 上, 主通道 vec):
  - 精度保持: pass_rate 变化在 ±5pp 内 → "文档翻倍未降低检索精度"
  - 精度提升: t1 pass_rate > t0 且 hit3/mrr 不降 → 支持用户假设
  - 精度退化: t1 pass_rate < t0 - 5pp → 需要披露并定位
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
SC = SUITE / "results" / "scaling"
TAGS = ["t0", "t05", "t1"]
SETS = ["old50", "bq10", "new50"]


def main() -> int:
    rows = []
    for tag in TAGS:
        for s in SETS:
            f = SC / f"scaling_{tag}_{s}.json"
            if not f.exists():
                continue
            d = json.loads(f.read_text(encoding="utf-8"))
            for ch in ("vec", "ts"):
                rows.append({"tag": tag, "set": s, "channel": ch,
                             "n": d["n"],
                             **{k: d[ch][k] for k in
                                ("pass", "pass_rate", "hit1", "hit3",
                                 "hit5", "mrr", "mean_top1_score")}})
    if not rows:
        print("no snapshots yet")
        return 1
    print(f"{'tag':5s} {'set':6s} {'ch':4s} {'pass':>7s} {'hit1':>6s} "
          f"{'hit3':>6s} {'hit5':>6s} {'mrr':>6s} {'top1':>6s}")
    for r in rows:
        print(f"{r['tag']:5s} {r['set']:6s} {r['channel']:4s} "
              f"{str(r['pass']) + '/' + str(r['n']):>7s} {r['hit1']:>6.2f} "
              f"{r['hit3']:>6.2f} {r['hit5']:>6.2f} {r['mrr']:>6.3f} "
              f"{r['mean_top1_score']:>6.3f}")

    def get(tag, s, ch, k):
        return next((r[k] for r in rows
                     if r["tag"] == tag and r["set"] == s and r["channel"] == ch), None)

    print("\n==== 结论(主通道 vec, 固定题集) ====")
    verdict = {}
    for s in ("old50", "bq10"):
        t0, t1 = get("t0", s, "vec", "pass_rate"), get("t1", s, "vec", "pass_rate")
        m0, m1 = get("t0", s, "vec", "mrr"), get("t1", s, "vec", "mrr")
        if t0 is None or t1 is None:
            continue
        delta = round((t1 - t0) * 100, 1)
        if abs(delta) <= 5:
            v = "保持(±5pp 内)"
        elif delta > 0:
            v = "提升"
        else:
            v = "退化(超 5pp, 需定位)"
        verdict[s] = {"t0": t0, "t1": t1, "delta_pp": delta,
                      "mrr_t0": m0, "mrr_t1": m1, "verdict": v}
        print(f"{s}: t0={t0} t1={t1} ({delta:+.1f}pp) mrr {m0}->{m1} → {v}")
    t05 = get("t05", "old50", "vec", "pass_rate")
    t0 = get("t0", "old50", "vec", "pass_rate")
    if t05 is not None and t0 is not None:
        print(f"纯语料翻倍效应(t0→t05, 未整理): "
              f"{t0}→{t05} ({round((t05-t0)*100,1):+.1f}pp)")
    (SUITE / "results" / "scaling" / "compare.json").write_text(
        json.dumps({"rows": rows, "verdict": verdict}, ensure_ascii=False,
                   indent=1), encoding="utf-8")
    print("\nsaved → results/scaling/compare.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
