#!/usr/bin/env python3
"""Paired agreement between the original E5 answer grid and its replication.

Both grids answer the same ten questions with the same three arms on the same
model, but under different substrates. This script pairs the cells by
(qid, arm) and reports, for each binary check, the 2x2 table, raw agreement,
Cohen's kappa (reported for completeness only; it is unstable when one
category dominates) and an exact two-sided McNemar test on the discordant
pairs. The McNemar test asks whether disagreements are symmetric; it does not
test which grid is correct.

Inputs are the deterministic grades of the frozen question key:
  benchmark-suite/results/exp_r2_grade_corrected.json   original grid
  benchmark-suite/results/exp_rerun5_grade.json         common-substrate grid
Output:
  paper-kbs/experiments/results/e5_replication_agreement.json
"""
from __future__ import annotations

import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ORIG = REPO / "benchmark-suite/results/exp_r2_grade_corrected.json"
REPL = REPO / "benchmark-suite/results/exp_rerun5_grade.json"
OUT = Path(__file__).resolve().parent / "results/e5_replication_agreement.json"

ARMS = ("a2", "b", "c")
MEASURES = (
    ("gold_hit", "Gold-ID present"),
    ("kw_alias_ok", "Alias-aware keyword coverage"),
    ("kw_ok", "Strict keyword coverage"),
    ("cited", "At least one document-style marker"),
)


def load(path: Path) -> dict[tuple[str, str], dict]:
    rows = json.loads(path.read_text(encoding="utf-8"))["rows"]
    return {(r["qid"], r["track"]): r for r in rows}


def exact_mcnemar(b: int, c: int) -> float:
    """Two-sided exact McNemar p over discordant counts b and c."""
    m = b + c
    if m == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(m, i) for i in range(k + 1)) / 2 ** m
    return min(1.0, 2.0 * tail)


def kappa(a: int, b: int, c: int, d: int) -> float | None:
    n = a + b + c + d
    po = (a + d) / n
    pe = ((a + b) * (a + c) + (c + d) * (b + d)) / n / n
    if pe == 1.0:
        return None
    return (po - pe) / (1.0 - pe)


def main() -> int:
    orig = load(ORIG)
    repl = load(REPL)
    missing = set(orig) ^ set(repl)
    if missing:
        raise SystemExit(f"cell sets differ: {sorted(missing)}")

    keys = sorted(orig)
    out = {
        "original": str(ORIG.relative_to(REPO)).replace("\\", "/"),
        "replication": str(REPL.relative_to(REPO)).replace("\\", "/"),
        "n_cells": len(keys),
        "measures": {},
    }
    print(f"paired cells: {len(keys)}")
    print(f"{'measure':42s}{'both':>6}{'orig':>6}{'repl':>6}{'none':>6}"
          f"{'agree':>8}{'kappa':>8}{'p':>9}")
    for field, label in MEASURES:
        a = sum(1 for k in keys if orig[k][field] and repl[k][field])
        b = sum(1 for k in keys if orig[k][field] and not repl[k][field])
        c = sum(1 for k in keys if not orig[k][field] and repl[k][field])
        d = sum(1 for k in keys if not orig[k][field] and not repl[k][field])
        p = exact_mcnemar(b, c)
        kap = kappa(a, b, c, d)
        agree = (a + d) / len(keys)
        out["measures"][field] = {
            "label": label,
            "both": a,
            "original_only": b,
            "replication_only": c,
            "neither": d,
            "agreement": round(agree, 4),
            "kappa": None if kap is None else round(kap, 4),
            "mcnemar_exact_p": round(p, 6),
            "original_only_cells": [list(k) for k in keys if orig[k][field] and not repl[k][field]],
            "replication_only_cells": [list(k) for k in keys if not orig[k][field] and repl[k][field]],
        }
        print(f"{label:42s}{a:>6}{b:>6}{c:>6}{d:>6}"
              f"{agree:>8.3f}{(kap if kap is not None else float('nan')):>8.3f}{p:>9.4f}")

    print("\nper-arm totals (original -> replication)")
    out["per_arm"] = {}
    for arm in ARMS:
        ks = [k for k in keys if k[1] == arm]
        vals = {}
        for field, _ in MEASURES:
            o = sum(bool(orig[k][field]) for k in ks)
            r = sum(bool(repl[k][field]) for k in ks)
            vals[field] = {"original": o, "replication": r, "n": len(ks)}
        out["per_arm"][arm] = vals
        print(f"  {arm}: " + " · ".join(
            f"{f} {vals[f]['original']}/{vals[f]['n']}->{vals[f]['replication']}/{vals[f]['n']}"
            for f, _ in MEASURES))

    # Marker counts are substrate-sensitive; report how often the count moves.
    count_diff = [k for k in keys
                  if len(orig[k]["cite_markers"]) != len(repl[k]["cite_markers"])]
    out["marker_count_differs_cells"] = len(count_diff)
    print(f"\nmarker counts differ in {len(count_diff)}/{len(keys)} cells")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
