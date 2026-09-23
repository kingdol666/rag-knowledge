---
name: knowledgebase-search
description: >
  QDCVR v2 — Vector-First, Content-Gated, Librarian-Fallback Retrieval.
  Phase 0 query prep → Phase 1 vector search FIRST (kb_search_vector, balance_kbs)
  + content-match gate (kb_doc_read + 0-8 rubric: can this truly answer the question?)
  → if the vector path cannot truly match, Phase 2 librarian deep fallback: traverse
  all KB directories level by level, read every KB summary, judge the most likely
  shelves (multi-path recall: two-stage BM25+graph + tags + descriptions) → re-verify
  → if both paths fail, honestly report the blind spot (never fabricate).
  Absorbs the former knowledgebase-search-enterprise (whole-library / cross-KB /
  comprehensive search). Triggered by: search, find, query, ask, retrieve, retrieval,
  Q&A, look it up, search the whole library, all KBs, cross knowledge base, cross-KB,
  cross-library, global search, comprehensive, thorough search, enterprise search,
  搜索, 检索, 查询, 问答, 帮我查, 问一下知识库, 搜, 全库搜索, 所有KB, 跨知识库, 跨库,
  全局搜索, 全面的.
---

## ⭐ Related Skills
- Document ingest → `skill://knowledgebase-ingest` — the A0-A9 pipeline ensures retrieval source quality
- KB management → `skill://knowledgebase-manage` — document move/rename/delete/merge
- Experience-first retrieval → E4 experience-first retrieval of `skill://knowledgebase-experience` (mandatory for incident/ops-type queries)
- KB organize & restructure → `skill://knowledgebase-organize` — reindexing needed after sub-KB splits/cross-library merges
- KB integrity validation → `skill://knowledgebase-verify` — three-way consistency + index coverage repair
- Knowledge graph → `skill://knowledgebase-graph` — graph build/document paths/cross-library discovery
- Architecture mental model → [kb-architecture.md](../knowledgebase/references/kb-architecture.md) of `skill://knowledgebase` (5-layer data model + 91-tool map)
- Batch operations → `skill://knowledgebase-batch` — batch ingest/tag migration/dedup

## Sequential Workflow
**Phase 0 — Query prep**: intent classification (factual/method/comparison/incident/navigational) → core entity extraction → rewrite as declarative sentence + keywords. Incident/ops → experience library first.
**Phase 1 — Vector first (fast lane)**: `kb_search_vector` on the whole library (or the KB the user named) with `balance_kbs=True` → hard-threshold + document-level dedup → **content-match gate**: `kb_doc_read` + 0-8 rubric judges whether the content can truly answer the question (long docs: chunk text + continuation reads, never head-only) → best score ≥6: fast exit to answer.
**Phase 2 — Librarian deep fallback (gate failed)**: traverse all KBs level by level — `kb_list(lightweight)` reads every KB summary, `fs_get_tree`/`kb_get_documents` walks the directory tree — librarian judgment ranks the most likely shelves → targeted multi-path recall there (two-stage BM25+graph / tags / doc descriptions) → re-verify with the same 0-8 rubric → P0/P1/P2 tiering.
**Phase 3 — Answer or honest report**: P0/P1 structured answer with sources; if both paths fail → honestly declare the blind spot (what was tried, what is missing, suggested next steps). Never fabricate.

# QDCVR v2 — Query-Driven · Content-Ruled · Vector-First with Librarian Fallback

## ⭐ Execution Model · Pre-Flight · Architecture (First Step of Any Job, Mandatory)

**Executor: Archival agent** — delegate via `task` (**delegation template + three-role execution model + combined-task boundaries**: must-read [execution-model.md](../knowledgebase/references/execution-model.md)). **Pre-Flight**: no work before it passes — one-probe double-check `kb_project_status` → branch handling → smoke test; full flow in [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md). **Mental model**: before operating, must-read [kb-architecture.md](../knowledgebase/references/kb-architecture.md) (5-layer model + consistency invariants + 91-tool map); MCP-first principle (no terminal/HTTP bypass) in [skill-trigger-contract.md](../knowledgebase/references/skill-trigger-contract.md) Rule 5.

- Archival is forbidden from: skipping Phase 0 query rewriting, skipping the content-match gate, skipping the librarian fallback when the vector path fails, skipping blind-spot declaration
---

## The One Picture (algorithm contract)

