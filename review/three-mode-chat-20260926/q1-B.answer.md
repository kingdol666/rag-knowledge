Gate complete: **12/13 survivors, status=ok, real Laya engine, threshold 0.5**. L3 also resolved the two `repro.md` docs (coffee-refractometer test data — verified unrelated). Aggregation (L5.5) is done by the script itself. Final answer:

---

## Search Paths

| Layer | Action | Result |
|---|---|---|
| **L0** | `kb_list(lightweight=true)` — every KB description read | 16 KBs |
| **L1** | Query dims (subject=InstructDS · attribute=query-based dialogue summarization · constraint=high-quality generation) vs all descriptions | **1 relevant** (计算机与人工智能), **9 possible** (vague/content-free descriptions: Corpus-Chunks800, e2e-demo, soul-e2e-tester, AI 基础设施, e2e-flow, soul-e2e, aw-industrial-e2e, ZZ×2), **6 out_of_scope** (226 docs pruned by trustworthy specific descriptions) |
| **L2** | `kb_get_documents(lightweight=true)` on all 10 kept shelves | 145 docs, all descriptions read; InstructDS located: `nlp__2310.10981__instructive-dialogue-summarization-with-quer` (4 parts) |
| **L3** | Trust check on vague/content-free descriptions → head reads | 7 verification reads (2× repro, harness-handbook, global-rag-benchmark, 3 summarization auxiliaries); repro/harness/rag-benchmark verified unrelated and excluded from the manifest |
| **L4** | Paginated `kb_doc_read` on every candidate → structure-aware segments | Paper read **end-to-end, all 4 parts** (parts 1–3 complete, incl. references/appendices; part 4 tables); **13 segments** built (10 paper + 3 aux), offsets recorded |
| **L5** | `jev_filter.py --engine laya --input tmp/candidates-q1.json --output tmp/judged-q1.json --require-real` | **backend=laya_sdk** (local `model/laya` checkpoint), **criterion=evidence** (auto; query is not enumerative), **threshold=0.5**, status=ok, real_engine=true, 13/13 scored, **12 survivors**, 0 errors, evidence_pack 15,136 chars, 0 truncated |

Gate verdicts: best 0.9284 (§4.3 Ablation) · all 10 paper segments kept · cand-13 *Demystifying Instruction Mixing* rejected at **0.212** (fail-closed, not used).

## Answer

InstructDS (A\*STAR, *Instructive Dialogue Summarization with Query Aggregations*, arXiv 2310.10981) generates high-quality query-based dialogue summaries by **synthesizing query–dialogue–summary (QDS) triples in a three-step pipeline, then instruction-tuning a unified model on them** — avoiding expensive, low-diversity human annotation.

**Step 1 — Summary-anchored query generation.** Using the question-generation ability of an LLM (Flan-T5-XL, "model X", trained on Quoref/MC-TACO/CosmosQA), it generates **five candidate queries per instance from the reference summary** (not the raw dialogue), via the template *"Generate an answerable and specific question based on the following context. Context: ${Summary}."* Anchoring on the summary ensures queries are answerable from actual dialogue content.

**Step 2 — Two-stage query filtering (the quality core).**
- **Text-based filtering**: model X acts as a binary classifier — *"Is the question fully answerable from the context without any guessing, yes or no?"* — eliminating **~45%** of generated queries (hallucination-prone "What will / How would" types).
- **Semantic-based filtering**: near-duplicate queries (normalized **BERTScore > 0.65**) are collapsed, keeping only the first — eliminating an **additional ~50%**.
- Measured effect: expert annotation of 100 triples shows quality (both unique *and* correct) rising **from 45% → 75%**.

**Step 3 — Query-based summary generation.** The query-based summary is produced by model X conditioned on **(query + complete summary)** rather than the raw dialogue — extracting from a condensed, structured source is easier and "further guarantees the quality." On average **1.3 QDS triples** are synthesized per dialogue-summary pair.

**Training.** Flan-T5-XL initialization; three instruction categories (general summarization, query-based summarization, length-aware augmentations); input template `###Instruction: {instruction}. ### Input: {dialogue}.`; length control via *"The generated summary should be around {summary length} words long."* QDS triples from SAMSum/DialogSum/TODSum (5k sampled each) + one length augmentation pass → **100k training samples**; **LoRA** with 37.7M trainable parameters in a single unified multi-dataset model. Supporting data-quality work: DialogSum speaker-name preprocessing (Flan-T5-XL name prediction + rule-based filtering + 10-name fallback pool, with the reference summary updated accordingly).

