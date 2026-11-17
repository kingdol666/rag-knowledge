# -*- coding: utf-8 -*-
"""S6d — R3 复现轮对比审计（R3 replication_bench vs final_bench 逐题配对）。

产出（写入 replication dir）:
  s6d_compare.json   逐臂对比 + 翻转清单 + 跨 run McNemar + 污染审计 + 回贴验证
  s6d_compare.md     人读汇总
用法:
  python scripts/s6d_compare_runs.py \
    --new artifacts/replication_bench_20261112 \
    --old artifacts/final_bench
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
EXP = BASE.parent
Z = 1.959963984540054

ARMS = ["A0", "A0f", "A0h", "PD", "A1b", "A2", "A3", "A1-readall"]
EVAL_PREFIX = "MD语料-"


def wilson(k, n):
    if n == 0:
        return None, None, None
    p = k / n
    denom = 1 + Z * Z / n
    center = p + Z * Z / (2 * n)
    half = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n))
    return p, (center - half) / denom, (center + half) / denom


def mcnemar_exact(b, c):
    """qid 配对精确双侧 McNemar（b,c = 不一致对计数）。"""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(0, k + 1)) / (2 ** (n - 1)) * (2 if k * 2 != n else 1)
    return min(1.0, p)


def load_traces(traces_path):
    d = json.loads(Path(traces_path).read_text(encoding="utf-8"))
    arms = {}
    for arm, rows in d.items():
        arms[arm] = {r["qid"]: r for r in rows}
    return arms


def find_trace_file(d: Path):
    if (d / "s4_traces_r3.json").exists():
        return d / "s4_traces_r3.json"
    if (d / "s4_traces_final.json").exists():
        return d / "s4_traces_final.json"
    cands = sorted(d.glob("s4_traces_*.json"))
    return cands[-1] if cands else None


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--new", required=True)
    ap.add_argument("--old", required=True)
    args = ap.parse_args()
    NEW, OLD = Path(args.new), Path(args.old)

    new_tr = load_traces(find_trace_file(NEW))
    old_tr = load_traces(find_trace_file(OLD))

    report = {"per_arm": {}, "audit": {}, "verdict_inputs": {}}
    md = ["# R3 复现对比（replication_bench_20261112 vs final_bench）", ""]

    audit = {"qid_unique": {}, "n_rows": {}, "route_card_leak": {}, "scoped_candidates": {},
             "gold_hit_paste_check": {}, "route_correct": {}}

    for arm in ARMS:
        n_rows = old_tr.get(arm) or {}
        w_rows = new_tr.get(arm) or {}
        if not n_rows and not w_rows:
            continue
        gold_qs = {qid: r for qid, r in n_rows.items() if not r.get("is_refusal")}
        common = sorted(set(gold_qs) & {q for q, r in w_rows.items() if not r.get("is_refusal")})
        old_hits = sum(1 for q in common if n_rows[q].get("gold_hit"))
        new_hits = sum(1 for q in common if w_rows[q].get("gold_hit"))
        n = len(common)
        po, lo, hi = wilson(old_hits, n)
        pn, ln, hn = wilson(new_hits, n)
        if n == 0 or lo is None or ln is None:
            report["per_arm"][arm] = {"n_paired": 0, "note": "no common gold rows"}
            continue
        agree = sum(1 for q in common if bool(n_rows[q].get("gold_hit")) == bool(w_rows[q].get("gold_hit")))
        flips = [{"qid": q, "old": bool(n_rows[q].get("gold_hit")), "new": bool(w_rows[q].get("gold_hit")),
                  "old_top1": n_rows[q].get("top1", ""), "new_top1": w_rows[q].get("top1", "")}
                 for q in common if bool(n_rows[q].get("gold_hit")) != bool(w_rows[q].get("gold_hit"))]
        b = sum(1 for q in common if n_rows[q].get("gold_hit") and not w_rows[q].get("gold_hit"))
        c = sum(1 for q in common if not n_rows[q].get("gold_hit") and w_rows[q].get("gold_hit"))
        p_cross = mcnemar_exact(b, c)
        ci_overlap = bool(lo <= hn and ln <= hi)
        report["per_arm"][arm] = {
            "n_paired": n, "old_hits": old_hits, "new_hits": new_hits,
            "old_rate": round(po, 4), "new_rate": round(pn, 4),
            "old_ci": [round(lo, 4), round(hi, 4)], "new_ci": [round(ln, 4), round(hn, 4)],
            "ci_overlap": ci_overlap, "delta_pp": round((pn - po) * 100, 1),
            "agree": agree, "agree_rate": round(agree / n, 4) if n else None,
            "flips": flips, "discordant": {"old1_new0": b, "old0_new1": c},
            "mcnemar_cross_run_p": round(p_cross, 6),
        }
        # 审计字段
        audit["qid_unique"][arm] = (len(n_rows) == len(set(n_rows)) and len(w_rows) == len(set(w_rows)))
        audit["n_rows"][arm] = {"old": len(n_rows), "new": len(w_rows)}
        leaks_old = [r.get("top1", "") for r in n_rows.values() if "路由目录卡" in str(r.get("top1", ""))] + \
                    [s for r in n_rows.values() for s in (r.get("survivors") or []) if "路由目录卡" in str(s)]
        leaks_new = [r.get("top1", "") for r in w_rows.values() if "路由目录卡" in str(r.get("top1", ""))] + \
                    [s for r in w_rows.values() for s in (r.get("survivors") or []) if "路由目录卡" in str(s)]
        audit["route_card_leak"][arm] = {"old": leaks_old[:3], "new": leaks_new[:3]}
        if arm in ("A1b", "A2", "PD"):
            # 候选范围审计：新 trace 的 top1 应属十评测库
            bad = [r.get("top1", "") for r in w_rows.values()
                   if r.get("top1") and not str(r.get("top1")).startswith(EVAL_PREFIX)]
            audit["scoped_candidates"][arm] = {"new_top1_out_of_scope": bad[:5], "n_bad": len(bad)}
        if arm in ("A0", "A0f", "A0h", "A3"):
            rc_o = sum(1 for r in n_rows.values() if r.get("route_correct") is True)
            rc_n = sum(1 for r in w_rows.values() if r.get("route_correct") is True)
            audit["route_correct"][arm] = {"old": rc_o, "new": rc_n}

    # responses 金标回贴验证（新 run 有 capture 时）
    resp_files = sorted(NEW.glob("s4_responses_*.json"))
    paste = {}
    for rf in resp_files:
        rd = json.loads(rf.read_text(encoding="utf-8"))
        for arm, rows in rd.items():
            ok = bad = 0
            bad_qids = []
            for qid, row in rows.items():
                if row.get("gold_hit") and row.get("gold_evidence"):
                    if row.get("gold_evidence") in (row.get("response_text") or ""):
                        ok += 1
                    else:
                        bad += 1
                        bad_qids.append(qid)
            paste[arm] = {"gold_hit_rows": ok + bad, "paste_ok": ok, "paste_fail": bad,
                          "fail_qids": bad_qids[:6]}
    audit["gold_hit_paste_check"] = paste

    # 拒答探针（is_refusal 行）
    probe = {}
    for arm in ARMS:
        po_rows = {qid: r for qid, r in (old_tr.get(arm) or {}).items() if r.get("is_refusal")}
        pn_rows = {qid: r for qid, r in (new_tr.get(arm) or {}).items() if r.get("is_refusal")}
        if po_rows or pn_rows:
            probe[arm] = {
                "old_refusal_ok": sum(1 for r in po_rows.values() if r.get("refusal_ok") is True),
                "old_n": len(po_rows),
                "new_refusal_ok": sum(1 for r in pn_rows.values() if r.get("refusal_ok") is True),
                "new_n": len(pn_rows),
            }
    report["refusal_probes"] = probe

    report["audit"] = {k: v for k, v in audit.items() if v}
    (NEW / "s6d_compare.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    # 人读 MD
    md.append("| 臂 | 旧(gold/n) | 新(gold/n) | Δpp | 旧 95%CI | 新 95%CI | CI 重叠 | 逐题一致率 | 翻转(旧1→新0/旧0→新1) | 跨run McNemar p |")
    md.append("|---|---|---|---:|---|---|---|---:|---|---:|")
    for arm, v in report["per_arm"].items():
        if "note" in v:
            md.append(f"| {arm} | — | — | — | — | — | — | — | — | — | ({v['note']}) |")
            continue
        md.append(
            f"| {arm} | {v['old_hits']}/{v['n_paired']} ({v['old_rate']*100:.1f}%) | "
            f"{v['new_hits']}/{v['n_paired']} ({v['new_rate']*100:.1f}%) | {v['delta_pp']:+.1f} | "
            f"[{v['old_ci'][0]:.3f},{v['old_ci'][1]:.3f}] | [{v['new_ci'][0]:.3f},{v['new_ci'][1]:.3f}] | "
            f"{'Y' if v['ci_overlap'] else 'N'} | {v['agree']}/{v['n_paired']} ({v['agree_rate']*100:.1f}%) | "
            f"{v['discordant']['old1_new0']}/{v['discordant']['old0_new1']} | {v['mcnemar_cross_run_p']:.4g} |")
    md.append("")
    md.append("## 翻转清单（qid 级）")
    for arm, v in report["per_arm"].items():
        if not v.get("flips"):
            continue
            md.append(f"### {arm}（{len(v['flips'])} flips）")
            for f in v["flips"]:
                md.append(f"- {f['qid']}: {int(f['old'])}→{int(f['new'])} | old_top1={f['old_top1'][:40]} | new_top1={f['new_top1'][:40]}")
    md.append("")
    md.append("## 拒答探针（OOD）")
    for arm, v in probe.items():
        md.append(f"- {arm}: old {v['old_refusal_ok']}/{v['old_n']} → new {v['new_refusal_ok']}/{v['new_n']}")
    md.append("")
    md.append("## 审计")
    md.append(f"- qid 唯一: {json.dumps(audit.get('qid_unique', {}), ensure_ascii=False)}")
    md.append(f"- n_rows: {json.dumps(audit.get('n_rows', {}), ensure_ascii=False)}")
    md.append(f"- 路由卡泄漏: {json.dumps(audit.get('route_card_leak', {}), ensure_ascii=False)[:400]}")
    md.append(f"- scoped 候选越界: {json.dumps(audit.get('scoped_candidates', {}), ensure_ascii=False)[:400]}")
    md.append(f"- 路由正确: {json.dumps(audit.get('route_correct', {}), ensure_ascii=False)}")
    md.append(f"- 金标回贴: {json.dumps(paste, ensure_ascii=False)[:600]}")
    (NEW / "s6d_compare.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md[:22]))
    print(f"\nwritten: {NEW/'s6d_compare.json'} + s6d_compare.md")


if __name__ == "__main__":
    main()
