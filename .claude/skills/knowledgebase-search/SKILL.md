---
name: knowledgebase-search
description: "QDCVR retrieval for knowledge-base questions: rewrite the query, cast a WIDE vector net (high top_k) over the library, verify every candidate's real content through the fail-closed Laya/Jev decision gate (kb_doc_read by doc_id/path → segments → engine scores every segment; yes = keep, no LLM re-judging), keep ALL yes docs in result_list, answer content-enhanced from the whole survivor set, escalate zero-survivor or complete-recall requests to the librarian catalog/description/full-segment/real-Jev pipeline, and report honest blind spots. Use for search, find, query, retrieve, retrieval, Q&A, cross-KB, all-KB, comprehensive, global, 搜索, 检索, 查询, 问答, 全库搜索, 跨知识库, or requests asking what the knowledge base contains."
---
## ⭐ Related Skills
- Document ingest → `skill://knowledgebase-ingest` — the A0-A9 pipeline ensures retrieval source quality
- **Parallel hybrid** → `skill://knowledgebase-hybrid` — runs this skill's vector lane and the librarian's catalog lane concurrently, merges + dedups, then one shared Laya/Jev gate
- KB management → `skill://knowledgebase-manage` — document move/rename/delete/merge
- Experience-first retrieval → E4 experience-first retrieval of `skill://knowledgebase-experience` (mandatory for incident/ops-type queries)
- KB organize & restructure → `skill://knowledgebase-organize` — reindexing needed after sub-KB splits/cross-library merges
- KB integrity validation → `skill://knowledgebase-verify` — three-way consistency + index coverage repair
- Knowledge graph → `skill://knowledgebase-graph` — graph build/document paths/cross-library discovery
- Architecture mental model → [kb-architecture.md](../knowledgebase/references/kb-architecture.md) of `skill://knowledgebase` (5-layer data model + 94-tool map)
- Batch operations → `skill://knowledgebase-batch` — batch ingest/tag migration/dedup

## Sequential Workflow
**Phase 0 — Query prep**: intent classification (factual/method/comparison/incident/navigational) → core entity extraction → rewrite as declarative sentence + keywords. Incident/ops → experience library first.
**Phase 1 — Vector wide net + Jev verify gate (fast lane)**: `kb_search_vector` on the whole library (or the KB the user named) with `balance_kbs=True` and a HIGH top_k (default 30) → hard-threshold + document-level dedup, keep ALL deduped docs → **Jev verify gate**: batch `kb_doc_read` every candidate by doc_id/path, structure-segment the real body, and let the real Laya (default) / Jev engine score EVERY segment (fail-closed, script: `scripts/vector_jev_search.py`) → every doc with ≥1 yes segment enters `result_list` → answer content-enhanced from the whole survivor set.
**Phase 2 — Librarian deep fallback (zero survivors):** traverse every KB and unlimited-depth sub-KB in the catalog, label shelves `relevant/possible/out_of_scope`, retain all `relevant/possible` shelves for complete-recall requests, read every document description, read every candidate segment, invoke the real Jev filter — **the librarian lane ends at the engine gate: every yes-scored survivor (score ≥ threshold) is evidence, delivered whole as knowledge enhancement with no re-scoring and no pruning**; answer from all of it.
**Phase 3 — Answer or honest report**: P0/P1 structured answer with sources; if both paths fail → honestly declare the blind spot (what was tried, what is missing, suggested next steps). Never fabricate.

# QDCVR v2 — Query-Driven · Content-Ruled · Vector-First with Librarian Fallback

## ⭐ Execution Model · Pre-Flight · Architecture (First Step of Any Job, Mandatory)

**Executor: Archival agent** — delegate via `task` (**delegation template + three-role execution model + combined-task boundaries**: must-read [execution-model.md](../knowledgebase/references/execution-model.md)). **Pre-Flight**: no work before it passes — one-probe double-check `kb_project_status` → branch handling → smoke test; full flow in [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md). **Mental model**: before operating, must-read [kb-architecture.md](../knowledgebase/references/kb-architecture.md) (5-layer model + consistency invariants + 94-tool map); MCP-first principle (no terminal/HTTP bypass) in [skill-trigger-contract.md](../knowledgebase/references/skill-trigger-contract.md) Rule 5.

- Archival is forbidden from: skipping Phase 0 query rewriting, skipping the Jev verify gate, skipping the librarian fallback when the vector path yields zero survivors, skipping blind-spot declaration
---

## The One Picture (algorithm contract)

