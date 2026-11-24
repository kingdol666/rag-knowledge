# Supplementary inventory source map

Look up the `section / Src n` references from `supplementary-inventory.md` here. Paths are relative to the `rag-knowledge` repository root unless noted. File patterns, run identifiers and field names are preserved for lookup. Some entries point to historical artifacts that may not be in the current checkout or release. This map does not redistribute those artifacts or change their access or licensing terms. It is separate from the inventory passed to Pandoc.

## Part A. System-level test campaigns

### A.1 Eighteen-scenario end-to-end harness campaign

- **A.1 / Src 1.** `review/fulltest-20261012/SUMMARY.md`.

### A.2 Archived three-lane stability suite

- **A.2 / Src 1.** Original report: `review/stability-multiround-20260930/REPORT.md`.
- **A.2 / Src 2.** Original run files: `review/stability-multiround-20260930/results/r{1,2,3}_{attention,seismology,pickles}_{A,B,C}.json`.
- **A.2 / Src 3.** Runner: `review/stability-multiround-20260930/run_stability.py`.
- **A.2 / Src 4.** Later rerun: `review/stability-multiround-20261013/results`.

### A.3 Concurrency and load campaign

- **A.3 / Src 1.** `review/stress-20260923/STRESS-REPORT.md`.

### A.4 Paper acquisition campaign

- **A.4 / Src 1.** `paper-kbs/experiments/results/exp10_ingest_state.json`. Library ID `6a3c45f2-a1a1-4ce7-b64d-7a5a2f293bb5`; parse task ID `40f6fd42930d`; keys `parse_task_done`, `saved`, `saved_all`.
- **A.4 / Src 2.** `paper-kbs/experiments/results/exp10_papers_toollayer.json`; key `n_docs`.
- **A.4 / Src 3.** Later disk inventory: `review/_exp_rerun_20261114/disk_inventory.json`.

### A.5 Fifty-paper ingest and 30,000-character tier

- **A.5 / Src 1.** `benchmark-suite/results/BENCHMARK-30000chunk-20260918.md`.
- **A.5 / Src 2.** `benchmark-suite/results/ingest_report.json`; per-record keys `tag_ok`, `verify_ok`.
- **A.5 / Src 3.** `paper-kbs/notes/functional-test-evidence-2026-10-12.md`.
- **A.5 / Src 4.** `paper-kbs/tex/journal_20p/n8a_eval.tex`.

### A.6 Reorganisation campaign

- **A.6 / Src 1.** `paper-kbs/notes/functional-test-evidence-2026-10-12.md`.
- **A.6 / Src 2.** `benchmark-suite/results/R2-SCALING-20260921.md`.
- **A.6 / Src 3.** `paper-kbs/tex/journal_20p/n8a_eval.tex`.

### A.7 Cross-lingual ingestion campaign

- **A.7 / Src 1.** `paper-kbs/tex/journal_20p/_appendix-archived/n_appendix_tables.tex`; Table S2 in the manuscript source before the 2026-10-16 revision.
- **A.7 / Src 2.** `paper-kbs/tex/journal_20p/n8a_eval.tex`.
- **A.7 / Src 3.** `paper-kbs/tex/journal_20p/n4_acquisition.tex`.
- **A.7 / Src 4.** `benchmark-web/benchmark/results/benchmark/`, in the separate web-repository checkout, not in this repository.

### A.8 Sixteen-skill lifecycle scenarios

- **A.8 / Src 1.** `benchmark-suite/results/SKILL-E2E-REPORT.md`.
- **A.8 / Src 2.** `.e2e/skilltest/calls.jsonl`.
- **A.8 / Src 3.** Disposable library lookup IDs in the report and call log: `E2E-SkillTest-1457` = `95f4e9a1-b24d-43c1-b94d-04c55d90b5d1`; `E2E-SkillTest-Dst-1457` = `c2e2bf92-db86-48f5-96f8-7ac9b9931f67`.

### A.9 Static skill and tool evidence chain

- **A.9 / Src 1.** `benchmark-suite/results/SKILL-AUDIT.md`.
- **A.9 / Src 2.** `benchmark-suite/results/SKILL-SMOKE.md`.
- **A.9 / Src 3.** `benchmark-suite/results/SKILL-STANDARD-AND-CHAT-LANE-TEST.md`.

### A.10 Isolated-environment ingest and index probe

- **A.10 / Src 1.** `benchmark-suite/results/SKILL-E2E-REPORT.md`.

