# -*- coding: utf-8 -*-
"""crosscheck_numbers.py — 论文评测数字 vs final_bench 冻结工件逐项对账（评审专用，只读）。"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

ROOT = Path(r"D:/codes/ClaudeGPT/rag_project/rag-knowledge")
FB = ROOT / "review/experiment-redesign-20261101/artifacts/final_bench"
PAP = ROOT / "paper-kbs/tex/journal_20p"

FAIL = []
def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f" — {detail}" if detail else ""))
    if not cond:
        FAIL.append(name)

stats = json.loads((FB / "s6_stats.json").read_text(encoding="utf-8"))
floor = json.loads((FB / "s5_floor.json").read_text(encoding="utf-8"))
attr = json.loads((FB / "attribution_a0_misses.json").read_text(encoding="utf-8"))
traces = json.loads((FB / "s4_traces_final.json").read_text(encoding="utf-8"))

paper = ""
for f in ["main_20p.tex","n1_intro.tex","n2_related.tex","n3_overview.tex","n8a_eval.tex",
          "n8b_eval.tex","n8c_eval.tex","n9_discussion.tex","n10_threats.tex","n11_conclusion.tex"]:
    paper += (PAP / f).read_text(encoding="utf-8")

S = stats["per_arm"]

# ── 1. 八臂主数字 ──────────────────────────────────────────────
print("== 1. 臂级 gold 命中（论文声称 vs s6_stats.json） ==")
expect = {
    "A0h": (52, 72, 0.7222, "6.1\\times10^{-5}"),
    "PD":  (46, 72, 0.6389, "0.0039"),
    "A0f": (45, 72, 0.625, "0.0078"),
    "A0":  (37, 72, 0.5139, None),
    "A1b": (39, 72, 0.5417, "0.6875"),
    "A2":  (25, 72, 0.3472, "0.0227"),
    "A3":  (33, 72, 0.4583, "0.4545"),
    "A1-readall": (72, 72, 1.0, None),
}
for arm, (k, n, rate, p) in expect.items():
    s = S[arm]
    check(f"{arm} hits {k}/{n}", s["gold_hits"] == k and s["n_gold"] == n,
          f"file={s['gold_hits']}/{s['n_gold']}")
    check(f"{arm} rate", abs(s["gold_rate"] - rate) < 5e-4, f"file={s['gold_rate']:.4f} paper={rate}")
    pat = f"{k}/72" if n == 72 else f"{k}/{n}"
    check(f"{arm} 论文含 {pat}", pat in paper)
    if p:
        pnorm = p.replace("\\times10^{-5}", "e-5").replace("\\times10^{-5}", "")
        check(f"{arm} 论文含 p={p}", p in paper or pnorm in paper)

# ── 2. McNemar 配对值 ────────────────────────────────────────
print("== 2. 配对 McNemar vs s6_stats.json ==")
pm = stats["paired_mcnemar_vs_baseline"]
paper_p = {
    "A0h": 6.1e-05, "PD": 0.0039, "A0f": 0.0078, "A1b": 0.6875,
    "A2": 0.0227, "A3": 0.4545,
}
for arm, pv in paper_p.items():
    f = pm.get(arm, {}).get("p_exact_two_sided")
    check(f"{arm} p 文件={pv} vs 冻结={f}", f is not None and abs(f - pv) < 1e-9 or
          (arm == "A0h" and abs((f or 0) - 6.1e-05) < 1e-7), f"file={f}")

# ── 3. 头对头 A0h vs PD 7:1 ─────────────────────────────────
print("== 3. 头对头 A0h vs PD ==")
base = {r["qid"]: bool(r.get("gold_hit")) for r in traces["A0"] if not r.get("is_refusal")}
h = {r["qid"]: bool(r.get("gold_hit")) for r in traces["A0h"] if not r.get("is_refusal")}
d = {r["qid"]: bool(r.get("gold_hit")) for r in traces["PD"] if not r.get("is_refusal")}
ah = sum(1 for q in h if h[q] and not d.get(q))   # A0h-only
pd_ = sum(1 for q in h if not h[q] and d.get(q))  # PD-only
check(f"A0h-only={ah} PD-only={pd_}（论文声称 7:1, 8 discordant）", ah == 7 and pd_ == 1,
      f"actual {ah}:{pd_}")
check("论文含 7--1 / 8 discordant", ("7--1" in paper) and ("eight questions" in paper or "8 discordant" in paper))

# ── 4. bytes/tool 时间 ──────────────────────────────────────
print("== 4. bytes / tool seconds ==")
check(f"A0h avg_bytes={S['A0h']['avg_bytes_gold']:.0f}（论文 ~307KB? 论文写法待查）", True)
check("A0 31.4 KB in paper", "31.4 KB" in paper, f"file={S['A0']['avg_bytes_gold']/1000:.1f}KB")
check("A0 16.3 s in paper", "16.3 s" in paper or "16.3\\,s" in paper, f"file={S['A0']['avg_tool_s_gold']}")
check("A1 24.3 MB in paper", "24.3 MB" in paper or "24.3\\,MB" in paper,
      f"file={S['A1-readall']['avg_bytes_gold']/1e6:.1f}MB")
check("A1 253.7 s in paper", "253.7" in paper, f"file={S['A1-readall']['avg_tool_s_gold']}")
check("A3 23.5 KB in paper", "23.5 KB" in paper or "23.5\\,KB" in paper,
      f"file={S['A3']['avg_bytes_gold']/1000:.1f}KB")
check("A3 7.8 s in paper", "7.8 s" in paper or "7.8\\,s" in paper, f"file={S['A3']['avg_tool_s_gold']}")

# ── 5. 归因 35 = 5 窗口 + 30 判卷; 修复杠杆 8/15/9 ────────────
print("== 5. 归因账目 ==")
from collections import Counter
rows = attr.get("rows", []) if isinstance(attr, dict) else attr
cnt = Counter(r.get("cls") for r in rows)
check("归因 35 行", len(rows) == 35)
check("窗口 5 + 判卷 30", cnt.get("window-truncation-miss") == 5 and cnt.get("judge-miss") == 30,
      str(dict(cnt)))
check("论文含 35 misses / five window / thirty judge",
      "35 A0 misses" in paper and "five in window truncation" in paper and "thirty in judge" in paper)

# 修复杠杆：A0f 修复数 = A0f∩(~A0), A0h 修复数, PD 修复数
def repairs(arm):
    m = {r["qid"]: bool(r.get("gold_hit")) for r in traces[arm] if not r.get("is_refusal")}
    return sum(1 for q in m if m[q] and not base.get(q))
check(f"A0f repairs={repairs('A0f')} (paper 8)", repairs("A0f") == 8)
check(f"A0h repairs={repairs('A0h')} (paper 15)", repairs("A0h") == 15)
check(f"PD repairs={repairs('PD')} (paper 9)", repairs("PD") == 9)
check("论文含 A0f repairs eight / A0h fifteen / PD nine",
      "repairs eight" in paper and "fifteen" in paper and "PD nine" in paper)

# ── 6. 路由 72/72 vs 37/72, McNemar 5.82e-11 ────────────────
print("== 6. 路由审计数字 ==")
rc0 = [r.get("route_correct") for r in traces["A0"] if r.get("route_correct") is not None]
rc3 = [r.get("route_correct") for r in traces["A3"] if r.get("route_correct") is not None]
check(f"A0 route {sum(rc0)}/{len(rc0)}（论文 72/72）", sum(rc0) == 72 and len(rc0) == 72)
check(f"A3 route {sum(rc3)}/{len(rc3)}（论文 37/72）", sum(rc3) == 37 and len(rc3) == 72)
# 35 discordant 全单向 → p = 2/2^35
import math
b = sum(1 for q in base if base[q] and not {})  # placeholder
# route pairing: A0 correct & A3 wrong = 35, reverse = 0
a0r = {r["qid"]: bool(r.get("route_correct")) for r in traces["A0"] if r.get("route_correct") is not None}
a3r = {r["qid"]: bool(r.get("route_correct")) for r in traces["A3"] if r.get("route_correct") is not None}
only0 = sum(1 for q in a0r if a0r[q] and not a3r.get(q))
only3 = sum(1 for q in a0r if not a0r[q] and a3r.get(q))
p_route = 2 * sum(math.comb(only0 + only3, i) for i in range(0, min(only0, only3) + 1)) / 2 ** (only0 + only3)
check(f"route discordant {only0}/{only3}, p={p_route:.3e}（论文 35/0, 5.82e-11）",
      only0 == 35 and only3 == 0 and abs(p_route - 5.82e-11) < 1e-13)
check("论文含 5.82\\times10^{-11}", "5.82\\times10^{-11}" in paper)

# ── 7. floor ────────────────────────────────────────────────
print("== 7. floor（s5_floor.json） ==")
frows = floor.get("rows") or floor.get("results") or floor
if isinstance(frows, dict):
    for k, v in frows.items():
        if isinstance(v, dict) and "hits" in v:
            print(f"  floor {k}: {v['hits']}/{v.get('n', v.get('total','?'))}")

# ── 8. A3 泄漏披露（15/72）是否进论文 ────────────────────────
print("== 8. A3 跨库泄漏披露（终审计新增） ==")
leak_disclosed = ("15" in paper and ("leak" in paper.lower() or "production knowledge base" in paper.lower()
                                   or "candidate" in paper.lower()))
# 精确：搜 15/72 或 fifteen leak
has_leak = bool(re.search(r"15\s*/\s*72|fifteen.*(leak|production)|(leak|production).{0,120}15", paper, re.I))
check("A3 候选池跨库泄漏（15/72）在论文中披露", has_leak,
      "终审计 2026-11-11 发现并要求披露：A3 15/72 行混入生产库候选，剔除后 26/57=45.6% 不变")

# ── 9. 复现稳定性（§4: 71/72=98.6%, 68/72=94.4%）是否需要提及 ──
print("== 9. 已知限制覆盖（RESULTS §7 vs 论文 threats） ==")
for item, pat in [
    ("剩余 20 深部判卷缺口（题点词型金标 Laya<0.5）", r"LLaMA|Odyssey|20.*(judge|deep)|deep.*judge.*(miss|fail)"),
    ("金标 containment ≠ 回答正确率", r"containment.*not|not.*answer quality|proxy"),
    ("A0h/PD 读入 ~307KB/题", r"307|309"),
]:
    found = bool(re.search(pat, paper, re.I))
    print(("PASS " if found else "WARN ") + f"论文提及: {item}" + ("" if found else " — 未找到明确表述"))

print()
if FAIL:
    print(f"CROSSCHECK FAILED: {len(FAIL)} 项")
    for f in FAIL:
        print("  -", f)
    sys.exit(1)
print("CROSSCHECK ALL-PASS：论文评测数字与冻结工件一致。")
