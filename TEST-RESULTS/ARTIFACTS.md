# Where the paper's evaluation artifacts live

One entry point for **the current results** and for **where the superseded ones
went**. The current artifacts are plain directories (read them directly); the
superseded campaigns live inside tarballs and are restored on demand.

Paper: `paper-kbs/tex/journal_20p/main_20p.tex` (journal variant, 20-page
limit). Every path below is relative to the repository root.

## Current

| what the paper reports | artifact |
|---|---|
| E5 three-arm grid (30 cells: platform / file-tools / dense, 10 questions, $17.25) | `benchmark-suite/results/runs/run-20261013T094350Z-5f9faac/` — `track_{a2,b,c}_BQ*.json` per cell, `SUMMARY.md` with verbatim answers, `run_manifest.json` with commit + config hash |
| E5 grades (grounded / key facts / citation, deterministic string tests) | `benchmark-suite/results/exp_r2_grade.json` + `benchmark-suite/results/R2-EXP-3TRACK-REPORT.md`, produced by `benchmark-suite/scripts/107_exp_grade.py --run run-20261013T094350Z-5f9faac --qfile data/papers/qa_questions.json` |
| E5 figure | `paper-kbs/figures/fig11_three_arms.pdf` / `.png`, rebuilt by `paper-kbs/figures/build_fig11_three_arms.py` (it re-reads the run cells and the grade file, and refuses to draw if they disagree) |
| E5 cross-arm statistics (means, paired t) | `paper-kbs/tex/journal_20p/e5_numbers.json`, recomputed by `_e5_stats.py` |
| E7 stability campaign (27 cells, zero failures) | `review/stability-multiround-20261013/results/` |
| E4/E6 retrieval matrices, judge failure, span NLI, graded probes, agent abstention | `paper-kbs/experiments/results/` |

## Superseded (archived 2026-10-13)

Restore with `tar -xzf <tarball> -C .` from the repository root; archive members
keep their original repository-relative paths.

| tarball | holds |
|---|---|
| `benchmark-suite/results/archive-superseded/superseded-20261013.tar.gz` | `benchmark-suite/results/runs/run-20261013T035250Z-5f9faac/` (retrieval matrix), `run-20261013T040929Z-5f9faac/` (two-track COMPARE), and the other superseded October runs |
| `benchmark-suite/results/archive-superseded/superseded-20261013-batch2.tar.gz` | older `chatmodes-*` runs (delivery-channel comparisons) |
| `review/archive-superseded/review-superseded-20261013.tar.gz` | `review/retrieval-e2e-20261012/` (timed three-channel gate campaign) and the other superseded review campaigns |

Each tarball carries a `MANIFEST.json` (per-path list) and `DELETED.json`.

## Verify

```
python TEST-RESULTS/verify.py
```

prints the current headline numbers straight from the artifacts above, so a
reader can confirm the paper's claims without re-running anything.
