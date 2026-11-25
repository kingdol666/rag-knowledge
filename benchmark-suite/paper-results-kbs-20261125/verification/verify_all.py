# -*- coding: utf-8 -*-
"""Verify selected paper and supplement claims against archived records.

Run with python -I -X utf8 verification/verify_all.py. Use --report-dir to
write the verification reports elsewhere; derived CSVs land in tables/.
"""
from __future__ import annotations

import argparse
import csv
from decimal import Decimal, ROUND_HALF_UP
import json
import math
import re
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
REC = BENCH / "records"
TAB = BENCH / "tables"
REPO = BENCH.parents[1]
SRC = REPO / ("paper-kbs/finalpaper/HMRS-KBS-FINAL-20261124-EVIDENCE-LAYOUT/"
              "04-source/source")
DIMS = ("factual", "completeness", "groundedness", "sources")
ARMS6 = ["hmrs-agent", "bm25", "dense", "rrf", "raptor", "lightrag", "deepread-native", "graphrag"]
CHECKS = []


def read_jsonl(p: Path) -> list:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def read_csv(p: Path) -> list:
    with p.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def check(cid: str, section: str, claim: str, expected, got, source: str, tol: float = 5e-3) -> None:
    ok = False
    if isinstance(expected, (int, float)) and isinstance(got, (int, float)):
        ok = abs(expected - got) <= tol + 1e-9
    else:
        ok = expected == got
    CHECKS.append({"id": cid, "section": section, "claim": claim, "expected": expected,
                   "recomputed": got, "source": source, "status": "PASS" if ok else "FAIL"})


