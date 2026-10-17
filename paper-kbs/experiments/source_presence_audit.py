"""Source-presence audit of matched facts (supplementary Table S7).

For each of the 30 answer cells, every annotated strict keyword that the answer
matched is looked up in the cited gold document. Lexical traceability, not
entailment.

Run: python paper-kbs/experiments/source_presence_audit.py
"""
from __future__ import annotations

import json
from pathlib import Path

EXP = Path(__file__).resolve().parent
REPO = EXP.parents[1]
RUN = REPO / "benchmark-suite/results/runs/run-20261013T094350Z-5f9faac"
Q = json.loads((REPO / "benchmark-suite/data/papers/qa_questions_e5_corrected.json")
               .read_text(encoding="utf-8"))["questions"]
QS = {q["qid"]: q for q in Q}

docs = {}
for p in (REPO / "benchmark-suite/data/corpus_md").glob("*.md"):
    for q in Q:
        if q["arxiv_id"] in p.name:
            docs[q["qid"]] = p.read_text(encoding="utf-8", errors="ignore")

ARMS = {"a2": "P", "b": "F", "c": "D"}
per_arm = {a: [0, 0] for a in ARMS.values()}   # [cells ok, cells with matches]
total = ok = 0
for f in sorted(RUN.glob("track_*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    qid, arm = d["qid"], ARMS[d["track"]]
    ans = (d.get("answer") or "").lower()
    text = docs.get(qid, "").lower()
    matched = [k for k in QS[qid]["gold_keywords"] if k.lower() in ans]
    total += 1
    if matched:
        per_arm[arm][1] += 1
        if all(k.lower() in text for k in matched):
            ok += 1
            per_arm[arm][0] += 1

print(f"cells audited: {total}")
print(f"cells where every matched keyword occurs in the cited gold doc: {ok}/{total}")
print("per arm:", {a: f"{v[0]}/{v[1]}" for a, v in per_arm.items()})
