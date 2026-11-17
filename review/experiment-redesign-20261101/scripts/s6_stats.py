# -*- coding: utf-8 -*-
"""Stage 6 — gold-only 指标聚合 + 按 qid 配对统计检验。

gold containment 只使用非拒答题；OOD 探针只统计证据门拒绝候选，不代表最终回答拒答。
置信区间为 Wilson 95% CI。
McNemar 按 qid 对齐，不能依赖各臂 trace 的数组顺序。

注意：本脚本只修正统计口径，不会检查各实验臂的检索语料范围是否一致。
用法: python s6_stats.py traces.json [--baseline-arm A0]
"""
import json
import sys
from pathlib import Path


def wilson_ci(hits, n, z=1.959963984540054):
    """Wilson score interval for a binomial proportion."""
    if n <= 0:
        return None, None
    p = hits / n
    z2 = z * z
    den = 1 + z2 / n
    center = (p + z2 / (2 * n)) / den
    half = z * ((p * (1 - p) / n + z2 / (4 * n * n)) ** 0.5) / den
    return max(0.0, center - half), min(1.0, center + half)


def mcnemar(paired_a, paired_b):
    """按相同 qid 配对的精确双侧 McNemar 检验。"""
    if set(paired_a) != set(paired_b):
        raise ValueError("paired arms must contain the same qid set")
    qids = sorted(paired_a)
    b_only = sum(1 for qid in qids if (not paired_a[qid]) and paired_b[qid])
    a_only = sum(1 for qid in qids if paired_a[qid] and (not paired_b[qid]))
    n = a_only + b_only
    if n == 0:
        return a_only, b_only, 1.0
    from math import comb
    p = sum(comb(n, k) for k in range(0, min(a_only, b_only) + 1)) / (2 ** n) * 2
    return a_only, b_only, min(1.0, p)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    traces = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    base = "A0"
    if "--baseline-arm" in sys.argv:
        base = sys.argv[sys.argv.index("--baseline-arm") + 1]
    rows = {}
    gold_by_arm = {}
    for arm, lst in traces.items():
        gold_rows = [x for x in lst if not x.get("is_refusal", False)]
        probe_rows = [x for x in lst if x.get("is_refusal", False)]
        if len({x.get("qid") for x in gold_rows}) != len(gold_rows):
            raise ValueError(f"duplicate gold qid in arm {arm}")
        gold_by_arm[arm] = {x["qid"]: bool(x.get("gold_hit")) for x in gold_rows}
        gold_hits = sum(gold_by_arm[arm].values())
        glo, ghi = wilson_ci(gold_hits, len(gold_rows))

        # These traces record evidence-gate outcomes, not generated answers.
        gate_evaluable = arm in ("A0", "A1b", "A3", "A0f", "A0h", "PD")
        gate_rejections = (sum(bool(x.get("refusal_ok")) for x in probe_rows)
                           if gate_evaluable else None)
        gate_n = len(probe_rows) if gate_evaluable else None
        rlo, rhi = wilson_ci(gate_rejections, gate_n) if gate_evaluable else (None, None)

        bytesv = [x.get("bytes_ingested", 0) for x in gold_rows]
        tool = [x.get("tool_seconds", 0) for x in gold_rows]
        dig = [x.get("llm_digest_seconds", 0) for x in gold_rows]
        rows[arm] = dict(
            n_total=len(lst),
            n_gold=len(gold_rows),
            gold_hits=gold_hits,
            gold_rate=round(gold_hits / len(gold_rows), 6) if gold_rows else None,
            gold_ci95=[round(glo, 6), round(ghi, 6)] if glo is not None else None,
            n_probe=len(probe_rows),
            gate_rejections=gate_rejections,
            gate_rejection_rate=round(gate_rejections / gate_n, 6) if gate_n else None,
            gate_rejection_ci95=[round(rlo, 6), round(rhi, 6)] if rlo is not None else None,
            gate_evaluable=gate_evaluable,
            avg_bytes_gold=round(sum(bytesv) / len(bytesv)) if bytesv else None,
            avg_tool_s_gold=round(sum(tool) / len(tool), 1) if tool else None,
            avg_digest_s_gold=round(sum(dig) / len(dig), 1) if dig else None)

    print(f"{'arm':14s} {'gold n':>6s} {'hits':>6s} {'gold':>8s} {'Wilson 95% CI':>22s} "
          f"{'gate reject':>12s} {'bytes/q':>10s} {'tool_s':>8s}")
    for arm, r in rows.items():
        ci = f"[{r['gold_ci95'][0]:.3f},{r['gold_ci95'][1]:.3f}]" if r["gold_ci95"] else "-"
        rejected = (f"{r['gate_rejections']}/{r['n_probe']}" if r["gate_evaluable"] else "n/a")
        print(f"{arm:14s} {r['n_gold']:6d} {r['gold_hits']:6d} {r['gold_rate']:8.3f} "
              f"{ci:>22s} {rejected:>12s} {str(r['avg_bytes_gold']):>10s} "
              f"{str(r['avg_tool_s_gold']):>8s}")

    paired_tests = {}
    if base in traces:
        print(f"\n按 qid 配对的精确 McNemar（gold_hit，vs {base}）：")
        for arm in traces:
            if arm == base:
                continue
            a_only, b_only, p = mcnemar(gold_by_arm[base], gold_by_arm[arm])
            paired_tests[arm] = dict(base_only=a_only, arm_only=b_only, p_exact_two_sided=p)
            star = " *" if p < 0.05 else ""
            print(f"  {base} vs {arm:12s} base_only={a_only} arm_only={b_only} p={p:.4f}{star}")

    out = Path(sys.argv[1]).with_name("s6_stats.json")
    out.write_text(json.dumps(dict(per_arm=rows, paired_mcnemar_vs_baseline=paired_tests,
                                   metric_note="Gold containment is a retrieval proxy, not answer correctness.",
                                   ood_probe_note="Gate rejection counts are retrieval-stage outcomes, not final-answer abstentions; A1 and A2 have no applicable gate outcome.",
                                   scope_note="A1b/A2 are the final 2026-11-10 scoped-union re-runs (per-KB directed search merged by score); A0f/A0h/PD are the 2026-11-11 content-layer optimization arms (full-window judge; A0h adds a chunk-window union; PD drops navigation). New-arm traces were pollution-audited (top1/survivors all within the ten MD语料-* eval KBs, zero route-card leakage) before promotion."),
                              ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