def sign_p(k: int, n: int) -> float:
    """Exact two-sided sign test, ties dropped (k = minority-free wins)."""
    if n == 0:
        return 1.0
    kk = max(k, n - k)
    tail = sum(math.comb(n, i) for i in range(kk, n + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def strip_tex(s: str) -> str:
    s = re.sub(r"\$[^$]*\$", "", s)
    s = re.sub(r"\\textbf\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\emph\{([^}]*)\}", r"\1", s)
    s = s.replace("\\dagger", "").replace("\\ddagger", "")
    return s.strip()


def tex_rows(path: Path, label: str, ncols: int) -> list[list[str]]:
    """Rows between \\midrule and \\bottomrule of the tabular under \\label{label}."""
    text = path.read_text(encoding="utf-8")
    i = text.find(f"\\label{{{label}}}")
    assert i >= 0, f"label {label} not in {path}"
    j = text.find("\\midrule", i)
    k = text.find("\\bottomrule", j)
    rows = []
    for ln in text[j:k].splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("\\midrule") or ln.startswith("\\addlinespace"):
            continue
        cells = [strip_tex(c) for c in ln.rstrip("\\ ").split("&")]
        if len(cells) >= ncols:
            rows.append(cells[:ncols])
    return rows


# ---------------------------------------------------------------- E1: routing
def verify_e1() -> None:
    rc = REC / "routing_content_traces"
    rs = read_csv(rc / "redraw_route_summary.csv")
    traces = {}
    for f in sorted(rc.glob("supp_traces_*.csv")):
        rows = [r for r in read_csv(f) if r["qid"] not in ("R1", "R2", "R3", "R4")]
        per = {}
        for r in rows:
            a = r["arm"]
            per.setdefault(a, {"n": 0, "hits": 0, "route": 0, "bytes": 0, "q": {}})
            p = per[a]
            hit = r["gold_hit"] == "True"
            p["n"] += 1
            p["hits"] += hit
            p["route"] += r.get("route_correct") == "True"
            p["bytes"] += int(r["bytes_ingested"])
            p["q"][r["qid"]] = hit
        traces[f.stem.replace("supp_traces_", "")] = per

    # 1) every summary row is reproduced by some recorded run
    alias = {"Read-all": "A1-readall"}
    for row in rs:
        arm, hits, mb = row["arm"], int(row["hits"]), row["mean_mb"]
        matches = []
        for run, per in traces.items():
            p = per.get(alias.get(arm, arm))
            metric = p["route"] if (p and row["panel"] == "route") else (p or {}).get("hits")
            if not p or metric != hits:
                continue
            ratio = p["bytes"] / p["n"] / 1e6
            if not mb or abs(ratio - float(mb)) < 1e-5:
                matches.append(run)
        check(f"E1-summary-{row['panel']}-{arm}", "E1",
              f"summary {row['panel']}/{arm}: hits={hits}, mean={mb or '-'} MB",
              "reproduced", "reproduced" if matches else "NO RUN MATCHES",
              f"redraw_route_summary.csv vs traces {matches or '-'}")

    # Verify the named run, not merely any run that happens to match a count.
    frozen = traces["frozen"]
    for arm, want in (("A0", 72), ("A3", 37)):
        check(f"E3-route-{arm}", "E3", f"frozen routing hits {arm}", (want, 72),
              (frozen[arm]["route"], frozen[arm]["n"]), "supp_traces_frozen.csv")
    for run, a3 in (("followup", 49), ("rerun_20261117", 49)):
        for arm, want in (("A0", 72), ("A3", a3)):
            cell = traces[run][arm]
            check(f"E3-rerunroute-{run}-{arm}", "E3", f"{run} route hits {arm}",
                  (want, 72), (cell["route"], cell["n"]), f"supp_traces_{run}.csv")

    # 3) containment: A0 37, A0h 52, A3 33, read-all 72 (volume panel)
    vol = {r["arm"]: r for r in rs if r["panel"] == "volume"}
    for arm, want in (("A0", 37), ("A0h", 52), ("A3", 33), ("A1-readall", 72)):
        check(f"E1-containment-{arm}", "E1", f"containment hits {arm} = {want}",
              want, int(vol[arm]["hits"]), "redraw_route_summary.csv volume")
    check("E1-volume-A0-kB", "E1", "A0 handles 31.4 kB/question", 31.4,
          float(vol["A0"]["mean_mb"]) * 1000, "redraw_route_summary.csv volume", tol=0.05)
    check("E1-volume-A0h-kB", "E1", "A0h handles 309 kB/question", 309,
          float(vol["A0h"]["mean_mb"]) * 1000, "redraw_route_summary.csv volume", tol=0.6)

    # 4) reruns keep the gain (frozen/follow-up counts) and paired exact tests
    cs = read_csv(rc / "redraw_content_summary.csv")
    agg = {r["arm"]: r for r in cs if r["panel"] == "aggregate"}
    for arm, frozen, follow in (("A0", 37, 39), ("A0h", 52, 51), ("A0f", 45, 44), ("PD", 46, 45),
                                ("A1b", 39, 39), ("A2", 25, 25), ("A3", 33, 25)):
        check(f"E1-rerun-{arm}", "E1", f"{arm} containment frozen={frozen}, follow-up={follow}",
              (frozen, follow), (int(agg[arm]["frozen"]), int(agg[arm]["followup"])),
              "redraw_content_summary.csv")
    # per-question paired counts in the frozen traces
    frozen = traces.get("frozen")
    if frozen:
        for a, b, w1, w2, pwant in (("A0h", "A1b", 13, 0, 0.000244), ("PD", "A1b", 7, 0, 0.015625),
                                    ("A0f", "A0", 8, 0, 0.0078125), ("A0h", "A0", 15, 0, 0.000061035),
                                    ("A0h", "PD", 7, 1, 0.0703125), ("A2", "A0", 6, 18, 0.0226558)):
            qa, qb = frozen[a]["q"], frozen[b]["q"]
            only_a = sum(qa[q] and not qb[q] for q in qa if q in qb)
            only_b = sum(qb[q] and not qa[q] for q in qa if q in qb)
            check(f"E1-sign-{a}-{b}", "E1", f"frozen paired {a}>{b}: {w1}-{w2}, exact sign p",
                  (w1, w2), (only_a, only_b), "frozen traces, per-question gold_hit")
            check(f"E1-signp-{a}-{b}", "E1", f"exact sign p for {a} vs {b}",
                  pwant, sign_p(only_a, only_a + only_b), "recomputed", tol=5e-5)

    # canonical summaries land in tables/ unchanged
    for f in ("redraw_route_summary.csv", "redraw_content_summary.csv"):
        (TAB / ("e1_" + f)).write_text((rc / f).read_text(encoding="utf-8"), encoding="utf-8")

    # 5) headline strings in the manuscript
    tex = " ".join((SRC / "main_20p.tex").read_text(encoding="utf-8").split())
    for frag, cid, claim in (
            ("72 cases with description-bearing cards and 37",
             "E3-abs-route", "abstract: 72 vs 37 routing"),
            ("raised target-string containment from 37 to 52 of 72 questions",
             "E4-abs-contain", "abstract: containment 37 to 52"),
            ("309~kB per question", "E4-abs-kB1", "abstract: 309 kB"),
            ("31.4~kB for the reference", "E4-abs-kB2", "abstract: 31.4 kB"),
            ("reduced top-five gold-document hits from 15 to seven", "E6-abs", "abstract: verifier 15 to seven"),
            ("a blind judge rated all ten HMRS answers correct", "E2-abs-10", "abstract: ten correct")):
        check(cid, "abstract", claim, "present", "present" if frag in tex else "MISSING",
              "main_20p.tex")


def arm_of(name: str) -> str:
    """Map a printed table row label to the record arm key (tolerates markup remnants)."""
    n = name.lower()
    for key, arm in (("hmrs", "hmrs-agent"), ("bm25", "bm25"), ("dense", "dense"),
                     ("rrf", "rrf"), ("raptor", "raptor"), ("lightrag", "lightrag"),
                     ("deepread", "deepread-native"), ("graphrag", "graphrag")):
        if key in n:
            return arm
    raise KeyError(name)


# ---------------------------------------------------------------- E2: T6 etc.
def verify_e2() -> None:
    base = REC / "external_baselines_v3"
    ans = read_jsonl(base / "answers-v3.jsonl")
    jud = read_jsonl(base / "judgments-unified.jsonl")
    summ = json.loads((base / "summary-unified.json").read_text(encoding="utf-8"))
    rows = [r for r in jud if r.get("ok")]
    by = {(r["qid"], r["arm"]): r for r in rows}
    assert len(rows) == len(by) == 80
    verify_unified_holm(by)
    arms = {}
    for a in ARMS6:
        qs = [r for r in rows if r["arm"] == a]
        n = len(qs)
        dims = {d: statistics.mean(r[d] for r in qs) for d in DIMS}
        overall = statistics.mean(sum(r[d] for d in DIMS) / 4 for r in qs)
        verd = {v: sum(r["verdict"] == v for r in qs) for v in ("correct", "partial", "incorrect")}
        aa = [r for r in ans if r["arm"] == a]
        wall = statistics.mean(r["wall_s"] for r in aa)
        costs = [r["cost_usd"] for r in aa if r.get("cost_usd")]
        cost = statistics.mean(costs) if costs else None
        arms[a] = {"n": n, "dims": dims, "overall": overall, "verdicts": verd,
                   "wall_s": wall, "cost_usd": cost}

    # T6 parsed from the manuscript
    t6 = tex_rows(SRC / "n8d_eval.tex", "tab:external-baselines", 10)
    name2arm = {}  # resolved through arm_of()
    assert len(t6) == 8, t6
    derived = []
    for cells in t6:
        nm = cells[0]
        arm = arm_of(nm)
        got = arms[arm]
        f, c, g, s, ov = (float(cells[2]), float(cells[3]), float(cells[4]),
                          float(cells[5]), float(cells[6]))
        cpi = cells[7]
        sec = "E2-T6"
        check(f"{sec}-{arm}-factual", sec, f"Table 6 {nm} factual", f, got["dims"]["factual"], "judgments-unified.jsonl", tol=0.06)
        check(f"{sec}-{arm}-compl", sec, f"Table 6 {nm} completeness", c, got["dims"]["completeness"], "judgments-unified.jsonl", tol=0.06)
        check(f"{sec}-{arm}-ground", sec, f"Table 6 {nm} groundedness", g, got["dims"]["groundedness"], "judgments-unified.jsonl", tol=0.06)
        check(f"{sec}-{arm}-attrib", sec, f"Table 6 {nm} attribution", s, got["dims"]["sources"], "judgments-unified.jsonl", tol=0.06)
        check(f"{sec}-{arm}-overall", sec, f"Table 6 {nm} overall", ov, got["overall"], "judgments-unified.jsonl", tol=0.006)
        v = got["verdicts"]
        check(f"{sec}-{arm}-cpi", sec, f"Table 6 {nm} C/P/I", cpi,
              f"{v['correct']}/{v['partial']}/{v['incorrect']}", "judgments-unified.jsonl")
        check(f"{sec}-{arm}-time", sec, f"Table 6 {nm} time", float(cells[8]), got["wall_s"], "answers-v3.jsonl", tol=0.051)
        exp_cost = None if cells[9] == "--" else float(cells[9])
        check(f"{sec}-{arm}-cost", sec, f"Table 6 {nm} cost", exp_cost, got["cost_usd"],
              "answers-v3.jsonl", tol=0.00051)
        # cross-check with summary-unified primary
        check(f"{sec}-{arm}-summary", sec, f"summary primary {nm} overall",
              summ["primary"][arm]["overall"], got["overall"], "summary-unified.json", tol=0.006)
        derived.append({"arm": nm, "record_arm": arm, "scope": cells[1],
                        "factual": round(got["dims"]["factual"], 1), "completeness": round(got["dims"]["completeness"], 1),
                        "groundedness": round(got["dims"]["groundedness"], 1), "attribution": round(got["dims"]["sources"], 1),
                        "overall": round_half_up(got["overall"], 2), "correct": v["correct"], "partial": v["partial"],
                        "incorrect": v["incorrect"], "time_s": round(got["wall_s"], 1),
                        "cost_usd": None if got["cost_usd"] is None else round(got["cost_usd"], 3),
                        "n": got["n"]})
    write_csv(TAB / "t6_external_baselines.csv", derived)

    # scope audit: nine questions with an unscoped search, 31 collections in results
    audit = json.loads((base / "hmrs-search-scope-audit.json").read_text(encoding="utf-8"))
    per_q = audit.get("per_question", [])
    unrestricted = {"list", "none"}
    search_tools = {"kb_search_vector", "kb_search_two_stage"}
    n_unscoped = sum(any(c["tool"] in search_tools and c.get("scope_argument") in unrestricted
                         for c in q["calls"]) for q in per_q)
    scopes = [c["scope_argument"] for q in per_q for c in q["calls"] if c["tool"] in search_tools]
    check("E2-scope-list-none", "E2", "13 list arguments and six missing restrictions",
          (13, 6), (scopes.count("list"), scopes.count("none")), "hmrs-search-scope-audit.json")
    check("E2-scope-questions", "E2", "nine of ten questions had an unscoped search",
          9, n_unscoped, "hmrs-search-scope-audit.json per_question calls")
    n_coll = audit.get("distinct_collections_in_results")
    check("E2-scope-collections", "audit transcription", "scope audit reports 31 distinct collection-ID values",
          31, n_coll, "hmrs-search-scope-audit.json (reported aggregate; individual IDs not shipped)")

    # S19 cross-batch
    s19 = tex_rows(SRC / "supplementary-external-baselines.tex", "tab:external-cross-batch", 5)
    assert len(s19) == 8, s19
    s19rows = []
    s18rows = []
    v4 = read_jsonl(base / "judgments-v4-sub.jsonl")
    v4m = {a: statistics.mean(sum(r[d] for d in DIMS) / 4 for r in v4 if r["arm"] == a and r.get("ok"))
           for a in ARMS6}
    r1m, r2m = (mean_overall_by_arm(read_jsonl(REC / "legacy" / filename))
                for filename in ("judgments-v3-round1.jsonl", "judgments-v3.jsonl"))
    for cells in s19:
        nm = cells[0]
        arm = arm_of(nm)
        uni, v4v, r1, r2 = map(float, cells[1:5])
        check(f"S19-{arm}-unified", "S19", f"S19 {nm} unified", uni, arms[arm]["overall"], "judgments-unified.jsonl", tol=0.006)
        check(f"S19-{arm}-v4", "S19", f"S19 {nm} v4", v4v, v4m[arm], "judgments-v4-sub.jsonl", tol=0.006)
        check(f"S19-{arm}-r1", "S19", f"S19 {nm} R1", r1, r1m[arm], "legacy/judgments-v3-round1.jsonl", tol=0.006)
        check(f"S19-{arm}-r2", "S19", f"S19 {nm} R2", r2, r2m[arm], "legacy/judgments-v3.jsonl", tol=0.006)
        s19rows.append({"arm": arm, "unified": round_half_up(arms[arm]["overall"], 2), "v4": round_half_up(v4m[arm], 2),
                        "R1": round_half_up(r1m[arm], 2),
                        "R2": round_half_up(r2m[arm], 2)})
    write_csv(TAB / "s19_cross_batch.csv", s19rows)

    # S20 question-level
    s20 = tex_rows(SRC / "supplementary-external-baselines.tex", "tab:external-question-level", 9)
    assert len(s20) == 10, s20
    s20rows = []
    for cells in s20:
        qid = cells[0]
        for nm, v in zip(["HMRS", "BM25", "Dense", "RRF", "RAPTOR", "LightRAG", "DeepRead", "GraphRAG"],
                         map(float, cells[1:])):
            arm = arm_of(nm)
            r = by[(qid, arm)]
            check(f"S20-{qid}-{arm}", "S20", f"S20 {qid} {nm}", v,
                  sum(r[d] for d in DIMS) / 4, "judgments-unified.jsonl", tol=0.006)
        s20rows.append({"qid": qid, **{a: round_half_up(sum(by[(qid, a)][d] for d in DIMS) / 4, 2) for a in ARMS6}})
    write_csv(TAB / "s20_question_level.csv", s20rows)

    # retrieval context sizes claimed in the supplement provenance paragraph
    sx = (SRC / "supplementary-external-baselines.tex").read_text(encoding="utf-8")
    for arm, want in (("bm25", 9.6), ("dense", 5.7), ("rrf", 9.6), ("raptor", 9.6),
                      ("lightrag", 6.6), ("graphrag", 9.3)):
        aa = [r for r in ans if r["arm"] == arm]
        per_q_chars = [sum(len(s.get("text") or "") for s in (r.get("sources") or [])) for r in aa]
        m = statistics.mean(per_q_chars) / 1000
        check(f"S19-text-{arm}", "S19", f"context characters per question {arm}", want, m,
              "answers-v3.jsonl sources", tol=0.06)
    dr = [r for r in ans if r["arm"] == "deepread-native"]
    dr_chars = [sum(len(s.get("text") or "") for s in (r.get("sources") or [])) for r in dr]
    nonempty = [c for c in dr_chars if c]
    check("S19-text-deepread", "S19", "DeepRead 6.8k over ten / 7.6k over nine recorded",
          (6.8, 7.6), (round(statistics.mean(dr_chars) / 1000, 1), round(statistics.mean(nonempty) / 1000, 1)),
          "answers-v3.jsonl sources", tol=0.06)
    plog = read_jsonl(base / "parse_log.jsonl")
    check("S19-deepread-docs", "S19", "DeepRead native corpus 96 documents",
          96, len(plog), "parse_log.jsonl")
    gold_in = sum(1 for r in dr if r.get("sources") and r["arxiv"] in json.dumps(r["sources"]))
    check("S19-deepread-gold", "S19", "gold paper present in all nine recorded contexts",
          9, gold_in, "answers-v3.jsonl sources")

    # v2: S21 / S18
    v2dir = REC / "baseline_quality_v2"
    a2 = read_jsonl(v2dir / "answers-v2.jsonl")
    j2 = [r for r in read_jsonl(v2dir / "judgments-v2.jsonl") if r.get("ok")]
    v2arms = {"hmrs-agent": "HMRS agent", "bm25": "BM25", "dense": "Dense (BGE-M3)", "rrf": "RRF-order (k=60)"}
    s21 = tex_rows(SRC / "supplementary-external-baselines.tex", "tab:baseline-quality", 11)
    assert len(s21) == 4, s21
    v2derived = []
    for cells in s21:
        arm = arm_of(cells[0])
        qs = [r for r in j2 if r["arm"] == arm]
        dims = {d: statistics.mean(r[d] for r in qs) for d in DIMS}
        overall = statistics.mean(sum(r[d] for d in DIMS) / 4 for r in qs)
        verd = {v: sum(r["verdict"] == v for r in qs) for v in ("correct", "partial", "incorrect")}
        aa = [r for r in a2 if r["arm"] == arm]
        wall = statistics.mean(r["wall_s"] for r in aa)
        cost = statistics.mean(r["cost_usd"] for r in aa)
        gid = sum(1 for r in aa if r["arxiv"] in r["answer"])
        kwc = statistics.mean(sum(k.lower() in r["answer"].lower() for k in r["kw_list"]) /
                              max(1, len(r["kw_list"])) for r in aa)
        sec = "S21"
        check(f"{sec}-{arm}-factual", sec, f"S21 {cells[0]} factual", float(cells[1]), dims["factual"], "judgments-v2.jsonl", tol=0.06)
        check(f"{sec}-{arm}-compl", sec, f"S21 {cells[0]} completeness", float(cells[2]), dims["completeness"], "judgments-v2.jsonl", tol=0.06)
        check(f"{sec}-{arm}-ground", sec, f"S21 {cells[0]} groundedness", float(cells[3]), dims["groundedness"], "judgments-v2.jsonl", tol=0.06)
        check(f"{sec}-{arm}-attrib", sec, f"S21 {cells[0]} attribution", float(cells[4]), dims["sources"], "judgments-v2.jsonl", tol=0.06)
        check(f"{sec}-{arm}-overall", sec, f"S21 {cells[0]} overall", float(cells[5]), overall, "judgments-v2.jsonl", tol=0.006)
        check(f"{sec}-{arm}-cpi", sec, f"S21 {cells[0]} C/P/I", cells[6],
              f"{verd['correct']}/{verd['partial']}/{verd['incorrect']}", "judgments-v2.jsonl")
        check(f"{sec}-{arm}-goldid", sec, f"S21 {cells[0]} gold-ID presence", cells[7],
              f"{gid}/10", "answers-v2.jsonl")
        check(f"{sec}-{arm}-kwcov", sec, f"S21 {cells[0]} keyword coverage", float(cells[8]), kwc, "answers-v2.jsonl", tol=0.006)
        check(f"{sec}-{arm}-time", sec, f"S21 {cells[0]} time", float(cells[9]), wall, "answers-v2.jsonl", tol=0.051)
        check(f"{sec}-{arm}-cost", sec, f"S21 {cells[0]} cost", float(cells[10]), cost, "answers-v2.jsonl", tol=0.00051)
        v2derived.append({"arm": cells[0], "record_arm": arm,
                          "factual": round(dims["factual"], 1), "completeness": round(dims["completeness"], 1),
                          "groundedness": round(dims["groundedness"], 1), "attribution": round(dims["sources"], 1),
                          "overall": round_half_up(overall, 2), "gold_id": f"{gid}/10",
                          "kw_coverage": round(kwc, 2), "time_s": round(wall, 1), "cost_usd": round(cost, 3)})
    write_csv(TAB / "s21_baseline_quality_v2.csv", v2derived)

    s18text = (SRC / "supplementary-baseline-quality.tex").read_text(encoding="utf-8")
    pair = re.compile(r"(BQ\d\d) & ([A-Za-z0-9 -]+?) & (\d) & (\d) & (\d) & (\d) & ([\d.]+) & (\w+)")
    seen = 0
    for m in pair.finditer(s18text):
        qid, nm, f, c, g, s, ov, verdict = m.groups()
        arm = {"HMRS": "hmrs-agent", "BM25": "bm25", "Dense": "dense", "RRF-order": "rrf"}[nm]
        r = next(x for x in j2 if x["qid"] == qid and x["arm"] == arm)
        got = (r["factual"], r["completeness"], r["groundedness"], r["sources"],
               sum(r[d] for d in DIMS) / 4, r["verdict"])
        check(f"S18-{qid}-{arm}", "S18",
              f"S18 {qid} {nm}: dims/overall/verdict",
              (int(f), int(c), int(g), int(s), float(ov), verdict), got, "judgments-v2.jsonl", tol=0.006)
        s18rows.append({"qid": qid, "arm": arm, "factual": r["factual"], "completeness": r["completeness"],
                        "groundedness": r["groundedness"], "attribution": r["sources"],
                        "overall": round(sum(r[d] for d in DIMS) / 4, 2), "verdict": r["verdict"]})
        seen += 1
    check("S18-rowcount", "S18", "S18 has 40 arm-question rows", 40, seen, "supplementary-baseline-quality.tex")
    write_csv(TAB / "s18_baseline_quality_qlevel.csv", s18rows)

    # T6/S19 cross-consistency of the unified column
    for cells in s19:
        nm = cells[0]
        arm = arm_of(nm)
        check(f"S19-T6-{arm}", "cross", f"S19 unified == T6 overall for {nm}",
              summ["primary"][arm]["overall"], float(cells[1]), "T6 vs S19", tol=0.006)



def round_half_up(value: float, digits: int) -> float:
    return float(Decimal(str(value)).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP))


def mean_overall_by_arm(rows: list[dict]) -> dict[str, float]:
    result = {}
    for arm in ARMS6:
        records = [r for r in rows if r.get("ok") and r["arm"] == arm]
        assert len(records) == 10 and len({r["qid"] for r in records}) == 10, arm
        result[arm] = statistics.mean(sum(r[d] for d in DIMS) / 4 for r in records)
    return result


def verify_unified_holm(by: dict[tuple[str, str], dict]) -> None:
    """Seven exact sign tests on paired scores, with ties discarded."""
    qids = sorted({q for q, _ in by})
    assert len(qids) == 10 and len(by) == len(ARMS6) * len(qids)
    derived = {}
    for arm in ARMS6[1:]:
        delta = [sum(by[q, "hmrs-agent"][d] - by[q, arm][d] for d in DIMS) for q in qids]
        wins = sum(x > 0 for x in delta)
        losses = sum(x < 0 for x in delta)
        derived[arm] = {"arm": arm, "wins": wins, "losses": losses, "ties": delta.count(0),
                        "raw_p": sign_p(wins, wins + losses)}
    running_max = 0.0
    for i, row in enumerate(sorted(derived.values(), key=lambda r: r["raw_p"])):
        running_max = max(running_max, min(1.0, (len(derived) - i) * row["raw_p"]))
        row["holm_p"] = running_max
    rows = tex_rows(SRC / "supplementary-external-baselines.tex", "tab:unified-holm", 6)
    assert {arm_of(c[0]) for c in rows} == set(derived) and len(rows) == 7
    for cells in rows:
        arm = arm_of(cells[0])
        row = derived[arm]
        for key, value in zip(("wins", "losses", "ties", "raw_p", "holm_p"), cells[1:]):
            check(f"S22-{arm}-{key}", "S22", f"{arm}: {key}", float(value), row[key],
                  "judgments-unified.jsonl", tol=5e-7)
    check("E2-no-Holm-rejections", "E2", "none of the seven paired comparisons survives Holm at 0.05",
          True, all(r["holm_p"] > .05 for r in derived.values()), "judgments-unified.jsonl")
    check("E2-no-matched-corpus-rejections", "E2", "BM25, Dense and RRF do not reach unadjusted 0.05",
          True, all(derived[a]["raw_p"] > .05 for a in ("bm25", "dense", "rrf")),
          "judgments-unified.jsonl")
    write_csv(TAB / "s22_unified_holm.csv", list(derived.values()))


def wilson(hits: int, n: int, z: float = 1.959964) -> tuple:
    p = hits / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, center - half) * 100, min(1.0, center + half) * 100


