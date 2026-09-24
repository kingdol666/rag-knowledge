# Long-Text Retrieval Test — *Pride and Prejudice* (Project Gutenberg #1342)

**Date:** 2026-09-24 · **Platform:** RAG Knowledge (backend `http://localhost:8771`, web `http://localhost:6789`)
**Channel:** real `kb-mcp` stdio client (`uv run --directory kb-mcp python server.py`) for all KB ops; real `POST /api/claude/chat` for every answer.
All numbers below come from tool outputs actually produced during this run; raw artifacts are under
`benchmark-suite/results/novel_test/` and `benchmark-suite/results/runs/run-20260924T061730Z-0968033/`.

---

## 1. Novel, source, and ingestion

| Item | Value |
|---|---|
| Title | *Pride and Prejudice* (Jane Austen) |
| Source URL (used) | `https://www.gutenberg.org/cache/epub/1342/pg1342.txt` (first URL; returned a valid file) |
| Local file | `benchmark-suite/data/novels/pride_and_prejudice.txt` |
| Size | **772,386 bytes**; decoded as **UTF-8**, **763,082 chars** (raw); **748,167 chars** after universal-newline normalisation |
| Header check | starts with `The Project Gutenberg eBook of Pride and Prejudice`; ends with the Gutenberg licence text ✅ |

First 300 chars (verbatim):
```
The Project Gutenberg eBook of Pride and Prejudice
    
This eBook is for the use of anyone anywhere in the United States and
most other parts of the world at no cost and with almost no restrictions
whatsoever. You may copy it, give it away or re-use it under the terms
of the Project Gutenberg 
```

### Ingestion (ingest skill A0–A9)
- **KB created:** `Novel-PridePrejudice`, **kb_id = `b4c48237-6937-440a-9696-cc1e66bed5c1`** (`kb_create`).
- **A2.5 split gate:** 748,167 chars > `ingestion.large_doc.max_chars = 30000` (repo-root `config.yml`) → ran
  `scripts/split_large_doc.py … --keep-source --out-dir data/novels/parts` → **26 parts** (`split: true`,
  `source_deleted: false` because `--keep-source`). Original txt kept for the human read.
- **A5 store:** `kb_doc_create` per part with a per-part description + tags `["Pride and Prejudice","Jane Austen","English novel","classical literature"]` → **26/26 ok**.
  The platform then auto-split two parts that were still >30,000 chars (part 1 = 30,017 and part 22 = 30,027) into
  `(part 1 of 2)`/`(part 2 of 2)` siblings → **28 documents in the KB**.
- **A6 index:** `kb_batch_index(kb_id, all 28 doc_paths, force=True)` → `success: true, total_indexed: 28, errors: 0, skipped: 0`.
- **A6-V verification:** `kb_search_stats` → collection **`kb_b4c48237-6937-440a-9696-cc1e66bed5c1`** (correct UUID), **chunk_count = 1679** (≥1 ✅).
- **Search probe:** `kb_search_vector` (novel KB, top_k 5, thr 0.35):
  - `"Pemberley"` → 5 hits, top 0.5249 (`part 16`), also `part 4`, `part 17`, `part 25` — spread across the book.
  - `"Wickham"` → 5 hits, top 0.5385 (`part 21`), also `part 14`, `part 7`, `part 18`.
  - `"Darcy first proposal rejected"` → 5 hits, top 0.5143 (`part 22 (part 1 of 2)`), also `part 14`, `part 12`, `part 2`, `part 7`.
  → the document is genuinely searchable and hits are not confined to the opening.

**Chapter→part map** (derived from the stored parts): part 2 = Ch I–IV … part 13 = Ch XXXIII–XXXV (first proposal + letter) … part 24 = Ch LVIII–LIX (second proposal) … part 26 = Gutenberg licence. (Part 1 = front matter/TOC.)

---

## 2. The long-arc question + reference answer

### Question (used verbatim in both (a) and (b))
> Trace how Elizabeth Bennet's opinion of Mr. Darcy changes across the whole novel, and identify the specific scenes that cause each change — from the Meryton assembly, through Wickham's account and the Hunsford proposal and Darcy's letter, to the Pemberley visit and the Lydia elopement crisis. In what ways does Darcy himself change, and how does each acknowledge their earlier error by the end?

