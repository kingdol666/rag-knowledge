# -*- coding: utf-8 -*-
"""Final consistency audit: main text <-> supplementary labels <-> experiment CSVs."""
import csv, re, sys
from pathlib import Path

BASE = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge\paper-kbs\tex\journal_20p")
ok, fail = [], []

def check(name, cond, detail=""):
    (ok if cond else fail).append(f"{name} {detail}")

# --- 1. S-labels referenced in main text exist in supplementary ---
main = "".join((BASE / f).read_text(encoding="utf-8")
               for f in ["n8a_eval.tex", "n8b_eval.tex", "n8c_eval.tex", "n9_discussion.tex", "n10_threats.tex"])
supp = (BASE / "supplementary.tex").read_text(encoding="utf-8") + \
       (BASE / "supplementary-arm-tables.tex").read_text(encoding="utf-8")
refs = sorted(set(re.findall(r"Table~?(S\d+)|Tables~S\d+[–-](S\d+)", main)))
# every S<number> token in main
s_tokens = sorted(set(int(n) for n in re.findall(r"\bS(\d+)\b", main)))
supp_labels = set(int(n) for n in re.findall(r"label\{tab:s(\d+)|label\{s(\d+)", supp) and
                 [a or b for a, b in re.findall(r"label\{(?:tab:)?s(\d+)\}", supp)] or [])
supp_labels = set(int(n) for n in re.findall(r"label\{(?:tab:)?s(\d+)\}", supp))
supp_mentioned = set(int(n) for n in re.findall(r"\bS(\d+)\b", supp))
missing = [s for s in s_tokens if s not in supp_labels and s not in supp_mentioned]
check("S-table refs", not missing, f"main mentions S{['S'+str(m) for m in missing] if missing else 'all resolvable'}")

# --- 2. CSV cross-checks ---
def readcsv(p):
    return list(csv.DictReader(open(BASE / "experiment_data" / p, encoding="utf-8")))

content = readcsv("redraw_content_summary.csv")
row = {r["arm"]: r for r in content if r["panel"] == "aggregate"}
for arm, exp in [("A0h", "52"), ("A0", "37"), ("A0f", "45"), ("PD", "46"), ("A1b", "39"), ("A2", "25")]:
    check(f"frozen {arm}", row[arm]["frozen"] == exp, f"csv={row[arm]['frozen']} expect={exp}")
    fexp = {"A0h": "51", "A0": "39", "A0f": "44", "PD": "45", "A1b": "39", "A2": "25"}[arm]
    check(f"followup {arm}", row[arm]["followup"] == fexp, f"csv={row[arm]['followup']}")

for contrast, fo, so, p in [("A0h–A0", "15", "0", "6.103515625e-05"),
                            ("A0h–A1b", "13", "0", "0.000244140625"),
                            ("A0h–PD", "7", "1", "0.0703125"),
                            ("A0f–A0", "8", "0", "0.0078125")]:
    r = next(x for x in content if x.get("contrast") == contrast)
    check(f"discordant {contrast}", r["first_only"] == fo and r["second_only"] == so and abs(float(r["p"]) - float(p)) < 1e-12)

# Wilson for A0h frozen 52/72
n, k = 72, 52
z = 1.959963984540054
ph = k / n; d = 1 + z*z/n
c = (ph + z*z/(2*n)) / d
h = z * ((ph*(1-ph)/n + z*z/(4*n*n)) ** 0.5) / d
check("Wilson A0h", f"{(c-h)*100:.1f}" == "61.0" and f"{(c+h)*100:.1f}" == "81.2", f"= {(c-h)*100:.2f}–{(c+h)*100:.2f}")

# McNemar 7/0 -> p=0.015625 (A0h vs A0f both campaigns)
p70 = 2 * 0.5**7
check("McNemar 7/0", abs(p70 - 0.015625) < 1e-12, f"p={p70}")

route = readcsv("redraw_route_summary.csv")
rr = {r["arm"]: r for r in route if r["panel"] == "route"}
check("route A0 72/72", rr["A0"]["hits"] == "72" and rr["A0"]["percent"] == "100.0")
check("route A3 37", rr["A3"]["hits"] == "37")

verif = readcsv("redraw_verifier_order.csv")
try:
    vrow = verif[0]
    check("verifier order cols", True, str(list(vrow.keys())[:6]))
except Exception as e:
    check("verifier order", False, str(e))

ans = readcsv("redraw_answer_matrix.csv")
check("answer matrix rows", len(ans) > 0, f"{len(ans)} rows")

# --- 3. main text contains the new numbers verbatim ---
body = main + (BASE / "main_20p.tex").read_text(encoding="utf-8")
for probe in ["52 to 45 in the frozen record and 51 to 44", "seven A0h-only hits and no reverse case ($p=0.016$)",
              "72 developer-authored questions", "route cards pairing each", "Model Context Protocol"]:
    check(f"text probe: {probe[:34]}", probe in body)

print(f"PASS {len(ok)} / FAIL {len(fail)}")
for f_ in fail:
    print("FAIL:", f_)
sys.exit(1 if fail else 0)