def verify_s12_s13() -> None:
    """Supplement Tables S12 (arm data) and S13 (paired contrasts) vs traces."""
    rc = REC / "routing_content_traces"
    runs = {}
    for name, f in (("frozen", "supp_traces_frozen.csv"), ("followup", "supp_traces_followup.csv"),
                    ("nov17", "supp_traces_rerun_20261117.csv")):
        rows = [r for r in read_csv(rc / f) if r["qid"] not in ("R1", "R2", "R3", "R4")]
        per = {}
        for r in rows:
            per.setdefault(r["arm"], {})[r["qid"]] = r["gold_hit"] == "True"
        runs[name] = per

    # S12 rows: Configuration, Frozen, Frozen rate, Wilson CI, Follow-up, Agreement, Nov 17
    s12 = tex_rows(SRC / "supplementary-arm-tables.tex", "tab:s-arm-data", 7)
    assert len(s12) == 8, s12
    alias = {"Read-all": "A1-readall"}
    for cells in s12:
        arm = alias.get(cells[0], cells[0])
        fz = runs["frozen"][arm]
        fu = runs["followup"].get(arm)
        nov = runs["nov17"].get(arm)
        hits, n = sum(fz.values()), len(fz)
        check(f"S12-{arm}-frozen", "S12", f"S12 {cells[0]} frozen count", cells[1], f"{hits}/{n}", "frozen traces")
        rate = float(cells[2].replace(r"\%", ""))
        check(f"S12-{arm}-rate", "S12", f"S12 {cells[0]} frozen rate", rate, hits / n * 100,
              "frozen traces", tol=0.051)
        lo, hi = wilson(hits, n)
        ci = cells[3].strip("[]" + chr(92) + "%").split(",")
        check(f"S12-{arm}-wilson-lo", "S12", f"S12 {cells[0]} Wilson low", float(ci[0]), lo, "recomputed", tol=0.12)
        check(f"S12-{arm}-wilson-hi", "S12", f"S12 {cells[0]} Wilson high", float(ci[1]), hi, "recomputed", tol=0.12)
        if fu is not None:
            check(f"S12-{arm}-follow", "S12", f"S12 {cells[0]} follow-up count", cells[4],
                  f"{sum(fu.values())}/{len(fu)}", "follow-up traces")
            agree = sum(fz[q] == fu[q] for q in fz if q in fu)
            check(f"S12-{arm}-agree", "S12", f"S12 {cells[0]} agreement", cells[5],
                  f"{agree}/{len(fz)}", "frozen vs follow-up traces")
        if nov is not None:
            check(f"S12-{arm}-nov17", "S12", f"S12 {cells[0]} Nov 17 count", cells[6],
                  f"{sum(nov.values())}/{len(nov)}", "Nov 17 traces")

    # S13 rows: Run, Contrast, first-only, second-only, p (exact McNemar = sign test)
    s13 = tex_rows(SRC / "supplementary-arm-tables.tex", "tab:s-paired-data", 5)
    assert len(s13) == 20, len(s13)
    for cells in s13:
        first = cells[0].strip()
        run = "frozen" if first == "Frozen" else "followup" if first == "Follow-up" else "nov17"
        m = re.match(r"(\w+) vs\.?\s*(\w+)", cells[1])
        a, b = m.group(1), m.group(2)
        qa, qb = runs[run][a], runs[run][b]
        only_a = sum(qa[q] and not qb[q] for q in qa if q in qb)
        only_b = sum(qb[q] and not qa[q] for q in qa if q in qb)
        check(f"S13-{run}-{a}-{b}-counts", "S13", f"S13 {cells[0]} {a} vs {b} discordant",
              (int(cells[2]), int(cells[3])), (only_a, only_b), f"{run} traces")
        check(f"S13-{run}-{a}-{b}-p", "S13", f"S13 {cells[0]} {a} vs {b} exact p",
              float(cells[4]), sign_p(only_a, only_a + only_b), "recomputed", tol=6e-5)