### A.11 Three-channel retrieval end-to-end campaign

- **A.11 / Src 1.** `review/retrieval-e2e-20261012/REPORT.md`.
- **A.11 / Src 2.** `review/retrieval-e2e-20261012/channel1_summary.json`.
- **A.11 / Src 3.** `benchmark-suite/results/runs/chatmodes-20261012T061102Z-5f9faac/CHAT-MODES-COMPARE.md`; run ID `chatmodes-20261012T061102Z-5f9faac`.
- **A.11 / Src 4.** `benchmark-suite/results/runs/run-20261012T062847Z-5f9faac/RETRIEVAL-COMPARE.md`; run ID `run-20261012T062847Z-5f9faac`, shortened in the historical inventory to `run-20261012T062847Z`.
- **A.11 / Src 5.** Earlier latency baseline, identified in the historical inventory as the 2026-09-26 baseline; the archived manuscript describes this snapshot in `paper-kbs/tex/n8b_eval.tex`.

### A.12 Stratified three-track run

- **A.12 / Src 1.** `benchmark-suite/results/stratified_grade_smoke.md`.
- **A.12 / Src 2.** `benchmark-suite/results/stratified_grade_smoke.json`; run ID `experiment_chat_20260922-211000`; `notfound_accuracy` and the judge-derived `correct` field.
- **A.12 / Src 3.** `benchmark-suite/data/papers/qa_questions.json` (named `qa_questions.json` in the archived report).

### A.13 Harness and honest-refusal campaign

- **A.13 / Src 1.** `benchmark-suite/results/PIPELINE-REPORT-20260930.md`.
- **A.13 / Src 2.** System-arm run ID `chatmodes-20260930T143945Z-3ec2174`.
- **A.13 / Src 3.** Reliability round 1 key `run-20260930T165316Z`.
- **A.13 / Src 4.** Reliability round 2 key `run-20260930T170730Z`.

### A.14 Two-lane isolation test

- **A.14 / Src 1.** `benchmark-suite/results/SKILL-STANDARD-AND-CHAT-LANE-TEST.md`.

### A.15 Three-engine and three-channel cost campaign

- **A.15 / Src 1.** `review/fulltest-20261012/SUMMARY.md`.
- **A.15 / Src 2.** `review/retrieval-e2e-20261012/channel1_summary.json`.
- **A.15 / Src 3.** `review/retrieval-e2e-20261012/REPORT.md`.
- **A.15 / Src 4.** `benchmark-suite/results/runs/chatmodes-20261012T061102Z-5f9faac/CHAT-MODES-COMPARE.md`; run ID as in A.11 / Src 3.
- **A.15 / Src 5.** `benchmark-suite/results/runs/run-20261012T062847Z-5f9faac/RETRIEVAL-COMPARE.md`; run ID as in A.11 / Src 4.
- **A.15 / Src 6.** `paper-kbs/notes/functional-test-evidence-2026-10-12.md`.
- **A.15 / Src 7.** `paper-kbs/supplementary/supplementary-material.md`.
- **A.15 / Src 8.** Exclusion check: `paper-kbs/experiments/results/exp8b*.json` matches `paper-kbs/experiments/results/exp8b_absent_agent.json`, not a cost-table source.

### A.16 Original 30-cell answer grid

- **A.16 / Src 1.** `benchmark-suite/results/runs/run-20261013T094350Z-5f9faac/track_*.json`; run ID `run-20261013T094350Z-5f9faac`; keys `latency_s`, `tool_call_count`, `total_cost_usd`.
- **A.16 / Src 2.** `benchmark-suite/results/exp_r2_grade_corrected.json`.

### A.17 Deployment-layer system arms

- **A.17 / Src 1.** `review/retrieval-e2e-20261012/`; see A.11 / Src 1 and A.11 / Src 2 for the report and streaming summary.

### A.18 Failure-mode catalogue

- **A.18 / Src 1.** Earlier manuscript: `paper-kbs/tex/n9_discussion.tex`, label `tab:failures`.
- **A.18 / Src 2.** `paper-kbs/notes/review-round3-2026-10-09.md`.
- **A.18 / Src 3.** `paper-kbs/notes/review-2026-10-08.md`.
- **A.18 / Src 4.** `paper-kbs/notes/restructure-plan-2026-10-12.md`.
- **A.18 / Src 5.** `paper-kbs/notes/functional-test-evidence-2026-10-12.md`.
- **A.18 / Src 6.** `benchmark-suite/results/SKILL-E2E-REPORT.md`.
- **A.18 / Src 7.** `benchmark-suite/results/graph_stats.json`.
- **A.18 / Src 8.** `benchmark-suite/results/tags_report.json`.