```
query
  │
  ├─ Phase 0 · Query prep            rewrite before retrieving; never feed raw queries
  │
  ├─ Phase 1 · VECTOR FIRST (fast)   kb_search_vector → dedup+threshold → READ content
  │     │                            0-8 rubric: can it truly answer?
  │     ├─ best ≥ 6 ────────────────►✅ answer (fast exit)
  │     └─ best ≤ 5 ────────────────►▼ vector path did not truly match
  │
  ├─ Phase 2 · LIBRARIAN FALLBACK    walk every shelf: KB summaries + directory tree
  │     │                            → judge most-likely KBs → targeted recall there
  │     │                            (BM25+graph two-stage / tags / descriptions)
  │     └─ re-verify 0-8 ───────────►✅ hits → answer · ✖ nothing → ▼
  │
  └─ Phase 3 · HONEST REPORT         report honestly: declare the blind spot, never fabricate
```

**Why this order**: vectors are fast and semantic — they earn the first at-bat. But a high cosine score is only a candidate, not an answer: the content gate reads the body and decides. When the gate says "not truly matching", brute-forcing more vectors is waste — switch to the librarian strategy: browse the catalog, read every KB's summary, walk the shelves, and pull from the most likely section. Only after both paths fail is "no answer" the truth.

**Six iron rules** (including the ⭐ MCP-first principle):
1. **Vector first** — Phase 1 always starts with `kb_search_vector`; do not pre-run BM25 or KB selection ceremonies. Whole-library default with `balance_kbs=True` prevents large-library dominance.
2. **Understand before retrieving** — Phase 0 rewrites the raw query; never fed directly to the retriever.
3. **Content gate owns the verdict** — vector 0.95 with content ≤4 is *discarded*, not down-ranked. Vector scores never overrule the 0-8 rubric.
4. **Gate failure triggers the librarian, not surrender** — best score ≤5 means the vector path cannot truly answer; Phase 2 MUST run before any "no result" conclusion.
5. **Better to give nothing than to give something wrong** — when both paths fail, honestly declare the blind spot; never fabricate.
6. ⭐ **MCP-first principle** — all kb-mcp operations must go through MCP tools (`mcp__kb-mcp__*`); replacing MCP tools with terminal commands like `curl`/`python -c`/`wget` or direct HTTP API calls is forbidden. Only when MCP is unavailable may you report to the user and let the user decide.

**Freedom Map** (freedom level per phase):
| Phase | Freedom | Notes |
|------|--------|------|
| Phase 0 rewrite / content gate / Phase 2 fallback trigger / Phase 3 blind-spot declaration | 🔒 **Mandatory** (low freedom) | Core gates; cannot be skipped or simplified |
| Phase 1 parameter tuning / Phase 2 shelf-ranking depth | 🎯 **Execute** (medium freedom) | Tune top_k/threshold per the scenario tables; decide how deep to walk the tree |
| Gate fast-exit decision / librarian "most likely shelf" judgment | 🧠 **Judgment** (high freedom) | Judge from query semantics; the decision tables guide but are not mechanical |
---

## Phase 0 — Query Prep (The First Gate of Retrieval Quality)

> Observed failure mode: long natural-language queries fed directly to retrieval; the retriever hits keywords but doesn't understand semantics (searching "PET film" returned PP literature).

### 0a Intent Classification
| Type | Features | Retrieval emphasis |
|---|---|---|
| **Factual** | "what is", "definition" | Vector first; authoritative review documents |
| **Method** | "how to", "methods" | Vector first; tags as fallback path |
| **Comparison** | "A vs B", "difference" | Parallel multi-entity recall (keep best chunk per entity) |
| **Incident/ops** | "error", "failed", "how to fix" | **Experience library first** (`experience_search_global`), then documents |
| **Experience/case** | "any similar cases", "how was it handled before" | `experience_search_global` first, documents as supplement |
| **Navigational** | "where is", "is there" | `kb_list(lightweight=true)` + `kb_get_documents(lightweight=true)` description matching |

### 0b Core Entity Extraction
Extract: **subject** (PET/RAG/lithium batteries) + **attribute** (crystallinity/hallucination/thermal management) + **constraints** (process parameters/2024).

### 0c Query Rewriting
- Raw colloquial query → **declarative sentence + keyword combination**
- Example: `"The influence of PET film biaxial stretching process parameters on crystallinity"`
  → Rewrite (vector): `"The influence of stretch ratio/temperature/speed on crystallinity and crystal structure in PET polyester film biaxial stretching"`
- Multi-concept queries → **split into sub-queries and retrieve in parallel** (mandatory for comparisons)

## Phase 1 — Vector First + Content-Match Gate (Fast Lane) ⭐

### 1a Vector Recall (primary, whole-library by default)

