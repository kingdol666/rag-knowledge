#!/usr/bin/env python3
"""Independent re-derivation of the paper's headline numbers — stdlib only.

This is NOT the grader. It re-implements the metrics from first principles
so a third party (reviewer / co-author / future you) can check the claims
without trusting any project script:

  grounded  : the designated paper's arXiv id appears in the saved answer, in the
              saved evidence texts, or in the saved tool-call trace
  keyword   : ALL gold keywords match at word boundaries (the journal paper's
              "strict keywords" row; case-insensitive; digits also match
              ordinal suffixes)
  cited     : the answer names a part / section / table marker (regex identical
              to the definition recorded in the grade JSON, Roman-numeral
              section locators included)
  chunk     : dense chunk identifiers, reported separately per the paper

Claims checked (paper-kbs/tex/journal_20p/n8c_eval.tex, Table tab:e5-arms
and the E5/E4 prose): grounded 10/10/10, strict keywords 9/10 each,
citation markers 9/10, 7/10, 2/10, chunk identifiers 5/0/7,
latency 52.6 / 22.2 / 24.5 s, cost $0.711 / $0.487 / $0.527.

Inputs (read-only):
  benchmark-suite/results/runs/<RUN>/track_<track>_<QID>.json   raw harness output
  benchmark-suite/data/papers/qa_questions.json                 question set

Usage:  python TEST-RESULTS/verify.py [--run <run-dir-name>]
Exit 0 = every checked claim reproduces.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
RESULTS = REPO / "benchmark-suite" / "results"
RUNS = RESULTS / "runs"
DEFAULT_RUN = "run-20261013T094350Z-5f9faac"
SENTINELS = ("KB_TOOLS_NOT_READY", "KB_NO_RETRIEVAL")
TRACKS = ("a2", "b", "c")
# the journal table grades the CORRECTED annotations; the pre-correction set
# (qa_questions.json, BQ06 gold key mis-aligned with its source paper) is kept
# in version control and regraded in exp_r2_grade_original_revised.json.
QFILE = REPO / "benchmark-suite" / "data" / "papers" / "qa_questions_e5_corrected.json"

# Claims of paper-kbs/tex/journal_20p (Table tab:e5-arms; E4/E5 prose).
CLAIMS = {
    "a2": dict(grounded=10, kw=9, cited=9, chunk=5, lat=52.6, cost=0.711),
    "b":  dict(grounded=10, kw=9, cited=7, chunk=0, lat=22.2, cost=0.487),
    "c":  dict(grounded=10, kw=9, cited=2, chunk=7, lat=24.5, cost=0.527),
}

# citation markers — identical to the definition recorded in
# exp_r2_grade_corrected.json 'citation_definition' (part N of M, numeric or
# Roman section locators, §-prefixed locators).
CITE_RE = re.compile(
    r"\bparts?\s+\d+\s+of\s+\d+"
    r"|\b(?:section|sections|table|tables|appendix|appendices)\s+"
    r"(?:\d+(?:\.\d+)*(?:-[A-Z0-9]+)?|[IVXLCDM]+(?:-[A-Z0-9]+)?)\b"
    r"|§\s*(?:\d+(?:\.\d+)*(?:-[A-Z0-9]+)?|[IVXLCDM]+(?:-[A-Z0-9]+)?)\b",
    re.IGNORECASE,
)
# dense chunk references are reported separately and are NOT part of "cited"
CHUNK_RE = re.compile(r"\bchunk[_ ]?(?:index|id)?\s*\d+", re.IGNORECASE)


def kw_hit(answer: str, keywords: list[str]) -> list[str]:
    """Word-boundary keyword matcher (mirrors the documented grading rule)."""
    hits = []
    for kw in keywords:
        core = re.escape(kw.lower())
        if kw.isdigit():
            core += r"(?:st|nd|rd|th)?"
        if re.search(r"(?<![a-z0-9])" + core + r"(?![a-z0-9])", answer, re.IGNORECASE):
            hits.append(kw)
    return hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=DEFAULT_RUN)
    args = ap.parse_args()
    run = RUNS / args.run

    print("=" * 78)
    print(f"independent re-derivation · run {args.run}")
    print("=" * 78)
    if not run.is_dir():
        print(f"FAIL: run directory not found: {run}")
        return 1

    questions = json.loads(QFILE.read_text(encoding="utf-8"))
    if isinstance(questions, dict):
        questions = questions.get("questions", questions)
    qmap = {q.get("qid") or q.get("id"): q for q in questions}

    failures: list[str] = []
    summary: dict[str, dict] = {}

    for track in TRACKS:
        cells, errs, sentinels, grounded, kw_ok, cited, chunked, lat, cost, tools = \
            [], 0, 0, 0, 0, 0, 0, [], [], []
        for qid, q in qmap.items():
            f = run / f"track_{track}_{qid}.json"
            if not f.is_file():
                failures.append(f"missing cell {track}/{qid}")
                continue
            r = json.loads(f.read_text(encoding="utf-8"))
            cells.append(r)
            answer = str(r.get("answer") or "")
            blob = answer + "\n" + json.dumps(r.get("tool_calls") or [], ensure_ascii=False) + "\n" + \
                "\n".join(r.get("texts_full") or [])
            if r.get("error"):
                errs += 1
            if any(s in answer for s in SENTINELS):
                sentinels += 1
                continue
            gid = str(q.get("arxiv_id") or "")
            if gid and (gid in blob or gid.replace("-", "/") in blob):
                grounded += 1
            kws = q.get("gold_keywords") or []
            # strict keyword coverage: the journal paper's Table row requires
            # ALL gold keywords in the answer text (not the demo's 60% rule).
            if kws and len(kw_hit(answer, kws)) == len(kws):
                kw_ok += 1
            if CITE_RE.search(answer):
                cited += 1
            if CHUNK_RE.search(answer):
                chunked += 1
            if isinstance(r.get("latency_s"), (int, float)):
                lat.append(r["latency_s"])
            if isinstance(r.get("total_cost_usd"), (int, float)):
                cost.append(r["total_cost_usd"])
            tools.append(len(r.get("tool_calls") or []))

        n = len(cells)
        avg_lat = round(sum(lat) / len(lat), 1) if lat else 0.0
        avg_cost = round(sum(cost) / len(cost), 4) if cost else 0.0
        avg_tools = round(sum(tools) / len(tools), 1) if tools else 0.0
        summary[track] = dict(n=n, errors=errs, sentinels=sentinels, grounded=grounded,
                              kw=kw_ok, cited=cited, avg_latency_s=avg_lat,
                              avg_cost_usd=avg_cost, avg_tools=avg_tools)
        cl = CLAIMS[track]
        print(f"\n[{track}] {n} cells · errors {errs} · sentinels {sentinels}")
        print(f"   grounded {grounded}/{n}   (journal tab:e5-arms = {cl['grounded']}/10)")
        print(f"   strict kw {kw_ok}/{n}   (journal tab:e5-arms = {cl['kw']}/10)")
        print(f"   cited    {cited}/{n}   (journal tab:e5-arms = {cl['cited']}/10)")
        print(f"   chunk-id {chunked}/{n}   (journal tab:e5-arms = {cl['chunk']})")
        print(f"   latency  {avg_lat} s   (journal tab:e5-arms = {cl['lat']} s)")
        print(f"   cost     ${avg_cost}  (journal tab:e5-arms = ${cl['cost']})")
        checks = (
            ("grounded", grounded, cl["grounded"], 0),
            ("strict kw", kw_ok, cl["kw"], 0),
            ("cited", cited, cl["cited"], 0),
            ("chunk-id", chunked, cl["chunk"], 0),
            ("latency", avg_lat, cl["lat"], 0.05),
            ("cost", round(avg_cost, 3), cl["cost"], 0.001),
        )
        for label, obs, want, tol in checks:
            if abs(obs - want) > tol:
                failures.append(f"{track} {label}: observed {obs} vs journal claim {want}")
        if errs:
            failures.append(f"{track}: {errs} cells carry an error field")
        if sentinels:
            failures.append(f"{track}: {sentinels} sentinel cells (tool face was missing)")

    # The grid total has two independent homes: the run manifest the harness wrote
    # and the sum of the per-cell costs. They disagreed once ($17.03 vs $17.25) and
    # only a human noticed, so assert the agreement here.
    manifest = run / "run_manifest.json"
    if manifest.is_file():
        m = json.loads(manifest.read_text(encoding="utf-8"))
        declared = m.get("total_cost_usd")
        summed = round(sum(float(r["total_cost_usd"])
                           for r in (json.loads(f.read_text(encoding="utf-8"))
                                     for t in TRACKS
                                     for f in sorted(run.glob(f"track_{t}_*.json")))), 4)
        print(f"\n[cost]   manifest total_cost_usd = {declared}   "
              f"sum over 30 cells = {summed}")
        if declared is None or abs(float(declared) - summed) > 0.01:
            failures.append(f"cost total: manifest {declared} vs cell sum {summed}")
    else:
        print("\n[cost]   run_manifest.json absent — cost cross-check skipped")

    print("\n" + "=" * 78)
    if failures:
        print(f"RESULT: {len(failures)} claim(s) did NOT reproduce")
        for f in failures:
            print("   ✗", f)
        return 1
    print("RESULT: PASS — every grounded / strict-keyword / cited / chunk / latency / cost")
    print("        claim of paper-kbs/tex/journal_20p re-derives from the saved run.")
    print(f"        (run {args.run} · saved evidence under benchmark-suite/results/runs/{args.run}/)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
