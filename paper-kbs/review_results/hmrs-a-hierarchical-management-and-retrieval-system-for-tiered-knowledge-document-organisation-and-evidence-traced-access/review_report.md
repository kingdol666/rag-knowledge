# Deep Review Report

**Paper**: `D:\codes\ClaudeGPT\rag_project\rag-knowledge\paper-kbs\tex\journal_20p\main_20p.tex` | **Language**: EN | **Mode**: deep-review
**Generated**: 2026-11-14 00:25
**Artifacts**: `D:\codes\ClaudeGPT\rag_project\rag-knowledge\paper-kbs\review_results\hmrs-a-hierarchical-management-and-retrieval-system-for-tiered-knowledge-document-organisation-and-evidence-traced-access`

## Overall Assessment

Deep review found 1 major, 0 moderate, 0 minor issues. The highest-priority concerns are: Abstract and conclusion claims need explicit evidence traceability.

- **Major**: 1
- **Moderate**: 0
- **Minor**: 0

## Academic Pre-Review Committee

### Editor (Desk Reject Screen)

## Editor Pre-Screen (1-10)

Score: 4.0/10
Verdict: Desk Reject

### Desk-Reject Triggers (if any)
- Abstract and conclusion claims need explicit evidence traceability

### Top 3 Reasons (no hedging)
1. Abstract and conclusion claims need explicit evidence traceability

### Fast Fixes (within 1-2 days)
- Clarify abstract to address abstract and conclusion claims need explicit evidence traceability.

### Reviewer 1 (Theory Contribution)

## Theory Contribution Review

### 3 Fatal Theory Holes
1. (abstract) "These results demonstrate an auditable management structure with per-tier measurements and warn against verifier-as-ranker; they do not establish general retrieval superiority or semantic answer quality, but position a managed, auditable collection as an inspectable basis for evidence-traced knowledge bases." — At least one headline claim was detected. Deep review should check whether experiments and conclusion language trace back to the same bounded evidence base.

### Concrete Moves
- Tighten the paper's theoretical positioning in abstract to resolve abstract and conclusion claims need explicit evidence traceability.

### Reviewer 3 (Literature Dialogue)

## Literature Dialogue Review

### Closest Prior Work Risks
- No literature-grounding risk was surfaced by the fallback pass.

### Gap Claim Risks
- No selective-citation concern was surfaced.

### Fast Fixes
- Add one sentence identifying the closest prior work and the exact novelty delta.

### Reviewer 2 (Methodology & Transparency)

## Methodology Transparency Review (SRQR-aware)

### MUST-FIX (submission blockers)
- No methodology blocker was surfaced by the fallback pass.

### SHOULD-FIX (quality improvements)
- No secondary methodology issue was surfaced.

### SRQR Checklist Deltas
- Sampling rationale: clarify how the evidence base supports the paper's strongest claims.
- Data collection details (time/place/duration): add context when results depend on specific settings.
- Coding process (stages, coders, disagreement resolution): specify if qualitative or hybrid analysis is used.
- Saturation: state whether the evidence scope is exhaustive or bounded.
- Triangulation: explain whether multiple evidence sources were reconciled.
- Reflexivity: acknowledge researcher choices that shape interpretation.

### Reviewer 4 (Logic Chain)

## Logic Chain Review

### Breakpoints
- (abstract) "These results demonstrate an auditable management structure with per-tier measurements and warn against verifier-as-ranker; they do not establish general retrieval superiority or semantic answer quality, but position a managed, auditable collection as an inspectable basis for evidence-traced knowledge bases." — At least one headline claim was detected. Deep review should check whether experiments and conclusion language trace back to the same bounded evidence base.

### Structural Fix Moves
- Add one explicit bridge sentence in abstract so the argument chain closes cleanly.

### Committee Consensus

## Committee Consensus

Overall Score: 4.0/10
Editor Verdict: Desk Reject

### Score Formula
- base 9.0
- minus 1.5 * major (1)
- minus 0.7 * moderate (0)
- minus 0.2 * minor (0)
- floor 1.0
- desk reject cap 4.0

### Top 3 Issues To Fix First
1. Abstract and conclusion claims need explicit evidence traceability

## Paper Summary

# Paper Summary: HMRS: A hierarchical management-and-retrieval system for tiered knowledge document organisation and evidence-traced access

## Research Question
- Using document collections as a knowledge base requires parsing, placement, maintenance and retrieval to work together

## Core Thesis
- We present HMRS (Hierarchical Management Retrieval System), a self-hosted knowledge document management system managing documents at three levels---collection, document and segment---and serving queries along a tiered path from the catalogue of collections, through document descriptions, to the evidence-carrying segment.

## Headline Claims
- We present HMRS (Hierarchical Management Retrieval System), a self-hosted knowledge document management system managing documents at three levels---collection, document and segment---and serving queries along a tiered path from the catalogue of collections, through document descriptions, to the evidence-carrying segment.

## Section Map
- abstract (89-116): 251 words

## Closure Targets
- No closure target was extracted automatically.

## Major Issues

### M1: Abstract and conclusion claims need explicit evidence traceability
- **Type**: claim_accuracy
- **Source**: [LLM] via `claims_vs_evidence`
- **Confidence**: medium
- **Section**: abstract
- **Related Sections**: abstract, results, conclusion
- **Root Cause Key**: `abstract-and-conclusion-claims-need-explicit-evidence-traceability`
- **Quote Verified**: no
- **Quote**: `These results demonstrate an auditable management structure with per-tier measurements and warn against verifier-as-ranker; they do not establish general retrieval superiority or semantic answer quality, but position a managed, auditable collection as an inspectable basis for evidence-traced knowledge bases.`
- **Explanation**: At least one headline claim was detected. Deep review should check whether experiments and conclusion language trace back to the same bounded evidence base.

## Phase 0 Automated Findings

### [Script] BIB

