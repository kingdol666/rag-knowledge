---
title: "HMRS companion evidence inventory"
subtitle: "Manuscript evidence and historical coverage for Knowledge-Based Systems"
---

This inventory is a reading guide, not another results table. Part A indexes selected records behind the current manuscript and supplement. Use the **evidence crosswalk in the supplement** for the full claim-to-record mapping and the **external-baseline QA companion** for answer texts and judging rationales. Part B covers older studies without carrying their results into the submission. The evidence units differ by study; they are not successive stages of a single end-to-end test.

**How to locate the records.** Labels such as **E3/E4** resolve to exact repository paths and fields in `supplementary-inventory-source-map.md`, shipped with this Markdown source. The [frozen benchmark snapshot](https://github.com/kingdol666/rag-knowledge/tree/092e8bf2d65859dcd684071ed4169a40fbbc1563/benchmark-suite/paper-results-kbs-20261125) is at `benchmark-suite/paper-results-kbs-20261125` relative to the repository root.

## Part A. Evidence used in the manuscript and supplement

### E1 — Storage, catalogue and index checks

Start with the description audit and arXiv identifier probes (**E1**). A stored part is not the same unit as a source paper. Finding a paper identifier by a short query is not evidence of within-collection ranking; catalogue state, index state and the search view can disagree. The acquisition state list and the later catalogue enumeration do not match records paper by paper and cannot be subtracted to obtain parse failures (**Archive: acquisition**). The supplement crosswalk covers the individual management checks and distinguishes measured results from report-level observations.

### E2 — Native answer quality and judging sensitivity

For Table 6, join the native answer rows to the unified judgments by question and arm. The rows carry answers and deployment observations; the score and verdict come from the judge. Keep the scope audit with the comparison: the native HMRS search was not consistently restricted to the intended collections, so this is not a controlled catalogue-first evaluation. DeepRead cost was unmetered, not zero. The repeat judging batch and the earlier four-arm pass score saved answers and should not be counted as fresh retrieval runs (**E2**).

### Figure 5 — Separate BQ07 workflow illustration

BQ07 asks about MameLoshnLM and its parameter scale. This separate catalogue-first capture follows collection and document descriptions to the evidence gate and a source read. It illustrates execution, not frequency, routing accuracy or an answer-quality effect. It contributes no observation to the E2 comparison or the E3 routing counts. The earlier native BQ07 search trace is a different record despite the shared question ID (**Figure 5**).

### E3/E4 — Collection routing and evidence-pack containment

A **routing hit** means choosing the labelled collection; a **containment hit** means finding the annotated target string in the returned text, not necessarily in the annotated source. In the frozen scored set, A0 selected the labelled collection on **72/72** questions versus **37/72** for nominally name-only A3. In the same frozen set, A0 contained the string on **37/72** questions versus **52/72** for A0h. The two occurrences of 37 describe different arms and outcomes. Compare the arms within each run and exclude the refusal probes from these denominators (**E3/E4**).

A3 had possible unlogged fallback paths, and the evidence-pack arms change multiple settings. The same-question reruns are consistency checks, not independent samples. The retrieval text counter can include repeated text; it is not the final evidence-pack size, generator context length or network traffic.

### E5 — Operational lessons

The experience-store smoke checks and case report illustrate parts of the workflow. A report-level search observation without a retained response is not a verified retrieval score. Draft creation, successful retrieval, approval and lifecycle quality are distinct outcomes (**E5**).

### E6 — Verifier ordering versus admission

**Hit@5** is the presence of a gold document among the first five results. In the fixed-pool ordering replay, fusion order retained a hit in **15/16** pools and verifier-score order in **7/16**; eight pools lost a hit and none gained one. The distribution of recorded scores comes from a separate archive. Neither archive establishes whether the gate improves admission or final answers. Do not substitute the earlier judge/filter replay with different counts (**E6**).

### E7 — Lexical answer proxies and absent-answer probes

The original and common-substrate answer grids report lexical diagnostics, not semantic grades. The original run labels P/F/D correspond to platform/file/chunk replica; the current supplement writes the chunk arm as C. A gold-ID hit means an identifier was observed in the answer or trace. Strict and alias-aware coverage count literal and permitted variant matches, respectively; a marker is a citation-like string, not a resolved citation or proof of entailment. The replication uses different wording for BQ06, so an ID join alone does not guarantee matched wording. Keep those grids separate from the absent-answer probes and from E2. Recovering a candidate above a retrieval threshold does not establish answerability; a successful response can also hide incomplete search (**E7**).

## Part B. Historical coverage — not submission results

The older inventory and source map are preserved in the previous reading package (**Archive: inventory**). They document a broader set of developmental campaigns, not additional observations for the manuscript. The archive includes both record-backed and report-only material. Selected entry points with identifiable repository artifacts are given here without republishing their outcomes:

- **Acquisition and reorganisation.** Ingest-state and derived-library files document distinct snapshots. A historical functional report records lifecycle and reorganisation coverage. None is a paper-by-paper acquisition funnel (**Archive: acquisition**).
- **Retrieval and ablation.** The historical question definitions, rank-table generator, threshold and paraphrase work, NLI replays, and gate/partition ablation reports document the prior designs. The older route-card audit is a prior protocol, not the source for the current rerun comparison (**Archive: retrieval** and **Archive: route cards**).
- **Interface comparison.** The paired replication grades and source-presence script document how the archival lexical checks were conducted. Use the current supplement for retained grid results; do not combine the original and common-substrate runs or substitute them for the native answer-quality comparison (**E7** and **Archive: answer grids**).

**What was not carried forward.** The old table sequence, per-cell cost/latency grids and developmental configuration matrices are not reproduced. Headline claims from stress, stability, end-to-end harness and skill exercises, as well as exact structural-split, web-ingest, graph/tag and post-repair totals, are not presented here as results: their cited raw artifacts were unavailable or did not establish the stated quantities. Where records do survive, duplication would obscure which protocol and denominator the current manuscript uses. Omission is not a zero or a failed run. No historical artifact was changed to reconcile it with the submission.
