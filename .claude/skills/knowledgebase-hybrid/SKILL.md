---
name: knowledgebase-hybrid
description: "Serial hybrid retrieval driven entirely by MCP tool calls (no orchestration script): run the vector lane FIRST (kb_search_vector wide net, hard threshold, doc-level dedup, refs only), THEN the content/catalog lane (kb_list shelf selection, every document description, description-overlap ranking with trust check, budgeted reads), deduplicate the merged doc ids by (kb_id, doc_path) with lane provenance, send every merged document's segments to the REAL Laya engine gate (kb_laya_judge MCP tool — works in every harness, including shell-less chat agents), then kb_doc_read the FULL content of every relevant kept doc and answer with a knowledge-enhanced, cited synthesis. Use for 混合检索, 串行混合, serial hybrid, vector then catalog, hybrid retrieval, dual-lane retrieval, dedup retrieval, when vector recall alone is not trusted and the complete-recall scan alone is too slow."
---
## ⭐ Related Skills

- **Vector + Jev-gate lane** → `skill://knowledgebase-search` — lane A alone (fast semantic proposal + engine verify gate)
- **Complete-recall lane** → `skill://knowledgebase-librarian` — lane B alone (catalog/read/Jev, exhaustive; owns `jev_filter.py` and the Laya decision layer this skill shares)
- Document ingest → `skill://knowledgebase-ingest` — produces the descriptions the content lane relies on

## When to use this skill

| Situation | Use hybrid? |
|---|---|
| You want the **speed of vector recall** and the **coverage of the catalog scan** together | **Yes** — this skill's whole point |
| Vector search alone may miss paraphrased/mis-described evidence | **Yes** — the content lane is vector-independent |
| You only know the KB and ask a simple fact question | No — `knowledgebase-search` alone is cheaper |
| An explicit "read everything" request with no latency constraint | No — pure `knowledgebase-librarian` |

## The serial flow (S0–S6) — do it IN ORDER, one phase at a time

The flow is **serial by design**: the vector lane completes before the content lane starts. Every phase is executed with MCP tool calls — **no orchestration script**. `scripts/hybrid_search.py` is legacy (kept only for offline experiments); never run it in this flow.

```
S0  查询整容    extract subject × attribute × constraints; write bilingual keywords
                (descriptions and the query often live in different languages)
S1  向量车道    kb_search_vector(top_k=30, threshold=0.35, balance_kbs=true)
                → hard threshold → dedup by (kb_id, doc_path) → 候选 A
                refs only — do NOT read content yet
S2  内容车道    kb_list → select shelves → kb_get_documents(lightweight) for EVERY doc
                description → description-overlap ranking (+ L3 trust check) →
                重叠命中记录为引用（不整读正文）→ 候选 B（refs）
S3  去重合并    merge A ∪ B keyed on (kb_id, normalized doc_path)
                lane = both | vector | catalog; a both-doc is kept ONCE
                (catalog content + vector score); vector-only docs have no content yet
S4  LAYA 判卷   pass ALL merged candidates as REFERENCES in ONE call — the server
                fetches every body itself (raw text never enters context):
                kb_laya_judge(query, documents=[{kb_id, doc_path}, …] refs,
                criterion="evidence", threshold=0.5)
                → every ≥threshold segment survives (fail-closed); doc-level
                relative cut best−0.10 + top-5 floor gives the relevant-doc set
S5  证据包      evidence_pack = the merged kept content — the ONE full-content
                return; kb_doc_read a kept doc only to verify a specific quote
S6  增强回答    synthesize with citations: doc_path + lane provenance + engine score;
                zero kept docs = honest engine-level not-found
```

**Why serial:** the vector lane proposes cheap refs in seconds; the content lane then spends its read budget only where descriptions score, and the vector-only docs need just one reread each before judging. Running the lanes in parallel saves seconds but doubles connection bookkeeping and hides duplicate reads — measured 2026-09-28: the serial merge keeps both lanes' recall with zero duplicate reads.

## Phase notes

**S1 vector lane.** `kb_search_vector` with a wide net (`top_k=30`, `score_threshold=0.35`, `balance_kbs=true`). Threshold applies to chunk scores; dedup to document level immediately (best chunk score becomes the doc score). Record `(kb_id, doc_path, vector_score)` — no reads in this phase.