| Line | Severity | Issue |
|------|----------|-------|
| --- | Minor | Check: D:\codes\ClaudeGPT\rag_project\rag-knowledge\paper-kbs\tex\journal_20p\refs.bib |
| --- | Minor | FAIL |
| --- | Minor | entries: 35 |
| --- | Minor | entries: 34 |
| --- | Minor | @rag-lewis: [IEEE] 12 authors listed; style uses et al. after 6. Ensure bibliography style handles truncation. |
| --- | Minor | @rag-lewis: [IEEE] DOI recommended for inproceedings entries. |
| --- | Minor | @dpr: Missing required field 'author' |
| --- | Minor | @selfrag: [IEEE] DOI recommended for inproceedings entries. |
| --- | Minor | @crag: [IEEE] Missing recommended field 'volume' for article |
| --- | Minor | @crag: [IEEE] Missing recommended field 'pages' for article |
| --- | Minor | @flare: [IEEE] 9 authors listed; style uses et al. after 6. Ensure bibliography style handles truncation. |
| --- | Minor | @graphrag: [IEEE] Missing recommended field 'volume' for article |
| --- | Minor | @graphrag: [IEEE] Missing recommended field 'pages' for article |
| --- | Minor | @graphrag: [IEEE] 10 authors listed; style uses et al. after 6. Ensure bibliography style handles truncation. |
| --- | Minor | @graphrag: [IEEE] DOI recommended for article entries. |
| --- | Minor | @siren: [IEEE] Missing recommended field 'volume' for article |
| --- | Minor | @siren: [IEEE] Missing recommended field 'pages' for article |
| --- | Minor | @siren: [IEEE] 16 authors listed; style uses et al. after 6. Ensure bibliography style handles truncation. |
| --- | Minor | @siren: [IEEE] DOI recommended for article entries. |
| --- | Minor | @mineru: [IEEE] Missing recommended field 'volume' for article |
| --- | Minor | @mineru: [IEEE] Missing recommended field 'pages' for article |
| --- | Minor | @mineru: [IEEE] 18 authors listed; style uses et al. after 6. Ensure bibliography style handles truncation. |
| --- | Minor | @deepread: [IEEE] Missing recommended field 'volume' for article |
| --- | Minor | @deepread: [IEEE] Missing recommended field 'pages' for article |
| --- | Minor | @cyberbot: [IEEE] 10 authors listed; style uses et al. after 6. Ensure bibliography style handles truncation. |
| --- | Minor | @react-yao: [IEEE] 7 authors listed; style uses et al. after 6. Ensure bibliography style handles truncation. |
| --- | Minor | @toolformer: [IEEE] 9 authors listed; style uses et al. after 6. Ensure bibliography style handles truncation. |
| --- | Minor | @singh-agentic-rag: [IEEE] Missing recommended field 'volume' for article |
| --- | Minor | @singh-agentic-rag: [IEEE] Missing recommended field 'pages' for article |
| --- | Minor | @hmrs-demo: [IEEE] DOI recommended for inproceedings entries. |
| --- | Minor | @sun-urara: [IEEE] 8 authors listed; style uses et al. after 6. Ensure bibliography style handles truncation. |
| --- | Minor | @gao-ragsurvey: [IEEE] Missing recommended field 'volume' for article |
| --- | Minor | @gao-ragsurvey: [IEEE] Missing recommended field 'pages' for article |
| --- | Minor | 5 entries missing DOI/URL (Use --online-check to export list) |
| --- | Minor | AI-generated citations have ~40% error rate. Verify entries without DOI/URL using Semantic Scholar API or CrossRef. See references/citations/verification.md for verification workflow. |
| --- | Minor | [Script] checker exited 1 |
| --- | Minor | Check: D:\codes\ClaudeGPT\rag_project\rag-knowledge\paper-kbs\tex\journal_20p\refs_new_verified.bib |
| --- | Minor | WARNING |
| --- | Minor | entries: 30 |
| --- | Minor | entries: 29 |
| --- | Minor | @barredo-arrieta-xai-2020: [IEEE] 12 authors listed; style uses et al. after 6. Ensure bibliography style handles truncation. |
| --- | Minor | @chen2024dense: [IEEE] 8 authors listed; style uses et al. after 6. Ensure bibliography style handles truncation. |
| --- | Minor | @singh2021freshdiskann: Unprotected uppercase in title |
| --- | Minor | @xu2023spfresh: [IEEE] 12 authors listed; style uses et al. after 6. Ensure bibliography style handles truncation. |
| --- | Minor | @memgpt: [IEEE] Missing recommended field 'volume' for article |
| --- | Minor | @memgpt: [IEEE] Missing recommended field 'pages' for article |
| --- | Minor | @memgpt: [IEEE] 7 authors listed; style uses et al. after 6. Ensure bibliography style handles truncation. |
| --- | Minor | @memgpt: [IEEE] DOI recommended for article entries. |
| --- | Minor | @mem0: [IEEE] Missing recommended field 'volume' for article |
| --- | Minor | @mem0: [IEEE] Missing recommended field 'pages' for article |
| --- | Minor | @mem0: [IEEE] DOI recommended for article entries. |
| --- | Minor | @amem: [IEEE] Missing recommended field 'volume' for article |
| --- | Minor | @amem: [IEEE] Missing recommended field 'pages' for article |
| --- | Minor | @amem: [IEEE] DOI recommended for article entries. |
| --- | Minor | 6 entries missing DOI/URL (Use --online-check to export list) |
| --- | Minor | AI-generated citations have ~40% error rate. Verify entries without DOI/URL using Semantic Scholar API or CrossRef. See references/citations/verification.md for verification workflow. |

### [Script] CITATIONS

| Line | Severity | Issue |
|------|----------|-------|
| --- | Minor | No citation stacking issues found. |

### [Script] DEAI

| Line | Severity | Issue |
|------|----------|-------|
| --- | Minor | Use --analyze for full analysis |

### [Script] EXPERIMENT

| Line | Severity | Issue |
|------|----------|-------|
| --- | Major | (n7_implementation.tex:43) : Performance claim lacks an explicit baseline or comparator. |
| --- | Critical | (n7_implementation.tex:45) : Conclusion overreaches the reported evidence; avoid universal or guarantee-style claims. |
| --- | Minor | (n7_implementation.tex:1) : No ablation or component-level evidence is mentioned; verify that contribution attribution is covered. |
| --- | Minor | (n7_implementation.tex:1) : No statistical significance, variance, or confidence information is mentioned. |
| --- | Major | (n9_discussion.tex:1) : Discussion may lack depth: low ratio of explanatory/attribution language (0/34 lines). Add causal analysis explaining why results occur. |
| --- | Major | (n9_discussion.tex:1) : Discussion may lack layered structure: it should cover at least two categories (mechanism, comparison with prior work, limitations/boundaries, implications/outlook) instead of only restating results. |
| --- | Major | (n9_discussion.tex:1) : No citations from Related Work reappear in Discussion. Compare your findings with prior work to strengthen the narrative. |
| --- | Major | (n11_conclusion.tex:1) : Conclusion lacks limitations or future work discussion. |
| --- | Minor | (n11_conclusion.tex:1) : Conclusion lacks implications or broader impact statement. |
| --- | Minor | (n11_conclusion.tex:1) : Conclusion lacks explicit summary of core findings. |