```
query
  │
  ├─ Phase 0 · Query prep            rewrite before retrieving; never feed raw queries
  │
  ├─ Phase 1 · VECTOR WIDE NET       kb_search_vector (top_k=30) → dedup+threshold
  │     │                            → kb_doc_read EVERY candidate (doc_id/path)
  │     │                            → segments → real Laya/Jev scores every segment
  │     ├─ ≥1 yes doc ──────────────►✅ answer from ALL survivors (result_list)
  │     └─ zero survivors ──────────►▼ vector path found no true evidence
  │
  ├─ Phase 2 · LIBRARIAN FALLBACK    read every KB/doc description → every candidate segment
  │     │                            → real Jev gate: yes ≥ threshold = keep ALL
  │     └─ Jev survivors ───────────►✅ answer from all of them · ✖ zero survivors → ▼
  │
  └─ Phase 3 · HONEST REPORT         report honestly: declare the blind spot, never fabricate
```

**Why this order**: vectors are fast semantic proposals, but a vector score is only a
candidate. The verify gate reads every candidate's real body (by doc_id/path) and lets
the decision engine — not an LLM rubric, not the vector score — decide which documents
hold answer evidence. Wide net + per-segment engine judgment finds ALL documents related
to the question scenario, not just the single best chunk. Only the aggregated,
engine-scored evidence enters the answer; if scope or the engine is unavailable, report
the exact blind spot.

**Six iron rules** (including the ⭐ MCP-first principle):
1. **Vector wide net first** — Phase 1 always starts with `kb_search_vector` at a HIGH top_k (default 30); do not pre-run BM25 or KB selection ceremonies. Whole-library default with `balance_kbs=True` prevents large-library dominance.
2. **Understand before retrieving** — Phase 0 rewrites the raw query; never fed directly to the retriever.
3. **The Jev gate owns the verdict** — candidates are verified by real content (batch `kb_doc_read` by doc_id/path → segments → engine scores every segment, fail-closed). A vector 0.95 whose segments all score no is *discarded*; a vector 0.40 with a yes segment survives. Vector scores never overrule the engine.
4. **Zero survivors triggers the librarian, not surrender** — an empty result_list means the vector path found no true evidence; Phase 2 MUST run before any "no result" conclusion.
5. **Better to give nothing than to give something wrong** — when both paths fail, honestly declare the blind spot; never fabricate.
6. **All yes docs, no second-guessing** — every doc with ≥1 yes segment enters `result_list` (score-sorted, no rubric, no retention cut); the answer draws on the WHOLE survivor set as knowledge enhancement.

**Freedom Map** (freedom level per phase):
| Phase | Freedom | Notes |
|------|--------|------|
| Phase 0 rewrite / Jev verify gate / Phase 2 fallback trigger / Phase 3 blind-spot declaration | 🔒 **Mandatory** (low freedom) | Core gates; cannot be skipped or simplified |
| Phase 1 top_k/threshold tuning / Phase 2 shelf-ranking depth | 🎯 **Execute** (medium freedom) | Tune top_k (wide net) /threshold per the scenario tables; decide how deep to walk the tree |
| Phase 0 rewrite depth / librarian "most likely shelf" judgment | 🧠 **Judgment** (high freedom) | Judge from query semantics; the decision tables guide but are not mechanical |
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
| **Navigational** | "where is", "is there" | `kb_list(lightweight=true)` + `kb_get_documents(lightweight=true)` description matching; complete requests continue through all candidate segments and Jev |

### 0b Core Entity Extraction
Extract: **subject** (PET/RAG/lithium batteries) + **attribute** (crystallinity/hallucination/thermal management) + **constraints** (process parameters/2024).

### 0c Query Rewriting
- Raw colloquial query → **declarative sentence + keyword combination**
- Example: `"The influence of PET film biaxial stretching process parameters on crystallinity"`
  → Rewrite (vector): `"The influence of stretch ratio/temperature/speed on crystallinity and crystal structure in PET polyester film biaxial stretching"`
- Multi-concept queries → **split into sub-queries and retrieve in parallel** (mandatory for comparisons)

## Phase 1 — Vector Wide Net + Jev Verify Gate (Fast Lane) ⭐

### 1a Vector recall (wide net, whole-library by default)

```
kb_search_vector(
    query=the Phase 0 rewritten query,
    kb_id=<the KB the user named> or "" (whole library),
    top_k=30,                  # ⭐ wide net: recall MANY candidate docs in one pass
    score_threshold=0.35,
    balance_kbs=True           # ⭐ mandatory for whole-library search; prevents large-library dominance
)
```

