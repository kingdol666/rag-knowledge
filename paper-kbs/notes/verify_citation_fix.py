"""Post-fix verification for the citation-consistency audit.

Checks:
  - every integrated key and every repaired orphan key is still cited
  - no citation points at an undefined key; hmrs-demo stays uncited
  - the five misplaced keys now live in the intended sections/paragraphs
  - the new wording no longer contains the four disproved claims
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
J = ROOT / "paper-kbs" / "tex" / "journal_20p"
NOTES = Path(__file__).resolve().parent

report = json.loads((NOTES / "kbs_integration_report.json").read_text(encoding="utf-8"))
new_keys = set(report["integrated"])
orphans = {"feng-abstain", "yin-knowwhat", "es-ragas-2024",
           "saad-falcon-ares-2024", "jarvelin-cumulated-gain-2002"}

tex = {p.name: p.read_text(encoding="utf-8") for p in J.glob("n*.tex")}
cited: set[str] = set()
for s in tex.values():
    for grp in re.findall(r"\\cite[tp]?\{([^}]*)\}", s):
        cited |= {k.strip() for k in grp.split(",")}
defined: set[str] = set()
for b in ("refs.bib", "refs_new_verified.bib"):
    defined |= set(re.findall(r"^@\w+\{([^,]+),", (J / b).read_text(encoding="utf-8"), re.M))

checks = {
    "all 27 integrated keys still cited": new_keys <= cited,
    "all 5 orphan keys still cited": orphans <= cited,
    "no undefined citations": not (cited - defined),
    "only hmrs-demo left uncited": defined - cited == {"hmrs-demo"},
}
related = tex["n2_related.tex"]
sec21 = related[related.index("\\subsection{Knowledge management"):
                related.index("\\subsection{Retrieval, organisation")]
sec23 = related[related.index("\\subsection{Verification"):
                related.index("\\subsection{Research gap")]
sys_keys = {"mohamed2026orchestra", "liu2026automatin", "chen2026enhancing",
            "sorokin2023sigopt"}
checks["4 system-engineering keys moved to sec 2.1"] = all(k in sec21 for k in sys_keys)
checks["those 4 keys absent from sec 2.3"] = all(k not in sec23 for k in sys_keys)
checks["wu2025informati in memory paragraph"] = (
    "information-theoretic dual" in sec23 and
    sec23.index("wu2025informati") < sec23.index("Self-RAG"))
checks["no 'trustworthiness side' framing left"] = "trustworthiness side" not in sec23
for bad in ("design-science derivation", "reasoning substrate",
            "automated model evaluation", "clinical reasoning"):
    checks[f"disproved phrase removed: {bad}"] = bad not in related
checks["domain-shift key group split"] = (
    "identifying what LLMs do not know" in related and
    "kamath,feng-abstain" not in related)

eval_tex = tex["n8a_eval.tex"]
checks["evaluation sentence moved next to metric definition"] = (
    eval_tex.index("assess the semantic quality") <
    eval_tex.index("The answer\ngrid"))
checks["RAGAs/ARES separated from cumulated gain"] = (
    "while cumulated-gain" in eval_tex)

for name, ok in checks.items():
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
print(f"\n[summary] {sum(checks.values())}/{len(checks)} checks passed | "
      f"cited={len(cited)} defined={len(defined)}")
if not all(checks.values()):
    raise SystemExit(1)
