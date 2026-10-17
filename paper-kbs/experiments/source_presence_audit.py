"""Source-presence audit of matched facts (supplementary Tables S7 and S8).

For each answer cell, every annotated strict keyword that the answer matched is
looked up in the cited gold document. This is lexical traceability, not
entailment. The default run is the original 30-cell grid; pass --run to audit
the common-substrate replication instead.

Run:
  python paper-kbs/experiments/source_presence_audit.py
  python paper-kbs/experiments/source_presence_audit.py \
      --run benchmark-suite/results/runs/rerun5-20261017
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

EXP = Path(__file__).resolve().parent
REPO = EXP.parents[1]
DEFAULT_RUN = REPO / "benchmark-suite/results/runs/run-20261013T094350Z-5f9faac"
Q = json.loads((REPO / "benchmark-suite/data/papers/qa_questions_e5_corrected.json")
               .read_text(encoding="utf-8"))["questions"]
QS = {q["qid"]: q for q in Q}

docs: dict[str, str] = {}
for p in (REPO / "benchmark-suite/data/corpus_md").glob("*.md"):
    for q in Q:
        if q["arxiv_id"] in p.name:
            docs[q["qid"]] = p.read_text(encoding="utf-8", errors="ignore").lower()

ARMS = {"a2": "P", "b": "F", "c": "D"}


def audit(run: Path) -> dict:
    run = run.resolve()
    per_arm = {a: {"cells": 0, "with_matches": 0, "all_present": 0}
               for a in ARMS.values()}
    cells = []
    total = ok = 0
    for f in sorted(run.glob("track_*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        qid, arm = d["qid"], ARMS[d["track"]]
        ans = (d.get("answer") or "").lower()
        text = docs.get(qid, "")
        matched = [k for k in QS[qid]["gold_keywords"] if k.lower() in ans]
        missing = [k for k in matched if k.lower() not in text]
        total += 1
        per_arm[arm]["cells"] += 1
        if matched:
            per_arm[arm]["with_matches"] += 1
            if not missing:
                ok += 1
                per_arm[arm]["all_present"] += 1
        cells.append({
            "qid": qid,
            "arm": arm,
            "matched": matched,
            "present": [k for k in matched if k not in missing],
            "missing_from_gold": missing,
            "ok": bool(matched) and not missing,
        })
    return {
        "run": str(run.relative_to(REPO)).replace("\\", "/"),
        "cells": total,
        "all_matched_keywords_present": ok,
        "per_arm": per_arm,
        "cell_records": cells,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, default=DEFAULT_RUN,
                    help="run directory containing track_*.json")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    out = audit(args.run)
    print(f"run: {out['run']}")
    print(f"cells audited: {out['cells']}")
    print(f"cells where every matched keyword occurs in the cited gold doc: "
          f"{out['all_matched_keywords_present']}/{out['cells']}")
    print("per arm (all present / cells with matches / cells): " + ", ".join(
        f"{a} {v['all_present']}/{v['with_matches']}/{v['cells']}"
        for a, v in out["per_arm"].items()))
    bad = [c for c in out["cell_records"] if c["matched"] and not c["ok"]]
    if bad:
        print("cells failing the check:")
        for c in bad:
            print(f"  {c['qid']}/{c['arm']}: missing {c['missing_from_gold']}")
    if args.out is None:
        name = Path(out["run"]).name
        args.out = EXP / "results" / f"source_presence_{name}.json"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
