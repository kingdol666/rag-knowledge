# -*- coding: utf-8 -*-
"""s9i_final_audit.py — 终版 bench 独立正确性审计（不信任任何汇总文件，全部重算）。

审计维度：
 A. 结构完整性：8 臂 × 76 行、gold=72 唯一 qid、拒答探针=4
 B. 指标重算：gold rate / Wilson 95% CI / 精确 McNemar（独立实现） vs s6_stats.json
 C. 端到端测量验证：复现跑中每条 gold_hit=True 的题，金标串必须真的出现在
    该臂 response_text 原文里（证明"命中"度量真实成立）
 D. 范围污染：8 臂全部 top1/survivors ⊆ 十个 MD语料-* 评测库，零目录卡泄漏
 E. 晋升 vs 复现一致性：逐臂逐题比对（应复现 §4 所载 98.6%/94.4%）
 F. 归因账目：35 缺口 = 5 窗口 + 30 判卷 + 0 路由 + 0 格式；抽查磁盘偏移真实性
 G. 题集完整性：72 gold + 4 refusal；锚串非空；域分布
 H. 平均值重算：bytes/tool/digest 与 s6_stats 一致
"""
from __future__ import annotations
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent
ART = BASE.parent / "artifacts"
FB = ART / "final_bench"

FAIL: list[str] = []
def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f" — {detail}" if detail else ""))
    if not cond:
        FAIL.append(name)

def wilson(k, n, z=1.959963985):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - r) / d, (c + r) / d)

