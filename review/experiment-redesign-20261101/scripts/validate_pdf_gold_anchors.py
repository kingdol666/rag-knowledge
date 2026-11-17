"""Check PDF-pending gold strings against their original source PDFs.

This checks source-PDF presence only. It does not prove that MinerU output or
the indexed part retained the anchor.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "corpus" / "multi-domain-docs-20261101"
QUESTIONS = ROOT / "review" / "experiment-redesign-20261101" / "artifacts" / "questions.jsonl"
OUTPUT = ROOT / "review" / "experiment-redesign-20261101" / "artifacts" / "pdf_anchor_audit_20261104.json"


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).casefold()


def main() -> None:
    extractor = shutil.which("pdftotext")
    if not extractor:
        raise SystemExit("pdftotext is required for source-PDF anchor validation")

    questions = [
        json.loads(line)
        for line in QUESTIONS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    pending = [q for q in questions if q.get("evidence_pending") == "pdf-parse"]
    rows = []
    for question in pending:
        source = (CORPUS / question["gold_doc"]).resolve()
        if not source.is_relative_to(CORPUS.resolve()):
            raise ValueError(f"gold_doc escapes corpus root: {question['gold_doc']}")
        result = subprocess.run(
            [extractor, "-layout", str(source), "-"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
        anchor = question["gold_evidence"]
        rows.append({
            "qid": question["id"],
            "source_pdf": question["gold_doc"],
            "gold_evidence": anchor,
            "whitespace_normalized_exact_match": normalize(anchor) in normalize(result.stdout),
        })

    matched = sum(row["whitespace_normalized_exact_match"] for row in rows)
    output = {
        "method": "Poppler pdftotext -layout; casefold + whitespace-normalized exact substring",
        "scope_note": "Validates source-PDF anchor presence only; does not validate MinerU output or indexed-part provenance.",
        "n_pending": len(rows),
        "n_source_matches": matched,
        "n_source_misses": len(rows) - matched,
        "rows": rows,
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Source PDF anchors: {matched}/{len(rows)} matched; wrote {OUTPUT}")


if __name__ == "__main__":
    main()