### A.19 Common-substrate replication

- **A.19 / Src 1.** `benchmark-suite/results/runs/rerun5-20261017/`; run ID `rerun5-20261017`.
- **A.19 / Src 2.** `benchmark-suite/results/exp_rerun5_grade.json`.
- **A.19 / Src 3.** `benchmark-suite/experiments/chat_tracks.py`; configuration names `RAG_BENCH_PIN_KB`, `RAG_BENCH_CORPUS_DIR`.
- **A.19 / Src 4.** `paper-kbs/experiments/e5_replication_agreement.py`.
- **A.19 / Src 5.** `paper-kbs/experiments/results/e5_replication_agreement.json`.

### A.20 Paired route-card audit

- **A.20 / Src 1.** `review/experiment-redesign-20261101/RESULTS.md`.
- **A.20 / Src 2.** `review/experiment-redesign-20261101/artifacts/final_bench/s4_traces_final.json`.
- **A.20 / Src 3.** `review/experiment-redesign-20261101/artifacts/final_bench/s6_stats.json`.
- **A.20 / Src 4.** `review/experiment-redesign-20261101/artifacts/provenance/pdf_anchor_audit_20261104.json`.

## Part B. Retrieval evaluation matrix

### B.1 Five configurations on the 42-document corpus

- **B.1 / Src 1.** `paper-kbs/experiments/results/exp1_summary.json`.

### B.2 Judged / as-filter / judge-fuse decomposition

- **B.2 / Src 1.** `paper-kbs/experiments/results/exp5_judge_filter.json`; `rrf_fuse` is the fuse-replay key.
- **B.2 / Src 2.** `paper-kbs/experiments/results/exp1_summary.json`.

### B.3 Threshold selection

- **B.3 / Src 1.** `paper-kbs/experiments/results/exp6_loo_margin.json`.

### B.4 Paraphrase grid

- **B.4 / Src 1.** `paper-kbs/experiments/results/exp6_paraphrase.json`.

### B.5 Derived-library matrix

- **B.5 / Src 1.** `paper-kbs/experiments/results/exp10_papers_toollayer.json`.

### B.6 Four-lane agentic grid

- **B.6 / Src 1.** `paper-kbs/experiments/results/exp2_lanes/summary.json`.
- **B.6 / Src 2.** `paper-kbs/experiments/results/exp2_lanes/summary_gen.json`.
- **B.6 / Src 3.** `paper-kbs/experiments/results/exp2_lanes/run_{search,librarian,hybrid,bare}-Q{2,4,6,7}.json`.
- **B.6 / Src 4.** `paper-kbs/experiments/results/exp2_lanes_rep2/summary.json` and `paper-kbs/experiments/results/exp2_lanes_rep2/run_{search,librarian,hybrid,bare}-Q{2,4,6,7}.json`.

### B.7 Abstention runs

- **B.7 / Src 1.** `paper-kbs/experiments/results/exp4_abstention/run_{hybrid,librarian,search}-O{1,2}.json`.
- **B.7 / Src 2.** `paper-kbs/experiments/results/exp8b_absent_agent.json`.

### B.8 Out-of-corpus tool-layer probes

- **B.8 / Src 1.** `paper-kbs/experiments/results/exp3_abstention.json`.

### B.9 Graded probes

- **B.9 / Src 1.** `paper-kbs/experiments/results/exp8_graded_probes.json`.

### B.10 NLI second signal

- **B.10 / Src 1.** `paper-kbs/experiments/results/exp7_second_signal.json`.

### B.11 Span-level NLI

- **B.11 / Src 1.** `paper-kbs/experiments/results/exp9_span_nli.json`.

### B.12 Five-track matrix

- **B.12 / Src 1.** `benchmark-suite/results/runs/run-20260930T174948Z-3ec2174/`; run ID `run-20260930T174948Z-3ec2174`. The source names in this directory are `REPORT.md`, `report.json`, `run_manifest.json` (keys `n_rows`, `prompt_version`, `max_turns`, `selfheal`) and `track_*_QK*.json` (`track_{a2,bm25,vector,rrf,rerank}_QK01..QK10.json` in the historical inventory). The report lists `judge.json`, `qrels_scores.json` and `stats.json` as absent.

