---
name: knowledgebase-search-enterprise
description: >
  Enterprise multi-strategy retrieval. Auto-upgrades from knowledgebase-search when P0/P1 docs come from <2 KBs. Parallel 3-path recall (vector + tag semantic + BM25) with balance_kbs, cross-validation dedup, content ruling (0-8 scoring), graph expansion (only when P0<3), fused presentation with cross-KB blind-spot declaration. Triggered by: search the whole library, all KBs, cross knowledge base, cross-library, cross-KB, all KBs, enterprise search, global search, comprehensive, thorough search, comprehensive.
---

## ⭐ Related Skills
- Single-library retrieval → `skill://knowledgebase-search` (QDCVR two-stage)
- Cross-library bridge documents → `skill://knowledgebase-graph` (Cross-KB Discovery)
- Architecture mental model → [kb-architecture.md](../knowledgebase/references/kb-architecture.md) of `skill://knowledgebase`

## Sequential Workflow
**Step 1 — Query analysis+rewrite**: extract core concepts; generate multi-angle query variants.
**Step 2 — Parallel 3-path recall**: vector semantic + tag semantic + BM25 keyword, three paths in parallel.
**Step 3 — Cross-validation dedup**: cross-validate multi-path results + document-level dedup.
**Step 4 — Content ruling**: 0-8 rubric scoring → content verification independent of vectors.
**Step 5 — Fused presentation**: grouped by KB + cross-library blind-spot declaration.
# Enterprise Multi-Strategy Retrieval — Enterprise-Grade Multi-Strategy Refined Retrieval

## ⭐ Execution Model · Pre-Flight · Architecture (First Step of Any Job, Mandatory)

**Executor: Archival agent** — delegate via `task` (**delegation template + three-role execution model + combined-task boundaries**: must-read [execution-model.md](../knowledgebase/references/execution-model.md)). **Pre-Flight**: no work before it passes — one-probe double-check `kb_project_status` → branch handling → smoke test; full flow in [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md). **Mental model**: before operating, must-read [kb-architecture.md](../knowledgebase/references/kb-architecture.md) (5-layer model + consistency invariants + 91-tool map); MCP-first principle (no terminal/HTTP bypass) in [skill-trigger-contract.md](../knowledgebase/references/skill-trigger-contract.md) Rule 5.

- Archival is forbidden from: skipping the enterprise multi-strategy retrieval flow, skipping content ruling

---

> **Upgrade trigger**: knowledgebase-search Step 5 finds confirmed P0/P1 coming from <2 KBs (cross-library blind spot), or the user explicitly requests whole-library/cross-library/comprehensive retrieval.

---

## Mental Framework: When to Use Enterprise?

```
User query
  ├── Standard KB search (a specific KB specified) → knowledgebase-search ✅
  ├── Whole-library search (no KB specified) + ordinary query → knowledgebase-search ✅ (Step 1 auto-selects libraries)
  └── Whole-library search + the query hits <2 KBs → knowledgebase-search-enterprise ⬆️
      Or: the user emphasizes "whole library/cross-library/comprehensive/all KBs" → upgrade directly
```

> Enterprise is 3x heavier than standard QDCVR (3 parallel recall paths); do not use it by default. Run QDCVR first; upgrade only when it falls short.

---

## Execution Flow

### Phase 0 — Query Rewriting (Inherits QDCVR Step 0)

```
Raw query → intent classification + core entity extraction → generate a retrieval-friendly query
- For vector/BM25: declarative sentence + keyword combination
- For the tag path: domain concept words
- Multi-concept queries → split into sub-queries in parallel (mandatory for comparisons)
```
Incident/ops-type: first `mcp__kb-mcp__experience_search_global(query, top_k=5)`.

### Phase 1 — Parallel 3-Path Recall (All with balance_kbs=True to Prevent Large-Library Dominance)

> ⚠️ Note: paths A and C share the `kb_search_two_stage` engine (only the stage2_top_k parameter differs); they are not fully independent. Path B (tags) is the only truly independent recall path. A+C dual-path consensus confidence is lower than A+B or B+C.

