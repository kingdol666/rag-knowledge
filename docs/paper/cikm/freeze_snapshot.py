"""Freeze the exact benchmark artefacts this paper cites into an immutable snapshot.

WHY THIS EXISTS
---------------
`benchmark-suite/results/*.json` are overwritten in place by every re-run. During
the writing of this paper, `module_c_experience_r2.json` was re-run and its
`judge_score_mean` went from 3.5 to None (zero experiences produced). A paper that
cites a mutable path is citing a moving target: the numbers can change after
submission and no reader could reproduce them.

This script copies the exact bytes the paper used into `data-snapshot/` and
records a SHA-256 for each, so:
  * the paper is self-contained,
  * every reported number is traceable to a specific frozen file,
  * a re-run of the benchmark no longer silently changes the paper.

Run once. Re-run only when deliberately moving the paper to a new snapshot, and
record the change in the changelog below.

SNAPSHOT HISTORY
  2026-09-13-a  initial freeze. Experience numbers come from
                `results/archive-20260913-214859/module_c_experience_r2.json`
                because the live file was later overwritten by a re-run that
                produced zero experiences.
  2026-09-15-a  added E16 matrix/API/ops artifacts and the E16 replay.
  2026-09-16-a  re-pinned all 2026-09-15-a bytes from the snapshot itself
                (module_b_retrieval_r2 live file drifted after later re-runs
                while the paper cites the frozen values), and added the E8
                HotpotQA frozen artifact plus the two E19 real-scenario runs
                and their machine comparison (reproducibility-audit sources).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil

SNAPSHOT_ID = "2026-09-16-a"

ROOT = None
d = os.path.dirname(os.path.abspath(__file__))
for _ in range(8):
    if os.path.isdir(os.path.join(d, "benchmark-suite")):
        ROOT = d
        break
    d = os.path.dirname(d)
if ROOT is None:
    raise SystemExit("repository root not found")

DST = os.path.join(ROOT, "docs", "paper", "cikm", "data-snapshot")
os.makedirs(DST, exist_ok=True)

# (source relative to repo root, name in snapshot, note)
# 2026-09-16-a: 沿用 2026-09-15-a 冻结字节(data-snapshot 内已冻结的文件从
# 快照本身复读, 不从易变的 results/ 顶层重取 — module_b_r2 在 09-16 的重跑中
# 漂移至 0.75/0.90, 而论文引用的是冻结值 0.80/0.90, 这正是快照存在的理由),
# 新增: E8 HotpotQA 冻结产物(run-20260914T053707Z, tab-multidomain 之源)与
# E19 真实场景两次运行 + 机器对比(复现审计段落之源)。
SNAPSHOT_DIR_REL = "docs/paper/cikm/data-snapshot"
SOURCES = [
    ("docs/paper/cikm/data-snapshot/module_a_ingestion_r1.json", "module_a_ingestion_r1.json",
     "Module A ingestion (in-house) — producer: 01_ingestion.py (bytes pinned 2026-09-15-a)"),
    ("docs/paper/cikm/data-snapshot/module_a_std2_r1.json", "module_a_std2_r1.json",
     "Module A ingestion (standard corpus) — producer: 21_std2_ingest.py (bytes pinned 2026-09-15-a)"),
    ("docs/paper/cikm/data-snapshot/module_b_retrieval_r2.json", "module_b_retrieval_r2.json",
     "Module B in-house retrieval, 20 queries — producer: 02_retrieval.py (bytes pinned 2026-09-15-a)"),
    ("docs/paper/cikm/data-snapshot/module_b_std2_r2.json", "module_b_std2_r2.json",
     "Module B BEIR SciFact + SQuAD, 4 methods — producer: 22_std2_retrieval.py (bytes pinned 2026-09-15-a)"),
    ("docs/paper/cikm/data-snapshot/module_c_experience_r2.json",
     "module_c_experience_r2.json",
     "Module C experience, ARCHIVED copy (live file was overwritten) — producer: 03_experience.py"),
    ("docs/paper/cikm/data-snapshot/deepread_matrix.json",
     "deepread_matrix.json",
     "E16 DeepRead baseline matrix, 30 queries x 8 methods — producer: algorithms/run_matrix.py (bytes pinned 2026-09-15-a)"),
    ("docs/paper/cikm/data-snapshot/api_matrix.json",
     "api_matrix.json",
     "E16b API flow, 30 queries x 8 methods + middle-agent ranking — producer: scripts/27_api_flow_test.py + algorithms/api_server.py (bytes pinned 2026-09-15-a)"),
    ("docs/paper/cikm/data-snapshot/platform_ops_eval.json",
     "platform_ops_eval.json",
     "E17 platform organise functions (dedup/tags/graph/catalog) — producer: scripts/26_platform_ops_eval.py (bytes pinned 2026-09-15-a)"),
    ("docs/paper/cikm/data-snapshot/deepread_matrix_replay.json",
     "deepread_matrix_replay.json",
     "E16 cache-replay rerun (reproducibility evidence, summary must match deepread_matrix.json)"),
    ("benchmark-suite/results/run-20260914T053707Z/hotpot_main_2.json",
     "hotpot_main_2.json",
     "E8 multi-domain HotpotQA, 50 questions x 9 topic KBs x 4 methods — producer: scripts/60_hotpot_build.py + scripts/61_hotpot_eval.py (frozen run 2026-09-14T053707Z; post-freeze vector-store state sensitivity documented in the paper's reproducibility audit)"),
    ("benchmark-suite/results/real-scenario-20260916-001507/real_scenario_repaired.json",
     "real_scenario_run1.json",
     "E19 real-scenario run 1 (two user documents x 9 systems; parser-fallback repaired copy) — producer: scripts/29_real_scenario_test.py"),
    ("benchmark-suite/results/real-scenario-20260916-045222/real_scenario_repaired.json",
     "real_scenario_run2.json",
     "E19 real-scenario run 2 (independent full re-run for the reproducibility audit) — producer: scripts/29_real_scenario_test.py"),
    ("benchmark-suite/REALSCENARIO-COMPARISON.json",
     "real_scenario_comparison.json",
     "E19 run1-vs-run2 machine comparison: 47/48 retrieval positions, judge mean |d|=0.417 — producer: scripts/32_real_scenario_report.py --compare"),
]

# Frozen for the provenance record but NO LONGER CITED: the paper's main results
# table, FPR figure and ablation table used to come from cikm_summary.json. That
# artefact has no producer script anywhere in the repository (see
# provenance_audit.py and PROVENANCE.md), so the paper withdrew those results.
# The file is kept here only as evidence of what was withdrawn.
WITHHELD = [
    ("benchmark-web/backend/results/cikm/cikm_summary.json", "cikm_summary.json",
     "WITHHELD — former main results table, FPR figure and ablation. NO PRODUCER."),
]

manifest = {
    "snapshot_id": SNAPSHOT_ID,
    "frozen_at": "2026-09-16",
    "note": "Immutable copies of the benchmark artefacts cited by this paper. "
            "make_assets.py reads ONLY from here. Every cited artefact names its "
            "producing script; provenance_audit.py fails the build if one loses it.",
    "files": [],
    "withheld": [],
}

for src_rel, name, note in SOURCES:
    src = os.path.join(ROOT, src_rel)
    if not os.path.exists(src):
        raise SystemExit(f"missing source artefact: {src}")
    raw = open(src, "rb").read()
    dst = os.path.join(DST, name)
    with open(dst, "wb") as f:
        f.write(raw)
    manifest["files"].append({
        "name": name,
        "source": src_rel,
        "note": note,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
    })
    print(f"  frozen {name:<34} {len(raw):>7} B  sha256={manifest['files'][-1]['sha256'][:16]}…")

for src_rel, name, note in WITHHELD:
    src = os.path.join(ROOT, src_rel)
    if not os.path.exists(src):
        print(f"  (withheld artefact absent, skipped): {src_rel}")
        continue
    raw = open(src, "rb").read()
    with open(os.path.join(DST, name), "wb") as f:
        f.write(raw)
    manifest["withheld"].append({
        "name": name, "source": src_rel, "note": note,
        "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
    })
    print(f"  WITHHELD {name:<32} {len(raw):>7} B  (kept as evidence, not cited)")

with open(os.path.join(DST, "MANIFEST.json"), "w", encoding="utf-8", newline="\n") as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)
    f.write("\n")

print(f"\nSnapshot '{SNAPSHOT_ID}' written to docs/paper/cikm/data-snapshot/")
print("make_assets.py now reads only from this snapshot.")