**Why the output is high quality (ablation + evaluation).**
- Augmented QDS triples enhance dialogue understanding and reasoning, transferring to unseen query-based tasks: DREAM accuracy **56.4 → 59.1** without any in-domain data (57.8 multi-choice overall; **65.9** with in-domain data, vs ChatGPT 60.8); more triples → accuracy rising **54 → 58+**. Length augmentation adds controllability (TODSum caveat: templated summaries benefit less).
- InstructDS (3B) surpasses larger SOTA on SAMSum (**ROUGE-1 55.3**, BS 55.5; **58.4** with reference length given vs ChatGPT 40.8) and leads on DialogSum (R-1 47.8) and TODSum (R-1 89.3).
- Subjective Likert (faithfulness/fluency/informativeness/conciseness; 12 volunteers, 792 samples, 4.4 annotators avg): comparable to human-written summaries on fluency, informativeness, conciseness; improved faithfulness; ChatGPT-as-evaluator rates it on-par-or-better than human references on all four dimensions.
- Case studies show InstructDS preserving key facts where BART/Flan-UL2/Alpaca omit or fail them.

*Adjacent shelf items kept by the gate (not InstructDS components, but stored as related summarization work):* tone-biased MMR multi-document summarization (0.759) and cross-document endorsement modeling (0.8087).

## Sources

**Primary — 计算机与人工智能** `kb_id=b1199132-e4d4-4305-8c2e-82dc1753b0ba`, doc `nlp__2310.10981__instructive-dialogue-summarization-with-quer` (all engine-kept survivors):

| Part (doc_id) | Section | Lines | Jev score |
|---|---|---|---|
| part 1 (`f13cf459…`) | Abstract | 9–11 | 0.8495 |
| part 1 (`f13cf459…`) | §1 Introduction | 13–40 | 0.8959 |
| part 1 (`f13cf459…`) | §3.2 Synthesize QDS Triples | 78–96 | 0.9055 |
| part 1 (`f13cf459…`) | §3.3 Model Training | 98–104 | 0.8700 |
| part 2 (`b4f6bb7f…`) | §4.3 Ablation Study | 3–40 | 0.9284 |
| part 2 (`b4f6bb7f…`) | §4.4 Subjective Quality Evaluation | 55–75 | 0.7936 |
| part 3 (`da8bfc26…`) | A.1–A.3 Appendices | 1–28 | 0.5220 |
| part 4 (`bdcbe7a3…`) | Table 7 (prompt templates) | 12–22 | 0.6263 |
| part 4 (`bdcbe7a3…`) | Table 10 (SAMSum QDS example) | 25–40 | 0.7089 |
| part 4 (`bdcbe7a3…`) | Tables 13–17 (case studies) | 40–56 | 0.8128 |

**Auxiliary survivors (same KB):** `nlp__1802.09426__tone-biased-mmr-text-summarization.md` Abstract ¶1–20 (0.7590) · `nlp__2110.07844__modeling-endorsement-for-multi-document-abst (part 1 of 3).md` Abstract ¶8–20 (0.8087).
**Rejected at the gate:** `large-language-models__2312.10793__demystifying-instruction-mixing…` (0.2120 — not used).

## Confidence

**High for the core question.** 10 engine-kept survivors from the primary paper span the entire evidence chain (abstract → method → training → ablation → subjective eval → appendix → templates → case studies), with 8/10 scoring ≥ 0.62 against a strict 0.5 threshold on a real local Laya engine (status=ok, 0 errors, evidence pack complete at 15,136 chars, nothing truncated — no survivor silently dropped). The winning document was read **end-to-end before judging** (all 4 parts, zero unread sections), and the top survivor (§4.3, 0.9284) independently corroborates the pipeline's causal contribution. Two adjacent summarization docs passed the same gate, adding shelf corroboration but not altering the core answer.

## Blind Spots (Cross-Library Perspective)

- **Body-unread in kept shelves: 134 of 145 docs** (all 145 *descriptions* were read; 11 docs were content-touched). Breakdown: 计算机与人工智能 124/131 bodies unread (only the InstructDS paper + 3 auxiliaries read), AI 基础设施 3/3, soul-e2e-tester 4/4, aw-industrial-e2e 1/1, e2e-demo 2/3 unread; e2e-flow 1/1, ZZ×2 2/2 fully checked (verified unrelated).
- **Entirely unscanned shelves: 6 KBs / 226 docs** (自然科学与地球科学 75, 生命科学与医学 53, 工程与能源 39, 经济与社会 24, Novel-PridePrejudice 28, aw-industrial 7) — pruned at L1 on specific, trustworthy descriptions; a cross-domain citation of InstructDS there is unlikely but not impossible.
- **Empty shelves**: Corpus-Chunks800 (0 docs), soul-e2e-20260926-022340 (0 docs).
- **No cross-library corroboration**: only one KB holds the InstructDS paper (4-part single-document evidence base); no independent second treatment was found.
- **Engine caveat**: the Laya checkpoint emitted a runtime warning about invalid temperature entries (confidence for those entries uncalibrated); scores are real and fail-closed, but the borderline survivor (A.1–A.3 at 0.522) sits close to the threshold.