# 2026-11-17 Bench Pipeline Reproduction Report

## Execution summary
- Pipeline: EXPERIMENT-PIPELINE.md stages S0 → S0i/S0c preflight → S1 → S3 → S4 (7 arms) → S6.
- Platform restarted clean (backend -> kb-mcp -> web, venv-parented chains, token refreshed, health 200×3; a zombie spawn-worker holding :8771 was killed per the orphan-worker SOP).
- S4 rerun into artifacts/repro_20261117/ (temp dir per Stage-9 discipline; final_bench SHA256 verified identical before/after).
- Arms: ALL SEVEN A0, A0f, A0h, PD, A1b, A2, A3 (72 gold rows + 4 refusal probes each; 532 checkpoint rows total).
- Incident, disclosed: the first A3 attempt hung inside --prepare-a3's from-scratch twin-library rebuild (same failure family as the archived attempt1_aborted_route_card_death of the R3 replication). Killed per SOP; retry WITHOUT --prepare-a3 (reusing the existing twin libraries) completed normally at frozen pace (8.3 s/q).

## Aggregate containment (72 in-domain questions)

| Arm | Repro 2026-11-17 | Paper frozen | Paper follow-up | Delta vs frozen | Route (repro) |
|---|---|---|---|---|---|
| A0  | 36/72 | 37/72 | 39/72 | -1 | 72/72 |
| A0f | 41/72 | 45/72 | 44/72 | -4 | 72/72 |
| A0h | 48/72 | 52/72 | 51/72 | -4 | 72/72 |
| PD  | 42/72 | 46/72 | 45/72 | -4 | n/a |
| A1b | 36/72 | 39/72 | 39/72 | -3 | n/a |
| A2  | 23/72 | 25/72 | 25/72 | -2 | n/a |
| A3  | 26/72 | 33/72 | 25/72 | -7 | **49/72 (= follow-up exactly)** |

- Ordering: A0h > PD > A0f > A0 ≈ A1b > A2 — identical to the paper's ordering across all recorded runs.
- A0h - A0 gap: +12 (paper frozen +15, follow-up +12) — matches follow-up exactly.
- A0 - A2 gate-ablation gap: 13 questions (frozen 12, follow-up 14).
- A3 route-correct 49/72 equals the follow-up record exactly.

## Paired exact McNemar vs A0 (repro run; s6_stats.py)

| Contrast | Repro | Paper frozen | Paper follow-up |
|---|---|---|---|
| A0h - A0 | 12-0, p=0.000488 | 15-0, p=6.1e-5 | **12-0, p=0.00049 (identical)** |
| A0f - A0 | 5-0, p=0.0625 | 8-0, p=0.0078 | **5-0, p=0.0625 (identical)** |
| PD - A0 | 6-0, p=0.03125 | (not listed) | **6-0, p=0.03125 (identical)** |
| A1b - A0 | 1-1, p=1.0 | 2-4, p=0.69 | **1-1, p=1.0 (identical)** |
| A2 - A0 | 5-18, p=0.0106 | 6-18, p=0.0227 | 5-19, p=0.0066 |
| A3 - A0 | 4 vs 14, p=0.031 | (route arm, weaker) | consistent direction |

Four of the six paired contrasts reproduce the follow-up records bit-for-bit (same discordance, same p to 6 decimals).

## Per-question agreement with frozen
A0 95.8%, A0f 94.4%, A0h 94.4%, PD 94.4%, A1b 95.8%, A2 97.2%, A3 84.7%.
Paper's own frozen-vs-follow-up agreement band: 94.4-100% (A3 75%). Repro sits in the same band; A3 remains the most volatile arm, exactly as the paper reports.

## Pollution audit (pipeline S8 criteria, run on merged traces)
1. qid unique per arm, n=76: PASS (all 7 arms).
2. Route-card KB contamination in survivors/top1: 0 occurrences.
3. A1b/A2 candidate paths confined to the ten MD语料-* evaluation KBs: 0/1252 violations.
4. final_bench SHA256 before == after: PASS.

## Verdict
The bench pipeline reproduces on a clean-restarted stack: identical arm ordering,
headline gaps preserved (A0h-A0 +12 = follow-up), four paired McNemar records
bit-identical to the paper's follow-up, per-question agreement inside the
paper's own stability band, zero pollution-audit violations. The uniform
small downward shift (-1..-4, A3 -7) is consistent with the live corpus having
grown past the frozen 879-part state (the paper's follow-up already recorded
906 parts), a corpus-state drift the paper discloses as a confound. The
execute layer (questions, routing, judging, containment) is reproducible; the
read-all arm was not rerun (mechanical scan, ~5 h, no new information — its
frozen 72/72 upper bound is a script property, not a stochastic result).