```
kb_search_vector(
    query=the Phase 0 rewritten query,
    kb_id=<the KB the user named> or "" (whole library),
    top_k=10,
    score_threshold=0.35,
    balance_kbs=True        # ⭐ mandatory for whole-library search; prevents large-library dominance
)
```

**Hierarchical KB pass-through** (parent KB containing sub-KBs): `kb_search_vector` against the **parent KB** is the correct entry — sub-KB documents' vector chunks live under the parent's collection (searching a sub-KB UUID returns 0; `kb_search_two_stage` on a parent returns empty container entries). A result whose `doc_path` carries a sub-KB prefix and non-empty content is a successful pass-through. `kb_graph_kb_overview(kb_id)` is for viewing structure only, never a search entry.

**Empty handling**: 0 results → retry once with `score_threshold=0.30`; still 0 → go directly to Phase 2.

### 1b Filter (before reading)

```
1. Hard threshold: drop chunks with score < 0.35 (0.30 on the retry pass)
2. Document-level dedup: per normalized doc_path keep only the highest-scoring chunk
3. Short content: <50 chars drop; 50-200 chars mark ⚠️ and demote one level when scoring
4. Sort desc; top 3-5 documents proceed to the gate
```
**Exception**: comparison queries keep the best chunk for both entities.

### 1c Content-Match Gate ⭐ (does the content TRULY answer the question?)

For each surviving candidate:
```
kb_doc_read(kb_id, doc_path, max_chars=3000)     # read 1: head window → returns totalLines + truncated
```
**0-8 scoring (actionable criteria)**:

| Dimension | Pts | Criteria |
|---|---|---|
| **Topic relevance** (0-3) | 3=body directly about the query subject; 2=touches the subject; 1=marginally related; 0=irrelevant |
| **Scenario/problem match** (0-3) | 3=directly solves the query's problem; 2=related methods transferable; 1=generic coverage; 0=answer misses the question |
| **Answer evidence** (0-2) | 2=body contains directly quotable data/steps/conclusions; 1=directional information; 0=empty |

**Content score > vector score.** Vector 0.9 but content ≤3 → discard. Vector 0.5 but content ≥6 → adopt.

#### Long-document provisions ⭐ (head-read blind spot)

A head window of 3000 chars covers only the front of a long document — evidence living deeper would be under-scored and wrongly discarded. Three mandatory rules:

1. **The retrieved chunk is admissible evidence.** The vector hit already contains ~500 chars of real body text from the matching position. Score the *evidence* dimension on **chunk text ∪ read windows**, never on the head window alone. A document whose head misses but whose chunk directly answers the question is a HIT, not a discard.
2. **Continuation reads when truncated.** If `truncated=true` and neither head nor chunk settles the verdict, read deeper — `kb_doc_read` paginates by line: `offset` = line offset, `limit` = lines, response carries `totalLines`. Probe at `offset=totalLines/3` then `2*totalLines/3` (`limit=100`, `max_chars=3000`); **at most 2 continuation reads**, then score on the best window seen. Document-part files (≤10k chars) may be read in full (`max_chars=12000`).
3. **Part files are self-describing.** Documents >12k chars were split at ingest into `(part k of N)` siblings, each carrying a context header (source title + part i/N + section path). Use the header for topic scoring; use the vector hit's own part for evidence — never read part 1 assuming it represents the whole.

### 1d Gate Decision

| Best content score | Verdict | Action |
|---|---|---|
| **≥6** | ✅ vector path truly answers | Fast exit → Phase 3 answer (skip Phase 2) |
| **5** | ⚠️ on-topic but incomplete | Keep as **P1 backstop**; run Phase 2 to find better |
| **≤4** | ❌ vector path missed | Run Phase 2; these candidates are discarded |

Boundary decisions: unsure at exactly 4-5 → re-read 500 chars to confirm; multiple docs >5 → take the best 2-3, do not cite all; good score but outdated doc → demote one tier and flag timeliness.

## Phase 2 — Librarian Deep Fallback (when the gate fails) ⭐

> The librarian does not summon books by shouting keywords louder. **He walks the stacks**: reads the catalog, scans every shelf's summary, and pulls from the section most likely to hold the answer. This phase absorbs the former `knowledgebase-search-enterprise` skill (multi-path recall + cross-validation + graph expansion).

### 2a Walk the Stacks (read every KB summary + traverse directories)

