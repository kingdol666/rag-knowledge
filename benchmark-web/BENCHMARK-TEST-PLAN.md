# QDCVR Knowledge Base System — Comprehensive Benchmark Plan v3.0
# Holistic Evaluation: Ingestion + Organization + Retrieval + Experience + End-to-End
# Target: CIKM 2027 / SIGIR 2027 Experimental Evaluation
# Date: 2026-07-30

## 0. Philosophy: What Are We Actually Evaluating?

Standard RAG benchmarks measure one thing: "given query Q and corpus C, rank documents correctly."
This system does FIVE fundamentally different things:

  ┌──────────────────────────────────────────────────────────┐
  │               KNOWLEDGE BASE LIFECYCLE                    │
  │                                                           │
  │  ① INGEST         ② ORGANIZE       ③ RETRIEVE            │
  │  Raw PDF/Word      Auto-tag         MoE gate → QDCVR     │
  │  → Auto-parse      → Sub-KB route   → Content verify     │
  │  → Auto-tag        → Dedup          → Answer + blind-spot │
  │  → Auto-describe   → Restructure                          │
  │  → Auto-index      → Verify                               │
  │                                                           │
  │  ④ EXPERIENCE      ⑤ VERIFY                               │
  │  Q&A → Meditation  Integrity check                        │
  │  → Extract         → Orphan detection                     │
  │  → Publish         → Consistency audit                    │
  └──────────────────────────────────────────────────────────┘

Each phase needs its OWN test data, ground truth, metrics, and success criteria.
No existing benchmark covers this — we must design it from scratch.


## I. TEST DATA REQUIREMENTS

### Dataset A: Ingestion Test Set (30 documents)
─────────────────────────────────────────
30 real research paper abstracts NOT currently in any KB.
Each document needs HUMAN annotation:

  {
    "id": "ingest-001",
    "title": "Strain-Induced Crystallization of PET During Biaxial Stretching",
    "content": "<full abstract text>",
    "ground_truth": {
      "primary_kb": "高分子双向拉伸文献库",
      "sub_kb": "03_PET_BOPET - 聚酯双向拉伸",
      "tags": ["PET", "应变诱导结晶", "双向拉伸", "聚酯", "结晶动力学"],
      "description": "研究了PET在双向拉伸过程中的应变诱导结晶行为，分析了拉伸温度和拉伸比对结晶度和晶态结构的影响。采用DSC和WAXD表征手段。",
      "category": "research_paper",
      "language": "en"
    }
  }

Domain distribution: 5 per domain × 6 domains = 30
- 高分子双向拉伸: 5 (spread across PET/PVA/BOPP/PLA/Physics sub-KBs)
- AI-ML-Research: 5
- Energy-Batteries: 5
- Materials-Science: 5
- Biomedical-Engineering: 5
- Embodied-AI: 5


### Dataset B: Organization Test Set (messy KB state)
─────────────────────────────────────────
Create a deliberately messy KB state and measure improvement:

Pre-state (messy):
  - 5 documents with missing tags
  - 3 documents with empty descriptions
  - 2 duplicate document pairs (same content, different names)
  - 1 document in wrong KB (misclassified)
  - 1 KB that should be split into sub-KBs (8+ related docs)

Post-state (after Organize):
  - All tags populated
  - All descriptions >= quality threshold
  - Duplicates detected and flagged
  - Misclassified document moved to correct KB
  - Sub-KB created with appropriate documents

This is a CONTROLLED experiment — we create the messy state deliberately
so we know the ground truth for every fix needed.


### Dataset C: Retrieval Test Set (40 queries)
─────────────────────────────────────────
40 queries with human-annotated ground truth:

For EACH query, annotate:
  - correct_kb: which KB(s) should the MoE gate activate?
  - relevant_docs: list of doc_paths that contain the answer (graded 0-3)
    0 = irrelevant, 1 = tangentially related, 2 = partially answers, 3 = directly answers
  - answer_fragment: the specific text that answers the query (for content verification eval)

