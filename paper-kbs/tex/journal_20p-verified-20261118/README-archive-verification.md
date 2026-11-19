# Archived-label verification

Run with Python 3.9 or newer, from any working directory:

```text
python -I -B /path/to/journal_20p-verified-20261118/verify_archived_labels.py
```

The standard-library-only script reads the three `experiment_data/supp_traces_{frozen,followup,rerun_20261117}.csv` files alongside it. It neither connects to a service nor writes data; `-B` also disables Python bytecode files. It checks duplicate `(arm, qid)` pairs, the same 72 non-refusal question IDs and four refusal IDs with consistent `is_refusal` labels across complete arms and campaigns, complete-arm hit counts against the archived table, A0/A3 correct-collection counts from `route_correct`, and A0h-versus-A0/PD discordant pairs (also A0h versus A0f for November~17) and exact two-sided McNemar p-values. The p-value is twice the lower binomial tail under p=0.5, capped at 1; zero discordances gives 1. Values are exploratory and unadjusted. Nonzero exit indicates malformed input or a failed check.

`A1-readall` is checked separately: a complete frozen set is reported as such, while missing or partial sets are never treated as 72 misses or as a complete hit rate. The follow-up and November 17 CSVs contain no read-all rows; their absence does not establish that no partial scan existed elsewhere. The November 12 scan was incomplete; the November 17 scan was omitted.

This only recomputes and checks the **archived labels**. It does not verify labels against source texts, independently establish the 72-ID list, evaluate answer correctness, or rerun the system. Count references are the reported table values, not independently established ground truth.

## November evidence checks

From the manuscript directory:

```text
python -I -B verify_november_sources.py
python -I -B figure_scripts/build_fig_latest.py --check-only
```

These commands require no live service. They recompute released trace metrics and validate the two figures' input data; the figures can be rebuilt with Matplotlib (omit `--check-only` when generating into an empty copy). `experiment_data/november_source_checks.json` records the dated batch and deployment checks separately from the research benchmark. In particular, the November 18 initial contract run and the later readback retests are not pooled as a first-pass success rate. The vector-response assertion could pass with an empty results list and is not evidence of a returned document.

With the full repository and original local artifacts available, use:

```text
python -I -B verify_november_sources.py --repo-root ../../.. --require-originals
python -I -B rescore_bq_answers_20261115.py --repo-root ../../.. --check-dir bq_supplement_20261115
```

Use an explicit absolute repository path if the manuscript is not in its repository directory. The first command checks pinned sources and compares all 532 November 17 rows and 13 export columns byte-for-byte with the original merged trace; it also recomputes engineering assertions and the question-overlap split. The second reproduces the two November 15 answer-rescoring CSVs from the archived answers and annotations. The raw November 18 API records remain local; an external reader receives the sanitised summary, not the raw service receipts. None of these commands reproduces the live corpus/index state or independently validates all November 17 containment labels, because the full returned packs were not retained.