**S2 content lane.** Full catalog discipline from the librarian lane applies: never guess shelves by name (`kb_list` first), read every description, rank by description-overlap with the S0 bilingual keywords, respect the L3 trust check (boilerplate/content-free descriptions get a 600-char head read and stay candidates). Read the overlap hits (budget ≈15 docs; `(part k of N)` siblings of any hit come along — stem completion). Zero-overlap docs are NOT silently dropped: they are reported and (budget permitting) head-peeked — the engine, not description vocabulary, decides their fate.

**S3 merge & dedup.** Identity is `(kb_id, normalized doc_path)` — backslashes and slashes are the same path. A document found by both lanes is kept **once** with `lane=both` (catalog signal + vector score, both provenance values retained). Report the counts: `from_both / from_vector_only / from_catalog_only`. Neither lane's hits need their bodies in context — S4 fetches server-side.

**S4 real engine gate — reference mode.** Pass ALL merged candidates as refs in one call (the judge fetches each body itself):

```
kb_laya_judge(query, documents_json, criterion="evidence", threshold=0.5)
   documents_json = [{"kb_id", "doc_path", "name", "description", "content"}, ...]
```

The tool segments every document structure-aware (headings/paragraphs/lists/tables/sentences) and scores EVERY segment with the real local Laya (GPU, fail-closed — missing model/score rejects, never an implicit pass). It returns `{status, real_engine, criterion, threshold, candidate_count, scored_count, survivors[] (text+score+provenance), evidence_pack, errors[]}`.

Derive the relevant-doc set: doc best-score ≥ `global_best − 0.10` **or** top-5 doc (relative cut + floor — the local Laya distribution on prose is top-heavy, measured median ≈0.88; `abs_kept`/cut are in the verdict for audit). Shell-capable harnesses may equivalently run `knowledgebase-librarian/scripts/jev_filter.py` — same engine, same contract.

**S5 full reads.** The judge works on the content you supplied; if any kept doc was truncated at 20k chars, paginate `kb_doc_read(offset/limit)` until the full readable body is covered. The answer must draw on complete content, not heads.

**S6 answer.** Synthesize from ALL kept docs. The result must include: `Search Paths` (S1 hits/dedup, S2 shelves/descriptions/reads, S3 merge counts, S4 engine/backend/criterion/threshold/kept), `Answer` with citations (`doc_path` + lane + engine score), `Confidence` grounded in coverage, and `Blind Spots` (unscanned docs, failed phases — partial is labelled partial). Zero kept docs after the gate = honest engine-level not-found; never fabricate.

## ⚠️ NEVER list

| ❌ Don't | Why | ✅ Do instead |
|---|---|---|
| Run `hybrid_search.py` / parallel-thread scripts in this flow | Serial MCP flow is the design; the script hides the phases | Execute S1→S6 yourself with MCP tool calls |
| Start the content lane before the vector lane finishes | Serial contract: S1 refs gate S3's merge | Complete S1 first |
| Dedup on `doc_path` alone | Same path can exist in two KBs | Key on `(kb_id, doc_path)` |
| Read a `lane=both` document twice | Wasted I/O, duplicate work | Merge first; reread only vector-only docs |
| Judge a document that never got content | Description ≠ evidence | Reread in S4 first; `unscanned` + honest report otherwise |
| Keep docs because a lane found them | Lanes propose, the engine disposes | Every segment through `kb_laya_judge` (real engine) |
| Hide a failed or skipped phase | Partial coverage looks like full coverage | Report counts and blind spots per phase |
| Answer from unscored text or re-score kept docs | The engine verdict is final | Answer from ALL kept docs; zero kept = honest not-found |

## Quick rule reference

1. **Serial, no scripts** — S1 vector → S2 content → S3 dedup → S4 judge → S5 full reads → S6 answer, all via MCP tools
2. **Vector lane proposes refs only** — no reads until S3/S4
3. **Merge on (kb_id, doc_path)**; `both` docs survive once with both provenances
4. **One `kb_laya_judge` call for all merged docs** — real engine, fail-closed, verdict final
5. **Relative cut best−0.10 + top-5 floor** selects the relevant-doc set (audit fields included)
6. **Full-content reads of every kept doc** before answering (S5)
7. **Answer with citations + lane provenance + blind spots** — zero kept = honest not-found
