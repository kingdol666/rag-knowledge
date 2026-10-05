Evidence gathered from the primary paper plus appendix. Delivering the five-section report.

## Search Paths

**Mode C — 并行混合双道 (dual-lane parallel hybrid)**, engine `laya` (real, `laya_sdk`), threshold 0.5, `lane_agreement=true`, `top_k_floor=5`, `require_real`.

| Lane | Statistics | Latency |
|---|---|---|
| **Vector** (semantic) | 10 raw hits → 9 dedup docs | 21.1 s |
| **Catalog** (description-tree) | 14 shelves scanned (2 excluded), **371 descriptions** scanned, 120 docs peek-peeked (0 empty), 7 description-overlap, 2 stem-completion, 12 full reads | 16.5 s + 34.5 s peek |
| **Merge** | **140 unique docs** = 1 both-lane ∧ 8 vector-only ∧ 131 catalog-only | — |
| **Reread** | 8 queued / 6 re-read, 0 errors | — |

**Laya judge verdict (判决):** `global_best=0.937`, `relative_cut=0.837`, floor applied → **24 docs kept** out of 140 merged (`kept_total=24`). Total wall clock **371.1 s**.

## Answer

**InstructDS** (*Instructive Dialogue Summarization with Query Aggregations*, arXiv 2310.10981 — Bin Wang, Zhengyuan Liu, Nancy F. Chen; I2R A\*STAR Singapore / CNRS@CREATE) is an instruction-following dialogue summarization model. Its central problem is **data scarcity**: query-based dialogue summarization supervision barely exists (prior work QMSum has only 232 meeting samples). Its answer is a **three-step LLM synthesis pipeline that manufactures high-quality query–dialogue–summary (QDS) triples from ordinary dialogue-summary pairs** — explicitly inspired by Self-Instruct.

**Step 1 — Summary-anchored query generation.** Rather than generating questions from the raw dialogue, the pipeline anchors on the **reference summary**, which is a condensed, structured rendition of the dialogue. It uses **Flan-T5-XL** ("model X", already trained on Quoref, MC-TACO, CosmosQA question-generation datasets) to emit **five candidate queries per instance**. Prompt: *"Generate an answerable and specific question based on the following context. Context: ${Summary}"*.

**Step 2 — Query filtering (validity + diversity).** Two complementary filters:
- **Text-based filtering** — model X reused as a binary classifier for answerability ("Can we get an answer from the context, yes or no?"). Removes **~45%** of queries judged unanswerable without hallucination (typically "What will…", "How would…" forms).
- **Semantic-based filtering** — near-duplicate queries for the same dialogue-summary pair are collapsed using **normalized BERTScore** at a **>0.65 similarity threshold** (keep first only). Removes a **further ~50%**, guaranteeing question diversity.

**Step 3 — Query-based summary generation.** The query plus the **complete summary** (not the dialogue) is fed back into model X to synthesize the query-conditioned summary. The paper's key rationale: generating a query-focused summary *from the condensed summary* is markedly easier for the model than from the dialogue, and "further guarantees the quality."

**Quality gate (empirical).** An expert annotated 100 triples: **"both unique and correct" rose 45% → 75%** after filtering; answerability 76% → 94%, diversity 63% → 90%, correctness 71% → 83%. Average yield: **1.3 QDS triples per dialogue-summary pair** (SAMSum 18,245; DialogSum 18,600; TODSum 8,705).

**Training.** Flan-T5-XL initialization, **LoRA** (37.7M trainable of 3B params), unified across three datasets. Instructions are three-fold: general summarization, query-based summarization, and **length-aware augmentations** ("The generated summary should be around {summary length} words long"), with input template `###Instruction: {instruction}. ### Input: {dialogue}.` → **100k training samples**. Results: new SOTA on SAMSum (ROUGE-1 **55.3** / ROUGE-2 **31.3** / BS 55.5), DialogSum R-1 47.8, TODSum R-1 89.3; on DREAM (zero-shot, never trained on it) 57.8%, rising to 65.9% with in-domain data — surpassing ChatGPT — demonstrating transferability of the synthesized triples.

## Sources

| Document | KB | Lane | Score |
|---|---|---|---|
| `nlp__2310.10981__instructive-dialogue-summarization-with-quer (part 1 of 4).md` | 计算机与人工智能 | catalog | judge **0.9368** ← core method (§3.2, Tables 1–3) |
| `nlp__2310.10981__… (part 2 of 4).md` | 计算机与人工智能 | **both** | judge 0.9182 · vector **0.7759** ← ablation, QDS contribution |
| `nlp__2310.10981__… (part 4 of 4).md` | 计算机与人工智能 | catalog | judge 0.6803 ← **prompt templates (Table 7)**, QDS examples |
| `nlp__2310.10981__… (part 3 of 4).md` | 计算机与人工智能 | catalog | judge 0.6047 ← ROUGE/DREAM eval protocol |

*(Parts 1, 3, 4 retrieved in the evidence pack / confirmed via `kb_doc_read`.)* Non-InstructDS survivors carried incoherently high judge scores (quantum-physics 0.9317, medical-imaging 0.9169, math 0.9138) and were not used.

## Confidence

**High** on the three-step synthesis mechanism, the two filter types and their thresholds, the length-aware training recipe, and the Flan-T5-XL + LoRA configuration — all read directly from the paper's own §3.2/§3.3 and appendix Table 7. **Medium-high** on exact percentages (45% / 50% / 45%→75%) as they are self-reported. **Medium** on model-selection rationale, which the paper states qualitatively.

## Blind Spots (Cross-Library Perspective)

1. **Vector-lane miss:** the semantic lane surfaced **only part 2** of the paper; parts 1, 3, 4 were reached **solely via the catalog lane** (description overlap). A pure-vector search would have returned the ablation section without the method section — this query validates the dual-lane design.
2. **A chunk-level duplicate exists and was unscanned:** `Corpus-Chunks800/nlp__2310.10981__instructive-dialogue-summarization-with-quer__k22.md` (KB `0942f1a6…`) was flagged `empty_content`. That KB is not covered by the description catalog, so any distinct content there is invisible to this search.
3. **Judge precision limit:** 20 of 24 survivors are off-topic (quantum chemistry, biomedical segmentation, moment optimization, TraceLens ops notes) scoring 0.85–0.93 — the Laya judge appears to grade *summary quality* rather than *answer-fit*; also two duplicated path pairs (medical-imaging part 1, math part 6) entered via vector+catalog with differing path separators (`/` vs `\`).
4. **Cross-library perspective:** relevant material outside 计算机与人工智能 was **not** found anywhere else in the 14 scanned shelves — this is a single-paper topic. The nearest genuine cross-links would be the instruction-tuning neighbours already in the same KB (`demystifying-instruction-mixing`, `vision-flan`, `bert`) but none scored above 0.55 and all were correctly rejected.
5. **Appendix figures (Fig. 2 framework diagram, Tables 10–12 full renderings) are only partially legible** in the markdown — diagram-level architecture detail is a residual gap.