### [Script] FIGURES

| Line | Severity | Issue |
|------|----------|-------|
| --- | Minor | figures in D:\codes\ClaudeGPT\rag_project\rag-knowledge\paper-kbs\tex\journal_20p\main_20p.tex... |
| --- | Minor | 8 figures. |
| --- | Minor | n3_overview.tex:77: fig_analogy_single |
| --- | Minor | n3_overview.tex:85: fig_architecture_cropped |
| --- | Minor | Raster format (.png) used. Prefer Vector (PDF/EPS). |
| --- | Minor | Pillow not installed; skipped DPI analysis (install Pillow for DPI checks). |
| --- | Minor | n3_overview.tex:135: fig_workflow_demo_cropped |
| --- | Minor | Raster format (.png) used. Prefer Vector (PDF/EPS). |
| --- | Minor | Pillow not installed; skipped DPI analysis (install Pillow for DPI checks). |
| --- | Minor | n6_retrieval.tex:47: fig_tiered_algorithm |
| --- | Minor | n8a_eval.tex:95: fig3_routing |
| --- | Minor | n8b_eval.tex:86: fig_ladder_optimization |
| --- | Minor | n8b_eval.tex:101: fig_miss_overlap |
| --- | Minor | n8c_eval.tex:106: fig4_inflation |
| --- | Minor | Found 2 potential issues. |
| --- | Minor | [Script] checker exited 1 |

### [Script] FORMAT

