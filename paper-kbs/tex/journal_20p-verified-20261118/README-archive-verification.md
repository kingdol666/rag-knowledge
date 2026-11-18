# Archived-label verification

Run with Python 3.9 or newer, from any working directory:

```text
python -I -B /path/to/journal_20p-verified-20261118/verify_archived_labels.py
```

The standard-library-only script reads the three `experiment_data/supp_traces_{frozen,followup,rerun_20261117}.csv` files alongside it. It neither connects to a service nor writes data; `-B` also disables Python bytecode files. It checks duplicate `(arm, qid)` pairs, the same 72 non-refusal question IDs and four refusal IDs with consistent `is_refusal` labels across complete arms and campaigns, complete-arm hit counts against the archived table, A0/A3 correct-collection counts from `route_correct`, and A0h-versus-A0/PD discordant pairs and exact two-sided McNemar p-values. The p-value is twice the lower binomial tail under p=0.5, capped at 1; zero discordances gives 1. Values are exploratory and unadjusted. Nonzero exit indicates malformed input or a failed check.

`A1-readall` is checked separately: a complete frozen set is reported as such, while missing or partial sets are never treated as 72 misses or as a complete hit rate. The follow-up and November 17 CSVs contain no read-all rows; their absence in these files does not establish that no partial scan existed elsewhere. The paper reports three completed follow-up rows and says the November 17 scan was omitted.

This only recomputes and checks the **archived labels**. It does not verify labels against source texts, prove the intended 72-ID list independently, evaluate answer correctness, or reproduce the real system. Count references are taken from `supplementary-arm-tables.tex`, not independently established ground truth.
