#!/usr/bin/env python3
"""Independent re-derivation of the paper's headline numbers — stdlib only.

This is NOT the grader. It re-implements the three metrics from first principles
so a third party (reviewer / co-author / future you) can check the claims without
trusting any project script:

  grounded  : the designated paper's arXiv id appears in the saved answer, in the
              saved evidence texts, or in the saved tool-call trace
  keyword   : >= ceil(60% of the question's gold key facts) matched at word
              boundaries (case-insensitive; digits also match ordinal suffixes)
  cited     : the answer names a part / section / table marker

Inputs (read-only):
  benchmark-suite/results/runs/<RUN>/track_<track>_<QID>.json   raw harness output
  benchmark-suite/data/papers/qa_questions.json                 question set
  paper_demo/tex/main.tex                                       the paper's macros

Usage:  python TEST-RESULTS/verify.py [--run <run-dir-name>]
Exit 0 = every checked claim reproduces.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
RESULTS = REPO / "benchmark-suite" / "results"
RUNS = RESULTS / "runs"
QFILE = REPO / "benchmark-suite" / "data" / "papers" / "qa_questions.json"
MAIN_TEX = REPO / "paper_demo" / "tex" / "main.tex"

DEFAULT_RUN = "run-20261013T094350Z-5f9faac"
SENTINELS = ("KB_TOOLS_NOT_READY", "KB_NO_RETRIEVAL")
TRACK_MACRO = {"a2": "A", "b": "B", "c": "C"}

# citation markers — the paper's definition of "cited" (part / section / table).
# Written out here verbatim so this checker does not import the project grader.
CITE_RE = re.compile(
    r"(?:\bparts?\s+\d+\s+of\s+\d+"                       # "part 1 of 3"
    r"|\b(?:section|sections|table|tables|appendix|appendices)\s+(?:\d+(?:\.\d+)*|[A-Z](?:\.\d+)*)"
    r"|§\s*\d+(?:\.\d+)*)",                               # "§3.2"
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


def read_macros() -> dict[str, str]:
    text = MAIN_TEX.read_text(encoding="utf-8")
    return dict(re.findall(r"\\newcommand\{\\NUM(\w+)\}\{([^}]*)\}", text))


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
    macros = read_macros()

    failures: list[str] = []
    summary: dict[str, dict] = {}

    for track in ("a2", "b", "c"):
        cells, errs, sentinels, grounded, kw_ok, cited, lat, cost, tools = [], 0, 0, 0, 0, 0, [], [], []
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
            need = max(1, math.ceil(len(kws) * 3 / 5))
            # keyword-verified is judged on the ANSWER text (the paper's metric);
            # grounded additionally accepts the saved trace / evidence texts.
            if len(kw_hit(answer, kws)) >= need:
                kw_ok += 1
            if CITE_RE.search(answer):
                cited += 1
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
        m = TRACK_MACRO[track]
        print(f"\n[{track}] {n} cells · errors {errs} · sentinels {sentinels}")
        print(f"   grounded {grounded}/{n}   (paper \\NUMgrounded{m} = {macros.get('grounded' + m)})")
        print(f"   keyword  {kw_ok}/{n}   (paper \\NUMkw{m} = {macros.get('kw' + m)})")
        print(f"   cited    {cited}/{n}   (paper \\NUMcite{m} = {macros.get('cite' + m)})")
        print(f"   latency  {avg_lat} s   (paper \\NUMlat{m} = {macros.get('lat' + m)})")
        print(f"   cost     ${avg_cost}  (paper \\NUMcost{m} = {macros.get('cost' + m)})")
        for label, obs, macro in (("grounded", grounded, "grounded"), ("keyword", kw_ok, "kw"),
                                  ("cited", cited, "cite"), ("latency", avg_lat, "lat"),
                                  ("cost", avg_cost, "cost")):
            want = macros.get(macro + m)
            if want is None:
                continue
            if label == "latency":
                want_v = float(re.sub(r"[^0-9.]", "", want))
            elif label == "cost":
                want_v = float(re.sub(r"[^0-9.]", "", want))
            else:
                want_v = int(want)
            ok = abs(obs - want_v) <= (1.0 if label in ("latency", "cost") else 0)
            if not ok:
                failures.append(f"{track} {label}: observed {obs} vs paper {want_v}")
        if errs:
            failures.append(f"{track}: {errs} cells carry an error field")
        if sentinels:
            failures.append(f"{track}: {sentinels} sentinel cells (tool face was missing)")

    print("\n" + "=" * 78)
    if failures:
        print(f"RESULT: {len(failures)} claim(s) did NOT reproduce")
        for f in failures:
            print("   ✗", f)
        return 1
    print("RESULT: PASS — every grounded / keyword / cited / latency / cost claim re-derives")
    print(f"        (run {args.run} · saved evidence under benchmark-suite/results/runs/{args.run}/)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
