# Experiment records

This folder holds the records behind Section 8.3 (E2) of the manuscript and
Supplementary Tables S18–S21. The files are stored as produced during the
runs. The companion `external-baselines-qa.pdf` prints every answer with its
scores and rationale; `build_external_baselines_qa.py` regenerates its source
from `answers-v3.jsonl` and `judgments-unified.jsonl`.

## Arm names

| `arm` in the records | Manuscript (Table 6) | Indexed scope at answer time |
|---|---|---|
| `hmrs-agent` | HMRS agent | full export, 328 parts |
| `bm25` | BM25 | full export |
| `dense` | Dense (BGE-M3) | full export |
| `rrf` | RRF-order (k = 60) | full export |
| `raptor` | RAPTOR | 30 gold parts |
| `lightrag` | LightRAG | full export, 699 chunks |
| `deepread-native` | DeepRead | 23 of 96 native documents (including the gold papers); 96 parsed after answering |
| `graphrag` | GraphRAG | 30 gold parts |

The HMRS index covered the full export, but its search calls were not
consistently restricted to the five configured collections; see
`external_baselines_v3/hmrs-search-scope-audit.json` and Section 8.3.

Questions are `BQ01`–`BQ10`; `arxiv` and `kw_list` in each answer row give the
gold paper identifier and the annotated keywords of the question.

## `external_baselines_v3/`: unified eight-arm comparison

| File | Content |
|---|---|
| `answers-v3.jsonl` | 80 rows (8 arms × 10 questions): question text, gold identifier and keywords, engine and model identifier, HTTP status and error, wall time and latency, number of turns and tool calls with the tool-name sequence, metered cost, the verbatim answer, and the context units that entered the prompt after the twelve-unit cap (`sources`: document path, score, text). |
| `judgments-unified.jsonl` | 80 rows of the unified blind pass: four dimension scores (`factual`, `completeness`, `groundedness`, `sources`), verdict, per-dimension rationale and summary rationale. `system` is the anonymous letter of the arm. |
| `mapping-unified.json` | Anonymous letter assigned to each arm for each question. |
| `summary-unified.json` | Per-arm means and verdict counts of the unified pass (`primary`) and the cross-batch means of Table S19 (`judge_batches`). |
| `paired-unified.json` | Paired exact sign tests and exact McNemar tests for the three retrieval-mode contrasts against HMRS, derived by `figure_scripts/build_unified_paired_stats.py`. |
| `external-baselines-v3-derived.json` | Per-arm and per-question derived values, head-to-head counts and the indexed scope of each arm; records the SHA-256 of its two sources. |
| `judgments-v4-sub.jsonl` | Repeat subagent batch on the same 80 answers (Table S19, column v4). |
| `parse_log.jsonl` | Native DeepRead parse log: the 96 documents and their parse durations. |
| `protocol/` | Verbatim prompt texts: `answer-prompt.txt` is the one-shot prompt template of the retrieval-mode arms and `judge-instruction.txt` is the judge instruction of the unified pass, identical for all ten questions. |
| `translation-en/` | Reading overlay of the companion transcript, not part of the records: faithful English translations of the 11 answers that were generated in Chinese (`hmrs-agent` BQ01–BQ05 and BQ08–BQ10, `deepread-native` BQ05) and English glosses of the Chinese collection names that occur in context paths. The answers and judgments above are unchanged. |
| `fig-hmrs-case-provenance.json` | Tool-call trace of the deployed HMRS agent on E2 BQ07: the three calls with their queries, result counts and scores, and the document read. It supports the E2 narrative, not Figure 5. |

Per-question judgments are shipped for the unified pass, the v4 batch and the
earlier four-arm pass. The per-arm means of the two further earlier passes R1
and R2 of Table S19 are stored in `judge_batches` of `summary-unified.json`.

## `baseline_quality_v2/`: earlier four-arm pass

| File | Content |
|---|---|
| `answers-v2.jsonl` | The 40 answers of the four retrieval-mode arms, identical to the corresponding rows of `answers-v3.jsonl`. The HMRS search scope was not consistently restricted to the five configured collections. |
| `judgments-v2.jsonl` | 40 rows of the earlier pass that scored one answer per isolated call: dimension scores, verdict, rationale and the first 200 characters of the raw response (`raw_head`). |
| `mapping-v2.json` | Anonymous letters of that pass. |
| `summary-v2.json` | Per-arm means of that pass (Table S21). |
| `figure-values.json` | Values of `figs/fig_baseline_quality` with the SHA-256 of their sources. |

## `paired_diagnostics/`: verifier replay (Figure 8)

| File | Content |
|---|---|
| `redraw_verifier_order.csv` | The 16 fixed candidate pools; `fusion_hit` and `verifier_hit` mark a gold document in the top five under each order. Fusion keeps 15, verifier-score order keeps seven. |
| `redraw_verifier_scores.csv` | The 191 recorded Laya scores over the same pools: 17 gold and 174 non-gold candidates, medians 0.8759 and 0.8627. No recorded score is at or below 0.5; one further candidate (Q14) had no recorded score. |

These tables are the archived E6 records from which Figure 8 is drawn. The
counts are recomputed from the tables; no value is re-estimated.

## Recomputing the reported values

- `figure_scripts/build_unified_paired_stats.py` derives `paired-unified.json`
  from `judgments-unified.jsonl`.
- `figure_scripts/build_fig_external_baselines.py` derives the unified-pass
  scores of `figs/fig_external_baselines` from `judgments-unified.jsonl`. The
  heat map repeats Table 6 and is kept in the package without being placed in
  the manuscript or the supplement.
- `figure_scripts/build_fig5_tiered_case.py` draws Figure 5 from the independently captured BQ07 trace in `tiered_case/`. It is not part of either the E2 answer-quality or the E3 routing results.
- `figure_scripts/build_baseline_quality_supplement.py` builds Table S18 from
  the hash-checked records of `baseline_quality_v2/`.
- `build_external_baselines_qa.py` regenerates `external-baselines-qa.tex`,
  showing the Chinese answers through the `translation-en/` overlay.

The scripts resolve their inputs relative to their own location. Model
identifiers in the raw records carry a provider prefix; the manuscript and the
transcript give the model name only.
