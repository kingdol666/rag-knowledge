# r1_verify_stats.py -- Peer Reviewer 1 (IR evaluation methodologist)
# Recomputes key paper statistics from the landed artifacts and compares
# them with the numbers printed in main_20p (n8a/n8b/n8c + supplementary).
# Read-only with respect to paper sources; writes nothing except stdout.
# Run: python -I r1_verify_stats.py
import json, math
from itertools import combinations
from pathlib import Path

ART = Path(r"D:/codes/ClaudeGPT/rag_project/rag-knowledge/review/experiment-redesign-20261101/artifacts")
PROBES = {"R1", "R2", "R3", "R4"}

def binom_mcnemar(b, c):
    """Exact two-sided McNemar: 2 * P(X <= min(b,c)), X~Bin(b+c, .5)."""
    n, k = b + c, min(b, c)
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * tail)

def wilson(hits, n, z=1.959963984540054):
    if n == 0: return (0.0, 0.0)
    p = hits / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)

results = []
def check(name, claimed, actual, tol=0.0):
    ok = (abs(claimed - actual) <= tol) if isinstance(actual, float) else (claimed == actual)
    results.append((name, claimed, actual, "OK" if ok else "MISMATCH"))

# ---------- 1. s6_stats.json headline numbers ----------
s6 = json.loads((ART / "final_bench/s6_stats.json").read_text(encoding="utf-8"))
pa = s6["per_arm"]
for arm, hits in [("A0",37),("A0f",45),("A0h",52),("PD",46),("A1b",39),("A2",25),("A3",33),("A1-readall",72)]:
    check(f"s6 gold_hits {arm} (paper: {hits}/72)", hits, pa[arm]["gold_hits"])
check("s6 A2 gold_rate = 34.7% (paper 34.7%)", 0.347, round(pa["A2"]["gold_rate"], 3), 0.0005)
check("s6 A0 avg_bytes ~31.4 KB (paper 31.4 KB)", 31.4, round(pa["A0"]["avg_bytes_gold"]/1000, 1), 0.05)
check("s6 A0 avg tool s 16.3 (paper 16.3 s)", 16.3, pa["A0"]["avg_tool_s_gold"], 0.05)
check("s6 readall avg_bytes ~24.3 MB (paper 24.3 MB)", 24.3, round(pa["A1-readall"]["avg_bytes_gold"]/1e6, 1), 0.05)
check("s6 readall avg tool s 253.7 (paper 253.7 s)", 253.7, pa["A1-readall"]["avg_tool_s_gold"], 0.05)
check("s6 A0h avg_bytes ~309 KB (paper 309 KB)", 309, round(pa["A0h"]["avg_bytes_gold"]/1000, 0), 1.0)
check("s6 A0h avg tool s 13.8 (paper 13.8 s)", 13.8, pa["A0h"]["avg_tool_s_gold"], 0.05)
pm = s6["paired_mcnemar_vs_baseline"]
# paper (n8b/captions/supp): A2 p=0.0227 ; A0h vs A0 (implied 6.1e-05 in supp/inventory)
check("s6 A2 vs A0 exact McNemar p=0.0227", 0.0227, round(pm["A2"]["p_exact_two_sided"], 4), 0.00005)
check("s6 A0h vs A0 p=6.1e-05", 6.1e-05, round(pm["A0h"]["p_exact_two_sided"], 7), 1e-8)
check("s6 A3 vs A0 p=0.4545 (fig caption)", 0.4545, round(pm["A3"]["p_exact_two_sided"], 4), 0.00005)
check("s6 A1-readall vs A0 p=5.82e-11 (fig caption)", 5.82e-11, round(pm["A1-readall"]["p_exact_two_sided"], 13), 1e-13)
check("s6 A0f vs A0 p=0.0078", 0.0078125, pm["A0f"]["p_exact_two_sided"], 1e-9)
check("s6 PD vs A0 p=0.0039", 0.00390625, pm["PD"]["p_exact_two_sided"], 1e-9)
check("s6 A1b vs A0 p=0.6875", 0.6875, pm["A1b"]["p_exact_two_sided"], 1e-9)
# independent recomputation of the stored p's from (base_only, arm_only)
for arm, rec in pm.items():
    p_re = binom_mcnemar(rec["base_only"], rec["arm_only"])
    check(f"recompute McNemar {arm} from b,c={rec['base_only']},{rec['arm_only']}",
          round(rec["p_exact_two_sided"], 10), round(p_re, 10), 1e-10)
lo, hi = wilson(52, 72)
check("A0h Wilson CI [0.610,0.812] (paper [0.610,0.812])", True,
      abs(lo - 0.609536) < 1e-5 and abs(hi - 0.812397) < 1e-5)

# ---------- 2. s4_traces_final.json: per-arm hits + pairwise discordance ----------
tr = json.loads((ART / "final_bench/s4_traces_final.json").read_text(encoding="utf-8"))
def gold_map(arm):
    return {r["qid"]: bool(r["gold_hit"]) for r in tr[arm] if r["qid"] not in PROBES}
hits = {arm: sum(gold_map(arm).values()) for arm in tr}
for arm, h in [("A0",37),("A0f",45),("A0h",52),("PD",46),("A1b",39),("A2",25),("A3",33),("A1-readall",72)]:
    check(f"traces_final hits {arm} = {h}/72", h, hits[arm])
def disc(a, b):
    ga, gb = gold_map(a), gold_map(b)
    first = sum(1 for q in ga if ga[q] and not gb[q])
    second = sum(1 for q in ga if gb[q] and not ga[q])
    return first, second, binom_mcnemar(first, second)