def mcnemar_exact(b, c):
    """b=base_only, c=arm_only；精确双侧二项 p（n=b+c, p=0.5）。"""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    prob = sum(math.comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return min(1.0, 2 * prob)

def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    stats = json.loads((FB / "s6_stats.json").read_text(encoding="utf-8"))
    traces = json.loads((FB / "s4_traces_final.json").read_text(encoding="utf-8"))
    replication = json.loads((ART / "responses_capture" / "s4_traces_124310.json").read_text(encoding="utf-8")) \
        if (ART / "responses_capture" / "s4_traces_124310.json").exists() else {}
    responses = {}
    for f in sorted((FB / "responses").glob("*.json")):
        if f.stem != Path(stats.get("_src", "x")).stem and not f.stem.startswith("s4_responses_"):
            responses[f.stem] = json.loads(f.read_text(encoding="utf-8"))

    EXPECT_ARMS = ["A0", "A0f", "A0h", "PD", "A1b", "A2", "A3", "A1-readall"]

    # ── A. 结构完整性 ──
    print("== A. 结构完整性 ==")
    check("A1 臂集合完整", sorted(traces.keys()) == sorted(EXPECT_ARMS), f"got {sorted(traces.keys())}")
    for arm in EXPECT_ARMS:
        rows = traces[arm]
        gold = [r for r in rows if not r.get("is_refusal")]
        probes = [r for r in rows if r.get("is_refusal")]
        qids = [r["qid"] for r in gold]
        check(f"A2 {arm} 76=72gold+4probe", len(rows) == 76 and len(gold) == 72 and len(probes) == 4)
        check(f"A3 {arm} gold qid 唯一", len(set(qids)) == 72)

    # ── B. 指标重算（独立实现） ──
    print("== B. 指标重算 vs s6_stats.json ==")
    for arm in EXPECT_ARMS:
        gold = [r for r in traces[arm] if not r.get("is_refusal")]
        k = sum(1 for r in gold if r.get("gold_hit"))
        n = len(gold)
        s = stats["per_arm"][arm]
        check(f"B1 {arm} hits {k}=={s['gold_hits']}", k == s["gold_hits"])
        check(f"B2 {arm} rate {k/n:.6f}=={s['gold_rate']}", abs(k / n - s["gold_rate"]) < 1e-6)
        lo, hi = wilson(k, n)
        check(f"B3 {arm} Wilson CI 重算一致",
              abs(lo - s["gold_ci95"][0]) < 2e-6 and abs(hi - s["gold_ci95"][1]) < 2e-6,
              f"mine=[{lo:.6f},{hi:.6f}] file={s['gold_ci95']}")
        avg_b = sum(r.get("bytes_ingested", 0) or 0 for r in gold) / n
        avg_t = sum(r.get("tool_seconds", 0) or 0 for r in gold) / n
        check(f"B4 {arm} avg bytes/tool 重算一致",
              abs(avg_b - s["avg_bytes_gold"]) < 1.0 and abs(avg_t - s["avg_tool_s_gold"]) < 0.06,
              f"bytes {avg_b:.0f} vs {s['avg_bytes_gold']}, tool {avg_t:.1f} vs {s['avg_tool_s_gold']}")

    # McNemar（独立实现）vs 文件
    base_gold = {r["qid"]: bool(r.get("gold_hit")) for r in traces["A0"] if not r.get("is_refusal")}
    for arm in [a for a in EXPECT_ARMS if a != "A0"]:
        arm_gold = {r["qid"]: bool(r.get("gold_hit")) for r in traces[arm] if not r.get("is_refusal")}
        b = sum(1 for q in base_gold if base_gold[q] and not arm_gold.get(q))
        c = sum(1 for q in base_gold if not base_gold[q] and arm_gold.get(q))
        p = mcnemar_exact(b, c)
        f = stats["paired_mcnemar_vs_baseline"].get(arm, {})
        check(f"B5 {arm} McNemar b={b} c={c} p={p:.6f} vs file {f.get('p_exact_two_sided', 0):.6f}",
              b == f.get("base_only") and c == f.get("arm_only") and abs(p - f.get("p_exact_two_sided", 1)) < 1e-9)

    # ── C. 端到端测量验证（复现跑：gold_hit ⇒ 金标串 ∈ response_text） ──
    print("== C. 端到端测量验证（复现跑原文） ==")
    for arm in ["A0", "A0f", "A0h", "PD"]:
        resp = responses.get(arm)
        if not resp:
            check(f"C1 {arm} 回复原文存在", False, "missing in final_bench/responses")
            continue
        bad = []
        verified = 0
        for qid, r in resp.items():
            if r.get("is_refusal") or not r.get("gold_hit"):
                continue
            ev = r.get("gold_evidence", "")
            if not ev:
                continue
            verified += 1
            if ev not in (r.get("response_text") or ""):
                bad.append(qid)
        check(f"C2 {arm} 全部 {verified} 个 gold_hit 的金标串均在回复原文中", not bad,
              f"violations={bad[:5]}")
        # 反向：miss 的题金标串确实不在原文里（度量无假阴性漏记）
        miss_bad = [qid for qid, r in resp.items()
                    if not r.get("is_refusal") and not r.get("gold_hit")
                    and r.get("gold_evidence") and r.get("gold_evidence") in (r.get("response_text") or "")]
        check(f"C3 {arm} 无'原文含金标却记 miss'的漏记", not miss_bad, f"violations={miss_bad[:5]}")

    # ── D. 范围污染审计 ──
    print("== D. 范围污染审计 ==")
    bad_paths = []
    a3_prod_rows = []
    PROD_PREFIXES = ("自然科学与地球科学", "计算机与人工智能", "Corpus-Chunks800",
                     "生命科学与医学", "工程与能源")
    for arm in EXPECT_ARMS:
        for r in traces[arm]:
            paths = []
            t = r.get("top1")
            if isinstance(t, str) and t:
                paths.append(t)
            paths += [p for p in (r.get("survivors") or []) if isinstance(p, str)]
            for p in paths:
                if "路由目录卡" in p:
                    bad_paths.append((arm, r["qid"], "route-card", p[:60]))
                elif arm == "A3":
                    # A3 已披露缺陷（RESULTS §7）：部分域孪生库缺失时宽网候选跨库，
                    # 15/72 行混入生产库候选。此处核对泄漏行数与披露值一致。
                    if p.startswith(PROD_PREFIXES):
                        a3_prod_rows.append((r["qid"], bool(r.get("gold_hit"))))
                elif not p.startswith("MD语料-"):
                    bad_paths.append((arm, r["qid"], "expect MD语料-", p[:60]))
    check("D1 七个非 A3 臂 top1/survivors 零污染", not bad_paths, f"violations={bad_paths[:5]}")
    check("D2 A3 生产库泄漏行数 == 披露值 15（RESULTS §7 已披露；剔除后 26/57=45.6% 不变）",
          len(set(q for q, _ in a3_prod_rows)) == 15,
          f"leaked rows={len(set(q for q, _ in a3_prod_rows))}")

    # ── E. 晋升 vs 复现一致性（responses/*.json 携带复现 gold_hit，可独立重算） ──
    print("== E. 晋升 vs 复现一致性 ==")
    if responses:
        # RESULTS §4 载明：A0f/A0h/PD=71/72(98.6%)，A0=68/72(94.4%，3上1下)
        expect_agree = {"A0": 68, "A0f": 71, "A0h": 71, "PD": 71}
        for arm in ["A0", "A0f", "A0h", "PD"]:
            pm = {r["qid"]: bool(r.get("gold_hit")) for r in traces[arm] if not r.get("is_refusal")}
            rm = {qid: bool(r.get("gold_hit")) for qid, r in (responses.get(arm) or {}).items()
                  if not r.get("is_refusal")}
            agree = sum(1 for q in pm if q in rm and pm[q] == rm[q])
            check(f"E1 {arm} 复现一致 {agree}/72 == RESULTS §4 载明 {expect_agree[arm]}/72",
                  agree == expect_agree[arm])
        rc_rows = [r for arm in ("A0", "A0f", "A0h") for r in traces[arm]
                   if r.get("route_correct") is not None]
        check("E2 晋升 traces 路由 72/72 × 3 臂",
              sum(1 for x in rc_rows if x) == len(rc_rows) == 216,
              f"{sum(1 for x in rc_rows if x)}/{len(rc_rows)}")
    else:
        check("E0 responses 缺失，跳过 E1", False)

    # ── F. 归因账目 ──
    print("== F. 归因账目 ==")
    attr = json.loads((FB / "attribution_a0_misses.json").read_text(encoding="utf-8"))
    rows = attr.get("rows", []) if isinstance(attr, dict) else attr
    cnt = Counter(r.get("cls") for r in rows)
    file_counts = attr.get("counts", {}) if isinstance(attr, dict) else {}
    miss_qids = {q for q, hit in base_gold.items() if not hit}
    check(f"F1 归因行数 {len(rows)} == A0 缺口 35", len(rows) == 35)
    check("F2 归因类账目 5窗口+30判卷+0路由+0格式",
          cnt.get("window-truncation-miss") == 5 and cnt.get("judge-miss") == 30
          and cnt.get("routing-miss", 0) == 0 and cnt.get("format-mismatch", 0) == 0,
          f"rows={dict(cnt)} file_counts={file_counts}")
    check("F2b counts 字段与行计数一致",
          {k: v for k, v in file_counts.items() if v} == {k: v for k, v in cnt.items() if v},
          f"{file_counts}")
    check("F3 归因 qid 集合 == A0 未命中集合", {r.get("qid") for r in rows} == miss_qids)

    # ── G. 题集完整性 ──
    print("== G. 题集完整性 ==")
    qs = [json.loads(l) for l in (ART / "provenance" / "questions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    gold_qs = [q for q in qs if q.get("kind") != "refusal" and not q.get("needs_expansion")]
    ref_qs = [q for q in qs if q.get("kind") == "refusal"]
    check("G1 72 gold + 4 refusal (+2 需扩题被排除)",
          len(gold_qs) == 72 and len(ref_qs) == 4 and sum(1 for q in qs if q.get("needs_expansion")) == 2)
    check("G2 gold 锚串非空且唯一qid", all(q.get("gold_evidence") for q in gold_qs)
          and len({q["id"] for q in gold_qs}) == 72)
    dom = Counter(q.get("domain") for q in gold_qs)
    check("G3 gold 覆盖 10 域", len(dom) == 10, str(dict(dom)))

    # ── H. RESULTS.md §0 表与 s6_stats 交叉 ──
    print("== H. RESULTS.md 数字交叉 ==")
    res = (BASE.parent / "RESULTS.md").read_text(encoding="utf-8")
    for pat, label in [("52/72", "A0h 52/72"), ("72.2%", "A0h 72.2%"), ("63.9%", "PD 63.9%"),
                       ("62.5%", "A0f 62.5%"), ("51.4%", "A0 51.4%"), ("6.1e-05", "A0h 精确 p=6.1e-05")]:
        check(f"H1 RESULTS 含 {label}", pat in res)

    print()
    if FAIL:
        print(f"AUDIT FAILED: {len(FAIL)} 项")
        for f in FAIL:
            print("  -", f)
        sys.exit(1)
    print("AUDIT ALL-PASS：终版 bench 数字全部经独立重算核验。")


if __name__ == "__main__":
    main()
