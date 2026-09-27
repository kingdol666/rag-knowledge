# knowledgebase-hybrid skill — three-mode real retrieval test (2026-09-23/24)

Skill: `.claude/skills/knowledgebase-hybrid/` (SKILL.md + scripts/hybrid_search.py +
references/parallel-merge-protocol.md + tests, 15/15 offline tests, skill-creator valid).
All runs used the **real local Laya** (`backend=laya_sdk`, `real_engine=true`, `--require-real` exit 0).
Questions identical to `review/laya-three-mode-20260925` for comparability.

## Main comparison (3 questions × 3 modes)

| q | mode | secs | judged docs | gold kept | gold score (rank 1 everywhere) |
|---|------|-----:|------------:|-----------|-------------------------------|
| q1 InstructDS | A vector | 76.6 | 4 | ✅ | 0.918 |
| q1 | B catalog | 290.4 | 30 | ✅ | 0.936 |
| q1 | **C hybrid** | 377.4 | 36 | ✅ | 0.936 |
| q2 MultiMedQA | A vector | 49.0 | 4 | ✅ | 0.868 |
| q2 | B catalog | 258.9 | 30 | ❌ (relative cut) | 0.868 |
| q2 | **C hybrid** | 322.8 | 36 | ❌ (relative cut) | 0.868 |
| q3 trap cropping | A vector | 38.5 | 3 | ✅ | 0.796 |
| q3 | B catalog | 409.6 | 30 | ✅ | 0.829 |
| q3 | **C hybrid** | 548.2 | 37 | ✅ | 0.829 |

## Hybrid merge behavior (the dedup contract, verified on real data)

| q | vector lane | catalog lane | merged | both | vector-only | catalog-only | reread | unscanned |
|---|------------|--------------|-------:|-----:|------------:|-------------:|-------:|----------:|
| q1 | 5.8s / 9 docs | 19.7s / 30 docs | 38 | 1 | 8 | 29 | 6 ok | 2 empty-content |
| q2 | 5.0s / 9 docs | 19.8s / 30 docs | 37 | 2 | 7 | 28 | 6 ok | 1 |
| q3 | 7.3s / 10 docs | 20.7s / 30 docs | 39 | 1 | 8 | 29 | — | — |

- Retrieval phase runs concurrently: wall time ≈ max(lanes) ≈ 20s instead of ~26s serial.
- `lane=both` documents are read once and judged once (q1 gold part 2: vector 0.776 + judge 0.918).
- Vector-only proposals that read as empty (Corpus-Chunks800 / aw-industrial smoke docs)
  are reported in `unscanned`, never judged on their description — honest-coverage rule working.

## q2 calibration finding and the lane-agreement rescue

Without lane-agreement, q2 B/C cut the gold: a lexically-attractive wrong doc
(Vision-Flan, part 2) scored 0.974 and pushed the relative cut to 0.874, above the
gold's 0.868. The gold part 1 was `lane=both` (two independent lanes agreed).

`C_hybrid_q2_laneagree.json` — same run with `--lane-agreement`:
gold kept=True (0.8683 ≥ absolute threshold, both-lane agreement), **gold in evidence**, kept 8 docs.
Answerable: MultiMedQA = 6 QA datasets + HealthSearchQA; Flan-PaLM SOTA on MedQA.

## Answer quality summary

- q1: all three modes answer fully (query-based generation pipeline; InstructDS outperforms SOTA baselines).
- q2: only A (and C with `--lane-agreement`) answer fully. B/C without the rule keep
  Vision-Flan/schizophrenia-review docs instead of the gold — a plausible-but-wrong answer risk.
- q3: all three modes answer fully (5–20% trap-crop allocation; eggplant ~49× attraction).

## Timing note

C is the slowest wall-clock (377–548s) because the union set (36–37 docs, 282–344
segments) is judged on CPU Laya. Parallelism wins on the retrieval phase; judge cost
scales with coverage. If latency matters, reduce `--doc-budget` or run the engine on GPU.

## Environment incident (documented, resolved)

At ~17:47 the backend (main.py, port 8771) restarted and rotated its auth token;
kb-mcp then returned empty catalogs (401 → retry ≈48s → empty) for ~15 minutes.
`lib.check_token()` refreshed `storage/loop-auth.json` via web login; MCP verified
restored (10 KBs / 4.9s). The failed first rescue attempt (17:50, empty lanes) is a
victim of this incident; the successful rerun (18:09) overwrote its transcript.
