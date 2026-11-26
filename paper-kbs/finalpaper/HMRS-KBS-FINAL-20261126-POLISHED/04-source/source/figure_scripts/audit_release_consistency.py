"""Fail-closed audit of the bundled native E2 records and release disclosures.

Run after building all submission PDFs. The project benchmark verifier checks
these and other experiments against the printed tables and original records.
"""
from hashlib import sha256
import json
from pathlib import Path
import re
from decimal import Decimal, ROUND_HALF_UP

SRC = Path(__file__).resolve().parents[1]
PACKAGE = SRC.parents[1]
DATA = SRC / "experiment_data/external_baselines_v3"
OUT = SRC.parent / "release/audit"
DIMS = ("factual", "completeness", "groundedness", "sources")


def rows(name):
    return [json.loads(line) for line in (DATA / name).read_text(encoding="utf-8").splitlines() if line.strip()]


def main():
    answers = rows("answers-v3.jsonl")
    judgments = rows("judgments-unified.jsonl")
    summary = json.loads((DATA / "summary-unified.json").read_text(encoding="utf-8"))["primary"]
    by_id = lambda records: {(r["arm"], r["qid"]) for r in records}
    main_text = (SRC / "n8d_eval.tex").read_text(encoding="utf-8")
    supp = (SRC / "supplementary-external-baselines.tex").read_text(encoding="utf-8")
    case = (SRC / "n8b_eval.tex").read_text(encoding="utf-8")
    checks = {
        "80_unique_paired_answer_judgment_ids": len(answers) == len(judgments) == len(by_id(answers)) == 80 and by_id(answers) == by_id(judgments),
        "case_excluded_from_e2_and_e3": "not included in the E2 judging or the E3 routing counts" in " ".join(case.split()),
        "case_packaged": (SRC / "figs/fig5_tiered_case.pdf").is_file() and any((SRC / "experiment_data/tiered_case").glob("*.json")),
        "qa_transcript_present": (PACKAGE / "03-supplementary/external-baselines-qa.pdf").is_file(),
        "native_scope_disclosed": "19 search" in main_text and "31 distinct collection-ID values" in " ".join(main_text.split()),
        "earlier_judging_not_pooled": bool(re.search(r"Not pooled\s+with the unified\s+batch", supp)),
    }
    for arm, tab in summary.items():
        rs = [r for r in judgments if r["arm"] == arm]
        overall = (Decimal(sum(r[k] for r in rs for k in DIMS)) / max(1, len(rs) * len(DIMS))).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
        checks[f"{arm}:mean_and_verdicts"] = (len(rs) == 10 and
            overall == Decimal(str(tab["overall"])) and
            all(sum(r["verdict"] == v for r in rs) == tab["verdicts"].get(v, 0)
                for v in ("correct", "partial", "incorrect")))
    inputs = [DATA / f for f in ("answers-v3.jsonl", "judgments-unified.jsonl", "summary-unified.json")]
    inputs += [SRC / f for f in ("n8b_eval.tex", "n8d_eval.tex", "supplementary-external-baselines.tex")]
    report = {"checks": checks, "input_sha256": {p.relative_to(SRC).as_posix(): sha256(p.read_bytes()).hexdigest() for p in inputs}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "consistency-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = ["# Submission evidence checks", "", "The native E2 comparison and the separate BQ07 Figure 5 trace are distinct records.", ""]
    lines += [f"- {name}: {'PASS' if ok else 'FAIL'}" for name, ok in checks.items()]
    (OUT / "consistency-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"PASS {sum(checks.values())}/{len(checks)}")
    if not all(checks.values()):
        raise SystemExit(f"Failed: {[k for k, ok in checks.items() if not ok]}")


if __name__ == "__main__":
    main()