def verify_legacy() -> None:
    """Supplement legacy tables that rest on records outside the package:
    S9 (management checks), S14 (30-cell answer grid), S15 (grid summary),
    and the three absent-answer probes of E7."""
    legacy = REC / "legacy"
    r2 = json.loads((legacy / "exp_r2_grade_corrected.json").read_text(encoding="utf-8"))
    r5 = json.loads((legacy / "exp_rerun5_grade.json").read_text(encoding="utf-8"))
    trk = {"P": "a2", "F": "b", "C": "c"}

    def grid_stats(doc: dict) -> dict:
        rows = doc["rows"]
        out = {}
        for letter, track in trk.items():
            qs = [r for r in rows if r["track"] == track]
            out[letter] = {
                "gold": sum(1 for r in qs if r["gold_hit"]),
                "strict": sum(1 for r in qs if r["kw_ok"]),
                "alias": sum(1 for r in qs if r["kw_alias_ok"]),
                "markers": sum(1 for r in qs if r.get("cite_markers")),
                "time": statistics.mean(r["latency_s"] for r in qs),
                "cost": statistics.mean(r["cost_usd"] for r in qs),
                "cells": {r["qid"]: r for r in qs},
            }
        return out

    g2, g5 = grid_stats(r2), grid_stats(r5)

    # S14: per-cell s/a/m for each track and the gold column
    s14 = tex_rows(SRC / "supplementary.tex", "tab:s-answer-grid", 12)
    assert len(s14) == 11, len(s14)          # ten BQ rows + the totals row
    totals = None
    for cells in s14:
        qid, gold = cells[0], cells[2]
        if not re.fullmatch(r"BQ\d\d", qid):
            if "All ten" in " ".join(cells):
                totals = cells
            continue
        for n, letter in enumerate("PFC"):
            st = g2[letter]["cells"][qid]
            s_val, a_val, m_val = cells[3 + 3 * n], cells[4 + 3 * n], cells[5 + 3 * n]
            want = ("yes" if s_val.strip() else "no", "yes" if a_val.strip() else "no", int(m_val))
            got = ("yes" if st["kw_ok"] else "no", "yes" if st["kw_alias_ok"] else "no",
                   len(st.get("cite_markers") or []))
            check(f"S14-{qid}-{letter}", "S14", f"S14 {qid} {letter}: s/a/m", want, got,
                  "exp_r2_grade_corrected.json")
        check(f"S14-{qid}-gold", "S14", f"S14 {qid} gold identifier", gold,
              r2["rows"][[r["qid"] for r in r2["rows"]].index(qid)]["gold"], "exp_r2_grade_corrected.json")

    if totals:
        nums = [int(c) for c in totals[3:12]]
        want = []
        for l in "PFC":                     # totals are grouped (s, a, m) per track
            want += [g2[l]["strict"], g2[l]["alias"],
                     sum(len(r.get("cite_markers") or []) for r in g2[l]["cells"].values())]
        check("S14-totals", "S14", "S14 totals s/a/m for P, F, C", want, nums, "exp_r2_grade_corrected.json")

    # S15: summary rows for the original and common-substrate grids
    s15 = tex_rows(SRC / "supplementary.tex", "tab:s-answer-summary", 7)
    assert len(s15) == 7, len(s15)
    name2grid = {"Original, P": (g2, "P", 52.6, 0.711), "Original, F": (g2, "F", 22.2, 0.487),
                 "Original, C": (g2, "C", 24.5, 0.527), "Common, P": (g5, "P", 37.7, 0.672),
                 "Common, F": (g5, "F", 15.2, 0.377), "Common, C": (g5, "C", 19.6, 0.524)}
    fresh = json.loads((legacy / "answers_fresh_summary.json").read_text(encoding="utf-8"))
    assert len(fresh) == len({r["qid"] for r in fresh}) == 10
    for cells in s15:
        label = cells[0]
        if label == "Current, post-repair":
            n = len(fresh)
            st = [sum(r["grade"]["gold_id_in_answer"] for r in fresh),
                  sum(r["grade"]["kw_hits"] == r["grade"]["kw_total"] for r in fresh),
                  sum(r["grade"]["cited"] for r in fresh)]
            check("S15-post-repair-proxies", "S15", "post-repair gold-ID, strict keyword and marker coverage",
                  (cells[1], cells[2], cells[4]), tuple(f"{k}/{n}" for k in st), "answers_fresh_summary.json")
            check("S15-post-repair-wall", "S15", "post-repair mean wall time (seconds)",
                  float(cells[5]), round_half_up(statistics.mean(r["wall_s"] for r in fresh), 0),
                  "answers_fresh_summary.json (wall_s, not latency_s)", tol=0)
            check("S15-post-repair-cost", "S15", "post-repair total cost (USD)",
                  float(cells[6].removesuffix(" total")),
                  round_half_up(sum(r["cost_usd"] for r in fresh), 2), "answers_fresh_summary.json", tol=0)
            continue
        grid, letter, t_want, c_want = name2grid[label]
        st = grid[letter]
        sec = "S15"
        check(f"{sec}-{label}-gold", sec, f"S15 {label} gold-ID", cells[1], f"{st['gold']}/10", "grid rows")
        check(f"{sec}-{label}-strict", sec, f"S15 {label} strict", cells[2], f"{st['strict']}/10", "grid rows")
        check(f"{sec}-{label}-alias", sec, f"S15 {label} alias", cells[3], f"{st['alias']}/10", "grid rows")
        check(f"{sec}-{label}-markers", sec, f"S15 {label} markers", cells[4], f"{st['markers']}/10", "grid rows")
        check(f"{sec}-{label}-time", sec, f"S15 {label} time", float(cells[5]), st["time"], "grid rows", tol=0.051)
        check(f"{sec}-{label}-cost", sec, f"S15 {label} cost", float(cells[6].replace("/q", "")),
              st["cost"], "grid rows", tol=0.00051)

    # S9: management-layer rows that rest on shipped legacy records
    desc = json.loads((legacy / "desc_audit.json").read_text(encoding="utf-8"))
    entries = [e for v in desc["audit"].values() for e in v]
    check("S9-desc-total", "S9", "328/328 parts had descriptions", 328, len(entries), "desc_audit.json")
    check("S9-desc-ok", "S9", "all descriptions pass the audit", 328,
          sum(1 for e in entries if e["ok"]), "desc_audit.json")
    check("S9-desc-min", "S9", "descriptions at least 60 characters", True,
          min(e["desc_len"] for e in entries) >= 60, "desc_audit.json")
    probe = json.loads((legacy / "probe5_final.json").read_text(encoding="utf-8"))
    check("S9-probe-hit", "S9", "identifier probe finds all 100 target arXiv IDs", 100,
          sum(1 for x in probe if x["probe_hit"]), "probe5_final.json")
    check("S9-probe-unscoped", "S9", "72 probes unscoped", 72,
          sum(1 for x in probe if not x["lib"]), "probe5_final.json")
    check("S9-probe-chunkcopy", "S9", "45 returned a chunk-copy name first", 45,
          sum(1 for x in probe if x["names"] and re.search(r"__k\d\d", x["names"][0])),
          "probe5_final.json")
    ing = json.loads((legacy / "ingest_report.json").read_text(encoding="utf-8"))
    check("S9-parse-ok", "S9", "50/50 parsed and verified", (50, 50),
          (ing["total"], ing["verified"]), "ingest_report.json")
    check("S9-tagflags", "S9", "41 tag flags negative", 41,
          sum(1 for x in ing["routed"] if x.get("tag_ok") is False), "ingest_report.json routed")
    dups = json.loads((legacy / "o2_duplicates.json").read_text(encoding="utf-8"))
    groups = [e for v in dups.values() for e in v]
    check("S9-dups", "S9", "35 candidate groups", 35, len(groups), "o2_duplicates.json")
    sims = [e["similarity"] for e in groups]
    check("S9-dups-range", "S9", "similarities 0.90-0.975", True,
          0.90 <= min(sims) and max(sims) <= 0.975, "o2_duplicates.json")
    audit_path = legacy / "audit_manifest.json"
    am = json.loads(audit_path.read_text(encoding="utf-8"))
    check("S9-content-audit", "S9", "322/322 content audited", (322, 322),
          (am["total"], am["audited"]), "benchmark-suite/results/r2_organize/audit_manifest.json")

    # Historical records: distinguish raw tool results from report-level evidence.
    state = json.loads((legacy / "exp10_ingest_state.json").read_text(encoding="utf-8"))
    enumeration = json.loads((legacy / "exp10_papers_toollayer.json").read_text(encoding="utf-8"))
    check("S9-state-enumeration", "S9", "91 saved names and 79 enumerated records (unmatched)",
          (91, 79), (len(state["saved_all"]), enumeration["n_docs"]), "exp10_ingest_state.json; exp10_papers_toollayer.json")
    tag = json.loads((legacy / "tags_report.json").read_text(encoding="utf-8"))
    check("S9-apply-tags", "S9", "165 tags applied successfully in 47.6 s", (165, 47.6),
          (tag["ok"], tag["seconds"]), "tags_report.json")
    calls = read_jsonl(legacy / "skilltest-calls.jsonl")
    by_step = {r["step"]: r["result"] for r in calls}
    before, after = (by_step[step]["stats"] for step in ("Step1 neo4j check", "Step8 verify stats"))
    check("S9-graph", "S9", "lifecycle run: 316 tags, 658 nodes, 4675 to 4679 edges",
          (316, 658, 4675, 4679), (before["tag_count"], before["node_count"], before["edge_count"], after["edge_count"]),
          "skilltest-calls.jsonl")
    chunks = tuple(by_step[step]["stats"]["chunk_count"] for step in
                   ("index stats", "V4 kb_search_stats", "M4 stats after reindex done"))
    check("E1-rename", "E1", "rename/move residue and forced reindex: 9, 18, 9", (9, 18, 9), chunks,
          "skilltest-calls.jsonl")
    smoke = json.loads((legacy / "experience_smoke.json").read_text(encoding="utf-8"))
    check("E5-candidates", "E5", "separate extraction smoke test records 13 candidates",
          13, smoke["extract_candidates"], "experience_smoke.json")
    check("E5-disposable-empty", "E5", "disposable fixture: no global hits and no pending drafts", (0, 0),
          (by_step["E4 global search"]["count"], by_step["E3 drafts_list"]["count"]), "skilltest-calls.jsonl")
    for cid, file, claim, substrs in (
        ("S9-routing-report", "BENCHMARK.md", "routing campaign reports 202 tags", ("tags: 202",)),
        ("S9-split-report", "BENCHMARK-30000chunk-20260918.md", "campaign report: 165 parts, 9 whole, 156 split, 2672 s",
         ("2672s", "165 个入库文档 = 9 篇整文档 + 156")),
        ("S10-load-report", "STRESS-REPORT.md", "vector-only report: 159/270 in 30 seconds",
         ("30s", "159/270")),
        ("E7-shelf-report", "RETRIEVAL-E2E-REPORT.md", "shelf-output report: 131 documents and 74.9 kB", ("131", "74.9KB")),
        ("E7-pagination-report", "PRODUCTION-LADDER-INDEX.md", "pagination report: 131 documents in four pages",
         ("131 documents paginate in four pages",)),
    ):
        report = (legacy / file).read_text(encoding="utf-8")
        check(cid, "report transcription", claim, True, all(x in report for x in substrs), file)
    diagnostic = json.loads((legacy / "exp3_abstention.json").read_text(encoding="utf-8"))
    kept = [r["kept_n"] for r in diagnostic["probes"]]
    merged = [r["merge_n"] for r in diagnostic["probes"]]
    check("FigS3-probes", "Fig S3", "tool-probe ranges: kept documents and merged candidates",
          (9, 11, 42, 43), (min(kept), max(kept), min(merged), max(merged)), "exp3_abstention.json")
    cut = diagnostic["cut_replay"]
    check("FigS4-cut-replay", "Fig S4", "relative-margin replay: candidate means and preserved gold instances",
          (6.4, 11.9, 16, 17, 17, 17),
          (cut["0.05"]["mean_kept"], cut["0.35"]["mean_kept"], cut["0.15"]["gold_kept"],
           cut["0.15"]["gold_pool"], cut["0.2"]["gold_kept"], cut["0.2"]["gold_pool"]), "exp3_abstention.json cut_replay")
    gate = json.loads((legacy / "exp11_gate_ablation.json").read_text(encoding="utf-8"))["per_question"]
    check("E6-gate-equal-count", "E6", "gate replay has equal final document counts in nine of ten pairs",
          (9, 10), (sum(r["arms"]["C-nogate"]["n_docs"] == r["arms"]["C-judge"]["n_docs"] for r in gate), len(gate)),
          "exp11_gate_ablation.json (counts, not document-set identity)")

    # E7: three industrial probes reported not-found
    exp8b = json.loads((legacy / "exp8b_absent_agent.json").read_text(encoding="utf-8"))
    check("E7-probes", "E7", "three absent-answer probes", 3, len(exp8b), "exp8b_absent_agent.json")
    check("E7-probes-tier", "E7", "all three are absent-tier probes", True,
          all(x.get("tier") == "absent" for x in exp8b), "exp8b_absent_agent.json")