| Line | Severity | Issue |
|------|----------|-------|
| --- | Minor | ============================================================ |
| --- | Minor | Format Check Report |
| --- | Minor | ============================================================ |
| --- | Minor | D:\codes\ClaudeGPT\rag_project\rag-knowledge\paper-kbs\tex\journal_20p\main_20p.tex |
| --- | Minor | WARNING |
| --- | Minor | Found 186 issues |
| --- | Minor | Found |
| --- | Minor | (21 issues) |
| --- | Minor | 34: Wrong length of dash may have been used. |
| --- | Minor | 50: Wrong length of dash may have been used. |
| --- | Minor | 50: Wrong length of dash may have been used. |
| --- | Minor | 50: Wrong length of dash may have been used. |
| --- | Minor | 26: Wrong length of dash may have been used. |
| --- | Minor | ... and 16 more |
| --- | Minor | (165 issues) |
| --- | Minor | 79: Intersentence spacing (`\@') should perhaps be used. |
| --- | Minor | 119: Command terminated with space. |
| --- | Minor | 119: Command terminated with space. |
| --- | Minor | 120: Command terminated with space. |
| --- | Minor | 120: Command terminated with space. |
| --- | Minor | ... and 160 more |
| --- | Minor | ============================================================ |

### [Script] GRAMMAR

| Line | Severity | Issue |
|------|----------|-------|
| --- | Minor | [Script]: goal=grammar strength=minimal |
| --- | Minor | No rule-based issues detected in selected scope. |

### [Script] LOGIC

| Line | Severity | Issue |
|------|----------|-------|
| --- | Critical | Section not found: methods (available: introduction, related, experiment, experiment_2, discussion, conclusion, abstract) |
| --- | Major | REVIEW (n2_related.tex:128-138) : No research gap derivation found at end of Related Work |
| --- | Major | Abstract, contribution claims, and conclusion may be misaligned. |
| --- | Minor | conclusion missing contribution, method; conclusion missing contribution response. |
| --- | Minor | Make sure all three sections consistently state the problem, method, key results, and contribution. |
| --- | Minor | These sections should tell the same core story with different emphasis, not diverge. |

### [Script] PRESUBMISSION

| Line | Severity | Issue |
|------|----------|-------|
| --- | Minor | [A1] Abstract five-element check is incomplete; missing background, method. |
| 89 | Minor | [G2] Long paragraph detected (266 words, 11 sentences); split or add a clearer topic sentence. |

### [Script] SENTENCES

| Line | Severity | Issue |
|------|----------|-------|
| --- | Minor | [Script]: goal=grammar strength=minimal |
| --- | Minor | SENTENCE (n1_intro.tex:57, 23 words, 4 clauses)  [Script] |
| --- | Minor | The platform integrates document parsing, automatic collection assignment, lifecycle management, operational experiences, the tiered access path and a Model Context Protocol (MCP) server  . |
| --- | Minor | The platform integrates document parsing. automatic collection assignment. lifecycle management. operational experiences. the tiered access path and a Model Context Protocol (MCP) server  .. |
| --- | Minor | Sentence exceeds complexity threshold, split for readability. Applying the split needs --strength moderate or higher. |
| --- | Minor | none (split proposal only; source not rewritten) |
| --- | Minor | none |
| --- | Minor | Check: NEEDS-LLM |
| --- | Minor | Flags:    not-assessed |
| --- | Minor | SENTENCE (n1_intro.tex:64, 57 words, 5 clauses)  [Script] |
| --- | Minor | \noindent\textbf{Contributions.} \begin{enumerate} \item A management-level model for knowledge document management and its implementation: documents are managed at collection, document and segment level, collections are assigned automatically from parsed content, sub-libraries are nodes with their own indices, and the state of a collection is described by three sources that can be compared in lifecycle audits. |
| --- | Minor | \noindent\textbf{Contributions.} \begin{enumerate} \item A management-level model for knowledge document management and its implementation: documents are managed at collection. document and segment level. collections are assigned automatically from parsed content. sub-libraries are nodes with their own indices. and the state of a collection is described by three sources that can be compared in lifecycle audits.. |
| --- | Minor | Sentence exceeds complexity threshold, split for readability. Applying the split needs --strength moderate or higher. |
| --- | Minor | none (split proposal only; source not rewritten) |
| --- | Minor | none |
| --- | Minor | Check: NEEDS-LLM |
| --- | Minor | Flags:    not-assessed |
| --- | Minor | SENTENCE (n1_intro.tex:64, 61 words, 3 clauses)  [Script] |
| --- | Minor | A mechanical full-read script found the target strings in 72/72 cases after reading 879 parts (24.3 MB, 253.7 s per question) but generated no answers, and two ten-question answer grids reported gold identifiers in the answer or recorded trace for all 60 cells while strict and alias-aware lexical coverage and recognised citation markers vary with the corpus substrate. |
| --- | Minor | A mechanical full-read script found the target strings in 72/72 cases after reading 879 parts (24.3 MB. 253.7 s per question) but generated no answers. and two ten-question answer grids reported gold identifiers in the answer or recorded trace for all 60 cells while strict and alias-aware lexical coverage and recognised citation markers vary with the corpus substrate.. |
| --- | Minor | Sentence exceeds complexity threshold, split for readability. Applying the split needs --strength moderate or higher. |
| --- | Minor | none (split proposal only; source not rewritten) |
| --- | Minor | none |
| --- | Minor | Check: NEEDS-LLM |
| --- | Minor | Flags:    not-assessed |
| --- | Minor | SENTENCE (n1_intro.tex:64, 59 words, 4 clauses)  [Script] |
| --- | Minor | \item A same-pool diagnostic on the segment tier: score-based ordering lowers Hit@5 from 0.94 to 0.44, while fusion order among recorded survivors restores 0.94, and all 191 recorded scores exceed the configured 0.5 threshold, so the measurable risk lies in ordering; filtering was not activated on this pool and therefore remains untested (Sections~  and~ ). |
| --- | Minor | \item A same-pool diagnostic on the segment tier: score-based ordering lowers Hit@5 from 0.94 to 0.44. while fusion order among recorded survivors restores 0.94. and all 191 recorded scores exceed the configured 0.5 threshold. so the measurable risk lies in ordering; filtering was not activated on this pool and therefore remains untested (Sections~  and~ ).. |
| --- | Minor | Sentence exceeds complexity threshold, split for readability. Applying the split needs --strength moderate or higher. |
| --- | Minor | none (split proposal only; source not rewritten) |
| --- | Minor | none |
| --- | Minor | Check: NEEDS-LLM |
| --- | Minor | Flags:    not-assessed |
| --- | Minor | SENTENCE (n1_intro.tex:124, 37 words, 4 clauses)  [Script] |
| --- | Minor | Section~  positions the work; Sections~ -- describe the management model, the collection and document levels, and the tiered access path; Section~  covers deployment and enforcement; and Section~  evaluates the system, followed by implications, limitations and conclusions in Sections~ -- . |
| --- | Minor | Section~  positions the work; Sections~ -- describe the management model. the collection and document levels. and the tiered access path; Section~  covers deployment and enforcement; and Section~  evaluates the system. followed by implications. limitations and conclusions in Sections~ -- .. |
| --- | Minor | Sentence exceeds complexity threshold, split for readability. Applying the split needs --strength moderate or higher. |
| --- | Minor | none (split proposal only; source not rewritten) |
| --- | Minor | none |
| --- | Minor | Check: NEEDS-LLM |
| --- | Minor | Flags:    not-assessed |
| --- | Minor | SENTENCE (n2_related.tex:4, 29 words, 4 clauses)  [Script] |
| --- | Minor | \subsection{Knowledge management and document acquisition} Public knowledge bases organise facts under explicit ontologies \citep{auer-dbpedia-kb-2007,hoffart-yago2-kb-2013}, whereas enterprise content management emphasises governance over organisational documents \citep{paivarinta-ecm-2005,tyrvaainen-ecm-2006}. |
| --- | Minor | \subsection{Knowledge management and document acquisition} Public knowledge bases organise facts under explicit ontologies \citep{auer-dbpedia-kb-2007. hoffart-yago2-kb-2013}. whereas enterprise content management emphasises governance over organisational documents \citep{paivarinta-ecm-2005. tyrvaainen-ecm-2006}.. |
| --- | Minor | Sentence exceeds complexity threshold, split for readability. Applying the split needs --strength moderate or higher. |
| --- | Minor | none (split proposal only; source not rewritten) |
| --- | Minor | none |
| --- | Minor | Check: NEEDS-LLM |
| --- | Minor | Flags:    not-assessed |
| --- | Minor | SENTENCE (n2_related.tex:4, 37 words, 6 clauses)  [Script] |
| --- | Minor | Research on organisational knowledge explains how tacit experience becomes shareable \citep{nonaka-seci-1994,nonaka-seci-ba-2000}; adjacent work studies metadata quality, tagging, human review and auditability \citep{park-metadata-quality-2009,golder-tagging-2006,mosqueira-rey-hitl-2022,barredo-arrieta-xai-2020}; automated text categorization provides the classification backbone \citep{sebastiani2002machine}. |
| --- | Minor | Research on organisational knowledge explains how tacit experience becomes shareable \citep{nonaka-seci-1994. nonaka-seci-ba-2000}; adjacent work studies metadata quality. tagging. human review and auditability \citep{park-metadata-quality-2009. golder-tagging-2006. mosqueira-rey-hitl-2022. barredo-arrieta-xai-2020}; automated text categorization provides the classification backbone \citep{sebastiani2002machine}.. |
| --- | Minor | Sentence exceeds complexity threshold, split for readability. Applying the split needs --strength moderate or higher. |
| --- | Minor | none (split proposal only; source not rewritten) |
| --- | Minor | none |
| --- | Minor | Check: NEEDS-LLM |
| --- | Minor | Flags:    not-assessed |
| --- | Minor | SENTENCE (n2_related.tex:4, 18 words, 4 clauses)  [Script] |
| --- | Minor | Document-AI methods, including layout-aware analysis and MinerU, recover text and structure from complex documents \citep{zhong-publaynet-layout-2019,huang-layoutlmv3-docai-2022,mineru}. |
| --- | Minor | Document-AI methods. including layout-aware analysis and MinerU. recover text and structure from complex documents \citep{zhong-publaynet-layout-2019. huang-layoutlmv3-docai-2022. mineru}.. |
| --- | Minor | Sentence exceeds complexity threshold, split for readability. Applying the split needs --strength moderate or higher. |
| --- | Minor | none (split proposal only; source not rewritten) |
| --- | Minor | none |
| --- | Minor | Check: NEEDS-LLM |
| --- | Minor | Flags:    not-assessed |
| --- | Minor | SENTENCE (n2_related.tex:104, 24 words, 4 clauses)  [Script] |
| --- | Minor | The LLM-as-a-judge literature documents preference bias, imperfect agreement, listwise instability and self-preference \citep{zheng-llmjudge,sun-urara,panickssery-selfpref}; outcome-based verification can reward flawed reasoning \citep{lightman-verify}. |
| --- | Minor | The LLM-as-a-judge literature documents preference bias. imperfect agreement. listwise instability and self-preference \citep{zheng-llmjudge. sun-urara. panickssery-selfpref}; outcome-based verification can reward flawed reasoning \citep{lightman-verify}.. |
| --- | Minor | Sentence exceeds complexity threshold, split for readability. Applying the split needs --strength moderate or higher. |
| --- | Minor | none (split proposal only; source not rewritten) |
| --- | Minor | none |
| --- | Minor | Check: NEEDS-LLM |
| --- | Minor | Flags:    not-assessed |
| --- | Minor | SENTENCE (n2_related.tex:112, 40 words, 5 clauses)  [Script] |
| --- | Minor | HMRS examines how acquisition checks, automatic collection assignment, tiered retrieval and answer-time evidence inspection interact in one knowledge document management workflow, reports where implementation and transport boundaries constrain that workflow, and measures separately the two roles a verifier can play. |
| --- | Minor | HMRS examines how acquisition checks. automatic collection assignment. tiered retrieval and answer-time evidence inspection interact in one knowledge document management workflow. reports where implementation and transport boundaries constrain that workflow. and measures separately the two roles a verifier can play.. |
| --- | Minor | Sentence exceeds complexity threshold, split for readability. Applying the split needs --strength moderate or higher. |
| --- | Minor | none (split proposal only; source not rewritten) |
| --- | Minor | none |
| --- | Minor | Check: NEEDS-LLM |
| --- | Minor | Flags:    not-assessed |
| --- | Minor | SENTENCE (n2_related.tex:125, 45 words, 5 clauses)  [Script] |
| --- | Minor | Its contribution is a knowledge document management workflow that connects and exposes stages from parse admission through answer-evidence reporting, a per-question account of answer-layer checks, and a same-pool diagnostic showing that ordering by the verifier score, not threshold filtering, is where the measurable loss sits. |
| --- | Minor | Its contribution is a knowledge document management workflow that connects and exposes stages from parse admission through answer-evidence reporting. a per-question account of answer-layer checks. and a same-pool diagnostic showing that ordering by the verifier score. not threshold filtering. is where the measurable loss sits.. |
| --- | Minor | Sentence exceeds complexity threshold, split for readability. Applying the split needs --strength moderate or higher. |
| --- | Minor | none (split proposal only; source not rewritten) |
| --- | Minor | none |
| --- | Minor | Check: NEEDS-LLM |
| --- | Minor | Flags:    not-assessed |
| --- | Minor | SENTENCE (n7_implementation.tex:8, 77 words, 14 clauses)  [Script] |
| --- | Minor | They fall into the management groups of Table~ : parsing and quality review for admission, library and sub-library creation, placement, description and tag editing for organisation, move, rename, delete and forced re-index for lifecycle, catalogue, vector, keyword and two-stage search for the access path, the Laya evidence gate for segment admission, the document graph for navigation, and operational-experience tools, plus persona-distillation workflows that are outside the scope of this evaluation and use their own retrieval and synthesis path. |
| --- | Minor | They fall into the management groups of Table~ : parsing and quality review for admission. library and sub-library creation. placement. description and tag editing for organisation. move. rename. delete and forced re-index for lifecycle. catalogue. vector. keyword and two-stage search for the access path. the Laya evidence gate for segment admission. the document graph for navigation. and operational-experience tools. plus persona-distillation workflows that are outside the scope of this evaluation and use their own retrieval and synthesis path.. |
| --- | Minor | Sentence exceeds complexity threshold, split for readability. Applying the split needs --strength moderate or higher. |
| --- | Minor | none (split proposal only; source not rewritten) |
| --- | Minor | none |
| --- | Minor | Check: NEEDS-LLM |
| --- | Minor | Flags:    not-assessed |
| --- | Minor | SENTENCE (n8a_eval.tex:37, 27 words, 4 clauses)  [Script] |
| --- | Minor | \textbf{Measures and controls.} Document-level Hit@5, Recall@5 and MRR@5 measure the returned top five, with MRR zero if no gold is in that window . |
| --- | Minor | \textbf{Measures and controls.} Document-level Hit@5. Recall@5 and MRR@5 measure the returned top five. with MRR zero if no gold is in that window .. |
| --- | Minor | Sentence exceeds complexity threshold, split for readability. Applying the split needs --strength moderate or higher. |
| --- | Minor | none (split proposal only; source not rewritten) |
| --- | Minor | none |
| --- | Minor | Check: NEEDS-LLM |
| --- | Minor | Flags:    not-assessed |
| --- | Minor | SENTENCE (n8a_eval.tex:69, 25 words, 5 clauses)  [Script] |
| --- | Minor | Of 16 lifecycle scenarios, create, move, delete and forced re-index passed, while task-status reporting and the update check failed; merge and split were not controlled. |
| --- | Minor | Of 16 lifecycle scenarios. create. move. delete and forced re-index passed. while task-status reporting and the update check failed; merge and split were not controlled.. |
| --- | Minor | Sentence exceeds complexity threshold, split for readability. Applying the split needs --strength moderate or higher. |
| --- | Minor | none (split proposal only; source not rewritten) |
| --- | Minor | none |
| --- | Minor | Check: NEEDS-LLM |
| --- | Minor | Flags:    not-assessed |
| --- | Minor | SENTENCE (n8a_eval.tex:115, 38 words, 4 clauses)  [Script] |
| --- | Minor | Reading the full corpus took 64{,}584 calls in total, an average of 897 calls per question, and averaged 24.3 MB and 253.7 s per question, versus 31.4 KB and 16.3 s for A0. |
| --- | Minor | Reading the full corpus took 64{. }584 calls in total. an average of 897 calls per question. and averaged 24.3 MB and 253.7 s per question. versus 31.4 KB and 16.3 s for A0.. |
| --- | Minor | Sentence exceeds complexity threshold, split for readability. Applying the split needs --strength moderate or higher. |
| --- | Minor | none (split proposal only; source not rewritten) |
| --- | Minor | none |
| --- | Minor | Check: NEEDS-LLM |
| --- | Minor | Flags:    not-assessed |
| --- | Minor | SENTENCE (n8b_eval.tex:10, 107 words, 6 clauses)  [Script] |
| --- | Minor | Three case measurements exist: an extraction campaign over one small knowledge base produced thirteen candidate drafts (archived \path{experience_smoke.json} in the 2026-10-13 batch tarball; \texttt{extract\_candidates}~13, \texttt{drafts\_created}~13); one end-to-end scenario was sedimented into one experience (\texttt{exp-d6f4d47ae3d6}) that a later global experience search returned first, at local similarity 0.711 (archived scenario A6 of the 2026-10-12 full-test campaign); and the draft-approval path was never exercised, because the draft pool was empty (\texttt{count}~0) and \path{experience_draft_read} and \path{experience_draft_approve} could not run; the heuristic extraction path had run only in dry-run mode, returning a dump the quality gate would reject. |
| --- | Minor | Three case measurements exist: an extraction campaign over one small knowledge base produced thirteen candidate drafts (archived \path{experience_smoke.json} in the 2026-10-13 batch tarball; \texttt{extract\_candidates}~13. \texttt{drafts\_created}~13); one end-to-end scenario was sedimented into one experience (\texttt{exp-d6f4d47ae3d6}) that a later global experience search returned first. at local similarity 0.711 (archived scenario A6 of the 2026-10-12 full-test campaign); and the draft-approval path was never exercised. because the draft pool was empty (\texttt{count}~0) and \path{experience_draft_read} and \path{experience_draft_approve} could not run; the heuristic extraction path had run only in dry-run mode. returning a dump the quality gate would reject.. |
| --- | Minor | Sentence exceeds complexity threshold, split for readability. Applying the split needs --strength moderate or higher. |
| --- | Minor | none (split proposal only; source not rewritten) |
| --- | Minor | none |
| --- | Minor | Check: NEEDS-LLM |
| --- | Minor | Flags:    not-assessed |
| --- | Minor | SENTENCE (n8b_eval.tex:31, 46 words, 7 clauses)  [Script] |
| --- | Minor | A0 is the tiered baseline; A0f uses expanded document windows, A0h additionally unions vector chunk windows, PD uses a navigation-free precise per-document search, A1b a scoped flat union and reference-mode judge, A2 skips that judge, A3 uses nominally name-only cards, and read-all scans every stored part. |
| --- | Minor | A0 is the tiered baseline; A0f uses expanded document windows. A0h additionally unions vector chunk windows. PD uses a navigation-free precise per-document search. A1b a scoped flat union and reference-mode judge. A2 skips that judge. A3 uses nominally name-only cards. and read-all scans every stored part.. |
| --- | Minor | Sentence exceeds complexity threshold, split for readability. Applying the split needs --strength moderate or higher. |
| --- | Minor | none (split proposal only; source not rewritten) |
| --- | Minor | none |
| --- | Minor | Check: NEEDS-LLM |
| --- | Minor | Flags:    not-assessed |
| --- | Minor | SENTENCE (n8b_eval.tex:39, 42 words, 5 clauses)  [Script] |
| --- | Minor | The no-gate arm A2, which skips the judge on the tiered route, contained the string for 25/72 against 37/72 for A0 (uncorrected exact McNemar ; the later record repeats 25/72 exactly), the arm contrast that bears on the evidence gate. |
| --- | Minor | The no-gate arm A2. which skips the judge on the tiered route. contained the string for 25/72 against 37/72 for A0 (uncorrected exact McNemar ; the later record repeats 25/72 exactly). the arm contrast that bears on the evidence gate.. |
| --- | Minor | Sentence exceeds complexity threshold, split for readability. Applying the split needs --strength moderate or higher. |
| --- | Minor | none (split proposal only; source not rewritten) |
| --- | Minor | none |
| --- | Minor | Check: NEEDS-LLM |
| --- | Minor | Flags:    not-assessed |
| --- | Minor | SENTENCE (n8b_eval.tex:61, 58 words, 4 clauses)  [Script] |
| --- | Minor | In a separately added later A3 record, containment is 25/72, the scripted gold domain is selected for 49/72, with 13 missing top candidates and 23 empty packs; their causes are not established, and the routing drop from 72/72 in the frozen record is consistent with route-card indexing state rather than with the description ablation itself. |
| --- | Minor | In a separately added later A3 record. containment is 25/72. the scripted gold domain is selected for 49/72. with 13 missing top candidates and 23 empty packs; their causes are not established. and the routing drop from 72/72 in the frozen record is consistent with route-card indexing state rather than with the description ablation itself.. |
| --- | Minor | Sentence exceeds complexity threshold, split for readability. Applying the split needs --strength moderate or higher. |
| --- | Minor | none (split proposal only; source not rewritten) |
| --- | Minor | none |
| --- | Minor | Check: NEEDS-LLM |
| --- | Minor | Flags:    not-assessed |
| --- | Minor | SENTENCE (n8b_eval.tex:77, 18 words, 4 clauses)  [Script] |
| --- | Minor | Among A0's 35 misses, A0f, A0h and PD contain the string in 8, 15 and 9 cases, respectively. |
| --- | Minor | Among A0's 35 misses. A0f. A0h and PD contain the string in 8. 15 and 9 cases. respectively.. |
| --- | Minor | Sentence exceeds complexity threshold, split for readability. Applying the split needs --strength moderate or higher. |
| --- | Minor | none (split proposal only; source not rewritten) |
| --- | Minor | none |
| --- | Minor | Check: NEEDS-LLM |
| --- | Minor | Flags:    not-assessed |
| --- | Minor | SENTENCE (n8c_eval.tex:33, 243 words, 0 clauses)  [Script] |
| --- | Minor | \begin{tabular}{@{}l>{\raggedright\arraybackslash}p{0.335\textwidth}l*{9}{c}@{}} \toprule & & & \multicolumn{3}{c}{Platform (P)} & \multicolumn{3}{c}{File tools (F)} & \multicolumn{3}{c}{Chunk replica (C)}\\ \cmidrule(lr){4-6}\cmidrule(lr){7-9}\cmidrule(lr){10-12} Q & Question (abridged) & Gold & s & a & m & s & a & m & s & a & m\\ \midrule BQ01 & Transformer attention; why recurrence is replaced & 1706.03762 & \yes & \yes & 6 & \yes & \yes & 0 & \yes & \yes & 5\\ BQ02 & NISQ definition and its central limitation & 1801.00862 & \yes & \yes & 4 & \yes & \yes & 3 & \yes & \yes & 0\\ BQ03 & MultiMedQA and Flan-PaLM on MedQA & 2212.13138 & \yes & \yes & 4 & \yes & \yes & 1 & \yes & \yes & 1\\ BQ04 & Three ontologies subdividing the Gene Ontology & 1602.01876 & \yes & \yes & 1 & \yes & \yes & 1 & \yes & \yes & 0\\ BQ05 & European growth versus Unified Growth Theory & 1512.08067 & \yes & \yes & 0 & \yes & \yes & 0 & \yes & \yes & 0\\ BQ06 & Contributions governing precipitation extremes & 1503.07557 &   & \yes & 6 & \yes & \yes & 4 & \yes & \yes & 0\\ BQ07 & MameLoshnLM and its parameter scale & 2608.05850 & \yes & \yes & 1 & \yes & \yes & 2 & \yes & \yes & 0\\ BQ08 & Oxygen redox and cathode capacity & 2408.09942 & \yes & \yes & 2 & \yes & \yes & 0 & \yes & \yes & 0\\ BQ09 & Visual SLAM in dynamic scenes (MLP-SLAM) & 2410.10669 & \yes & \yes & 2 &   & \yes & 6 & \yes & \yes & 0\\ BQ10 & Tumour control under immune evasion & 2604.01385 & \yes & \yes & 3 & \yes & \yes & 6 &   & \yes & 0\\ \midrule & \emph{All ten questions} & & 9 & 10 & 29 & 9 & 10 & 23 & 9 & 10 & 6\\ \bottomrule \end{tabular} \end{table*} |
| --- | Minor | \begin{tabular}{@{}l>{\raggedright\arraybackslash}p{0.335\textwidth}l*{9}{c}@{}} \toprule & & & \multicolumn{3}{c}{Platform (P)} & \multicolumn{3}{c}{File tools (F)} & \multicolumn{3}{c}{Chunk replica (C)}\\ \cmidrule(lr){4-6}\cmidrule(lr){7-9}\cmidrule(lr){10-12} Q & Question (abridged) & Gold & s & a & m & s & a & m & s & a & m\\ \midrule BQ01 & Transformer attention; why recurrence is replaced & 1706.03762 & \yes & \yes & 6 & \yes & \yes & 0 & \yes & \yes & 5\\ BQ02 & NISQ definition and its central limitation & 1801.00862 & \yes & \yes & 4 & \yes & \yes & 3 & \yes & \yes & 0\\ BQ03 & MultiMedQA and Flan-PaLM on MedQA & 2212.13138 & \yes & \yes & 4 & \yes & \yes & 1 & \yes & \yes & 1\\ BQ04 & Three ontologies subdividing the Gene Ontology & 1602.01876 & \yes & \yes & 1 & \yes & \yes & 1 & \yes & \yes & 0\\ BQ05 & European growth versus Unified Growth Theory & 1512.08067 & \yes & \yes & 0 & \yes & \yes & 0 & \yes & \yes & 0\\ BQ06 & Contributions governing precipitation extremes & 1503.07557 &   & \yes & 6 & \yes & \yes & 4 & \yes & \yes & 0\\ BQ07 & MameLoshnLM and its parameter scale & 2608.05850 & \yes & \yes & 1 & \yes & \yes & 2 & \yes & \yes & 0\\ BQ08 & Oxygen redox and cathode capacity & 2408.09942 & \yes & \yes & 2 & \yes & \yes & 0 & \yes & \yes & 0\\ BQ09 & Visual SLAM in dynamic scenes (MLP-SLAM) & 2410.10669 & \yes & \yes & 2 &   & \yes & 6 & \yes & \yes & 0\\ BQ10 & Tumour control under immune evasion & 2604.01385 & \yes & \yes & 3 & \yes & \yes & 6 &   & \yes & 0\\ \midrule & \emph{All ten questions} & & 9 & 10 & 29 & 9 & 10 & 23 & 9 & 10 & 6\\ \bottomrule \end{tabular} \end{table*} |
| --- | Minor | Sentence exceeds complexity threshold, split for readability. Applying the split needs --strength moderate or higher. |
| --- | Minor | none (split proposal only; source not rewritten) |
| --- | Minor | none |
| --- | Minor | Check: NEEDS-LLM |
| --- | Minor | Flags:    not-assessed |
| --- | Minor | SENTENCE (n8c_eval.tex:56, 39 words, 4 clauses)  [Script] |
| --- | Minor | In the original grid strict keyword coverage was 9/10 for each arm, alias-aware coverage 10/10, and marker-bearing answers 9/10, 7/10 and 2/10 for P, F and C (Table~ ; Fig.~S2 shows the grid's aggregate). |
| --- | Minor | In the original grid strict keyword coverage was 9/10 for each arm. alias-aware coverage 10/10. and marker-bearing answers 9/10. 7/10 and 2/10 for P. F and C (Table~ ; Fig.~S2 shows the grid's aggregate).. |
| --- | Minor | Sentence exceeds complexity threshold, split for readability. Applying the split needs --strength moderate or higher. |
| --- | Minor | none (split proposal only; source not rewritten) |
| --- | Minor | none |
| --- | Minor | Check: NEEDS-LLM |
| --- | Minor | Flags:    not-assessed |
| --- | Minor | SENTENCE (n9_discussion.tex:4, 18 words, 5 clauses)  [Script] |
| --- | Minor | Of 16 lifecycle scenarios, create, move, delete and forced re-index passed, whereas task-status reporting and update checks failed. |
| --- | Minor | Of 16 lifecycle scenarios. create. move. delete and forced re-index passed. whereas task-status reporting and update checks failed.. |
| --- | Minor | Sentence exceeds complexity threshold, split for readability. Applying the split needs --strength moderate or higher. |
| --- | Minor | none (split proposal only; source not rewritten) |
| --- | Minor | none |
| --- | Minor | Check: NEEDS-LLM |
| --- | Minor | Flags:    not-assessed |
| --- | Minor | SENTENCE (n9_discussion.tex:34, 24 words, 4 clauses)  [Script] |
| --- | Minor | Stronger claims need independent questions, controlled single-factor comparisons, repeated runs, semantic support review, and tests of operations and recovery beyond the present local setting. |
| --- | Minor | Stronger claims need independent questions. controlled single-factor comparisons. repeated runs. semantic support review. and tests of operations and recovery beyond the present local setting.. |
| --- | Minor | Sentence exceeds complexity threshold, split for readability. Applying the split needs --strength moderate or higher. |
| --- | Minor | none (split proposal only; source not rewritten) |
| --- | Minor | none |
| --- | Minor | Check: NEEDS-LLM |
| --- | Minor | Flags:    not-assessed |
| --- | Minor | SENTENCE (n11_conclusion.tex:4, 62 words, 9 clauses)  [Script] |
| --- | Minor | At the collection level, documents are parsed, classified into the library whose scope matches their body, and catalogued with derived descriptions and tags; at the document level, move, rename, delete and forced re-index operations update the collection, while reconciliation can detect selected disagreements among three state sources; at the segment level, an optional gate scores candidate passages and returns survivors with provenance. |
| --- | Minor | At the collection level. documents are parsed. classified into the library whose scope matches their body. and catalogued with derived descriptions and tags; at the document level. move. rename. delete and forced re-index operations update the collection. while reconciliation can detect selected disagreements among three state sources; at the segment level. an optional gate scores candidate passages and returns survivors with provenance.. |
| --- | Minor | Sentence exceeds complexity threshold, split for readability. Applying the split needs --strength moderate or higher. |
| --- | Minor | none (split proposal only; source not rewritten) |
| --- | Minor | none |
| --- | Minor | Check: NEEDS-LLM |
| --- | Minor | Flags:    not-assessed |
| --- | Minor | SENTENCE (n11_conclusion.tex:14, 19 words, 5 clauses)  [Script] |
| --- | Minor | In 16 lifecycle scenarios, create, move, delete and forced re-index passed, whereas task-status reporting and the update check failed. |
| --- | Minor | In 16 lifecycle scenarios. create. move. delete and forced re-index passed. whereas task-status reporting and the update check failed.. |
| --- | Minor | Sentence exceeds complexity threshold, split for readability. Applying the split needs --strength moderate or higher. |
| --- | Minor | none (split proposal only; source not rewritten) |
| --- | Minor | none |
| --- | Minor | Check: NEEDS-LLM |
| --- | Minor | Flags:    not-assessed |
| --- | Minor | SENTENCE (n11_conclusion.tex:14, 48 words, 5 clauses)  [Script] |
| --- | Minor | On the same 72-question corpus, the tiered path with a chunk-window evidence union contained the gold string in 52/72, above a scoped flat union with a potentially gold-dependent reference lookup (39/72; 13--0, unadjusted  ) and above a precise arm without navigation (46/72; 7--1,  , not statistically resolved). |
| --- | Minor | On the same 72-question corpus. the tiered path with a chunk-window evidence union contained the gold string in 52/72. above a scoped flat union with a potentially gold-dependent reference lookup (39/72; 13--0. unadjusted  ) and above a precise arm without navigation (46/72; 7--1. not statistically resolved).. |
| --- | Minor | Sentence exceeds complexity threshold, split for readability. Applying the split needs --strength moderate or higher. |
| --- | Minor | none (split proposal only; source not rewritten) |
| --- | Minor | none |
| --- | Minor | Check: NEEDS-LLM |
| --- | Minor | Flags:    not-assessed |
| --- | Minor | SENTENCE (n11_conclusion.tex:43, 30 words, 4 clauses)  [Script] |
| --- | Minor | Broader evaluation needs independently authored questions, repeated agent trials with run-to-run variance estimates, claim-level support review, larger and repeated versions of the ladder-versus-flat-and-precise contrast with multiplicity control, and crash-recovery tests. |
| --- | Minor | Broader evaluation needs independently authored questions. repeated agent trials with run-to-run variance estimates. claim-level support review. larger and repeated versions of the ladder-versus-flat-and-precise contrast with multiplicity control. and crash-recovery tests.. |
| --- | Minor | Sentence exceeds complexity threshold, split for readability. Applying the split needs --strength moderate or higher. |
| --- | Minor | none (split proposal only; source not rewritten) |
| --- | Minor | none |
| --- | Minor | Check: NEEDS-LLM |
| --- | Minor | Flags:    not-assessed |
| --- | Minor | SENTENCE (n11_conclusion.tex:43, 22 words, 4 clauses)  [Script] |
| --- | Minor | Within these bounds, HMRS shows that treating the collection as a managed, auditable object is a viable, inspectable basis for evidence-traced retrieval. |
| --- | Minor | Within these bounds. HMRS shows that treating the collection as a managed. auditable object is a viable. inspectable basis for evidence-traced retrieval.. |
| --- | Minor | Sentence exceeds complexity threshold, split for readability. Applying the split needs --strength moderate or higher. |
| --- | Minor | none (split proposal only; source not rewritten) |
| --- | Minor | none |
| --- | Minor | Check: NEEDS-LLM |
| --- | Minor | Flags:    not-assessed |
| --- | Minor | SENTENCE (main_20p.tex:89, 39 words, 4 clauses)  [Script] |
| --- | Minor | We present HMRS (Hierarchical Management Retrieval System), a self-hosted knowledge document management system managing documents at three levels---collection, document and segment---and serving queries along a tiered path from the catalogue of collections, through document descriptions, to the evidence-carrying segment. |
| --- | Minor | We present HMRS (Hierarchical Management Retrieval System). a self-hosted knowledge document management system managing documents at three levels---collection. document and segment---and serving queries along a tiered path from the catalogue of collections. through document descriptions. to the evidence-carrying segment.. |
| --- | Minor | Sentence exceeds complexity threshold, split for readability. Applying the split needs --strength moderate or higher. |
| --- | Minor | none (split proposal only; source not rewritten) |
| --- | Minor | none |
| --- | Minor | Check: NEEDS-LLM |
| --- | Minor | Flags:    not-assessed |

## Decision Signals

- **Committee Score**: 4.0/10
- **Editor Verdict**: Desk Reject
- **Reviewer Recommendation**: Major Revision
- **Issue Bundle**: 1 major / 0 moderate / 0 minor

## Revision Roadmap

### Priority 1 --- Must Address (Blocking)

- [ ] Abstract and conclusion claims need explicit evidence traceability ([LLM]; abstract)
