#!/usr/bin/env python3
"""Offline supplementary rescore of the ten archived November 15 BQ answers.

Run with Python 3.10+ and -I, explicitly passing --repo-root and either
--output-dir (must not exist) or --check-dir (byte-compare existing CSVs).
Only BQ01.json through BQ10.json under the fixed archive path, the named
annotation sources, and the original grader's bytes are read. The original
runner is never imported or executed. CSVs contain no answers or prompts.

The primary IDs come from qa_questions.json; the historical first-cell term
lists are the ones used by run100_answers.py. Both term thresholds use its
substring matcher, so this is threshold sensitivity, not a different grader.
Corrected E5 BQ06 is a cross-annotation diagnostic, not a rerun of that prompt.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from decimal import Decimal
from pathlib import Path
from statistics import median

ARCHIVE = Path("review/_exp_rerun_20261114/answers_fresh")
QIDS = tuple(f"BQ{i:02d}" for i in range(1, 11))
PAPERS = Path("benchmark-suite/data/papers")
QUESTIONS = PAPERS / "qa_questions.json"
E5 = PAPERS / "qa_questions_e5_corrected.json"
RETRY = PAPERS / "_bq06_retry.json"
HISTORY = Path("benchmark-suite/results/paper_report.json")
GRADER = Path("review/experiment-redesign-20261101/scripts/run100_answers.py")
CASE_CSV = "bq_20261115_per_case.csv"
AGG_CSV = "bq_20261115_aggregate.csv"

# Verbatim broad alternatives and case-sensitive, unbounded matching.
BROAD = re.compile(
    r"(arxiv:\d{4}\.\d{4,5}|\[\d{1,2}\]|§\d[\.\d]*|Table \d+|"
    r"part \d+ of \d+|Fig\.? \d+|\d{4}\.\d{4,5})"
)
# Narrow diagnostic: explicit arXiv: label or arxiv.org abs/pdf URL with a
# bounded modern ID, case-insensitive, optional version. Not a link check.
EXPLICIT_ARXIV = re.compile(
    r"(?<!\w)(?:arxiv:[ \t]*|https?://arxiv\.org/(?:abs|pdf)/)"
    r"[0-9]{4}\.[0-9]{4,5}(?:v[1-9][0-9]*)?(?!\w|\.[0-9])",
    re.IGNORECASE,
)


def csv_bytes(rows: list[dict]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def term_scores(answer: str, terms: list[str]) -> dict[str, int]:
    if not terms or any(not isinstance(t, str) or not t for t in terms):
        raise ValueError("Missing or invalid annotated term list")
    low = answer.lower()
    n = len(terms)
    hits = sum(t.lower() in low for t in terms)
    need = (3 * n + 4) // 5
    return {"term_hits": hits, "term_total": n, "terms_full": int(hits == n),
            "term_required_ceil_3n_5": need, "terms_ge_ceil_3n_5": int(hits >= need)}


def metric_number(value: object, field: str, qid: str) -> Decimal:
    if type(value) not in (Decimal, int):
        raise ValueError(f"{qid}: missing or invalid {field}")
    number = Decimal(value)
    if not number.is_finite() or number < 0:
        raise ValueError(f"{qid}: invalid {field}")
    return number


def rescore(repo: Path) -> dict[str, bytes]:
    hashes = {}

    def read_bytes(path: Path) -> bytes:
        data = (repo / path).read_bytes()
        hashes[path.as_posix()] = hashlib.sha256(data).hexdigest()
        return data

    def read_json(path: Path) -> dict:
        return json.loads(read_bytes(path), parse_float=Decimal)

    questions = {q["qid"]: q for q in read_json(QUESTIONS)["questions"]}
    corrected = next(q for q in read_json(E5)["questions"] if q["qid"] == "BQ06")
    retry = next(q for q in read_json(RETRY)["questions"] if q["qid"] == "BQ06")
    history = read_json(HISTORY)["per_question"]
    read_bytes(GRADER)  # provenance only; do not execute the live runner
    cases = []
    summary = []

    def add(scope: str, metric: str, value: object = "", denominator: int | str = "",
            sha256: str = "") -> None:
        summary.append({"scope": scope, "metric": metric, "value": value,
                        "denominator": denominator, "source_sha256": sha256})

    for qid in QIDS:
        path = ARCHIVE / f"{qid}.json"
        raw = read_json(path)
        q = questions[qid]
        gid = q["arxiv_id"]
        terms = history[qid]["cells"][0]["kw_list"]
        if (raw["qid"] != qid or raw["arxiv"] != gid or raw["question"] != q["question"]
                or history[qid]["gold"] != gid or history[qid]["question"] != q["question"]
                or terms != q["gold_keywords"]):
            raise ValueError(f"{qid}: archive, primary annotation, or historical term mismatch")
        answer = raw["answer"]
        if not isinstance(answer, str):
            raise ValueError(f"{qid}: answer is not a string")
        cases.append({
            "qid": qid, "source_sha256": hashes[path.as_posix()],
            "completed": int(raw["http"] == 200 and raw["success"] is True
                             and raw["error"] == "" and bool(answer.strip())),
            "gold_id_substring": int(gid in answer),
            **term_scores(answer, terms),
            "broad_markers": len(BROAD.findall(answer)),
            "broad_matches_gold_id_alone": int(bool(BROAD.search(gid))),
            "broad_markers_with_gold_id_masked": len(BROAD.findall(
                answer.replace(gid, "X" * len(gid)))),
            "explicit_arxiv_markers": len(EXPLICIT_ARXIV.findall(answer)),
            "wall_s": metric_number(raw["wall_s"], "wall_s", qid),
            "cost_usd": metric_number(raw["cost_usd"], "cost_usd", qid),
        })
        if qid == "BQ06":
            scope = "BQ06_E5_corrected_annotation_on_original_answer"
            add(scope, "question_exactly_matches_archive", int(corrected["question"] == raw["question"]))
            add(scope, "gold_id_same_as_original", int(corrected["arxiv_id"] == gid))
            add(scope, "term_list_same_as_original", int(corrected["gold_keywords"] == terms))
            add(scope, "gold_id_substring", int(corrected["arxiv_id"] in answer), 1)
            e5_scores = term_scores(answer, corrected["gold_keywords"])
            add(scope, "term_hits", e5_scores["term_hits"], e5_scores["term_total"])
            for k in ("terms_full", "terms_ge_ceil_3n_5"):
                add(scope, k, e5_scores[k], 1)
            scope = "BQ06_retry_prompt_fixture"
            add(scope, "question_exactly_matches_archive", int(retry["question"] == raw["question"]))
            add(scope, "has_gold_id_and_terms", int(bool(retry.get("arxiv_id") and retry.get("gold_keywords"))))

    version_rows = summary.copy()
    summary.clear()
    n = len(cases)
    add("original_archive", "n_cases", n)
    for k in ("completed", "gold_id_substring", "terms_full", "terms_ge_ceil_3n_5",
              "broad_markers", "broad_matches_gold_id_alone",
              "broad_markers_with_gold_id_masked", "explicit_arxiv_markers"):
        add("original_archive", f"cases_with_{k}", sum(row[k] > 0 for row in cases), n)
    add("original_archive", "pooled_term_hits", sum(row["term_hits"] for row in cases),
        sum(row["term_total"] for row in cases))
    for k in ("broad_markers", "broad_markers_with_gold_id_masked", "explicit_arxiv_markers"):
        add("original_archive", f"total_{k}", sum(row[k] for row in cases))
    for k in ("wall_s", "cost_usd"):
        vals = [row[k] for row in cases]
        total = sum(vals)
        for stat, value in (("sum", total), ("mean", total / n), ("median", median(vals)),
                            ("min", min(vals)), ("max", max(vals))):
            add("original_archive", f"{k}_{stat}", format(value, ".8f" if k == "cost_usd" else "f"))
    summary.extend(version_rows)
    for path in (QUESTIONS, HISTORY, E5, RETRY, GRADER):
        add("source", path.as_posix(), sha256=hashes[path.as_posix()])
    return {CASE_CSV: csv_bytes(cases), AGG_CSV: csv_bytes(summary)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True, type=Path)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--output-dir", type=Path, help="new directory for the two CSVs")
    action.add_argument("--check-dir", type=Path, help="read-only byte comparison with existing CSVs")
    args = parser.parse_args()
    try:
        outputs = rescore(args.repo_root)
        if args.check_dir is not None:
            for name, data in outputs.items():
                if (args.check_dir / name).read_bytes() != data:
                    raise ValueError(f"Recomputed bytes differ: {name}")
            print(f"Verified {len(outputs)} CSVs byte-for-byte.")
        else:
            args.output_dir.mkdir(exist_ok=False)
            for name, data in outputs.items():
                with (args.output_dir / name).open("xb") as stream:
                    stream.write(data)
            print(f"Wrote {len(outputs)} CSVs to {args.output_dir}.")
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as exc:
        parser.exit(1, f"Offline rescore failed: {exc}\n")


if __name__ == "__main__":
    main()