### B.13 Verification-gate ablation

- **B.13 / Src 1.** `paper-kbs/experiments/results/exp11_gate_ablation.json`.
- **B.13 / Src 2.** `paper-kbs/experiments/results/exp11/exp11-20261012-full/`; run directory `exp11-20261012-full`. Files named in the inventory: `cell_QK01..QK10.json`, `cand_QK01..QK10.json`, `repairs.json`.
- **B.13 / Src 3.** `paper-kbs/notes/exp11-gate-ablation-report.md`.
- **B.13 / Src 4.** `benchmark-suite/data/papers/qa_quick10.json`.

### B.14 Library-partition ablation

- **B.14 / Src 1.** `paper-kbs/experiments/results/exp12_partition_ablation.json`.
- **B.14 / Src 2.** `paper-kbs/experiments/results/exp12_partition_ablation_n2.json` (superseded).
- **B.14 / Src 3.** `paper-kbs/experiments/results/exp12/exp12-20261012-full/cell_QK01..QK10.json`; run directory `exp12-20261012-full`.
- **B.14 / Src 4.** `paper-kbs/notes/exp12-partition-ablation-report.md`.

### B.15 Sixteen-question gold set

- **B.15 / Src 1.** `paper-kbs/experiments/kbcommon.py`; `QUESTIONS` list, lines 195–292 as recorded in the inventory, with the stale comment at line 190. Keys `qid`, `kb`, `text`, `gloss`, `gold_doc_substrings`, `fact_markers`, `exp2`.
- **B.15 / Src 2.** `paper-kbs/experiments/results/exp1_retrieval.json`; `corpus_docs`.
- **B.15 / Src 3.** `paper-kbs/experiments/results/exp5_judge_filter.json`; row keys `Q1`–`Q16`.
- **B.15 / Src 4.** `paper-kbs/tex/journal_20p/_appendix-archived/n_appendix_tables.tex`; Table S3 in the manuscript source before the 2026-10-16 revision.

### B.16 Per-question rank table and generator

- **B.16 / Src 1.** `paper-kbs/experiments/derive_appendix.py`.
- **B.16 / Src 2.** `paper-kbs/experiments/kbcommon.py`; list `QUESTIONS`.
- **B.16 / Src 3.** `paper-kbs/experiments/results/exp1_retrieval.json`.
- **B.16 / Src 4.** `paper-kbs/experiments/results/exp5_judge_filter.json`.
- **B.16 / Src 5.** `paper-kbs/tex/journal_20p/_appendix-archived/tab_appendix_ranks.tex`.

## Part C. Evidence limitations

- **C / Src 1.** Parent-scope probe: `review/kb-capability-20261021/result.json`.

## Part D. Supporting tables

- **D / Src 1.** `paper-kbs/tex/journal_20p/_appendix-archived/n_appendix_tables.tex` (Tables S1, S2, S3, S5).
- **D / Src 2.** `paper-kbs/tex/journal_20p/_appendix-archived/tab_appendix_ranks.tex` (Table S4).
- **S3 / Src 1.** Q2 gold filename substring `EL-2025-0317`, in the `gold_doc_substrings` field of B.15 / Src 1. This identifies a corpus document, not an execution date for the benchmark.
- **S6 / Src 1.** `paper-kbs/experiments/results/exp1_retrieval.json`; `judge_scores.all` on the `hmrs_hybrid` rows.
- **S6 / Src 2.** `paper-kbs/experiments/kbcommon.py`; `QUESTIONS` for the gold substrings.
- **S7 / Src 1.** `benchmark-suite/results/runs/run-20261013T094350Z-5f9faac/track_*.json`; original answer-grid run ID `run-20261013T094350Z-5f9faac`.
- **S7 / Src 2.** `benchmark-suite/data/papers/qa_questions_e5_corrected.json`.
- **S7 / Src 3.** `benchmark-suite/data/corpus_md/*.md`.
- **S8 / Src 1.** `benchmark-suite/results/runs/rerun5-20261017/track_*.json`; replication-grid run ID `rerun5-20261017`.
- **S8 / Src 2.** `benchmark-suite/data/papers/qa_questions_e5_corrected.json`.
- **S8 / Src 3.** `benchmark-suite/data/corpus_md/*.md`.
- **S8 / Src 4.** `paper-kbs/experiments/source_presence_audit.py`.
