#!/usr/bin/env python3
"""Build the E3 question-level score table from hash-pinned records."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "experiment_data" / "baseline_quality_v2"
OUTPUT = HERE.parent / "supplementary-baseline-quality.tex"
EXPECTED = {
    "answers-v2.jsonl": "4254613b4e23ec9ea3d022a6bce95967ec7d1334bdcd7e46d61b99083ec11e42",
    "judgments-v2.jsonl": "1aea092f722962f029278fca6adec4664bb9fb9c7d47759aa7079d124fd66842",
}
ARMS = {
    "hmrs-agent": "HMRS",
    "bm25": "BM25",
    "dense": "Dense",
    "rrf": "RRF-order",
}
QUESTIONS = [f"BQ{i:02d}" for i in range(1, 11)]


def load_rows(name: str) -> dict[tuple[str, str], dict]:
    path = DATA / name
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != EXPECTED[name]:
        raise ValueError(f"SHA256 mismatch for {name}: {digest}")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    keyed = {(row["qid"], row["arm"]): row for row in rows}
    if len(rows) != 40 or len(keyed) != 40:
        raise ValueError(f"Expected 40 unique rows in {name}; found {len(keyed)}")
    return keyed


def main() -> None:
    answers = load_rows("answers-v2.jsonl")
    judgments = load_rows("judgments-v2.jsonl")
    rows = [
        r"\begin{table*}[!t]",
        r"\centering",
        r"\footnotesize",
        r"\setlength{\tabcolsep}{4pt}",
        r"\renewcommand{\arraystretch}{1.0}",
        r"\caption{Question-level E3 judge scores by arm. Each cell represents one answer",
        r"from the single run. Overall is the unweighted mean of factual correctness,",
        r"completeness, groundedness and attribution. The judge saw one anonymised",
        r"answer and a head-only gold-paper prefix, not the retrieved context; the",
        r"scores should be interpreted in light of the protocol limitations discussed in the main text.}",
        r"\label{tab:baseline-quality-question-level}",
        r"\begin{tabular}{@{}llrrrrrl@{}}",
        r"\toprule",
        r"Question & Arm & Factual & Complete & Grounded & Attribution & Overall & Verdict\\",
        r"\midrule",
    ]
    for qid in QUESTIONS:
        for arm, label in ARMS.items():
            key = (qid, arm)
            if key not in answers or key not in judgments:
                raise ValueError(f"Missing answer or judgment: {key}")
            answer = answers[key]
            judge = judgments[key]
            if not answer.get("success") or not judge.get("ok"):
                raise ValueError(f"Unsuccessful E3 row: {key}")
            overall = sum(judge[d] for d in ("factual", "completeness", "groundedness", "sources")) / 4
            rows.append(
                f"{qid} & {label} & {judge['factual']} & {judge['completeness']} & "
                f"{judge['groundedness']} & {judge['sources']} & {overall:.2f} & "
                f"{judge['verdict']}\\\\"
            )
        if qid != QUESTIONS[-1]:
            rows.append(r"\addlinespace[1pt]")
    rows.extend([r"\bottomrule", r"\end{tabular}", r"\end{table*}"])
    OUTPUT.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.name}: {len(QUESTIONS) * len(ARMS)} rows")


if __name__ == "__main__":
    main()
