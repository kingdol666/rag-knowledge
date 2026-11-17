# -*- coding: utf-8 -*-
"""A2/A4/A5 验收门精查（数字对账 + claim 次数 + 摘要词数 + S 编号）。"""
import re
import glob

BASE = r"D:\codes\ClaudeGPT\rag_project\rag-knowledge\paper-kbs\tex\journal_20p"

tex = ""
for f in ("n8a_eval.tex", "n8b_eval.tex", "n8c_eval.tex",
          "n1_intro.tex", "n9_discussion.tex", "n10_threats.tex",
          "n11_conclusion.tex", "main_20p.tex"):
    try:
        tex += open(BASE + "\\" + f, encoding="utf-8").read()
    except FileNotFoundError:
        pass

print("=== A2 冻结值（含变体写法）===")
checks = {
    "45/72 或 45 of 72": ["45/72", "45 of 72", "45 strings"],
    "44/72": ["44/72"],
    "51/72": ["51/72"],
    "25/72": ["25/72"],
    "96.8": ["96.8"],
}
for label, variants in checks.items():
    n = sum(tex.count(v) for v in variants)
    print(f"  {label}: {n}")

print("=== A4 claim 出现次数（精确模式，≤3 纪律）===")
exact = {
    "13--0 (A0h vs A1b)": ["13--0", "13-0", "thirteen questions, all A0h-only",
                            "13 wins", "13--0 discordant"],
    "7--1 (A0h vs PD)": ["7--1", "seven\nA0h-only", "seven A0h-only"],
    "0.94 (Hit@5)": ["0.94"],
    "0.44": ["0.44"],
    "72/72 路由": ["72/72"],
}
for label, variants in exact.items():
    n = sum(tex.count(v) for v in variants)
    print(f"  {label}: {n} 次")

print("=== A5 摘要词数 ===")
main = open(BASE + r"\main_20p.tex", encoding="utf-8").read()
m = re.search(r"begin\{abstract\}(.*?)end\{abstract\}", main, re.S)
if m:
    words = len(m.group(1).split())
    print("  abstract words:", words, "(KBS ≤250)" , "PASS" if words <= 250 else "FAIL")
else:
    print("  abstract env not found in main_20p.tex")

print("=== A5 highlights ===")
try:
    hl = open(BASE + r"\highlights.tex", encoding="utf-8").read()
    n_hl = hl.count("\\item") 
    print("  highlights items:", n_hl, "(3-5)", "PASS" if 3 <= n_hl <= 5 else "CHECK")
    over = [l for l in hl.splitlines() if "\\item" in l and len(l) > 95]
    print("  >85 char items:", len(over))
except FileNotFoundError:
    print("  highlights.tex missing")

print("=== S 编号连续性（supplementary 源）===")
supp_paths = glob.glob(BASE + r"\..\supplementary\*.tex") + glob.glob(BASE + r"\supplementary*.tex")
supp = ""
for f in supp_paths:
    supp += open(f, encoding="utf-8").read()
if supp:
    missing = [f"S{i}" for i in range(1, 15) if (f"{{S{i}}}" not in supp and f"S{i}:" not in supp
                                                and f"S{i} " not in supp and f"S{i}." not in supp)]
    print("  supplementary files:", len(supp_paths), "| missing S labels:", missing or "none")
else:
    print("  supplementary tex not found at expected paths — check manually")