### Reference answer — key beats (from my own reading of the local file)
1. **Meryton assembly (Ch 3).** Darcy refuses to dance and says of Elizabeth, verbatim: *"She is tolerable: but not handsome enough to tempt me; and I am in no humour at present to give consequence to young ladies who are slighted by other men."* Elizabeth "remained with no very cordial feelings towards him." (prejudice planted)
2. **Wickham's account (Ch 15–16).** Wickham claims the living intended for him was withheld by Darcy; Elizabeth believes him and her prejudice hardens. (false impression planted)
3. **Hunsford, first proposal (Ch 34).** *"In vain have I struggled. It will not do. My feelings will not be repressed."* — but Darcy dwells on "her inferiority", "the degradation", the "family obstacles". Elizabeth refuses: *"I have every reason in the world to think ill of you … the man who has been the means of ruining, perhaps for ever, the happiness of a most beloved sister."*
4. **Darcy's letter (Ch 35).** Reveals Wickham's dissipation and his attempt to elope with Georgiana (then 15) for her £30,000; *"Mr. Wickham's chief object was unquestionably my sister's fortune."* Elizabeth's prejudice dissolves.
5. **Elizabeth's self-reproach (Ch 36).** *"Till this moment, I never knew myself."*
6. **Pemberley (Ch 43–44).** Housekeeper Mrs. Reynolds: *"He is the best landlord, and the best master … that ever lived"*; *"I have never had a cross word from him in my life."* Elizabeth: "In what an amiable light does this place him!" (feelings shift toward love)
7. **Lydia's elopement (Ch 46–52).** Darcy secretly finds Wickham and Lydia and settles everything; Ch 52: *"Darcy did everything; made up the match, gave the money, paid the fellow's debts, and got him his commission!"* Elizabeth's gratitude/love confirmed; Wickham's true character now known.
8. **Second proposal (Ch 58).** Darcy: *"My affections and wishes are unchanged."* Both acknowledge error — Darcy: *"Your reproof, so well applied, I shall never forget: 'Had you behaved in a more gentlemanlike manner.' … how they have tortured me"*; Elizabeth: her "sentiments had undergone so material a change".
9. **Darcy's own arc.** Proud/forbidding → self-critical and generous ("It was unpardonable. I cannot think of it without abhorrence").

---

## 3. Retrieval trace — protocol (a)

### Phase 0 — query prep
- Intent: **comparison/synthesis** (not factual). Core entities: Elizabeth, Darcy, Wickham, Pemberley, Hunsford, Lydia.
- Rewrite (declarative, fed to retrieval):
  > *"Elizabeth Bennet's changing judgment of Mr Darcy across Pride and Prejudice: his insult at the Meryton assembly; Wickham's false account of the living; the first proposal at Hunsford and Darcy's letter revealing Wickham's true character; the Pemberley visit and the housekeeper's praise; Darcy secretly resolving Lydia's elopement; the second proposal and mutual acknowledgement of past error."*
- Multi-concept split → **7 per-beat sub-queries** (S1…S7), retrieved in parallel.

### Phase 1 — vector first
`kb_search_vector(rewrite, kb_id="", top_k=10, score_threshold=0.35, balance_kbs=True)` → 10 hits (whole library);
same on the novel KB → 10 hits. Per-beat sub-queries on the novel KB → 5 hits each.
Candidate docs after document-level dedup (novel KB + cross-KB noise), top by score:

```
0.7151 part 22 (LIII–LV)      0.6869 part 25 (LX–LXI)    0.6385 part 16 (XLII–XLIII)
0.7093 part 11 (XXVII–XXIX)   0.6868 part 18 (XLV–XLVI)  0.6084 part 20 (XLIX–L)
0.6992 part 24 (LVIII–LIX)    0.6861 part 21 (LI–LII)    0.6075 part 12 (XXX–XXXII)
0.6953 part 1 (front matter)  0.6631 part 17 (XLIV)      0.6073 part 15 (XXXVIII–XLI)
0.6950 part 3 (V–VII)         0.6500 part 2 (I–IV)       0.5951 part 14 (XXXVI–XXXVII)
0.6938 part 6 (XV–XVI)        0.6385 part 16             0.5168 genomics paper (noise)
0.6899 part 7 (XVII–XVIII)                               0.5046 LLM paper, 0.4549 econ, 0.4518 ocean, …
```
Cross-KB noise (genomics/LLM/economics/oceanography/maths papers, scores 0.13–0.52) was retrieved by the whole-library search and is discarded by the gate.

