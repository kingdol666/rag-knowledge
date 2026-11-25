# HMRS companion evidence inventory: source map

Paths below are relative to the repository root. For package paths written `SOURCE/...`, replace `SOURCE` with `paper-kbs/finalpaper/HMRS-KBS-FINAL-20261124-EVIDENCE-LAYOUT/04-source/source`. This is a lookup aid for the companion inventory. The full claim-to-record mapping belongs to the evidence crosswalk in `SOURCE/supplementary.tex`; the benchmark verification entry point is `benchmark-suite/paper-results-kbs-20261125/verification/verify_all.py`.

## Manuscript and supplement records

### E1 — Storage, catalogue and index checks

- `benchmark-suite/paper-results-kbs-20261125/records/legacy/desc_audit.json` — stored-part description checks under `audit`.
- `benchmark-suite/paper-results-kbs-20261125/records/legacy/probe5_final.json` — filename-stem identifier probes. Use each row's probe result and inspect the query scope before treating it as a collection-specific observation.
- `benchmark-suite/paper-results-kbs-20261125/records/legacy/ingest_report.json` and `benchmark-suite/results/r2_organize/audit_manifest.json` — separate ingestion and reconciliation records. Do not use the earlier reconciliation sample as a denominator for the later description audit.
- `SOURCE/n8a_eval.tex`, `sec:exp-e1` — manuscript scope, including the distinction between an index defect and a later stale cache label. Use the supplement's crosswalk for the underlying checks and which incidents are report-level.

### E2 — Native answer quality and judging sensitivity

- `benchmark-suite/paper-results-kbs-20261125/records/external_baselines_v3/answers-v3.jsonl` and `benchmark-suite/paper-results-kbs-20261125/records/external_baselines_v3/judgments-unified.jsonl` — join on `(qid, arm)`; code assignments are in `benchmark-suite/paper-results-kbs-20261125/records/external_baselines_v3/mapping-unified.json`. See `benchmark-suite/paper-results-kbs-20261125/tables/t6_external_baselines.csv` for the released aggregate and `SOURCE/n8d_eval.tex`, `tab:external-baselines`, for its interpretation. In `benchmark-suite/paper-results-kbs-20261125/records/external_baselines_v3/summary-unified.json`, `primary.deepread-native.mean_cost_usd` is `null`; do not interpret the answer rows' zero placeholder as zero cost.
- `benchmark-suite/paper-results-kbs-20261125/records/external_baselines_v3/hmrs-search-scope-audit.json` — `per_question`, `totals` and `distinct_collections_in_results` record why the configured scope is not the observed search scope.
- `benchmark-suite/paper-results-kbs-20261125/records/external_baselines_v3/judgments-v4-sub.jsonl` — repeat judgments on the saved answers. In `benchmark-suite/paper-results-kbs-20261125/records/external_baselines_v3/summary-unified.json`, `judge_batches` holds the earlier batch aggregates. The earlier four-arm answer subset and its separate judgments are `benchmark-suite/paper-results-kbs-20261125/records/baseline_quality_v2/answers-v2.jsonl` and `benchmark-suite/paper-results-kbs-20261125/records/baseline_quality_v2/judgments-v2.jsonl`.
- `SOURCE/external-baselines-qa.tex` — separate transcript of the native comparison, not the illustrated Figure 5 run.

### Figure 5 — Separate BQ07 workflow illustration

- `benchmark-suite/paper-results-kbs-20261125/records/tiered_case/tiered-bq07.json` — catalogue-first BQ07 execution (`qid`, `question`, `calls`, `answer`); `benchmark-suite/paper-results-kbs-20261125/records/tiered_case/trace-evidence.json` supplies selected tool-return evidence. `SOURCE/n8b_eval.tex`, `fig:tiered-case`, states the non-pooling rule. The run is neither a new native E2 row nor an E3 route-audit row.
- `benchmark-suite/paper-results-kbs-20261125/records/external_baselines_v3/fig-hmrs-case-provenance.json` — earlier BQ07 native E2 search path. Its `calls` and answer-row locator identify the E2 record; this file does **not** back the current Figure 5.

### E3/E4 — Collection routing and evidence-pack containment

- `benchmark-suite/paper-results-kbs-20261125/records/routing_content_traces/supp_traces_frozen.csv` — select `is_refusal=False`; count `route_correct=True` by `arm` for A0 and A3, and `gold_hit=True` for containment for A0 and A0h. `bytes_ingested` is the trace text counter. Neither passage text nor the matched reference strings are included in the released traces.
- `benchmark-suite/paper-results-kbs-20261125/records/routing_content_traces/supp_traces_followup.csv` and `benchmark-suite/paper-results-kbs-20261125/records/routing_content_traces/supp_traces_rerun_20261117.csv` — same-question reruns; compare matching question IDs within each run.
- `SOURCE/n8b_eval.tex`, `sec:exp-e3` and `sec:exp-e4` — possible A3 fallback, definitions of the scoped configurations and interpretation of the text counter. `SOURCE/n8a_eval.tex`, `sec:eval-setup` — metric definitions.