```
catalog = kb_list(lightweight=true)     # EVERY KB: {kb_id, name, description, doc_count}
tree    = fs_get_tree(max_depth=2)      # KB hierarchy (raise depth only if needed)
```
For the 1-3 most promising KBs, drill into their shelves:
```
kb_get_documents(lightweight=true, kb_id)   # every doc's name + description
```
**Part-aware grouping ⭐**: split documents appear as `(part k of N)` siblings (e.g. `ARCHITECTURE (part 7 of 15).md`). Group siblings by their stem — they are ONE logical book, not N documents. Judge relevance by stem + description; when a vector hit names a specific part, that part is where the evidence lives. Counting/dedup/citation all operate on the logical (stem) level; cite the concrete part when quoting.

### 2b Librarian Judgment (which shelf is most likely?)

Match Phase 0 entities against **KB descriptions + document names + directory names**:
- Score each KB: subject match (does the KB's domain cover the subject?) × attribute match (does any doc name/description mention the attribute?) × constraint match (year/scope qualifiers).
- Rank and keep the **top 2-3 KBs** (plus their most promising sub-directories).
- This judgment replaces the old "smart KB selection" front gate: it runs only when vectors missed, and it is informed by having read *every* summary, not just the top hit.

### 2c Targeted Multi-Path Recall (in the judged shelves only)

```
# Path A — BM25 + graph two-stage (lexical precision inside the likely KBs)
kb_search_two_stage(query, kb_id=<likely KB>, stage1_top_k=20, stage2_top_k=5,
                    enable_graph_expansion=true, score_threshold=0.30, balance_kbs=True)

# Path B — Tags (semantic concepts vectors missed)
kb_tags_list() → match 3-5 tags to the query entities
→ kb_doc_get_by_tag(tag, kb_id=<likely KB> or "")

# Path C — Descriptions + navigation (doc names/descriptions from 2a re-read closely)
kb_get_documents(lightweight=true, kb_id) → shortlist by description match

# Path D — Experience library (incident/ops queries)
experience_search_global(query, top_k=5)
```
Path tuning: large KB (>10 docs) stage1_top_k=30; recall-first stage2_top_k=10, threshold 0.30; precision-first stage2_top_k=3, threshold 0.45.

**Cross-validation + dedup**: merge paths, dedup by doc_path (keep best chunk; record hit-path count — multi-path consensus raises the *candidate* tier, but never the final verdict), hard-threshold 0.30 pre-filter, short-content downgrade.

**Restrained graph expansion** (only when P0 <3 or explicitly cross-library):
```
kb_graph_document_related(doc_path) / kb_graph_central_documents(kb_id) / kb_graph_cross_kb_documents(min_kbs=2)
```

### 2d Re-Verify (same gate, same rubric)

Every new candidate goes through `kb_doc_read` + the same 0-8 rubric.

**Final confidence**:
| Source + content score | Tier |
|---|---|
| Any recall path + content ≥6 | **P0 Strong** — cite directly |
| Any recall path + content =5 | **P1 Confirmed** — adopt with attribution |
| Description-only match + content =5 | **P2 Supplement** — flagged weak |
| Content ≤4 | **Discard** — even with three-path consensus |

Short content (<200 chars) demotes one tier. A Phase 1 P1 backstop beats a Phase 2 P2; if Phase 2 produced nothing better, answer from the backstop and say so.

## Phase 3 — Answer or Honest Report (Mandatory Standards)

### On hit — synthesized answer (five sections, all mandatory)

```
## Search Paths
Phase 1 vector (kb_search_vector, balance_kbs) → dedup → content gate (kb_doc_read, 0-8 scoring);
Phase 2 librarian fallback (kb_list summaries + two_stage/tags) → re-verify
→ N documents after dedup → after content verification P0:x / P1:y

## Answer
<Synthesized from P0 documents, citing specific data/conclusions; P1 as supplement>

## Sources (sorted by confidence + path consensus)
- [P0] <document name> @ <KB/path> — <why relevant, one sentence> (split docs: cite the concrete `(part k of N)` hit)
- [P1] <document name> @ <KB/path> — <what it adds>

## Confidence
High/medium/low — <reason, e.g. "2 P0 documents across 2 KBs consistent" or "only 1 P1 backstop; deeper verification recommended">

## Blind Spots (Cross-Library Perspective)
- <sub-domains the query touches but the whole library does not cover>
- <a library that may hold related content but was not hit this time — manual recheck recommended>
- <contested/timeliness/points needing user confirmation>
```

### On total failure — honest report (report honestly, first-class outcome)

When Phase 1 gate ≤4/5-only AND Phase 2 re-verify yields no P0/P1:
```
## Answer (No Confirmed Hit)
<One sentence: the knowledge base cannot currently answer this question.>

## What Was Tried
- Phase 1 vector: kb_search_vector(<rewritten query>, threshold 0.35→0.30) → N candidates, best content score x/8 (<what was found instead>)
- Phase 2 librarian: read M KB summaries, walked <KBs/dirs>, recalled via two_stage/tags → no candidate scored ≥5

## Blind Spots
- <the specific sub-topic the library lacks>
- <nearest-but-insufficient documents, and why they fail>

## Suggestions
- <ingest source X / broaden the query to Y / ask the user for the missing material>
```
Never dress a ≤4 candidate as an answer. Never fabricate data, citations, or confidence.

---

## ⚠️ NEVER List

| ❌ Don't do this | Why | ✅ Do this instead |
|-------------|------|-------------|
| Start with BM25/two-stage or KB-selection ceremonies | Vectors are the fast semantic lane; ceremonies add latency, not recall | Phase 1 `kb_search_vector` first, `balance_kbs=True` |
| Trust a high vector score without reading | Cosine ≠ answerable | Content gate: `kb_doc_read` 3000 chars + 0-8 rubric |
| Declare "no result" after Phase 1 alone | Vector miss ≠ corpus miss | Gate failure → Phase 2 librarian fallback is mandatory |
| Walk the stacks by guessing KBs | Summary-reading is the librarian's whole edge | Read EVERY KB description in `kb_list(lightweight)` before judging |
| Keep score <0.35 chunks | Cross-domain low-score pollution | Hard-threshold truncation both phases |
| Score a long doc by its head window alone | Evidence past char 3000 would be falsely discarded | Chunk text ∪ continuation reads (`offset`/`totalLines`) before verdict |
| Treat `(part k of N)` siblings as separate books | Part 1 doesn't represent the whole; counting inflates | Group by stem; read the HIT part; cite the concrete part |
| Include content ≤4 in the answer | Better to give nothing than something wrong | Discard → fallback → if nothing, honest report |
| Answer without the five sections / blind-spot declaration | The user assumes the KB covers everything | Mandatory output standards above |

## Quick Rule Reference
1. **Vector first** — `kb_search_vector` opens every search; whole-library default with balance_kbs
2. **Phase 0 mandatory** — raw colloquial queries are not retrieved directly
3. **Content gate owns the verdict** — read 3000 chars, score 0-8 independently; ≥6 fast exit
4. **Gate ≤5 → librarian fallback mandatory** — read all KB summaries → walk directories → targeted multi-path recall → re-verify
5. **Document-level dedup + hard threshold** — both phases, every path; `(part k of N)` siblings count as one logical document
6. **Content score > vector score > path consensus** — three-path hits with content ≤4 still die; evidence = chunk text ∪ all read windows
7. **Experience first** — incident/ops-type queries check experiences first
8. **Honest blind spots** — both paths failed → report honestly with what-was-tried evidence; never fabricate

<!-- SKILLOPT-SLEEP:LEARNED START -->
## Learned preferences & procedures

_This block is maintained by SkillOpt-Sleep. Edits here are proposed offline, validated against your past tasks, and adopted only after you approve them. Hand-edits outside this block are never touched._

- The Phase 1 vector recall tool is `mcp__kb-mcp__kb_search_vector(kb_id="", top_k=10, score_threshold=0.35, balance_kbs=True)`; the final answer's `## Search Paths` line MUST contain the literal token `kb_search_vector`. A final answer missing that token is a failure.
- The final answer MUST contain a section titled `## Blind Spots (Cross-Library Perspective)` (title containing both literal words `Blind Spots` and `Cross-Library`), itemizing: sub-domains not covered, a library that may have relevant content but was not hit (manual recheck recommended), and contested/timeliness/points needing confirmation. Missing the `Blind Spots`/`Cross-Library` labels is a failure.
- The `## Search Paths` line MUST contain `kb_doc_read` and `0-8 scoring`; the `## Confidence` line MUST contain `content verification` (e.g. `after content verification P0:3 documents`). Missing these literals is a failure.
- MUST-answer + MCP first: all recall for whole-library/cross-library retrieval MUST go through `mcp__kb-mcp__*` tools (kb_search_vector, kb_list, kb_doc_read, kb_search_two_stage, kb_tags_list, kb_doc_get_by_tag, ...); Bash/terminal/HTTP bypass is forbidden; the response MUST give the complete five-section final answer in the same turn (`## Search Paths`/`## Answer`/`## Sources`/`## Confidence`/`## Blind Spots (Cross-Library Perspective)`); ending the turn with a single tool call, probe command, or partial answer is forbidden.
<!-- SKILLOPT-SLEEP:LEARNED END -->