### Phase 1c — content-match gate (0–8: topic 0–3 / scenario 0–3 / evidence 0–2)
Scored on **chunk text ∪ `kb_doc_read` head** (long-doc provision). Because the question is a **whole-arc synthesis**, a single part covers at most one beat → scenario ≤1 for every part.

| Part | Chapters | Key beat present | Topic | Scenario | Evidence | **Total** |
|---|---|---|---|---|---|---|
| 2 | I–IV | Meryton assembly insult (verbatim) | 3 | 1 | 2 | **6** |
| 6 | XV–XVI | Wickham's account | 3 | 1 | 2 | **6** |
| 14 | XXXVI–XXXVII | letter aftermath + "never knew myself" | 3 | 1 | 2 | **6** |
| 15 | XXXVIII–XLI | Elizabeth tells Jane | 3 | 1 | 2 | **6** |
| 17 | XLIV | Pemberley housekeeper | 3 | 1 | 2 | **6** |
| 18 | XLV–XLVI | Lydia elopement news | 3 | 1 | 2 | **6** |
| 21 | LI–LII | Mrs. Gardiner's letter (Darcy's role) | 3 | 1 | 2 | **6** |
| 24 | LVIII–LIX | second proposal + mutual reproof | 3 | 1 | 2 | **6** |
| 25 | LX–LXI | finale summary | 3 | 1 | 2 | **6** |
| 3,5,7,11,12,16,20,22 | — | ambient/foreshadowing | 3 | 1 | 1 | **5** |
| non-novel papers | — | none | 0 | 0 | 0 | **0 (discard)** |

**Gate verdict:** best single-part content score = **6/8** → meets the skill's ≥6 fast-exit bar. **I nonetheless executed Phase 2**, because for a whole-arc question a single part at 6 produces a one-beat answer — the exact long-text failure mode. (Under a stricter reading where a single beat cannot be "directly quotable evidence *for the arc*", evidence=1 and the best score is 5, which also triggers Phase 2. Both readings were considered; see §6.)

