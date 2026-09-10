---
name: knowledgebase-search
description: >
  Query-Driven Content-Verified Retrieval (QDCVR). Step0 query analysis+rewrite
  → Step1 smart KB selection → Step2 two-stage vector+BM25 recall (balance_kbs)
  → Step2.5 document dedup+hard threshold → Step3 content verification (0-8 scoring)
  → fast exit if score≥6, otherwise Step4 tag+description expansion → Step5 confidence
  rating → Step6 synthesized answer with sources and blind-spots. Vector is fast,
  content is accurate. Triggered by: search, find, query, ask, retrieve, search,
  retrieval, query, Q&A, look it up for me, ask the knowledge base, search.
---

## ⭐ Related Skills
- Cross-library enterprise search (triggered when P0/P1 <2 KBs) → `skill://knowledgebase-search-enterprise` — parallel 3-path recall + graph expansion
- Document ingest → `skill://knowledgebase-ingest` — the A0-A9 pipeline ensures retrieval source quality
- KB management → `skill://knowledgebase-manage` — document move/rename/delete/merge
- Experience-first retrieval → E4 experience-first retrieval of `skill://knowledgebase-experience` (mandatory for incident/ops-type queries)
- KB organize & restructure → `skill://knowledgebase-organize` — reindexing needed after sub-KB splits/cross-library merges
- KB integrity validation → `skill://knowledgebase-verify` — three-way consistency + index coverage repair
- Knowledge graph → `skill://knowledgebase-graph` — graph build/document paths/cross-library discovery
- Architecture mental model → [kb-architecture.md](../knowledgebase/references/kb-architecture.md) of `skill://knowledgebase` (5-layer data model + 91-tool map)
- Batch operations → `skill://knowledgebase-batch` — batch ingest/tag migration/dedup

## Sequential Workflow
**Step 1 — Query analysis (Step 0)**: intent classification (factual/method/comparison/incident/navigational) → core entity extraction → rewrite the query as a declarative sentence + keywords (incident-type queries the experience library first).
**Step 2 — Smart KB selection (Step 1)**: `kb_list(lightweight=true)` → semantic matching against KB descriptions → pick the top 1-3 target KBs; when sub-KBs exist, use `kb_search_vector` against the parent KB for pass-through.
**Step 3 — Two-stage retrieval (Step 2)**: `kb_search_two_stage(balance_kbs=True)` — Stage1 BM25+graph candidates → Stage2 fine-grained vector search → tune parameters per scenario.
**Step 4 — Dedup filtering (Step 2.5)**: hard-threshold filtering (score<0.35 dropped) → document-level dedup (keep the highest score per document) → short-content downgrade → top 5 proceed to verification.
**Step 5 — Content verification (Step 3)**: `kb_doc_read(3000 chars)` → 0-8 rubric scoring (topic relevance/scenario match/answer evidence) → content-overrides-vector → ≥6 fast exit / 5 expand / ≤4 downgrade.
**Step 6 — Expansion recall (Step 4-5)**: tag+description expansion→re-verify→P0 Strong/P1 Confirmed/P2 Supplement confidence tiering.
**Step 7 — Synthesized answer (Step 6)**: P0/P1 structured output + sources (by confidence) + honest blind-spot declaration + upgrade to enterprise search when fewer than 2 KBs contribute.
# QDCVR — Query-Driven · Content-Ruled · Gated Refined Retrieval
## ⭐ Execution Model · Pre-Flight · Architecture (First Step of Any Job, Mandatory)

**Executor: Archival agent** — delegate via `task` (**delegation template + three-role execution model + combined-task boundaries**: must-read [execution-model.md](../knowledgebase/references/execution-model.md)). **Pre-Flight**: no work before it passes — one-probe double-check `kb_project_status` → branch handling → smoke test; full flow in [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md). **Mental model**: before operating, must-read [kb-architecture.md](../knowledgebase/references/kb-architecture.md) (5-layer model + consistency invariants + 91-tool map); MCP-first principle (no terminal/HTTP bypass) in [skill-trigger-contract.md](../knowledgebase/references/skill-trigger-contract.md) Rule 5.

- Archival is forbidden from: skipping Step 0 query rewriting, skipping content verification, skipping blind-spot declaration
---