**Hierarchical KB pass-through** (parent KB containing sub-KBs): sub-KB document vectors live in the **sub-KB's own collection** (`kb_<sub-KB UUID>`) — searching the sub-KB UUID directly returns its documents, and searching the **parent KB** aggregates all descendant documents. A result whose `doc_path` carries a sub-KB prefix and non-empty content is a successful pass-through. `kb_search_two_stage` on a parent may return sub-KB container entries (empty content) — retrieve real content with `kb_search_vector`. `kb_graph_kb_overview(kb_id)` is for viewing structure only, never a search entry.

**Empty handling**: 0 results → retry once with `score_threshold=0.30`; still 0 → go directly to Phase 2.

### 1b Filter (before reading)

```
1. Hard threshold: drop chunks with score < 0.35 (0.30 on the retry pass)
2. Document-level dedup: per normalized doc_path keep only the highest-scoring chunk
3. KEEP ALL deduped docs — no top 3-5 cut; the wide net exists precisely so the
   engine can judge many documents (recall now, precision by engine verdict)
```
**Exception**: comparison queries may additionally keep the best chunk for both entities.

### 1c ⭐ Jev verify gate (the engine — not an LLM rubric — decides)

For EVERY deduped candidate, read the real body by doc id/path and let the decision engine judge it:

```
kb_doc_read(kb_id, doc_path, max_chars=20000)    # full read; verify input = doc_id/doc_path
```
then structure-segment the body (headings/paragraphs/lists/tables/code, sentence fallback) and send EVERY segment to the real engine. The scripted form (preferred — one command does recall→reads→segments→gate→result_list):

> **Interpreter**: run judging scripts with `backend/.venv/Scripts/python.exe` — the MinerU env hosting `laya` + GPU torch (Laya auto-selects CUDA). Bare `python` without `laya` fails closed (`JevUnavailable`).

```bash
python .claude/skills/knowledgebase-search/scripts/vector_jev_search.py \
  --query "<rewritten query>" --top-k 30 --engine laya --require-real \
  --output tmp/vector-jev.json
# manual form: build the candidate manifest yourself and run
#   python .claude/skills/knowledgebase-librarian/scripts/jev_filter.py \
#     --engine laya --input candidates.json --output judged.json --require-real
```

Engine semantics (shared with the librarian/hybrid lanes):

- default engine `laya` (local SDK, repo-local checkpoint; `noul=P(true)`); explicit `engine=jev` only when remote Jev is intentionally selected; engines never silently fall back to one another;
- every segment gets a score record; missing SDK/model, request errors, malformed/out-of-range scores are **fail-closed** — the segment is rejected, never an implicit pass;
- lookup/evidence query → `criterion=evidence`; enumeration/completeness query → `criterion=instance` (auto-detected from the query);
- **no LLM 0-8 rubric anywhere in this lane** — the former read-and-judge-by-rubric step is replaced by the engine gate on real body text (which also removes the head-window blind spot: the full read feeds every segment, not just the first 3000 chars).

### 1d Gate decision (yes = keep ALL)

| Engine verdict | Verdict | Action |
|---|---|---|
| Doc has ≥1 yes segment (score ≥ threshold) | ✅ evidence | Enter `result_list` (score-sorted); answer draws on it |
| All segments no | ❌ not evidence | Discard (recorded in `judge.doc_scores` for audit) |
| Zero docs survive | ▼ vector path found nothing | Run Phase 2 librarian fallback before any "no result" |
| Engine `unavailable`/`error` | ⚠️ gate did not run | Report the blind spot; do NOT answer from unscored text |

The engine verdict is final: no content rubric, no doc-level retention cut, no P0/P1 tiering after the gate. `(part k of N)` split docs are handled naturally — the vector hit part is read in full and cited concretely; siblings may enter via Phase 2 complete recall when the question needs them.

## Phase 2 — Librarian Deep Fallback (when the gate fails) ⭐

> **Standalone form**: this phase is packaged as `skill://knowledgebase-librarian` — the complete-recall catalog/read/Jev lane (L0 all KBs and unlimited-depth sub-KBs → L1 relevant/possible labels → L2 all document descriptions → L3 description trust → L4 all candidate segments → L5 real Jev → aggregate ALL yes-survivors → L6 handoff).
> **This skill is the vector + Jev-gate lane** (`kb_search_vector` wide net → doc reads → engine gate). Use the Librarian lane when the shelf is unknown, the library is large/heterogeneous, similarity search missed, the question spans a long document, or the request asks for all/every/comprehensive recall.
> Both lanes end in the same engine-yes gate and five-section answer, but complete-recall results must include Jev backend/threshold and exact unscanned blind spots.

