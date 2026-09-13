# Review TODO — what must be supplied before submission

> Companion to `main.tex`. Every `\need{...}` marker in the PDF points here by ID.
> **The paper's own content is ~9 pages; the 12 red markers add ~2 pages of
> to-do text.** Remove every marker (and this list) before submitting — a
> submitted PDF must contain no red text.
>
> Generated 2026-09-13 alongside the reviewer audit (`REVIEWER-AUDIT.md`).
> Frozen data snapshot: `data-snapshot/` (id `2026-09-13-a`, SHA-256 pinned).

Legend: 🔴 blocks submission · 🟠 reviewers will demand it · 🟡 polish

---

## Intro

### TODO-1 · Motivating example is unreproducible 🔴
**Where:** §1, "Similarity is not usefulness".
**Problem:** the worked example (a film-stretching query retrieving literature on
a different polymer) exists only in `docs/paper/PAPER-FRAMEWORK.md`, the
project's internal design notes. No benchmark artefact contains it, so a
reviewer cannot verify it and we cannot defend it.
**Fix:** mine a real case from the frozen `module_b_retrieval_r2.json` — pick a
query whose top-1 vector hit is not the gold document — and report the exact
query, the retrieved title, its cosine score and the gold title. If no clean case
exists, state the failure mode abstractly and drop the example.

---

## Method

