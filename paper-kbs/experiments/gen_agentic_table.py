#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate tex/tab_agentic.tex + summary JSON/printout from exp2 run JSONs."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = HERE / "results" / "exp2_lanes"
TEX = HERE.parent / "tex" / "tab_agentic.tex"

ARMS = ["search", "librarian", "hybrid", "bare"]
ARM_LABELS = {"search": "Search (A)", "librarian": "Librarian (B)",
              "hybrid": "Hybrid (C)", "bare": "Bare (no KB)"}
QIDS = ["Q2", "Q4", "Q6", "Q7"]


def main() -> int:
    sys.path.insert(0, str(HERE))
    from kbcommon import QUESTIONS
    n_markers = {q["qid"]: len(q["fact_markers"]) for q in QUESTIONS if q["exp2"]}
    runs = {}
    for f in RES.glob("run_*.json"):
        d = json.loads(f.read_text(encoding="utf-8"))["run"]
        # recompute refusal from the answer opening (older run files may hold
        # a false positive from a whole-text marker scan)
        d["refusal"] = bool(
            d.get("refusal") is not None and d["answer_chars"] > 0
            and any(m in d["answer_head"][:200].lower()
                    for m in ("无法", "没有找到", "未找到", "未检索到",
                              "没有检索到", "不存在", "无法回答", "无法作答",
                              "not found", "cannot answer",
                              "unable to answer", "no evidence")))
        runs[(d["arm"], d["qid"])] = d
    missing = [(a, q) for a in ARMS for q in QIDS if (a, q) not in runs]
    if missing:
        print("missing runs:", missing)

    lines = ["\\begin{tabular}{llcccc}", "\\toprule",
             "Arm & Q & Wall (s) & Turns & Cite & Facts \\\\",
             "\\midrule"]
    agg = {a: {"n": 0, "wall": 0.0, "turns": 0, "cite": 0, "facts": 0,
               "tmo": 0, "spt": []} for a in ARMS}
    for a in ARMS:
        for q in QIDS:
            r = runs.get((a, q))
            if not r:
                lines.append(f"{a} & {q} & -- & -- & -- & -- \\\\")
                continue
            g = agg[a]
            if r["error"] and not r["answer_chars"]:
                g["tmo"] += 1
                lines.append(
                    f"{a} & {q} & {r['wall_s']:.0f} (t/o) & -- & -- & -- \\\\")
                continue
            turns = r["turns"] or 0
            g["n"] += 1
            g["wall"] += r["wall_s"]
            g["turns"] += turns
            g["cite"] += int(bool(r["doc_citation_hit"]))
            g["facts"] += r["n_fact_hits"]
            if turns:
                g["spt"].append(r["wall_s"] / turns)
            lines.append(f"{ARM_LABELS[a]} & {q} & {r['wall_s']:.0f} & {turns} & "
                         f"{'\\yes' if r['doc_citation_hit'] else '\\no'} & "
                         f"{r['n_fact_hits']}/{n_markers[q]} \\\\")
        lines.append("\\midrule")
    lines[-1] = "\\bottomrule"
    lines.append("\\end{tabular}")

    total_markers = sum(n_markers.values())
    summary = {}
    for a in ARMS:
        g = agg[a]
        n_tot = g["n"] + g["tmo"]
        if not n_tot:
            continue
        summary[a] = {
            "n_total": n_tot,
            "wall_mean_s": (g["wall"] / g["n"]) if g["n"] else None,
            "turns_mean": (g["turns"] / g["n"]) if g["n"] else None,
            "s_per_turn_mean": (sum(g["spt"]) / len(g["spt"])) if g["spt"] else None,
            "cite_rate": g["cite"] / n_tot,
            "fact_rate": g["facts"] / total_markers,
            "timeouts": g["tmo"],
        }
        s = summary[a]
        print(f"{a:<10} n={n_tot} wall={s['wall_mean_s'] or 0:.0f}s "
              f"turns={s['turns_mean'] or 0:.1f} "
              f"s/turn={s['s_per_turn_mean'] or 0:.1f} "
              f"cite={s['cite_rate']:.2f} facts={s['fact_rate']:.2f} "
              f"t/o={s['timeouts']}")
    TEX.parent.mkdir(parents=True, exist_ok=True)
    TEX.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (RES / "summary_gen.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {TEX}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