def verify_e6() -> None:
    d = REC / "paired_diagnostics"
    order = read_csv(d / "redraw_verifier_order.csv")
    scores = read_csv(d / "redraw_verifier_scores.csv")
    check("E6-pools", "E6", "16 fixed candidate pools", 16, len(order), "redraw_verifier_order.csv")
    check("E6-fusion", "E6", "fusion keeps gold in top five in 15 pools", 15,
          sum(int(r["fusion_hit"]) for r in order), "redraw_verifier_order.csv")
    check("E6-verifier", "E6", "verifier order keeps 7", 7,
          sum(int(r["verifier_hit"]) for r in order), "redraw_verifier_order.csv")
    lost = sum(1 for r in order if r["fusion_hit"] == "1" and r["verifier_hit"] == "0")
    gained = sum(1 for r in order if r["fusion_hit"] == "0" and r["verifier_hit"] == "1")
    check("E6-discordant", "E6", "eight pools lost a hit, none gained", (8, 0), (lost, gained),
          "redraw_verifier_order.csv")
    check("E6-p", "E6", "exact McNemar p for the ordering change", 0.0078125, sign_p(lost, lost + gained),
          "recomputed", tol=5e-5)
    check("E6-scores", "E6", "191 recorded scores", 191, len(scores), "redraw_verifier_scores.csv")
    gold = [float(r["score"]) for r in scores if r["group"] == "Gold"]
    non = [float(r["score"]) for r in scores if r["group"] == "Non-gold"]
    check("E6-gold-n", "E6", "17 gold candidates scored", 17, len(gold), "redraw_verifier_scores.csv")
    check("E6-nongold-n", "E6", "174 non-gold candidates scored", 174, len(non), "redraw_verifier_scores.csv")
    check("E6-median-gold", "E6", "gold score median 0.8759", 0.8759, statistics.median(gold),
          "redraw_verifier_scores.csv", tol=5e-5)
    check("E6-median-non", "E6", "non-gold median 0.8627", 0.8627, statistics.median(non),
          "redraw_verifier_scores.csv", tol=5e-5)
    check("E6-min", "E6", "no recorded score at or below 0.5", ">0.5",
          ">0.5" if min(gold + non) > 0.5 else f"<=0.5 (min={min(gold + non):.4f})",
          "redraw_verifier_scores.csv")
    per_q = {}
    for r in scores:
        per_q[r["qid"]] = per_q.get(r["qid"], 0) + 1
    missing = [q for q, n in per_q.items() if n == 11]
    check("E6-q14", "E6", "one candidate (Q14... pool) has no recorded score",
          1, len(missing), "redraw_verifier_scores.csv (12 per pool except one)")
    by_pool = {q: sorted((r for r in scores if r["qid"] == q), key=lambda r: float(r["score"]), reverse=True)
               for q in per_q}
    score_hits = {q: int(any(r["group"] == "Gold" for r in pool[:5])) for q, pool in by_pool.items()}
    check("E6-score-order-agreement", "E6", "sorting the recorded scores yields the same verifier flags",
          {r["qid"]: int(r["verifier_hit"]) for r in order}, score_hits,
          "redraw_verifier_scores.csv compared with redraw_verifier_order.csv (separate archives)")
    rows = [{"qid": r["qid"], "fusion_hit": int(r["fusion_hit"]), "verifier_hit": int(r["verifier_hit"])}
            for r in order]
    write_csv(TAB / "e6_pool_hits.csv", rows)