### TODO-2 · Blind-spot rule is unevaluated 🟠
**Where:** §4.6 (`sec:blindspot`).
**Problem:** the coverage-declaration rule ("fewer than two bases ⇒ declare
limited coverage") is asserted, never measured.
**Fix:** report both error directions on queries whose gold documents span ≥2
bases — how often the system correctly withholds a single-base answer, and how
often it wrongly suppresses a legitimate single-base result. A rule that
over-suppresses is as harmful as one that never fires.

---

## Experience (architecture kept as-is; measurement missing)

### TODO-3 · Temporal decay threshold unvalidated 🟠
**Where:** §5.3.
**Problem:** the 30-day window and demotion rules are asserted.
**Fix:** (i) decay precision/recall — of the entries the rule demotes, how many
were actually stale (contradicted by a newer document, or never applied after the
window)? (ii) sensitivity sweep over 7/14/30/90 days justifying the chosen value;
(iii) state the observation window — the design has not been live long enough to
observe a full 30-day cycle, so say that explicitly rather than implying
validation.

### TODO-4 · Multi-path retrieval has no measurement 🟠
**Where:** §5.4.
**Problem:** the five-path fusion (vector / keyword / scenario / tag /
quality-feedback) is described but not evaluated. As written the section is a
design description, not a contribution.
**Fix:** (i) leave-one-out ablation over the five paths, plus each path alone,
reporting Recall@k / nDCG@k on an experience query set; (ii) the fusion function
actually used (score normalisation, weights, or rank fusion) with its parameters;
(iii) comparison against a single-path vector baseline on the same queries.

### TODO-5 · Experience synthesis is not reproducible across runs 🔴
**Where:** §7.6.
**Problem:** the frozen snapshot records `judge_score_mean = 3.5` with 10
entries. **A later re-run of the same module produced `judge_score_mean = null`
and 0 entries.** The most likely cause is that the second run found a populated
experience store and the deduplication guard suppressed every candidate — i.e.
**the benchmark does not reset state between runs** (see `REVIEWER-AUDIT.md`
P2/F17). Do not submit a single favourable run of a module that answers
differently on re-execution.
**Fix:** make the module reset experience state; report ≥3 runs; if instability
persists, report both runs and analyse it as a finding.

### TODO-6 · Experience module has no baseline 🔴
**Where:** §7.6, "Baseline comparison for experience synthesis".
**Problem:** the module is evaluated against nothing. The first question a
reviewer asks is "compared to what?"
**Fix:** at minimum — (i) a no-synthesis baseline, i.e. retrieval over the raw
source documents with no experience layer, on the same operational queries; (ii)
an LLM-summary baseline, one-shot summarisation of the same documents into
"lessons". Score both with the identical judge prompt so the comparison is
like-for-like. Without this, §5 proposes a mechanism whose value over "just
summarise the docs" is unmeasured.

---

## Evaluation

### TODO-7 · Single run per configuration 🟠
**Where:** §7.2, Protocol/Statistics.
**Problem:** one run per configuration for the held-out benchmark.
**Fix:** five runs (CIKM convention) with standard deviation; name the exact test
(paired *t* vs Wilcoxon signed-rank) and say whether normality was checked; report
per-metric confidence intervals. Note the artefact currently repeats the same
`ci: [0.43, 0.57]` for every baseline, which suggests one shared interval rather
than per-comparison intervals — verify.

### TODO-8 · Missing embedding/index revisions 🟡
**Where:** §7.2, Implementation.
**Problem:** BGE-M3 revision (HF commit) and ChromaDB HNSW parameters
(`M`, `ef_construction`, `ef_search`) are not recorded.
**Fix:** read them from the deployment and state them; without them the baselines
are not reproducible at CIKM level.

### TODO-9 · Ablation is on a different scale from the main table 🔴
**Where:** §7.3.
**Problem:** main-table P@5 spans 0.117–0.200; ablation P@5 spans 0.723–0.875. A
4–7× gap means different query sets or different relevance definitions. Both come
from the same artefact, so the two tables cannot be read together, and a reviewer
will treat this as an inconsistency.
**Fix:** re-run the ablation on the same 50-query held-out set as Table 5, **or**
state explicitly in each caption which query set it uses and why they differ. Do
not merge them into one narrative before this is resolved.

### TODO-10 · Reproducibility of the reported numbers 🟠
**Where:** §7.8.
**Problem:** `benchmark-suite/results/` and `benchmark-web/backend/results/` are
overwritten in place by every re-run and carry no run identifier. This already
destroyed a result during preparation (TODO-5); the paper is protected only by a
manual snapshot.
**Fix:** (i) give every benchmark run a unique immutable output directory — the
repo already has an `archive-<timestamp>` convention, make it the default rather
than a manual step; (ii) record git commit, configuration hash and random seed
inside each result file; (iii) add an **anonymous artefact link**
(Zenodo / anonymous.4open.science) for the supplementary material — the current
draft has none and CIKM reviewers look for it.

---

## Standing experiment gaps (no inline marker; affect the whole Evaluation)

### TODO-11 · No inter-annotator agreement on the 0–8 rubric 🔴
The rubric is an LLM judgement with no human κ study. This is the single most
likely reviewer objection. Fix: 3 annotators × 40–60 queries, report κ, and
report the LLM-vs-human agreement separately.

### TODO-12 · The central claim rests entirely on author-built data 🔴
Every multi-domain result is author-constructed; every public benchmark
(SciFact, SQuAD, XQuAD) is single-domain. The claim that adjudication pays under
cross-domain distraction is therefore supported only by data the authors built.
Fix (choose one): (a) construct a multi-domain split from a public collection
(e.g. partition a BEIR subset into topic bases and evaluate routing); or
(b) explicitly bound the claim to the in-house corpus and say so in the abstract.
`docs/paper/DATASETS-AND-EXPERIMENTS.md` already documents a viable route:
HotpotQA supporting documents split into 8–12 topic KBs.

### TODO-13 · Public-benchmark scale is too small 🟠
SciFact 30 queries, SQuAD 16, XQuAD 32. SQuAD and XQuAD are at ceiling
(all methods ≈1.000) and therefore carry no information about method differences;
they occupy space that should go to a larger run. Fix: full-BEIR suite, or drop
the saturated benchmarks and say why.

### TODO-14 · XQuAD result contradicts the project's own report 🟠
Recorded: staged P@5 = 0.275 vs vector P@5 = 0.831 — vector is 3× better.
`benchmark-report.html` describes this as "near-ceiling scores for both methods",
which the numbers do not support. Not cited in the paper and deliberately excluded
from the frozen snapshot, but **the HTML report itself must be corrected** or it
will mislead the next author.


---

## TODO-18 · The distractor hypothesis has no traceable support 🔴

**Where:** §7.4 (`sec:honest`), and the abstract.
**Problem.** The paper's central explanatory claim — that content adjudication
helps in proportion to the number of cross-domain distractors present — was
supported entirely by the withheld artefact family (`PROVENANCE.md`). Both
traceable benchmarks are effectively single-domain, so they cannot test it either.
The mechanism remains architecturally motivated; the *benefit* is unmeasured.
**Fix.** One experiment decides it: build a multi-domain benchmark from a public
corpus (the project's own `docs/paper/DATASETS-AND-EXPERIMENTS.md` documents the
route — HotpotQA supporting documents clustered into 8–12 topic knowledge bases),
then run the **2×2 factorial** scoping × adjudication with its interaction term.
That interaction *is* the claim. Without it, either bound the claim in the
abstract and C1, or move the submission to the applied/industry track.

## TODO-19 · Query rewriting claims a number it cannot support 🟠

**Where:** §4.1 (`sec:intent`).
**Problem.** The stage is described with a ΔP@5 figure taken from the withheld
component study.
**Fix.** Re-measure on the committed harness, or drop the number and describe the
stage qualitatively.

## TODO-20 · No significance testing anywhere 🔴

**Where:** §7.2 (`Statistics`).
**Problem.** The revision removed every test statistic, *p*-value and confidence
interval, because the only ones that existed came from a protocol we cannot
reproduce. The paper now makes no significance claim at all — honest, but a CIKM
reviewer will expect one.
**Fix.** After re-running on a committed protocol: ≥5 runs with standard
deviation; name the test (paired *t* vs Wilcoxon, with the normality assumption
checked); per-metric confidence intervals; multiplicity correction across four
baselines; and a power statement given n = 20–30 queries per method.

## TODO-21 · Provenance gate must run in CI 🟠

**Where:** repository, not the paper.
**Problem.** `provenance_audit.py` exists and fails correctly, but nothing runs
it automatically. The failure it detects went unnoticed through several internal
review rounds.
**Fix.** Wire it into the pre-commit hook / CI for `docs/paper/cikm/`, and add the
same check to `benchmark-suite` so a benchmark that writes no manifest cannot be
cited by a later paper.
