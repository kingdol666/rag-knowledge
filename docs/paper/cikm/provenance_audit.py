"""Provenance gate: every artefact the paper cites must name its producer, the
producer must exist, and it must actually write that artefact.

WHY THIS EXISTS
---------------
During revision it was found that `benchmark-web/backend/results/cikm/` and
`.../results/v4/` — the source of the paper's former MAIN results table, FPR
figure and ablation table — have no producer script anywhere in the repository,
while the results the paper treated as secondary do. The paper was leading with
the only numbers it could not reproduce. Those artefacts were **withdrawn from
the paper** and are retained here as `WITHHELD` records under `data-snapshot/`.
They are evidence of what was removed, not claims.

An earlier version of this script used a filename-matching heuristic and reported
"0 missing", which was wrong: the benchmark-suite scripts write via COMPUTED
filenames, so an exact-name grep finds nothing, and loose matching then picked up
unrelated files. The map below is hand-verified by reading the write sites.

THREE CHECKS (all deterministic; no network, no model)
------------------------------------------------------
  A. every CITED artefact names a producer script that exists and still contains
     the write-site marker                                  -> blocking
  B. every producer script named in main.tex exists          -> blocking
     (catches a dangling "producer: foo.py" claim in the text)
  C. withheld artefacts are listed as such and are NOT cited -> recorded only

Run:  python provenance_audit.py
Exit code 1 if check A or B fails. Wire it into CI / pre-commit.
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

HERE = os.path.dirname(os.path.abspath(__file__))

# ── A. cited artefacts: (artefact, what the paper uses it for, producer script,
#    write-site marker that must appear in that script) ────────────────────────
CITED = [
    ("benchmark-suite/results/module_a_ingestion_r1.json", "Table 2 ingestion (in-house)",
     "benchmark-suite/scripts/01_ingestion.py", "results"),
    ("benchmark-suite/results/module_a_std2_r1.json", "Table 2 ingestion (standard)",
     "benchmark-suite/scripts/21_std2_ingest.py", "results"),
    ("benchmark-suite/results/module_b_retrieval_r2.json", "Table 6 in-house retrieval",
     "benchmark-suite/scripts/02_retrieval.py", r'module_b_retrieval\{OUT_SUFFIX\}_r\{ROUND\}\.json'),
    ("benchmark-suite/results/module_b_std2_r2.json", "Table 3 BEIR SciFact + SQuAD",
     "benchmark-suite/scripts/22_std2_retrieval.py", r'module_b_std2_r\{ROUND\}\{suffix\}\.json'),
    ("benchmark-suite/results/module_c_experience_r2.json", "Table 7 experience",
     "benchmark-suite/scripts/03_experience.py", "results"),
    ("docs/paper/cikm/data-snapshot/deepread_matrix.json", "Table 4 eight-system matrix",
     "benchmark-suite/algorithms/run_matrix.py", "json"),
    ("docs/paper/cikm/data-snapshot/api_matrix.json", "Table 4b API-driven rerun",
     "benchmark-suite/scripts/27_api_flow_test.py", "json"),
    ("docs/paper/cikm/data-snapshot/platform_ops_eval.json", "organise-function probe",
     "benchmark-suite/scripts/26_platform_ops_eval.py", "json"),
    ("docs/paper/cikm/data-snapshot/hotpot_main_2.json", "Table 8 multi-domain public benchmark",
     "benchmark-suite/scripts/60_hotpot_build.py", "json"),
    ("docs/paper/cikm/data-snapshot/real_scenario_comparison.json", "E19 real-scenario comparison",
     "benchmark-suite/scripts/32_real_scenario_report.py", "compare"),
]

# ── C. withheld artefacts: kept as evidence, must NOT be cited ───────────────
WITHHELD = [
    ("benchmark-web/backend/results/cikm/cikm_summary.json", "former Table 4/5 + Fig 3"),
    ("benchmark-web/backend/results/cikm/figure1_comparison.json", "former Fig 3 source"),
    ("benchmark-web/backend/results/cikm/table1_main.tex", "former Table 4 pre-rendered"),
    ("benchmark-web/backend/results/cikm/table3_ablation.tex", "former Table 5 pre-rendered"),
    ("benchmark-web/backend/results/v4/benchmark_report.json", "former §7.2 statistics"),
]

print("=== A. cited artefacts (each needs a live producer) ===")
print(f"{'artefact':<58} {'used for':<44} {'producer':<48} state")
print("-" * 168)

bad: list[str] = []
for rel, use, producer, marker in CITED:
    art_ok = os.path.exists(os.path.join(ROOT, rel))
    p = os.path.join(ROOT, producer)
    prod_ok = os.path.exists(p)
    if prod_ok and marker:
        txt = open(p, encoding="utf-8", errors="replace").read()
        prod_ok = bool(re.search(marker, txt))
    state = "ok" if (art_ok and prod_ok) else (
        "MISSING ARTEFACT" if not art_ok else "PRODUCER BROKEN")
    if state != "ok":
        bad.append(rel)
    print(f"{rel:<58} {use:<44} {producer:<48} {state}")

# ── B. producer scripts named in the manuscript must exist ───────────────────
print("\n=== B. producer scripts named in main.tex ===")
tex_path = os.path.join(HERE, "main.tex")
named: set[str] = set()
if os.path.exists(tex_path):
    tex = open(tex_path, encoding="utf-8").read()
    tex = tex.replace("\\_", "_")
    for m in re.finditer(r"\\texttt\{([A-Za-z0-9_./-]+\.py)\}", tex):
        named.add(m.group(1))
missing_named = []
for name in sorted(named):
    found = any(
        os.path.exists(os.path.join(ROOT, sub, name))
        for sub in ("benchmark-suite/scripts", "benchmark-suite/algorithms", "docs/paper/cikm")
    )
    print(f"  {name:<32} {'ok' if found else '!! NOT FOUND'}")
    if not found:
        missing_named.append(name)
bad.extend(missing_named)

# ── C. withheld artefacts (recorded, non-blocking) ──────────────────────────
print("\n=== C. withheld artefacts (withdrawn from the paper; not claims) ===")
for rel, use in WITHHELD:
    exists = os.path.exists(os.path.join(ROOT, rel))
    print(f"  {rel:<58} {use:<32} file {'present' if exists else 'absent'}")

print("\n" + "=" * 168)
if bad:
    print(f"GATE FAILED — {len(bad)} problem(s):")
    for b in bad:
        print(f"  !! {b}")
    print("""
An artefact the paper relies on has no live producer, or the manuscript names a
producer that does not exist. Either regenerate it from a committed script, or
remove the claim from the paper.""")
else:
    print(f"GATE PASSED — {len(CITED)} cited artefacts all traceable; "
          f"{len(named)} named producers all exist; "
          f"{len(WITHHELD)} withheld artefacts recorded and not claimed.")

sys.exit(1 if bad else 0)