Query categories:
  - Cat 1: Domain-Specific (24 queries, 4 per domain × 6 domains)
    Tests: KB routing accuracy + retrieval precision
  - Cat 2: Cross-Domain Adversarial (10 queries)
    Tests: MoE gate robustness — does it activate the right KBs when vocabulary overlaps?
  - Cat 3: Edge Cases (6 queries)
    Tests: Empty results, ambiguous intent, out-of-domain questions


### Dataset D: Experience Test Set (15 Q&A pairs)
─────────────────────────────────────────
15 question-answer pairs from real KB usage, with human evaluation of
extracted experiences:

For each Q&A pair:
  - query: what the user asked
  - answer: what the system returned (with source docs)
  - expected_experience: what SHOULD be extracted
    - actionable_title
    - problem_statement
    - solution_steps
    - key_lessons (3-5 bullet points)


## II. EVALUATION PHASES

### Phase A: Ingestion Accuracy (30 documents)

Pipeline: Raw document → parse_doc → A2-Q parse quality → A3a analysis →
          A3b tag quality → A3c description quality → A4 KB attribution →
          A5 store (kb_doc_save_parsed) → A6 index (kb_index_document)

Metrics:
┌────────────────────┬──────────────────────────────────────────┬────────┐
│ Metric             │ Definition                               │ Target │
├────────────────────┼──────────────────────────────────────────┼────────┤
│ KB Routing Acc.    │ % docs routed to correct primary KB      │ ≥ 90%  │
│ Sub-KB Routing Acc.│ % docs routed to correct sub-KB          │ ≥ 80%  │
│ Tag Precision      │ (# correct auto-tags) / (# auto-tags)    │ ≥ 80%  │
│ Tag Recall         │ (# auto-tags ∩ expected) / (# expected)  │ ≥ 70%  │
│ Tag F1             │ Harmonic mean of precision & recall      │ ≥ 75%  │
│ Desc Quality Score │ 0-4 rubric (domain+method+problem+result)│ ≥ 3.0  │
│ Parse Quality      │ % docs passing A2-Q gate on first try    │ ≥ 95%  │
│ Index Success Rate │ % docs searchable after kb_index_document│ 100%   │
│ Ingest Latency     │ End-to-end time per document (seconds)   │ ≤ 30s  │
└────────────────────┴──────────────────────────────────────────┴────────┘

Description Quality Rubric (0-4):
  0 = Empty or "TBD"
  1 = Only filename paraphrased (not content-based)
  2 = Domain identified + general topic mentioned
  3 = Domain + method/technique + problem context
  4 = Domain + method + problem + key finding/conclusion + language tag

Procedure:
  1. Load Dataset A (30 annotated documents) into a staging area
  2. For each document, run the full A0-A9 ingest pipeline
  3. Record all auto-generated tags, description, and KB routing decision
  4. Compare against human ground truth
  5. Compute all metrics
  6. Run kb_search_vector on each ingested doc to verify index success


### Phase B: Organization Quality (controlled messy KB)

Metrics:
┌──────────────────────┬────────────────────────────────────────┬────────┐
│ Metric               │ Definition                             │ Target │
├──────────────────────┼────────────────────────────────────────┼────────┤
│ Tag Gap Closure      │ % of missing tags corrected            │ 100%   │
│ Desc Gap Closure     │ % of empty/wrong descriptions fixed    │ 100%   │
│ Duplicate Recall     │ % of known duplicates detected         │ ≥ 95%  │
│ Duplicate Precision  │ % of flagged duplicates that are real  │ ≥ 90%  │
│ Misclass Correction  │ % of misclassified docs moved correctly│ 100%   │
│ Sub-KB Split Quality │ Is the new sub-KB appropriately scoped?│ Binary │
│ Sub-KB Doc Routing   │ % docs correctly assigned to new sub-KB│ ≥ 90%  │
│ Three-Way Consistency│ disk↔.tree-fs↔.yml all match post-fix  │ 100%   │
│ Ops Safety           │ All destructive ops used dry_run first │ 100%   │
└──────────────────────┴────────────────────────────────────────┴────────┘

Procedure:
  1. Set up the controlled messy KB state (Dataset B)
  2. Run kb_verify (V1-V9) to get baseline health score
  3. Run kb_organize (O1-O8) full restructuring
  4. Run kb_verify again to get post-organize health score
  5. Check each known issue was resolved
  6. Verify no regressions (no new issues introduced)
  7. Check three-way metadata consistency


### Phase C: Retrieval Quality (40 queries)

Metrics:
┌──────────────────────┬──────────────────────────────────────────┬────────┐
│ Metric               │ Definition                               │ Target │
├──────────────────────┼──────────────────────────────────────────┼────────┤
│ MoE Routing Prec.    │ % queries where correct KB is activated  │ ≥ 95%  │
│ MoE Routing Recall   │ % of all correct KBs that were activated │ ≥ 90%  │
│ Recall@5             │ % queries with ≥1 relevant doc in top-5  │ ≥ 90%  │
│ Precision@5          │ (# relevant docs in top-5) / 5           │ ≥ 70%  │
│ MRR                  │ Mean reciprocal rank of first relevant   │ ≥ 0.80 │
│ nDCG@5               │ Normalized discounted cumulative gain    │ ≥ 0.75 │
│ Content Verify Acc.  │ Agreement between system 0-8 & human 0-3 │ ≥ 85%  │
│ False Positive Rate  │ System scores ≥6 but human = 0           │ ≤ 10%  │
│ False Negative Rate  │ System scores ≤4 but human = 3           │ ≤ 10%  │
│ Blind-spot Rate       │ % answers that honestly declare gaps     │ ≥ 80%  │
│ Search Space Red.    │ (total chunks) / (chunks in activated KB)│ ≥ 5×   │
│ Avg Latency          │ End-to-end query time (seconds)          │ ≤ 3s   │
└──────────────────────┴──────────────────────────────────────────┴────────┘

Procedure:
  1. Load Dataset C (40 annotated queries)
  2. For each query, run the full QDCVR pipeline:
     Step 0: Query analysis → record intent + entities
     Step 1: MoE KB selection → record which KBs activated
     Step 2: Two-stage search → record results + scores
     Step 2.5: Dedup + threshold → record filtered results
     Step 3: Content verification → record 0-8 scores
     Step 6: Answer synthesis → record final answer + blind-spots
  3. Compare against human ground truth
  4. Compute all metrics
  5. Also run as ABLATIONS:
     - QDCVR-Flat (skip Step 1): measure MoE contribution
     - QDCVR-NoVerify (skip Step 3): measure content verification contribution


### Phase D: Experience Quality (15 Q&A pairs)

Metrics:
┌──────────────────────┬──────────────────────────────────────────┬────────┐
│ Metric               │ Definition                               │ Target │
├──────────────────────┼──────────────────────────────────────────┼────────┤
│ Actionability Score  │ 0-5: Can someone act on this experience? │ ≥ 3.0  │
│ Content Fidelity     │ Does experience match source doc? (0-3)  │ ≥ 2.5  │
│ Problem Accuracy     │ Does problem statement match Q&A intent? │ ≥ 80%  │
│ Solution Specificity │ Does solution contain concrete steps?    │ ≥ 70%  │
│ Key Lessons Quality  │ Are lessons independently useful? (0-3)  │ ≥ 2.0  │
│ Signal Conversion    │ Useful experiences / total Q&A signals   │ ≥ 60%  │
│ Meditation Success   │ % of meditation runs without errors      │ 100%   │
└──────────────────────┴──────────────────────────────────────────┴────────┘

Actionability Rubric (0-5):
  0 = Placeholder / "此经验由启发式引擎自动生成"
  1 = Generic advice with no specifics
  2 = Mentions a technique but no implementation details
  3 = Actionable with concrete steps (specific parameters/methods)
  4 = Actionable + references source documents + includes constraints
  5 = Actionable + source-verified + includes failure modes + alternatives

Procedure:
  1. Collect 15 real Q&A interactions as "signals" in a test KB
  2. Run experience_extract with mode="prepare" to get extraction templates
  3. LLM refines candidates and creates experiences
  4. Alternatively, trigger meditation: experience_meditation_run(kb_id)
  5. Human-evaluate each extracted experience on the rubric
  6. Compare auto-extracted vs human-expected experiences


### Phase E: End-to-End Pipeline (10 complete cycles)

Full lifecycle test: Raw PDF → Ingest → Search → Experience

Metrics:
┌──────────────────────┬──────────────────────────────────────────┬────────┐
│ Metric               │ Definition                               │ Target │
├──────────────────────┼──────────────────────────────────────────┼────────┤
│ Pipeline Success Rate│ % of documents completing full lifecycle  │ ≥ 95%  │
│ End-to-End Latency   │ PDF ingest → searchable (seconds)        │ ≤ 60s  │
│ Answer Correctness   │ % answers with factually correct info    │ ≥ 85%  │
│ Evidence Grounding   │ % claims backed by specific doc citation │ ≥ 90%  │
│ Hallucination Rate   │ % claims NOT supported by cited docs     │ ≤ 5%   │
│ User Satisfaction    │ Simulated user rating (1-5)              │ ≥ 4.0  │
└──────────────────────┴──────────────────────────────────────────┴────────┘

Procedure:
  1. Select 10 real PDFs from diverse domains
  2. For each PDF:
     a) Phase A: Full ingest pipeline (parse → tag → describe → store → index)
     b) Phase C: Run 2 queries against the newly ingested doc
     c) Phase D: Extract 1 experience from the Q&A pair
     d) Record all metrics at each stage
  3. Compute aggregate end-to-end metrics


