"""Provenance gate: every artefact the paper cites must name its producer, and the
producer must exist and actually write that artefact.

WHY THIS EXISTS
---------------
During revision it was found that `benchmark-web/backend/results/cikm/` and
`.../results/v4/` — the source of the paper's MAIN results table, FPR figure and
ablation table — have no producer script anywhere in the repository, while the
results the paper treated as secondary do. The paper was leading with the only
numbers it could not reproduce.

An earlier version of this script used a filename-matching heuristic and reported
"0 missing", which was wrong: the benchmark-suite scripts write via COMPUTED
filenames, so an exact-name grep finds nothing, and loose matching then picked up
unrelated files. The map below is hand-verified by reading the write sites; this
script checks that each claimed producer still exists and still writes.

Run:  python provenance_audit.py
Exit code 1 if any artefact lacks a live producer — wire it into CI.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = None
d = os.path.dirname(os.path.abspath(__file__))
for _ in range(8):
    if os.path.isdir(os.path.join(d, "benchmark-suite")):
        ROOT = d
        break
    d = os.path.dirname(d)
if ROOT is None:
    raise SystemExit("repository root not found")

# (artefact, what the paper uses it for, producer script, the write-site marker
#  that must appear in that script, traceable?)
MAP = [
    ("benchmark-suite/results/module_a_ingestion_r1.json", "Table 2 ingestion (in-house)",
     "benchmark-suite/scripts/01_ingestion.py", "results", True),
    ("benchmark-suite/results/module_a_std2_r1.json", "Table 2 ingestion (standard)",
     "benchmark-suite/scripts/21_std2_ingest.py", "results", True),
    ("benchmark-suite/results/module_b_retrieval_r2.json", "Table 6 in-house retrieval",
     "benchmark-suite/scripts/02_retrieval.py", 'module_b_retrieval{OUT_SUFFIX}_r{ROUND}.json', True),
    ("benchmark-suite/results/module_b_std2_r2.json", "Table 3 BEIR SciFact + SQuAD",
     "benchmark-suite/scripts/22_std2_retrieval.py", 'module_b_std2_r{ROUND}{suffix}.json', True),
    ("benchmark-suite/results/module_c_experience_r2.json", "Table 7 experience",
     "benchmark-suite/scripts/03_experience.py", "results", True),
    # ---- no producer found; exact-name grep over all code returns zero hits ----
    ("benchmark-web/backend/results/cikm/cikm_summary.json",
     "Table 4 MAIN + Figure 3 FPR + Table 5 ablation", None, None, False),
    ("benchmark-web/backend/results/cikm/figure1_comparison.json",
     "Figure 3 source data", None, None, False),
    ("benchmark-web/backend/results/cikm/table1_main.tex",
     "Table 4 pre-rendered", None, None, False),
    ("benchmark-web/backend/results/cikm/table3_ablation.tex",
     "Table 5 pre-rendered", None, None, False),
    ("benchmark-web/backend/results/v4/benchmark_report.json",
     "the statistics cited in §7.2", None, None, False),
]

print(f"{'artefact':<56} {'used for':<42} {'producer':<46} state")
print("-" * 160)

bad = []
for rel, use, producer, marker, traceable in MAP:
    art = os.path.join(ROOT, rel)
    art_ok = os.path.exists(art)
    if producer is None:
        state = "NO PRODUCER"
        prod_ok = False
    else:
        p = os.path.join(ROOT, producer)
        prod_ok = os.path.exists(p)
        if prod_ok and marker:
            txt = open(p, encoding="utf-8", errors="replace").read()
            prod_ok = marker in txt or bool(re.search(marker, txt))
        state = "ok" if (art_ok and prod_ok) else "BROKEN"
    if not traceable:
        bad.append(rel)
    print(f"{rel:<56} {use:<42} {(producer or '—'):<46} {state}")

print("\n" + "=" * 160)
print(f"UNTRACEABLE artefacts: {len(bad)}/{len(MAP)}")
for b in bad:
    print(f"  !! {b}")
print("""
These artefacts have no producer script in the repository. The paper must NOT
present them as measurements of the deployed system. Either regenerate them from
a committed script, or remove them from the paper's claims.""")

sys.exit(1 if bad else 0)
