# Source audit: figure drafts, 2026-09-19

## Scope and approval boundary

This note accompanies `fig1-concept-draft` and `fig3-evidence-draft` in this directory. Only draft SVGs, their HTML/PNG/PDF previews, the builder, and this authorized note are edited. The original paper and its figures remain untouched.

**After design approval, the original manuscript captions and accessibility descriptions must be corrected before substituting these figures.** In particular, remove generic claims that dense retrieval intrinsically cannot provide provenance or retry; describe the reproduced configuration and its logging limitations instead. Any BQ01 caption combining current part numbers with the archived gate/caveat must be replaced. Check related body-text assertions for the same run mismatch during that separately authorized integration pass.

All paths below are relative to the repository root. JSON selectors use predicate notation to identify records by `qid` or `pid`, rather than relying on array position. Figure prose is shorthand/paraphrase, not an invented verbatim quotation.

## Figure 1: protocol configuration, not a score comparison

- `paper_demo/tex/sec4_eval.tex`, Setup: Track C uses 800-character fixed chunks, top-2 evidence, a 4,000-character window, and one LLM call. Results explicitly attribute absent chunk-to-document metadata to the reproduction harness, not dense retrieval itself.
- `paper_demo/tex/sec2_system.tex`, Query-Driven, Content-Verified Retrieval: vector-first candidate recall; the gate reads text, scores topic/scenario/evidence on a combined 0–8 rubric, passes at ≥6, and otherwise invokes librarian fallback and rechecking.
- `benchmark-suite/results/bench10_qa.json`, `rows[qid=BQ02].question`: identifies the common NISQ query. Both sides of the figure receive this question; the diagram does not assert equivalent generation inputs or superior accuracy.
- Additional mismatch found while tightening the figure: `benchmark-suite/results/skill_track_answers.json`, `answers[qid=BQ02].gate.score` is **8**, and `final_answer` also says 8/8. Separately, `benchmark-suite/results/track_a_e2e_spot.json`, `rows[qid=BQ02].gate.score` = **"8/8"**, with `gate.path` = `fast-exit`; its top-level `scoring_rule_note` describes executing-agent rubric judgments. Thus both current answer and spot-run records say 8/8. `paper_demo/tex/sec3_demo.tex`, Scenario 2, instead describes 7/8. The earlier draft inherited 7/8 from the paper description. The revised conceptual figure intentionally makes **no instance-specific NISQ gate-score assertion**; it displays only the protocol threshold ≥6. The discrepancy must be reconciled against the intended demonstration run before manuscript integration.

## Figure 3: current BQ01 only

### Identity and current section trace

- `benchmark-suite/results/bench10_qa.json`, `rows[qid=BQ01]`: paper = *Attention Is All You Need*; `arxiv_id` = `1706.03762`; `question` asks how attention is computed and why it replaces recurrence/convolution.
- `benchmark-suite/results/skill_track_evidence.json` is a top-level array. In `[qid=BQ01].hits`, the first hit's `doc_path` names `artificial-intelligence__1706.03762__attention-is-all-you-need.md (part 2 of 2).md` in the computer-science/AI base. Its `chunk_text` starts with `## 7 Conclusion`.
- The second hit's `doc_path` names the same paper, `(part 1 of 2).md`; its `chunk_text` starts with `## 3.2.3 Applications of Attention in our Model`.
- Consequently, **part 1/2 → §3.2.3; part 2/2 → §7** is sourced from the current evidence record. The compact figure reverses retrieval order to display parts in document order, not to assert a ranking.

### Track A current answer and caveats

- `benchmark-suite/results/skill_track_answers.json`, `answers[qid=BQ01].gate.score` = **8**; `gate.decision` = `fast_exit (>=6)`.
- The same record's `final_answer` has Search Paths, Answer, Sources, Confidence and Blind Spots sections. The current Answer itself names scaled dot-product attention and provides multi-head dimensions; it is incorrect to portray this current answer as declaring the attention-computation formula unread.
- Its current Blind Spots section names the **positional-encoding formula**, training hyperparameter tables, and benchmark scores such as BLEU as outside the two read chunks. Figure shorthand: “Unread: positional formula, training details, benchmark scores.” This reports the answer's declaration, not an independent verification of full source coverage.
- The figure labels this mapping **Trace evidence**, and the HTML caption explicitly attributes the part-to-section mapping to `skill_track_evidence.json`, not verbatim answer citations. Part identifiers are recovered from the evidence JSON; they are not represented as a literal quote from the current final answer's Sources section.

### Track B: richer formula prose, self-reported source

