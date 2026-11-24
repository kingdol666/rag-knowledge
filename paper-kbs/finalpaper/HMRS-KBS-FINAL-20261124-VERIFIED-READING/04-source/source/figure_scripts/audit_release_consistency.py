"""Release consistency audit: data vs manuscript headline values.

Checks the unified eight-arm batch (primary E2) against summary-unified.json,
the paired-stats manifest, scope disclosures in the manuscript, and the
presence of the companion QA transcript. Writes release/audit reports.
"""
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
RELEASE = HERE.parent / "release"
DATA = HERE / "experiment_data" / "external_baselines_v3"

EXPECTED_OVERALL = {"hmrs-agent": 5.00, "bm25": 4.95, "dense": 4.90,
                    "rrf": 4.83, "raptor": 4.80, "lightrag": 4.75,
                    "deepread-native": 4.70, "graphrag": 4.28}


def sha256(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    answers = [json.loads(l) for l in (DATA / "answers-v3.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    judgments = [json.loads(l) for l in (DATA / "judgments-unified.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    summary = json.loads((DATA / "summary-unified.json").read_text(encoding="utf-8"))["primary"]
    paired = json.loads((DATA / "paired-unified.json").read_text(encoding="utf-8"))
    n8d = (HERE / "n8d_eval.tex").read_text(encoding="utf-8")
    n8d_body = "\n".join(l for l in n8d.splitlines() if not l.lstrip().startswith("%"))
    threats = (HERE / "n10_threats.tex").read_text(encoding="utf-8")
    supp_ext = (HERE / "supplementary-external-baselines.tex").read_text(encoding="utf-8")

    checks = {}
    checks["answers_80"] = len(answers) == 80
    checks["judgments_80"] = len(judgments) == 80
    for arm, want in EXPECTED_OVERALL.items():
        checks[f"{arm}_overall_{want:.2f}"] = abs(summary[arm]["overall"] - want) < 0.005
    checks["hmrs_verdict_10"] = summary["hmrs-agent"]["verdicts"]["correct"] == 10
    checks["paired_manifest_crosscheck"] = paired.get("mean_cross_check") == "PASS"
    checks["paired_no_significance"] = all(
        c["overall"]["sign_p"] >= 0.25 and c["verdict"]["mcnemar_p"] >= 0.5
        for c in paired["contrasts"].values())
    body = n8d + threats + supp_ext
    checks["scope_30_gold"] = ("30-part gold" in body or "30 gold parts" in body)
    checks["scope_deepread_23_96"] = bool(re.search(r"23\s+of\s+(its\s+)?96|23/96", body))
    checks["scope_lightrag_699"] = "699" in body
    # The judge model is deliberately not named in the manuscript; the
    # sensitivity of the effect size to the judge pass must still be stated.
    checks["judge_pass_sensitivity_disclosed"] = bool(
        re.search(r"judge-pass\s+sensitive", n8d_body))
    checks["deepread_provenance_conflict_disclosed"] = "provenance" in threats
    checks["eprag_excluded_disclosed"] = "EPRAG" in n8d
    checks["qa_pdf_present"] = (RELEASE / "paper-package" / "external-baselines-qa.pdf").exists()
    checks["main_no_stale_E11"] = not re.search(r"\bE11\b", n8d_body)

    hashes = {str(p.relative_to(HERE)): sha256(p) for p in [
        HERE / "main_20p.tex", HERE / "n8d_eval.tex", HERE / "supplementary.tex",
        HERE / "supplementary-external-baselines.tex",
        DATA / "answers-v3.jsonl", DATA / "judgments-unified.jsonl",
        DATA / "summary-unified.json", DATA / "paired-unified.json"]}

    report = {"checks": checks, "answers": len(answers), "judgments": len(judgments),
              "source_sha256": hashes,
              "notes": [
                  "E2 merges the former E3 (four-arm) and E11 (eight-arm) campaigns; the unified batch is primary.",
                  "Earlier local-judge passes retained as sensitivity (Tables S18/S21); not pooled.",
                  "EPRAG remains qualitative: no public implementation identified.",
                  "DeepRead generator provenance conflict disclosed in threats.",
              ]}
    (RELEASE / "audit").mkdir(parents=True, exist_ok=True)
    (RELEASE / "audit" / "consistency-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = ["# Release consistency check (E2 unified comparison)", "",
             f"- Answers: {len(answers)} (8 arms x 10 questions)",
             f"- Unified judgments: {len(judgments)}",
             "- Primary batch: summary-unified.json; paired stats: paired-unified.json.",
             "- Scope caveats: RAPTOR/GraphRAG 30 gold parts; LightRAG 699-chunk full export; DeepRead 23/96.",
             "", "## Checks"]
    lines += [f"- {k}: {'PASS' if v else 'FAIL'}" for k, v in checks.items()]
    (RELEASE / "audit" / "consistency-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    failed = [k for k, v in checks.items() if not v]
    print("FAILED:", failed if failed else "none")


if __name__ == "__main__":
    main()