**Six iron rules** (including the ⭐ MCP-first principle):
1. **Understand before retrieving** — the raw query is first rewritten into a retrieval-friendly form (Step 0); never fed directly to the retriever.
2. **Select libraries before recall** — when spanning libraries, first determine relevant KBs (Step 1) to avoid cross-domain noise and large-library dominance.
3. **Fast vector recall, true content ruling** — vectors pick candidates; reading the body with 0-8 scoring decides inclusion; vector scores do not influence decisions.
4. **Document-level dedup + hard threshold** — only the highest-scoring chunk per document is kept; score below the threshold is dropped directly.
5. **Better to give nothing than to give something wrong** — with no confirmed hit, honestly declare the blind spot; never fabricate.
6. ⭐ **MCP-first principle** — all kb-mcp operations must go through MCP tools (`mcp__kb-mcp__*`); replacing MCP tools with terminal commands like `curl`/`python -c`/`wget` or direct HTTP API calls is forbidden. Only when MCP is unavailable may you report to the user and let the user decide.


**Freedom Map** (freedom level per step):
| Step | Freedom | Notes |
|------|--------|------|
| Step 0 query rewrite / Step 2.5 dedup+hard threshold / Step 3 content ruling / Step 6 blind-spot declaration | 🔒 **Mandatory** (low freedom) | Core gates of retrieval quality; cannot be skipped or simplified |
| Step 1 smart KB selection / Step 2 parameter tuning | 🎯 **Execute** (medium freedom) | Select libraries by KB description; tune stage1/stage2/threshold per the scenario table |
| Step 0a intent classification / Step 3 fast-exit decision | 🧠 **Judgment** (high freedom) | Requires judging type and confidence from query semantics; the decision table guides but is not mechanical |
| Step 4 tag expansion (downgrade path) | 🎯 **Execute** (medium freedom) | Triggered only when vectors miss; must not run every time |
---

## Mental Framework: Settle Three Questions Before Retrieving ⭐

```
The user says "search for X"
  │
  ├── What type of query is this?
  │   Factual (what) / method (how) / comparison (A vs B) / incident (why broken) / navigational (where)
  │
  ├── Which KB to search?
  │   Explicitly says "search KB XX" → that KB directly
  │   Not said → Step 1 smart KB selection
  │
  └── Can it be answered quickly?
      Experience first? → incident-type queries the experience library first
      Direct document hit? → fast exit
```

---

## Step 0 — Query Analysis and Rewriting ⭐ (The First Gate of Retrieval Quality)

> Observed failure mode: long natural-language queries fed directly to retrieval; BM25 hits keywords but doesn't understand semantics (searching "PET film" returned PP literature).

### 0a Intent Classification
| Type | Features | Retrieval emphasis |
|---|---|---|
| **Factual** | "what is", "definition" | Vector reranking + authoritative review documents |
| **Method** | "how to", "methods" | Vector + tags (method words) |
| **Comparison** | "A vs B", "difference" | Parallel multi-entity recall |
| **Incident/ops** | "error", "failed", "how to fix" | **Experience library first** (experience-first), then documents |
| **Experience/case** | "any similar cases", "how was it handled before" | `experience_search_global` first, documents as supplement |
| **Navigational** | "where is", "is there" | kb_list(lightweight=true) + kb_get_documents(lightweight=true) description matching |

### 0b Core Entity Extraction
Extract from the query: **subject** (PET/RAG/lithium batteries) + **attribute** (crystallinity/hallucination/thermal management) + **constraints** (process parameters/2024).

### 0c Query Rewriting (Generate Retrieval-Friendly Queries)
- Raw colloquial query → **declarative sentence + keyword combination**
- Example: `"The influence of PET film biaxial stretching process parameters on crystallinity"`
  → Rewrite 1 (for vectors): `"The influence of stretch ratio/temperature/speed on crystallinity and crystal structure in PET polyester film biaxial stretching"`
  → Rewrite 2 (for BM25): `"PET BOPET biaxial stretching crystallinity stretch ratio process parameters"`
- Multi-concept queries → **split into sub-queries and retrieve in parallel** (mandatory for comparisons)

**Incident/ops-type queries**: first `experience_search_global(query, top_k=5)`; if experiences hit, use them with priority.

## Step 1 — Smart KB Selection (Mandatory When Spanning Libraries) ⭐

> Observed failure mode: blind whole-library search → large libraries (Materials-ML 11docs/1156chunks) dominate results and cross-domain noise floods in.