## III. COMPARATIVE BASELINES

We compare against ABLATIONS of our own system (not external RAG systems):

┌─────┬─────────────────────────┬──────────────────────────────────┐
│ ID  │ Method                  │ What It Tests                    │
├─────┼─────────────────────────┼──────────────────────────────────┤
│ S0  │ QDCVR-MoE (Full)        │ Complete pipeline — our system   │
│ S1  │ QDCVR-Flat              │ Ablation: skip MoE routing       │
│ S2  │ QDCVR-NoVerify          │ Ablation: skip content verify    │
│ S3  │ BM25-only               │ Baseline: pure keyword retrieval │
│ S4  │ Manual Ingest           │ Baseline: human-written tags/desc│
│ S5  │ No Organization         │ Baseline: skip organize step     │
└─────┴─────────────────────────┴──────────────────────────────────┘

Comparisons tell us:
  - S0 vs S1: Contribution of MoE KB routing (Phase C)
  - S0 vs S2: Contribution of content verification (Phase C)
  - S0 vs S3: Overall retrieval improvement (Phase C)
  - S0 vs S4: Auto-ingest quality vs human baseline (Phase A)
  - S0 vs S5: Organization impact on retrieval quality (Phase B→C)


## IV. AGGREGATE SYSTEM SCORE

