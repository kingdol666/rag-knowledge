# KBS submission — HMRS experiment results

This is the benchmark snapshot for *HMRS: Hierarchical document management for evidence-traced retrieval*, in `paper-kbs/finalpaper/HMRS-KBS-FINAL-20261124-EVIDENCE-LAYOUT`. The supplement contains a claim-to-record crosswalk; its companion evidence index explains which quantities can be recomputed and which observations are documented only in campaign reports. The publication snapshot does not replace historical experiment archives.

| Submission item | Records under `records/` | Scope |
|---|---|---|
| Fig. 5, BQ07 catalogue-first walkthrough | `tiered_case/tiered-bq07.json`, `tiered_case/trace-evidence.json` | Separate execution, not part of the E2 blind scores or E3 routing counts. |
| Table 6 (E2), native deployment | `external_baselines_v3/answers-v3.jsonl`, `judgments-unified.jsonl` and `hmrs-search-scope-audit.json` in the same directory | 80 answers and 80 judgments; the deployments differ in effective search scope and source access. |
| E2 judging and sensitivity, Tables S18–S22 | `baseline_quality_v2/` and `external_baselines_v3/` | S18 earlier four-arm per-question scores; S19 cross-batch means; S20 unified per-question scores; S21 earlier four-arm aggregate; S22 seven paired comparisons and Holm-adjusted results (`tables/s22_unified_holm.csv`). The batches are not pooled. |
| E3–E4 and Figs. 6–7, Tables S12–S13 | `routing_content_traces/supp_traces_*.csv`, `routing_content_traces/redraw_*_summary.csv` | Route correctness, literal target containment and trace-counted text volume. The frozen 72-question cohort excludes the four refusal probes. Reruns reuse the questions. |
| E6 and Fig. 8 | `paired_diagnostics/redraw_verifier_order.csv`, `paired_diagnostics/redraw_verifier_scores.csv` | The fixed-pool order replay and score archive answer different questions. Neither is evidence of an admission benefit. |
| Management, experience and operational checks | `legacy/` | Individual probe exports and contemporaneous campaign reports; consult the supplement for the exact record or report supporting each statement. |

`fig-hmrs-case-provenance.json` under `external_baselines_v3/` is the *different*, native E2 BQ07 trace and does not underlie the replacement Figure 5. Raw data files also retain historical scope and batch differences, including unmetered DeepRead cost (not zero cost). Earlier estimates from unrelated runs are not substitutes for a missing observation. `tables/` contains derived CSVs, not new model output. The two `e1_redraw_*_summary.csv` filenames are retained for compatibility with the frozen archive; they summarize the E3/E4 results, not the E1 lifecycle checks.

From this directory, rerun the verification and check the pinned record bytes:

```bash
python -I -X utf8 verification/verify_all.py
sha256sum -c verification/records-sha256.txt
```

`verification/report.json` records the comparison inputs and the results of each check. A data replay confirms arithmetic and agreement with the printed manuscript and supplement for the listed claims; it does not rerun the models or prove claim-level support in the answers. See the supplement for archive limitations (for example, missing returned passages and unlogged route fallbacks).