> The librarian walks the complete catalog: it reads every retained shelf summary and document description, then every candidate segment, sends all segments through the real Jev filter, and aggregates only scored evidence. This phase supersedes the former targeted enterprise/multi-path fallback for complete-recall requests.

### 2a Walk the Stacks (complete-recall mode)

```
catalog = kb_list(lightweight=true)     # EVERY KB: {kb_id, name, description, doc_count}
tree    = fs_get_tree(max_depth=2)       # hierarchy and sub-KBs
```

For ordinary fallback, label every KB `relevant / possible / out_of_scope`; when the query asks for all/every/comprehensive or the caller explicitly selects Librarian, keep every `relevant` and `possible` shelf rather than a fixed top-2/3. Read `kb_get_documents(lightweight=true, kb_id)` for every kept shelf. The lightweight catalog must retain `doc_id/file_id/doc_path/name/description`; group split siblings for logical-document reasoning but preserve each concrete part identity.

### 2b Description trust and candidate manifest

A description is a candidate-generation signal, never the final verdict. Check boilerplate, empty/content-free claims, contradictory section ranges, and degenerate labels. An untrusted description expands content reads instead of pruning the document. For every kept part, use paginated `kb_doc_read` to cover the readable body, segment it at structure-safe boundaries, and record `{kb_id, doc_id, doc_path, part, section, start_line/end_line, start_char/end_char, text}`. Any unread document/part is listed as an explicit blind spot.

### 2c Jev filtering and aggregation

Pass the complete candidate manifest to `.claude/skills/knowledgebase-librarian/scripts/jev_filter.py`. Every segment receives a real Jev `noul` verdict (`evidence` for lookup, `instance` for enumeration). Missing/error/out-of-range scores fail closed; no unscored segment enters the evidence pack. Aggregate scored survivors by source and offset, preserve Jev scores and provenance — **every yes-scored survivor is evidence; no rubric, no retention cut, no P0/P1 tiering after the gate** (same contract as Phase 1 and the librarian lane).


**Final confidence** (coverage-based, not score-tiered):
| Situation | Confidence |
|---|---|
| Multiple yes survivors across ≥2 KBs, mutually consistent | **High** — cite directly |
| 1-2 survivors in a single KB | **Medium** — attribution advised |
| Zero survivors on both paths (or engine `unavailable`) | **Blind spot** — honest report, never fabricate |

Answer from ALL survivors of both lanes; if Phase 2 produced nothing beyond Phase 1's survivors, say so.

## Phase 3 — Answer or Honest Report (Mandatory Standards)

Complete-recall answers must cite concrete `doc_id/doc_path`, part, section, line/char offsets, and Jev score. The `Search Paths` section must state L0/L1/L2/L3/L4 counts, Jev backend/criterion/threshold, aggregate survivor count, and any unscanned scope.

### On hit — synthesized answer (five sections, all mandatory)

```
## Search Paths
Phase 1 vector wide net (kb_search_vector, top_k=30, balance_kbs) → dedup → Jev verify gate (kb_doc_read by doc_id/path + jev_filter, Laya): N candidates → M yes docs in result_list;
Phase 2 Librarian complete-recall (all KB/doc descriptions + all candidate segments + real Jev) → all yes survivors (only when Phase 1 yielded zero survivors)

## Answer
<Synthesized from P0 documents, citing specific data/conclusions; P1 as supplement>

## Sources (sorted by engine score + path consensus)
- [<judge score>] <document name> @ <KB/path> — <why relevant, one sentence> (split docs: cite the concrete `(part k of N)` hit)

## Confidence
High/medium/low — <reason, e.g. "M yes docs across 2 KBs consistent" or "only 1 survivor in one KB; deeper verification recommended">

## Blind Spots (Cross-Library Perspective)
- <sub-domains the query touches but the whole library does not cover>
- <a library that may hold related content but was not hit this time — manual recheck recommended>
- <contested/timeliness/points needing user confirmation>
```

### On total failure — honest report (report honestly, first-class outcome)