```
# Path A — Vector+BM25 two-stage refined ranking
mcp__kb-mcp__kb_search_two_stage(
    Phase0 rewritten query, kb_id="",
    stage1_top_k=30, stage2_top_k=10,
    score_threshold=0.30,         # enterprise-level relaxed recall; Phase 3 screens strictly again
    balance_kbs=True              # ⭐ mandatory
)

# Path B — Tags (semantic concept matching)
mcp__kb-mcp__kb_tags_list()
→ for the query's core entities, semantically match the top 3-5 tags
→ mcp__kb-mcp__kb_doc_get_by_tag(tag, kb_id="") fetch documents per tag

# Path C — BM25 keywords (pure keywords; stage2 off)
mcp__kb-mcp__kb_search_two_stage(
    Phase0 rewritten query, kb_id="",
    stage1_top_k=25, stage2_top_k=0,   # stage1 candidates only
    balance_kbs=True
)
```
**Optional Path D — Experience library** (incident/ops-type): `mcp__kb-mcp__experience_search_global(query, top_k=5)` + `mcp__kb-mcp__experience_search_global(kb_id, query, top_k=5)`.

#### Path Failure Handling
- Path A vector returns 0 → lower score_threshold to 0.25 and retry
- Path B no tag matches → use `mcp__kb-mcp__kb_search` to keyword-search tag descriptions
- Path C BM25 no results → tokenize and search core words

### Phase 2 — Cross-Validation + Document-Level Dedup

Merge all paths' results, **dedup by doc_path** (keep only the highest-scoring chunk per document; record the number of hitting paths):

| Hit-path pattern | Candidate confidence |
|---|---|
| A + B + C three paths | **P0 candidate** (multi-path consensus)|
| A + B or B + C two paths | **P0 candidate** (semantic+keyword double confirmation)|
| A + C two paths (vector+BM25)| **P1 candidate** |
| Single path only | **P1/P2 candidate** (needs Phase 3 content verification)|