### E5 — Operational lessons

- `SOURCE/n8b_eval.tex`, `sec:exp-e5`, and `paper-kbs/tex/journal_20p/n8b_eval.tex` — report-level observations of the experience-store checks and their limits. `benchmark-suite/scripts/94_experience_smoke.py` is an example of the test procedure, not a retained successful tool response or a source for a score.

### E6 — Verifier ordering versus admission

- `benchmark-suite/paper-results-kbs-20261125/records/paired_diagnostics/redraw_verifier_order.csv` — paired `fusion_hit` and `verifier_hit` flags keyed by `qid`. Sum the columns for the two Hit@5 counts; tabulate discordant pairs to see which order gained or lost hits. These flags do not measure admission.
- `benchmark-suite/paper-results-kbs-20261125/records/paired_diagnostics/redraw_verifier_scores.csv` — separate score archive (`qid`, `group`, `score`). `SOURCE/n8c_eval.tex`, `sec:exp-e6` and `fig:verifier`, describes the two archives. Do not substitute `paper-kbs/experiments/results/exp5_judge_filter.json`, which is an earlier replay.

### E7 — Lexical answer proxies and absent-answer probes

- `benchmark-suite/paper-results-kbs-20261125/records/legacy/exp_r2_grade_corrected.json` and `benchmark-suite/paper-results-kbs-20261125/records/legacy/exp_rerun5_grade.json` — `rows` plus the `citation_definition` and `keyword_alias_policy` fields. The historical track keys are `a2`, `b`, and `c`. See `SOURCE/supplementary.tex`, `tab:s-answer-grid` and `tab:s-answer-summary`, for the manuscript's arm labels, and **Archive: answer grids** below for the wording caveat.
- `benchmark-suite/paper-results-kbs-20261125/records/legacy/exp8b_absent_agent.json` — separate absent-answer probes; `answer_head` records the reply opening. `SOURCE/n8c_eval.tex`, `sec:exp-e7`, describes the limits on abstention and the success-status observations.

## Historical coverage only

### Archive: inventory

- `paper-kbs/finalpaper/HMRS-KBS-FINAL-20261124-VERIFIED-READING/04-source/source/inventory-build/supplementary-inventory.md` — unchanged prior inventory, with the original campaign and table labels.
- `paper-kbs/finalpaper/HMRS-KBS-FINAL-20261124-VERIFIED-READING/04-source/source/inventory-build/supplementary-inventory-source-map.md` — the old path and run-ID catalogue, not a list of verified inputs. One archival lookup correction: its historic S6 entry refers to `paper-kbs/experiments/results/exp1_retrieval.json`, specifically `rows` where `method` is `qdcvr_hybrid` and the values are in `judge_scores.all`.

### Archive: acquisition

- `paper-kbs/experiments/results/exp10_ingest_state.json` (`parse_task_done`, `saved`, `saved_all`) and `paper-kbs/experiments/results/exp10_papers_toollayer.json` (`n_docs`) — different acquisition snapshots. `review/_exp_rerun_20261114/disk_inventory.json` is another inventory, not a per-paper parse log.
- `paper-kbs/notes/functional-test-evidence-2026-10-12.md` — a report of lifecycle and reorganisation checks, not a substitute for missing primary run records.

### Archive: retrieval

- `paper-kbs/experiments/kbcommon.py` (`QUESTIONS`) and `paper-kbs/experiments/derive_appendix.py` — historical question definitions and rank-table generation.
- `paper-kbs/experiments/results/exp6_loo_margin.json`, `paper-kbs/experiments/results/exp6_paraphrase.json`, `paper-kbs/experiments/results/exp7_second_signal.json`, `paper-kbs/experiments/results/exp9_span_nli.json` — earlier threshold, paraphrase and NLI diagnostics; not inputs to the retained verifier ordering.
- `paper-kbs/notes/exp11-gate-ablation-report.md` and `paper-kbs/notes/exp12-partition-ablation-report.md` — historical gate and partition protocols. They are not the E4 configuration study.

### Archive: route cards

- `review/experiment-redesign-20261101/RESULTS.md` and `review/experiment-redesign-20261101/artifacts/final_bench/s4_traces_final.json` — earlier route-card protocol and surviving trace artifact. Do not combine them with the released E3/E4 traces.

### Archive: answer grids

- `benchmark-suite/results/runs/run-20261013T094350Z-5f9faac/track_a2_BQ06.json` and `benchmark-suite/results/runs/rerun5-20261017/track_a2_BQ06.json` — compare `question` for the original and common-substrate runs. The agreement script joins by identifier; even with the same `qid`, the prompts do not ask exactly the same question.
- `paper-kbs/experiments/results/e5_replication_agreement.json`, `paper-kbs/experiments/e5_replication_agreement.py` and `paper-kbs/experiments/source_presence_audit.py` — prior cross-grid and source-presence analyses.