f13, s13, p13 = disc("A0h", "A1b")
check("A0h vs A1b discordance 13:0 (supp + n8b)", 13, f13); check("  reverse 0", 0, s13)
check("A0h vs A1b p=0.00024", 0.00024, round(p13, 5), 5e-6)
f7, s7, p7 = disc("A0h", "PD")
check("A0h vs PD discordance 7:1 (supp + n8b)", 7, f7); check("  reverse 1", 1, s7)
check("A0h vs PD p=0.0703", 0.0703, round(p7, 4), 5e-5)
fpd, spd, ppd = disc("PD", "A1b")
print(f"[info] PD vs A1b frozen discordance = {fpd}:{spd}, p={ppd:.6f}  "
      f"(NOT printed anywhere in main/supp as of this review)")
# zero-byte A3 cases (fig routing caption: 11 zeros)
zero_a3 = sum(1 for r in tr["A3"] if r["qid"] not in PROBES and (r.get("bytes_ingested") or 0) == 0)
check("A3 zero-byte cases = 11 (fig:routing caption)", 11, zero_a3)
# route correctness (n8a: A0 72/72, A3 37/72, 35 only-in-A0)
rc = {arm: sum(1 for r in tr[arm] if r["qid"] not in PROBES and r.get("route_correct")) for arm in ["A0","A3"]}
check("route correct A0 72/72 (n8a)", 72, rc["A0"])
check("route correct A3 37/72 (n8a)", 37, rc["A3"])
ga0, ga3 = gold_map("A0"), gold_map("A3")
only_a0 = sum(1 for r in tr["A0"] if r["qid"] not in PROBES and r.get("route_correct") and not
              (next(x for x in tr["A3"] if x["qid"]==r["qid"]).get("route_correct")))
check("routes correct only in A0 = 35 (n8a)", 35, only_a0)
check("route McNemar 35:0 -> 5.82e-11", 5.82e-11, round(binom_mcnemar(only_a0, 0), 13), 1e-13)
# read-all calls: paper "897 calls"
ra_calls = sum(r["calls"] for r in tr["A1-readall"] if r["qid"] not in PROBES)
print(f"[info] read-all total calls on gold set = {ra_calls} (paper: 'across 897 calls per question')")

# ---------- 3. s5_floor.json: BM25 floor ----------
fl = json.loads((ART / "final_bench/s5_floor.json").read_text(encoding="utf-8"))
for arm in fl:
    n = len(fl[arm]); h = sum(1 for r in fl[arm] if r["gold_hit"])
    print(f"[info] floor arm {arm}: {h}/{n} = {100*h/n:.1f}%")
bm = fl["F-bm25"]; hb = sum(1 for r in bm if r["gold_hit"])
check("floor BM25 = 24/40 = 60.0% (n8b)", 24, hb)
check("floor n=40", 40, len(bm))

# ---------- 4. replication s4_traces_r3_statsready.json ----------
r3 = json.loads((ART / "replication_bench_20261112/s4_traces_r3_statsready.json").read_text(encoding="utf-8"))
r3h = {arm: sum(1 for r in r3[arm] if r["qid"] not in PROBES and r["gold_hit"]) for arm in r3}
for arm, h in [("A0",39),("A0f",44),("A0h",51),("PD",45),("A1b",39),("A2",25),("A3",25)]:
    check(f"r3 later-record hits {arm} = {h}/72 (n8b)", h, r3h[arm])
frozen = {"A0":37,"A0f":45,"A0h":52,"PD":46,"A1b":39,"A2":25}
def agree(a):
    ga = gold_map(a); gb = {r["qid"]: bool(r["gold_hit"]) for r in r3[a] if r["qid"] not in PROBES}
    return sum(1 for q in ga if ga[q] == gb[q])
for arm, a in [("A0",68),("A0f",71),("A0h",71),("PD",71),("A1b",72),("A2",72)]:
    check(f"r3 agreement {arm} = {a}/72 (94.4/98.6/100%)", a, agree(arm))
r3a3 = [r for r in r3["A3"] if r["qid"] not in PROBES]
miss_top = sum(1 for r in r3a3 if not (r.get("top1") or "").strip())
empty_pack = sum(1 for r in r3a3 if (r.get("pack_bytes") or 0) == 0)
check("A3 later: 13 missing top candidates (n8b)", 13, miss_top)
check("A3 later: 23 empty packs (n8b)", 23, empty_pack)
# follow-up paired rows in supp: A0h vs A1b 12:0 p=0.00049 ; A0h vs PD 7:1 p=0.0703
def disc3(a, b):
    ga = {r["qid"]: bool(r["gold_hit"]) for r in r3[a] if r["qid"] not in PROBES}
    gb = {r["qid"]: bool(r["gold_hit"]) for r in r3[b] if r["qid"] not in PROBES}
    f = sum(1 for q in ga if ga[q] and not gb[q]); s = sum(1 for q in ga if gb[q] and not ga[q])
    return f, s, binom_mcnemar(f, s)
ff, ss, pp = disc3("A0h", "A1b")
check("follow-up A0h vs A1b 12:0 (supp)", 12, ff); check("  reverse 0", 0, ss)
check("follow-up A0h vs A1b p=0.00049", 0.00049, round(pp, 5), 5e-6)
ff2, ss2, pp2 = disc3("A0h", "PD")
check("follow-up A0h vs PD 7:1 (supp)", 7, ff2); check("  reverse 1", 1, ss2)
check("follow-up A0h vs PD p=0.0703", 0.0703, round(pp2, 4), 5e-5)

# ---------- report ----------
w = max(len(r[0]) for r in results)
bad = 0
for name, c, a, st in results:
    if st != "OK": bad += 1
    print(f"{st:8s} {name:<{w}}  paper={c}  artifact={a}")
print(f"\nTOTAL {len(results)} checks, mismatches = {bad}")