**Hard-threshold pre-filtering**: any chunk with vector score < 0.30 → discard (unless it's a tag-path hit with a strongly related description).
**Short-content downgrade**: chunk <50 chars discarded directly; 50-200 chars marked ⚠️, candidate confidence demoted one level.

### Phase 3 — Content Ruling (Independent Scoring, Final Inclusion Decision)

For each deduped candidate (≤12 documents):
```
mcp__kb-mcp__kb_doc_read(kb_id, doc_path, max_chars=3000)
```
**0-8 scoring** (same as QDCVR Step 3):

| Dimension | Pts | Criteria |
|---|---|---|
| Topic relevance (0-3) | 3=body about the subject / 2=touches it / 1=marginal / 0=irrelevant |
| Scenario match (0-3) | 3=directly solves the problem / 2=transferable / 1=generic / 0=misses the question |
| Answer evidence (0-2) | 2=concrete data/steps/conclusions / 1=directional / 0=empty |

| Content score | Final verdict |
|---|---|
| 6-8 | **P0** — included in the answer |
| 5 | **P1** — supplementary use |
| ≤4 | **Discard** |

**Content score beats everything**. Three-path hit but content ≤4 → discard (multiple paths can be jointly wrong).

### Phase 4 — Graph Expansion (When P0 <3 or Cross-Library Bridges Are Needed)

```
mcp__kb-mcp__kb_graph_document_related(doc_path)     # related documents of confirmed P0s
mcp__kb-mcp__kb_graph_central_documents(kb_id)       # hub/review documents
mcp__kb-mcp__kb_graph_cross_kb_documents(min_kbs=2)  # cross-library bridge documents
```
New documents enter Phase 3 content ruling. **Enable only when P0 is insufficient or the query is explicitly cross-library** to avoid graph noise.

### Phase 5 — Fused Presentation (Mandatory Standard)

```
## Search Paths
A vector + B tags + C BM25 (+ D experiences, if applicable) → N documents after dedup → P0:x / P1:y after content ruling

## Answer
<Synthesized from P0 documents, citing specific data/conclusions; P1 as supplement>

## Sources (sorted by confidence + path consensus)
- [P0] [A+B+C] <document name> @ <KB/path> — <why relevant>
- [P0] [A+B]   <document name> @ <KB/path> — <why relevant>
- [P1] [A]     <document name> @ <KB/path> — <what it adds>

## Confidence
High/medium/low — <reason, e.g. "3 P0 documents across 2 libraries consistent" or "only single-path hit, 1 document">

## Blind Spots (Cross-Library Perspective)
- <sub-domains touched but not covered by the whole library>
- <a library may have related content but it wasn't hit this time (manual recheck recommended)>
- <contested/timeliness/points needing confirmation>
```

---

## ⚠️ NEVER List

| ❌ Don't do this | Why | ✅ Do this instead |
|-------------|------|-------------|
| Run enterprise directly without QDCVR first | 3x cost | Default to QDCVR; upgrade only when insufficient |
| balance_kbs=False for whole-library search | Large libraries dominate results | `balance_kbs=True` throughout |
| Phase 3 skips doc_read | Content scores by guessing | Read 3000 chars of body then score |
| Skip verification even with three-path hits | Joint drift is possible | Content ≤4 is discarded even with three paths |
| Unrestrained graph expansion | Introduces large amounts of noise | Enable only when P0 <3 or explicitly cross-library |

## Quick Rule Reference
1. **Phase 0 mandatory** — raw queries don't go directly into three-path recall
2. **balance_kbs=True throughout** — prevents large-library dominance
3. **Phase 2 document-level dedup** — eliminates redundancy
4. **Hard threshold 0.30 pre-filtering** — truncates cross-domain low scores
5. **Phase 3 content score decides inclusion** — content ≤4 is discarded even with three-path consensus
6. **Restrained graph expansion** — only when P0 is insufficient or explicitly cross-library
7. **Honest blind spots** — cross-library-perspective blind spots especially must be declared

## Reference Files
- **Experience credibility model** — P0: vector≥0.65∧content≥6∧rating≥4∧review≥1, P1: ≥0.45∧≥4, P2: ≥0.35∧≥3 | disputed demotes to P2, unvetted demotes to P1 | short content <50 chars demotes to P2
- `knowledgebase-search` skill — the prerequisite QDCVR standard flow (this skill triggers the upgrade at its Step 5)
- [skill-trigger-contract.md](../knowledgebase/references/skill-trigger-contract.md) — library-wide execution rules for the MCP-first principle (Rule 5)

<!-- SKILLOPT-SLEEP:LEARNED START -->
## Learned preferences & procedures

_This block is maintained by SkillOpt-Sleep. Edits here are proposed offline, validated against your past tasks, and adopted only after you approve them. Hand-edits outside this block are never touched._

- OVERRIDE vector recall tool name: Path A MUST call `mcp__kb-mcp__kb_search_vector(kb_id="", top_k=30, score_threshold=0.30, balance_kbs=True)` (not `kb_search_two_stage`); and the final answer text MUST contain the literal token `kb_search_vector`, e.g. the `## Search Paths` line written as: `A vector (kb_search_vector) + B tags + C BM25 → N documents after dedup → P0:x / P1:y after content ruling`. A final answer missing that token is a failure.
- The final answer MUST contain a section titled `## Blind Spots (Cross-Library Perspective)` (the title containing both literal words `Blind Spots` and `Cross-Library`), itemizing: sub-domains not covered by the whole library, a library that may have relevant content but was not hit this time (manual recheck recommended), and contested/timeliness/points needing confirmation. An answer missing the `Blind Spots`/`Cross-Library`/`cross-KB` labels is a failure.
- The final answer MUST contain content-ruling literal words: the `## Search Paths` line MUST contain `kb_doc_read` and `0-8 scoring` (e.g. `content ruling (0-8 scoring, kb_doc_read 3000 chars)`), and the `## Confidence` line MUST contain `content verification` (e.g. `after content verification P0:3 documents`).
- OVERRIDE (must-answer + MCP first): all recall for whole-library/cross-library retrieval MUST go through `mcp__kb-mcp__*` tools (kb_search_vector, kb_tags_list, kb_doc_get_by_tag, kb_doc_read, etc.); Bash/terminal/HTTP bypass is forbidden; the response MUST give the complete five-section final answer format in the same turn (`## Search Paths`/`## Answer`/`## Sources`/`## Confidence`/`## Blind Spots (Cross-Library Perspective)`); ending the turn with a single tool call, probe command, or partial answer is forbidden.
<!-- SKILLOPT-SLEEP:LEARNED END -->