```
catalog = kb_list(lightweight=true)    # only [{kb_id, name, description, doc_count}]; context-friendly
```
- Use model judgment to read each KB's description and pick the **top 1-3 genuinely relevant** KBs.
- **Retrieve preferentially within the selected 1-3 KBs** (`kb_id=<selected KB>`); only when <2 KBs are selected or there are no hits, search the whole library with `kb_id=""`.
- Incident-type queries: experience library first; document libraries as supplement.

**Criterion**: a KB is selected only if its description's domain matches the query entities. Example: querying RAG → select only `AI-ML-Research`.

### Step 1b — Hierarchical KB Pass-Through (Mandatory When a Parent KB Contains Sub-KBs) ⭐

> ⚠️ **Empirical truth** (verified by the 2026-07-22 end-to-end test): the parent KB's `kb_search_two_stage` returns sub-KB container entries (content always empty). **Sub-KB documents' vector chunks are actually stored under the parent KB's collection** (searching the sub-KB UUID returns 0 results; `kb_search_stats(sub-KB)` shows chunk_count=0).

**Correct pass-through strategy** — pure vector search against the parent KB (not two_stage, not searching sub-KBs):
```
# The parent KB's two_stage returns empty containers, but kb_search_vector gets real content
results = kb_search_vector(query=..., kb_id=<parent KB id>, score_threshold=0.35, top_k=10)
# The result's doc_path carries the sub-KB path prefix (e.g. "Polymers...\\03_PET_BOPET\\xxx.md"),
# and the content field has real body text — that's a successful pass-through
```

**Auxiliary: understand sub-KB structure** (not for searching, only for understanding organization):
```
overview = kb_graph_kb_overview(kb_id=<parent KB>)  → sub_kbs structure + doc counts
# ⚠️ sub_kbs[].name returns UUIDs; use kb_list(lightweight=true) to look up readable names
# ⚠️ Do NOT run kb_search_two_stage / kb_search_vector against a sub_kb_id — returns 0
```

> ❌ **Wrong approach** (misled by old docs): getting sub-KB UUIDs and searching each sub-KB separately → all return 0, misjudged as "no relevant content".

## Step 2 — Vector Recall (Two-Stage, Balancing Multiple Libraries)

```
kb_search_two_stage(
    query=the query rewritten in Step0,
    kb_id=KBs selected in Step1 or "" (whole library),
    stage1_top_k=20,          # BM25 candidate documents
    stage2_top_k=5,           # chunks returned per document
    enable_graph_expansion=true,
    score_threshold=0.35,     # vector hard threshold (<=0 uses the backend default 0.35)
    balance_kbs=True          # ⭐ mandatory when spanning libraries; prevents large-library dominance
)
```

### Tuning Guide
| Scenario | stage1_top_k | stage2_top_k | score_threshold |
|------|-------------|-------------|-----------------|
| Standard | 20 | 5 | 0.35 |
| Large library (>10 docs) | 30 | 5 | 0.35 |
| Small library (<5 docs) | 10 | 3 | 0.30 |
| Precision-first | 20 | 3 | 0.45 |
| Recall-first | 30 | 10 | 0.30 |

### Empty-Result Handling
- 0 results returned → lower score_threshold to 0.30 and retry
- Still 0 → abandon vectors; go to Step 4 tag expansion

## Step 2.5 — Document-Level Dedup + Hard-Threshold Filtering ⭐ (Refine the Result Set)

> ⭐ Both `kb_search_vector` and `kb_search_two_stage` already auto-normalize paths (backslash→forward slash) and dedup by (doc_path, chunk_index) at the MCP layer. The Agent still performs document-level dedup (keep only the highest-scoring chunk per document).

Apply to `stage2.results`:

```
1. Hard-threshold filtering: drop chunks with score < 0.35
2. Document-level dedup: per doc_path (after forward-slash normalization), keep only the 1 highest-scoring chunk
3. Short-content downgrade: chunk body <50 chars → drop directly; 50-200 chars → mark ⚠️, demote one level when scoring
4. Sort: by score descending; top 5 proceed to Step 3
```
**Exception**: comparison queries (A vs B) keep the highest-scoring chunk for both A and B.

## Step 3 — Content Verification (Core Ruling, Independent of Vector Scores)

Content-verify the top 5 deduped candidates (already trimmed to 5 in Step 2.5):
```
kb_doc_read(kb_id, doc_path, max_chars=3000)
```
**0-8 scoring (actionable criteria)**:

| Dimension | Pts | Criteria |
|---|---|---|
| **Topic relevance** (0-3) | 3=body directly about the query subject; 2=touches the subject; 1=marginally related; 0=irrelevant |
| **Scenario/problem match** (0-3) | 3=directly solves the query's problem; 2=related methods transferable; 1=generic coverage; 0=answer misses the question |
| **Answer evidence** (0-2) | 2=body contains directly quotable data/steps/conclusions; 1=directional information; 0=empty |

**Content score > vector score.** Vector 0.9 but content ≤3 → discard. Vector 0.5 but content ≥6 → adopt.

### Step 3 Fast Exit
| Highest content score | Action |
|---|---|
| **≥6** | ✅ go directly to Step 6 to answer (skip Steps 4-5)|
| **5** | ⚠️ usable but needs supplementation → continue to Step 4 expansion recall |
| **≤4** | ❌ current recall missed → continue to Step 4 expansion recall |

### Step 3 Content-Score Boundary Decisions
- Score exactly 4 or 5 and unsure? → re-read 500 chars to confirm; do not fall back to Step 2
- Multiple documents with similar scores >5? → take the highest-scoring 2-3 and synthesize an answer; do not cite all
- High content score but the document looks outdated (pre-2020)? → demote one level and flag timeliness

## Step 4 — Tag + Description Expansion (When Vectors Miss)

```
kb_tags_list()
kb_doc_get_by_tag(tag="<semantically matching tag>", kb_id=KB selected in Step1 or "")
kb_get_documents(lightweight=true, kb_id)   # document description list for newly discovered KBs
kb_search_vector(Step0 rewritten query, kb_id="", top_k=10, score_threshold=0.30)
```

## Step 5 — Expanded Content Verification + Confidence Tiering

For Step 4's new candidates, likewise run `kb_doc_read` + 0-8 scoring; keep ≥5, drop ≤4.

**Final confidence**:
| Source + content score | Tier |
|---|---|
| Vector/tag recall + content ≥6 | **P0 Strong** — cite directly in the answer |
| Vector/tag recall + content =5 | **P1 Confirmed** — adopt with attribution |
| Description-only match + content =5 | **P2 Supplement** — supplementary use, flagged weak |
| Content ≤4 | **Discard** |

**Short content (<200 chars) demoted one level**; **cross-library blind spot**: confirmed P0/P1 from <2 KBs → escalate to `Skill("knowledgebase-search-enterprise")`.

## Step 6 — Synthesized Answer (Mandatory Standard)

```
## Answer
<A synthesized answer based on P0/P1 documents, citing specific data/conclusions>

## Sources (sorted by confidence)
- [P0] <document name> @ <KB/path> — <why relevant, one sentence>
- [P1] <document name> @ <KB/path> — <what it adds>

## Confidence
High/medium/low — <reason, e.g. "3 P0 documents consistently support" or "only 1 P1; needs further verification">

## Blind Spots (Honest Declaration)
- <parts the query touches that the knowledge base doesn't cover>
- <contested/timeliness/points needing user confirmation>
```

---

## ⚠️ NEVER List

| ❌ Don't do this | Why | ✅ Do this instead |
|-------------|------|-------------|
| Feed raw colloquial queries to the retriever | BM25 is semantically blind | Step 0 rewrite into declarative sentence + keywords |
| Skip Step 1 and blindly search the whole library | Cross-domain noise floods in | Select libraries first; restrict to 1-3 KBs |
| Content verification by guessing (not reading documents) | Vector scores don't reflect real content | `kb_doc_read` 3000 chars then score |
| Keeping score<0.35 without truncating | Cross-domain low-score pollution | Step 2.5 hard-threshold truncation |
| Including content scores ≤4 in the answer | Better to give nothing than something wrong | Discard → Step 4 expansion |
| Step 6 without blind-spot declaration | The user assumes the knowledge base covers everything | Honestly declare coverage blind spots |

## Quick Rule Reference
1. **Step 0 mandatory** — raw colloquial queries are not retrieved directly
2. **Step 1 mandatory when spanning libraries** — library selection reduces noise
3. **balance_kbs=True** (cross-library) — prevents large-library dominance
4. **Step 2.5 mandatory** — document-level dedup + hard threshold
5. **Content score > vector score** — read 3000 chars and score independently
6. **Exit on hit** — content ≥6 answers directly
7. **Tags are expanders** — used only when vectors miss
8. **Experience first** — incident/ops-type queries check experiences first
9. **Honest blind spots** — declare when there's no confirmed hit