- `benchmark-suite/results/track_bc.json`, `[qid=BQ01].track_b_bare_agent.raw_answer`: supplies the scaled dot-product expression, multi-head projection, complexity, parallel computation and short path-length rationale. The displayed expression is mathematical shorthand for that answer, not a verbatim prose quote.
- `track_b_bare_agent.files_used` contains `artificial-intelligence__1706.03762__attention-is-all-you-need.md`.
- `raw_model_output` asserts reading relevant sections and repeats the answer JSON. These self-reports do **not** provide an observed file-read audit trail. “Self-reported file source” is the intended claim, not that the answer lacks all section references: its prose does mention Section 4 and Table 1.

### Track C: observed abstention, unproved cause

- `benchmark-suite/results/track_bc.json`, `[qid=BQ01].track_c_dense_rag.raw_answer`: reports that the supplied excerpts concern English constituency parsing experiments and Table 4, then declares insufficient evidence and abstains. These content descriptions come only from the generated answer, not an independently inspected input payload.
- `evidence_chunks` = **2**, `evidence_chars` = **2854**, `evidence_docs` = **[]**.
- `raw_model_output.evidence_used` is embedded in a string and contains a coarse field label, not usable chunk-to-document provenance. The figure's “not logged in this harness” must not be generalized to dense retrieval as a method.
- Figure wording is **“C reports: parsing” + “Table 4 results”** and **“Reports insufficient evidence”**. These are explicitly attributed reports, not factual assertions that the input window was independently inspected. The logged `evidence_docs=[]` cannot substantiate the described content. **Chunking is only a possible cause; ranked-away evidence is not established**, because the relevant ranks/metadata are absent. This limitation is retained in the HTML caption rather than expanded inside the scientific figure.

## Archived BQ01: excluded from revised figure

- `benchmark-suite/results/archive-20260917-10000chunk/skill_track_answers.json`, `answers[qid=BQ01].final_answer`: records **7/8**, cites **part 25/26, §7** and **part 11/26, §3.2.3**, and declares that the exact scaled-dot-product formula in §3.2.1 lies outside the verified read windows.
- These archived identifiers and caveats cannot be combined with the current two-part document and current 8/8 record to manufacture a single trace.
- The revised SVG, PNG and PDF contain **no archive panel or run-history diagnostic**. This note is the location for the historical distinction.

## P2 bottom rejection trace

- `benchmark-suite/results/honest_failure_probe.json`, `probes[pid=P2].question`: asks about training epochs in *Spectral Tuning for Low-Resource Odor Recognition*; `why_out_of_corpus` identifies a fabricated citation absent from the corpus.
- `phase1_top_docs[0]`: BERT paper, `nlp__1810.04805__bert-pre-training-of-deep-bidirectional-transfor.md (1) (part 2 of 3).md`.
- `gate.score` = **"1/8"**; `gate.justification` explains that training-epoch strings concern BERT's own recipe, not the requested paper.
- `phase2_librarian.shelf_census`: five category bases with counts 72, 43, 32, 6 and 12, totaling **165 indexed documents**. `report_text` states **50 papers** in that scope.
- `phase2_librarian.finding` reports no answering document; `verdict` = **NOT_FOUND**. The diagram does not imply exhaustive absence beyond the recorded knowledge-base scope.

## Presentation and verification

- Figure 1: **1000 × 560** SVG units. Figure 3: **1000 × 594** SVG units. PNGs are rendered at 2×; PDFs are single-page figure-only exports.
- Body labels are mainly 19–20 SVG units; at a final width of 420 pt, these become approximately 8.0–8.4 pt. Final print size still depends on the approved LaTeX inclusion width. All SVG text is at least 14 units; the smallest section glyphs are not body prose.
- Explanatory HTML captions retain scope, paraphrase status, self-assessment limitations and the unproved chunking hypothesis. Captions are intentionally excluded from PNG/PDF figure exports and hidden for printing.
- Both SVGs have `title`/`desc`, editable text and paths, no foreignObject, and no external assets. Build checks parse XML, enforce minimum font size and height, check text viewport bounds, and assert selected JSON facts. Browser renders are visually inspected separately.
- Rebuild: `python paper_demo/figures/redesign-20260919/build_case_drafts.py`.

## Independent-verifier corrections applied

Track C content descriptions are now attributed to its generated answer. Track A part identifiers are explicitly labeled trace evidence. The P2 scope says indexed docs. A standalone 14-unit line states “Gate scores: LLM self-assessments, not accuracy.” The HTML caption repeats that limitation. Both current BQ02 score sources are checked by the builder. Original manuscript files remain unchanged pending approval.