A single composite score (0-100) weighting all phases:

┌────────────────────┬───────┬────────────────────────────────────┐
│ Phase              │ Weight│ How Scored                         │
├────────────────────┼───────┼────────────────────────────────────┤
│ A: Ingestion       │  25%  │ Avg of all Phase A metrics         │
│ B: Organization    │  20%  │ % of known issues resolved         │
│ C: Retrieval       │  30%  │ Weighted: Recall@5(0.4) + MRR(0.3)│
│                    │       │ + ContentVerify(0.2) + MoE(0.1)    │
│ D: Experience      │  15%  │ Avg actionability + fidelity       │
│ E: End-to-End      │  10%  │ Pipeline success + correctness     │
├────────────────────┼───────┼────────────────────────────────────┤
│ TOTAL              │ 100%  │ Weighted sum                       │
└────────────────────┴───────┴────────────────────────────────────┘

Target: System Score ≥ 85/100 for publication-ready evaluation.


## V. STATISTICAL RIGOR

For each metric comparing S0 vs any baseline:
  1. Paired t-test (α = 0.05, Bonferroni-corrected for 5 comparisons → α' = 0.01)
  2. Cohen's d effect size (target ≥ 0.8 for "large" effect)
  3. 95% confidence intervals for all mean values
  4. Bootstrap resampling (n=10,000) for metrics with non-normal distributions

Minimum sample sizes for statistical power:
  - Phase A: 30 documents (power > 0.80 for d ≥ 0.6)
  - Phase C: 40 queries (power > 0.80 for d ≥ 0.5)
  - Phase D: 15 Q&A pairs (exploratory — power may be limited)

## VI. EXECUTION CHECKLIST

Phase A: Ingestion Accuracy
  □ Prepare 30 annotated test documents (Dataset A)
  □ Set up clean staging KB for test
  □ Run A0-A9 pipeline on all 30 documents
  □ Record all auto-generated metadata
  □ Human-evaluate tag precision/recall
  □ Human-score all descriptions (0-4 rubric)
  □ Verify index success via kb_search_vector
  □ Compute all Phase A metrics
  □ Compare S0 (auto) vs S4 (human baseline)

Phase B: Organization Quality
  □ Set up controlled messy KB state
  □ Run kb_verify baseline (pre-organize health score)
  □ Run full O1-O8 organize pipeline
  □ Run kb_verify post-organize
  □ Check each known issue resolved
  □ Verify three-way metadata consistency
  □ Compute all Phase B metrics

Phase C: Retrieval Quality
  □ Prepare 40 annotated queries (Dataset C)
  □ Run S0 (full QDCVR) on all 40 queries
  □ Run S1 (flat), S2 (no-verify), S3 (BM25) ablations
  □ Human-evaluate content verification scores
  □ Compute all Phase C metrics
  □ Run statistical tests (t-test, Cohen's d, bootstrap)

Phase D: Experience Quality
  □ Collect 15 Q&A pairs as meditation signals
  □ Run experience_extract (prepare mode)
  □ LLM-refine and create experiences
  □ Human-score all experiences on actionability rubric
  □ Compare auto vs human-expected experiences
  □ Compute all Phase D metrics

Phase E: End-to-End
  □ Select 10 real PDFs
  □ Run full lifecycle for each (Ingest → Search → Experience)
  □ Record all metrics at each stage
  □ Compute aggregate end-to-end metrics
  □ Score hallucination rate via human review

Phase F: Report Generation
  □ Compute aggregate System Score
  □ Generate LaTeX tables for paper
  □ Generate HTML visualization report
  □ Write findings and discussion section


## VII. DELIVERABLES

1. **Complete metrics JSON** — all raw + aggregate results
2. **HTML visualization report** — interactive charts + tables
3. **LaTeX paper tables** — table1 (main), table2 (ablation), table3 (experience)
4. **Statistical analysis** — t-tests, effect sizes, confidence intervals
5. **Human annotation dataset** — released for reproducibility
6. **Benchmark methodology paper** — describing the evaluation framework

## VIII. TIMELINE

┌────────────┬────────────────────────┬────────┐
│ Phase      │ Task                   │ Est.   │
├────────────┼────────────────────────┼────────┤
│ Preparation│ Create Dataset A (30)  │ 2 days │
│ Preparation│ Create Dataset C (40)  │ 1 day  │
│ Preparation│ Create Dataset B+D     │ 1 day  │
│ Execution  │ Phase A: Ingestion     │ 1 day  │
│ Execution  │ Phase B: Organization  │ 0.5 day│
│ Execution  │ Phase C: Retrieval     │ 1 day  │
│ Execution  │ Phase D: Experience    │ 0.5 day│
│ Execution  │ Phase E: End-to-End    │ 1 day  │
│ Analysis   │ Statistics + Report    │ 2 days │
├────────────┼────────────────────────┼────────┤
│ Total      │                        │ ~10 days│
└────────────┴────────────────────────┴────────┘
