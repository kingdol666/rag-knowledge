#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Round-2 analyses: rep2 agreement + decontaminated fact checks +
refusal recomputation (opening-200 rule)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
sys.path.insert(0, str(HERE))
from kbcommon import QUESTIONS

exp2 = {q["qid"]: q for q in QUESTIONS if q["exp2"]}


def load(dirname):
    out = {}
    for f in sorted((RES / dirname).glob("run_*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))["run"]
        out[(d["arm"], d["qid"])] = d
    return out


def decontaminate(text: str, gold_subs: list[str]) -> str:
    """Drop lines that cite the gold document by name, so fact markers must
    come from the answer's own words/tables."""
    kept_lines = []
    for line in text.splitlines():
        if any(g.lower() in line.lower() for g in gold_subs):
            continue
        kept_lines.append(line)
    return "\n".join(kept_lines)


MARKERS_HEAD = ("无法", "没有找到", "未找到", "未检索到", "没有检索到", "不存在",
                "无法回答", "无法作答", "not found", "cannot answer",
                "unable to answer", "no evidence")


def main() -> int:
    rep1 = load("exp2_lanes")
    rep2 = load("exp2_lanes_rep2")

    print("== rep1 vs rep2 agreement ==")
    cells = sorted(set(rep1) & set(rep2))
    agree_cite = 0
    for cell in cells:
        a, b = rep1[cell], rep2[cell]
        same = bool(a["doc_citation_hit"]) == bool(b["doc_citation_hit"])
        agree_cite += same
        print(f"{cell[0]:<10} {cell[1]}: rep1 wall={a['wall_s']:>6} turns={a['turns']} "
              f"cite={a['doc_citation_hit']} facts={a['n_fact_hits']} | "
              f"rep2 wall={b['wall_s']:>6} turns={b['turns']} "
              f"cite={b['doc_citation_hit']} facts={b['n_fact_hits']} "
              f"{'SAME' if same else 'DIFF'}")
    print(f"citation agreement: {agree_cite}/{len(cells)}")

    print("\n== decontaminated fact checks (rep1, transcript heads; "
          "gold-citing lines removed) ==")
    for (arm, qid), r in sorted(rep1.items()):
        q = exp2[qid]
        body = decontaminate(r["answer_head"], q["gold_doc_substrings"])
        hits = [m for m in q["fact_markers"] if m in body]
        raw = [m for m in q["fact_markers"] if m in r["answer_head"]]
        print(f"{arm:<10} {qid}: raw={len(raw)}/{len(q['fact_markers'])} "
              f"decontam={len(hits)}/{len(q['fact_markers'])} ({hits})")

    print("\n== refusal recomputation (opening-200 rule) ==")
    for name, runs in (("rep1", rep1), ("rep2", rep2)):
        for (arm, qid), r in sorted(runs.items()):
            head = r["answer_head"][:200].lower()
            ref = any(m in head for m in MARKERS_HEAD) if r["answer_chars"] else None
            print(f"{name} {arm:<10} {qid}: refusal={ref}")

    # aggregate rep2 wall/turns for grounded arms
    print("\n== rep2 ranges (KB-grounded arms) ==")
    for arm in ("search", "librarian", "hybrid"):
        walls = [rep2[c]["wall_s"] for c in rep2
                 if c[0] == arm and rep2[c]["answer_chars"]]
        turns = [rep2[c]["turns"] or 0 for c in rep2
                 if c[0] == arm and rep2[c]["answer_chars"]]
        if walls:
            print(f"{arm:<10} wall {min(walls):.0f}-{max(walls):.0f}s "
                  f"turns {min(turns)}-{max(turns)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