### ⭐ The recall miss
**Part 13 (Ch XXXIII–XXXV = the first proposal + Darcy's letter) never appeared in any Phase-1 or Phase-2 result**, despite being the pivotal beat. Verification:
- Part 13 **is indexed**: a near-verbatim probe `"In vain have I struggled. It will not do. My feelings will not be repressed"` → top hit **0.7418, `part 13` chunk 32**; `"I have every reason in the world to think ill of you"` → **0.6726, `part 13` chunk 40**.
- But the *paraphrased* S3 query (`"Darcy's first proposal to Elizabeth at Hunsford and her refusal accusing him over Jane and Wickham"`) put part 12 / part 22 / part 14 / part 6 / part 24 in its top-5 — **not part 13**.

### Phase 2 — librarian fallback (executed)
- `kb_list(lightweight=True)` → 10 KBs (catalog); `kb_get_documents(lightweight=True, novel KB)` → 28 docs.
- `kb_search_two_stage(rewrite, novel KB, stage1_top_k=20, stage2_top_k=5, enable_graph_expansion=True, thr 0.30)` → top-5 = part 22 / part 11 / part 24 / part 1 / part 6 — **same as Phase 1; still no part 13**.
- `kb_tags_list` + `kb_doc_get_by_tag("Pride and Prejudice")` → **26 documents** (tag applied). `kb_doc_get_by_tag("Jane Austen")` → **0** (tag dropped by the normaliser).
- Part-aware grouping applied (all `(part k of N)` siblings = one logical book).

### Evidence assembled for (a)
To answer the whole-arc question I had to reach past the natural-language miss, so the evidence pack was built by
**10 targeted KB retrievals** (one near-verbatim probe per beat) — each a real `kb_search_vector` call. Verbatim chunks
were pulled for: assembly insult (part 2 c45), Wickham (part 7 c36 — *wrong passage*), first proposal (part 13 c32),
refusal (part 13 c40), letter/Georgiana (part 14 c27), "never knew myself" (part 14 c52), Pemberley housekeeper (part 17 c3),
Lydia news (part 18 c52), "Darcy did everything" (part 25 c0), second proposal (part 24 c26). **Pack = 6,027 chars.**
`answer_closed_book(question, evidence)` → answer (a) below.

---

## 4. Verbatim answers

### (a) Skill protocol + `answer_closed_book`  — artifacts: `results/novel_test/answer_a.json`, `evidence_pack.txt`, `retrieval_trace.json`
> The evidence traces the arc but only partially and out of order. B1 (Meryton, part 2, chunk 45) shows the insulted first impression: Darcy coldly calls Elizabeth merely "tolerable." B2 (part 7, chunk 36) shows Darcy's guarded remark on Wickham's "retaining" friends, which Elizabeth answers with pointed reproach, marking her half-formed judgment against him. B3 (part 13, chunk 32) is the Hunsford proposal — "In vain have I struggled... how ardently I admire and love you" — and B4 (part 13, chunk 40) her refusal, charging him with ruining her sister's happiness. B5 (part 14, chunk 27) is Darcy's letter exposing Wickham's real conduct toward Georgiana, and B6 (part 14, chunk 52) shows her self-reproach: "Till this moment, I never knew myself." B7 (part 17, chunk 3) is the Pemberley housekeeper's testimony that he is "the best landlord, and the best master," which reframes him as amiable; B8 (part 18, chunk 52) is Lydia's elopement news and Elizabeth's cry that she might have prevented it; B9 (part 25, chunk 0) reveals Darcy secretly settled the affair; B10 (part 24, chunk 26) has Darcy confessing his Hunsford words "tortured me."
>
> However, the evidence is insufficient to answer the question fully: the chunks are excerpts that cut off mid-sentence, several key scenes are only fragments (e.g., B4, B6, B9 end abruptly), and the requested full arc — including how Darcy changes and how *each* acknowledges their earlier error by the end — is not completely documented here. In particular, no chunk supplies Elizabeth's final explicit acknowledgement of error or a complete picture of Darcy's transformation beyond these fragments, so the trajectory cannot be fully traced from this evidence alone.
>
> Sources used: pride_and_prejudice (part 2 of 26).md, chunk 45; (part 7 of 26).md, chunk 36; (part 13 of 26).md, chunks 32 and 40; (part 14 of 26).md, chunks 27 and 52; (part 17 of 26).md, chunk 3; (part 18 of 26).md, chunk 52; (part 25 of 26).md, chunk 0; (part 24 of 26).md, chunk 26.

### (b) Platform full flow — `python exp.py "<question>" --baselines bm25,vector`
- **run id = `run-20260924T061730Z-0968033`** (git `0968033`, config_hash `9fb259c0cf2b6dea`, prompt `v3-neutral`).
- Artifacts: `results/runs/run-20260924T061730Z-0968033/{COMPARE.md,COMPARE.html,SUMMARY.md,monitor.json,track_a2_Q1.json,track_bm25_Q1.json,track_vector_Q1.json}`.
- Methods: `a2` (platform QDCVR, kb tools only), `bm25`, `vector`.

**a2 answer (verbatim, abridged only in whitespace):**
> I have sufficient retrieved evidence. Here is my answer.
>
> **Answer**
>
> Elizabeth's opinion of Darcy moves through five documented stages. At the **Meryton assembly** his character "was decided. He was the proudest, most disagreeable man in the world, and everybody hoped that he would never come there again" (part 2, chunk 41). **Wickham's account** hardens this — Elizabeth tells him she thinks Darcy "very disagreeable," and later calls him "that abominable Mr. Darcy," blaming him for Wickham's misfortunes (part 6, chunk 41; part 10, chunk 53). At **Hunsford** she refuses him outright: "You are mistaken, Mr. Darcy, if you suppose that the mode of your declaration affected me in any other way than as it spared me the concern which I might have felt in refusing you, had you behaved in a more gentlemanlike manner" (part 13, chunk 48). **Darcy's letter** (part 14, chunk 31) produces the reversal: she "grew absolutely ashamed of herself. Of neither Darcy nor Wickham could she think, without feeling that she had been blind, partial, prejudiced, absurd — 'How despicably have I acted!'" (part 14, chunk 50). At **Pemberley**, the housekeeper's testimony and Darcy's own altered manner work on her — "at that moment she felt that to be mistress of Pemberley might be something!" (part 16, chunk 54), and she later calls Wickham's stories "lies about the whole Pemberley family" (part 19, chunk 16). During the **Lydia crisis** Darcy acts secretly, and Elizabeth tells her father "what Mr. Darcy had voluntarily done for Lydia," moving Mr. Bennet to say "he deserves you. I could not have parted with you, my Lizzy, to anyone less worthy" (part 24, chunk 66).
>
> Darcy's change is stated by himself: his original object in meeting her again was "to show you, by every civility in my power, that I was not so mean as to resent the past; and I hoped to obtain your forgiveness, to lessen your ill opinion, by letting you see that your reproofs had been attended to" (part 24, chunk 36). Elizabeth acknowledges her error as prejudice and blindness (part 14, chunk 50); Darcy acknowledges his as pride and resentfulness, and courts her again only after she has been undeceived about Wickham (part 24, chunks 17, 66).
>
> **Sources used:** `Novel-PridePrejudice/pride_and_prejudice (part 2 of 26).md` (chunk 41); `part 6` (chunk 41); `part 7` (chunks 25–26, 36); `part 10` (chunk 53); `part 13` (chunk 48); `part 14` (chunks 31, 50); `part 15` (chunks 46–47, 54–55); `part 16` (chunks 1, 54, 62); `part 17` (chunk 52); `part 18` (chunk 20); `part 19` (chunk 16); `part 21` (chunk 28); `part 24` (chunks 17, 36, 39, 66); `part 25` (chunks 8, 21, 33–34, 39).

**Baselines (bm25 / vector) — both abstained:**
> *bm25:* "The evidence is insufficient. The three retrieved documents are unrelated to the question: they concern infrastructure investment and economic growth in China (1609.00415), ECB … monetary policy (2011.14424), and large language models encoding clinical knowledge (2212.13138)."
> *vector:* "The evidence is insufficient. No retrieved chunk discusses *Pride and Prejudice* … The provided chunks are from unrelated papers (e.g., [2005.14165] …)."
>
> **Reason:** `experiments/baselines.py` hardwires retrieval to `VECTOR_KB = "Corpus-Chunks800"` / `data/corpus_md` (the paper corpus). The novel KB is invisible to these baselines, so they are **not valid comparators for this task** — this is a configuration fact, not a novel-retrieval failure.

**Run table (from `SUMMARY.md`):** a2 = 111.5 s, 14 tool calls, 2,250 out-tokens, $0.9537; bm25 = 12.7 s; vector = 16.2 s; 6/6 self-checks passed.
The a2 agent issued **8 `kb_search_vector` calls with varied sub-queries** (incl. *"Darcy's letter to Elizabeth Hunsford proposal"*) and then **`kb_doc_read` on part 13** — its multi-query + read strategy is why it reached part 13, which my single rewrite + fixed 7 sub-queries did not.

---

## 5. Quality assessment

Per-criterion verdicts (judged against my own reading):

| Criterion | (a) skill protocol + closed-book | (b) platform a2 |
|---|---|---|
| Answers the long-arc question (not one scene)? | **Partial** — walks all beats but frames itself as "partial / out of order" | **Yes** — five explicit stages, beginning→end |
| Turning points correct & complete? | Mostly correct beats, but B2 hit the *wrong* passage (Darcy's "retaining friends" line, part 7, not Wickham's account) and it omits the **second proposal** scene | Correct and better anchored: Meryton → Wickham → Hunsford refusal → letter → Pemberley → Lydia → Darcy's own admission; still light on the literal second-proposal scene |
| Cites specific sources (part/file)? | **Yes** — every beat cites part + chunk | **Yes** — 14 parts cited (2,6,7,10,13,14,15,16,17,18,19,21,24,25) |
| Fabrication / prior-knowledge leakage? | **None** — quotes match the retrieved chunks; explicitly refuses to over-claim | **None** — quotes match the novel text (spot-checked against the local file) |
| Retrieval spread across the book? | **Spread** (parts 2–25) but **missed part 13** (proposal+letter) in the natural-language pass | **Spread, including part 13** (via multi-query + explicit doc-read) |
| Chunk-window bias? | **Present** — paraphrased queries cluster on the semantically "loud" passages (balls, dancing, Pemberley) and skip the pivotal Hunsford chapters | **Mitigated** by iterative sub-queries + `kb_doc_read` |

**What worked**
- Ingestion at scale: 748k-char novel → 26 script-split parts → 28 stored docs → 1,679 chunks in the correct collection, 0 errors; probes hit across the whole book.
- The skill's long-document provisions (chunk ∪ read, part-aware grouping) let the gate recognise on-topic parts despite head windows.
- Honesty: both (a) and the baselines refused to fabricate; the closed-book channel correctly declined to answer beyond its evidence.
- The platform's `a2` agent produced a genuinely long-arc, well-cited answer by issuing multiple targeted queries and reading the hit part.

**What failed**
- **Single-query recall of a pivotal beat.** Neither `kb_search_vector` (rewrite), the 7 sub-queries, nor `kb_search_two_stage` surfaced **part 13 (Ch 33–35: first proposal + letter)** — the most important turning point — even though it is indexed (0.74 on a near-verbatim probe). Paraphrased semantics were not enough.
- **The 0–8 gate cannot express "no single chunk answers a whole-book question."** The best single part scores 6/8 (on-topic + quotable) and meets the fast-exit bar, which would have produced a one-beat answer.
- **Baselines are mis-wired for this task** (`Corpus-Chunks800`), so bm25/vector abstained for a non-retrieval reason.

---

## 6. Honest limitations
- **I did not read all 748k chars line-by-line.** I read the ~10 pivotal chapters in full (III, XXXIV, XXXV, XXXVI, XLIII, XLIV, LII, LVIII) and used the rest for the chapter→part map; the reference answer is grounded in those verbatim reads plus the novel's well-known structure. Chapters I, II, and the minor middle chapters were not read in full — my reference answer does not depend on them, but I cannot claim a complete page-by-page read.
- **Part 13 miss is the headline finding**, but note it is a *paraphrase-recall* miss, not an indexing miss (verified: exact-phrase probes return it at 0.74). It is reproducible in this run; whether it generalises is untested.
- **(a) is not a pure single-shot result.** Because the natural-language pass missed part 13, I assembled the evidence pack with **near-verbatim per-beat probes** (10 extra `kb_search_vector` calls). So (a)'s coverage reflects *known-item* retrieval, not blind recall — the honest blind-recall picture is the Phase-1 trace in §3, which missed part 13.
- **Gate scoring is a judgment call** at the 5/6 boundary (see §3). I documented both readings; the phase decision (run Phase 2) is defensible under either.
- **(b)'s baselines are not comparable** (wrong KB); only the `a2` arm is meaningful for the novel. I did not re-point the baselines at the novel KB.
- **`kb_doc_get_by_tag("Jane Austen")` returned 0** — one of the two tags I applied is not retrievable by tag (normaliser/graph lag). Reported, not fixed.
- **Cross-KB noise** (papers scoring 0.13–0.52) was returned by whole-library search; `balance_kbs=True` did not suppress it. It was correctly discarded by the gate, but it inflates candidate lists.
- One sub-query (B2) retrieved a *nearby but wrong* passage for Wickham's account; the evidence pack therefore mislabels that beat (part 7 c36 instead of part 6). Flagged in §5.

---

## 7. Reproduction
```bash
cd benchmark-suite
# 1) novel + split
python .claude/skills/knowledgebase-ingest/scripts/split_large_doc.py \
  data/novels/pride_and_prejudice.txt --keep-source --out-dir data/novels/parts   # (run from repo root)
# 2) ingest / index / retrieve / answer (real MCP + chat API)
python results/novel_test/step_ingest.py
python results/novel_test/step_upload.py
python results/novel_test/step_index.py
python results/novel_test/step_retrieve.py
python results/novel_test/step_answer.py
# 3) platform full flow
python exp.py "<question>" --baselines bm25,vector     # run-20260924T061730Z-0968033
```