When Phase 1 Jev gate yields zero survivors AND Phase 2 yields zero survivors:
```
## Answer (No Confirmed Hit)
<One sentence: the knowledge base cannot currently answer this question.>

## What Was Tried
- Phase 1 vector: kb_search_vector(<rewritten query>, top_k=30, threshold 0.35→0.30) → N candidates, M yes survivors (Jev backend/threshold; <what the top-scoring no-docs were about instead>)
- Phase 2 Librarian: read every retained KB description, every document description, every candidate segment, and run `jev_filter.py`; report the exact scanned/unscanned scope and whether Jev was available.

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
| Start with BM25/two-stage or KB-selection ceremonies | The fast lane starts with vectors; complete recall is a separate catalog/read/Jev contract | Phase 1 `kb_search_vector` wide net first, then complete-recall fallback when required |
| Trust a high vector score without the engine gate | Cosine ≠ answerable; and a modest score may still hold evidence | Jev verify gate: batch `kb_doc_read` by doc_id/path → segments → real engine scores every segment |
| Cut the candidate pool to top 3-5 before judging | The whole point of the wide net is letting the engine find ALL related docs | Keep ALL deduped docs; the gate (not a rank cut) decides |
| Declare "no result" after Phase 1 alone with survivors empty | Vector miss ≠ corpus miss; but also never answer from unscored text | Zero survivors → Phase 2 librarian fallback; engine `unavailable` → blind-spot report |
| Walk the stacks by guessing KBs | Summary-reading is the librarian's whole edge | Read EVERY KB description in `kb_list(lightweight)` before judging |
| Keep score <0.35 chunks | Cross-domain low-score pollution | Hard-threshold truncation both phases |
| Re-score, re-rank or prune Jev-yes docs | The engine verdict is final; extra cuts recreate recall loss | result_list = ALL yes docs, score-sorted |
| Treat `(part k of N)` siblings as separate books | Part 1 doesn't represent the whole; counting inflates | Group by stem; read the HIT part; cite the concrete part |
| Include Jev-no segments in the answer | Better to give nothing than something wrong | Discard → fallback → if nothing, honest report |
| Answer without the five sections / blind-spot declaration | The user assumes the KB covers everything | Mandatory output standards above |

## Quick Rule Reference
2. **Phase 0 mandatory** — raw colloquial queries are not retrieved directly
3. **Jev gate owns the verdict** — wide net (top_k=30) → keep ALL deduped docs → batch `kb_doc_read` by doc_id/path → real Laya/Jev scores every segment (fail-closed); yes docs ALL enter result_list
4. **Zero survivors → complete-recall librarian fallback** — read all retained KB summaries and document descriptions → all candidate segments → real Jev → all yes survivors → answer
5. **Document-level provenance** — preserve every concrete part/path/offset; do not replace complete mode with a top-k or head-only shortcut
6. **Engine verdict > vector score > path consensus** — evidence must be engine-scored on real body text; unscanned scope is a blind spot
7. **Experience first** — incident/ops-type queries check experiences first
8. **Honest blind spots** — both paths failed or Jev unavailable → report what was tried and what remains unscanned

<!-- SKILLOPT-SLEEP:LEARNED START -->
## Learned preferences & procedures

_This block is maintained by SkillOpt-Sleep. Edits here are proposed offline, validated against your past tasks, and adopted only after you approve them. Hand-edits outside this block are never touched._

- The Phase 1 vector recall tool is `mcp__kb-mcp__kb_search_vector(kb_id="", top_k=30, score_threshold=0.35, balance_kbs=True)`; the verify gate is `python .claude/skills/knowledgebase-search/scripts/vector_jev_search.py --query "..." --top-k 30 --engine laya --require-real`. The final answer's `## Search Paths` line MUST contain the literal token `kb_search_vector`. A final answer missing that token is a failure.
- The final answer MUST contain a section titled `## Blind Spots (Cross-Library Perspective)` (title containing both literal words `Blind Spots` and `Cross-Library`), itemizing: sub-domains not covered, a library that may have relevant content but was not hit (manual recheck recommended), and contested/timeliness/points needing confirmation. Missing the `Blind Spots`/`Cross-Library` labels is a failure.
- The `## Search Paths` line MUST contain `kb_doc_read` and `jev_filter` (or `Laya`); the `## Confidence` line MUST contain `Jev verification` (e.g. `after Jev verification M/N docs survived`). Missing these literals is a failure.
- MUST-answer + MCP first: all catalog/read operations MUST use `mcp__kb-mcp__*`; complete-recall requests must finish the catalog → descriptions → full segments → `jev_filter.py` → all yes survivors → answer contract in the same turn or explicitly report the unscanned scope.
<!-- SKILLOPT-SLEEP:LEARNED END -->