def write_csv(path: Path, rows: list) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-dir", type=Path, default=HERE)
    report_dir = parser.parse_args().report_dir
    report_dir.mkdir(parents=True, exist_ok=True)
    verify_e1()
    verify_e2()
    verify_s12_s13()
    verify_legacy()
    verify_e6()
    npass = sum(c["status"] == "PASS" for c in CHECKS)
    fails = [c for c in CHECKS if c["status"] != "PASS"]
    (report_dir / "report.json").write_text(json.dumps(
        {"checks": CHECKS, "pass": npass, "fail": len(fails)}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    secs = {}
    for c in CHECKS:
        s = secs.setdefault(c["section"], {"pass": 0, "fail": 0})
        s["PASS" if c["status"] == "PASS" else "FAIL" if c["status"] == "FAIL" else "INFO"] = \
            s.get("PASS" if c["status"] == "PASS" else "FAIL", 0) + 1
    lines = ["# Verification report — paper/supplement values vs shipped records", "",
             f"Checks: {len(CHECKS)} — PASS {npass}, FAIL {len(fails)}", ""]
    for sec in sorted(secs):
        lines.append(f"- {sec}: " + ", ".join(f"{k} {v}" for k, v in sorted(secs[sec].items())))
    if fails:
        lines += ["", "## Failures", ""]
        for c in fails:
            lines.append(f"- **{c['id']}** ({c['source']}): claim {c['expected']!r} vs recomputed {c['recomputed']!r}")
    lines += ["", "Full machine-readable report: `verification/report.json`."]
    (report_dir / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:40]))
    print(f"\nPASS {npass} / {len(CHECKS)}")
    if fails:
        for c in fails[:20]:
            print("FAIL", c["id"], "|", c["claim"], "| expected", c["expected"], "| got", c["recomputed"])
        raise SystemExit(1)


if __name__ == "__main__":
    main()
