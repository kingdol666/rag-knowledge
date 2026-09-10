---
name: knowledgebase-organize
description: >
  Full collection restructuring engine. O1→O8 workflow (plus O5b three-way
  consistency): hierarchical discovery (sub-KB split detection + cross-KB merge
  analysis), deep content audit (1000+ chars per doc), tiered fix execution,
  sub-KB auto-creation, cross-KB merge, parent restructuring, vector index +
  graph rebuild, three-way consistency, hygiene cleanup. No document splitting.
  Triggered by: organize, clean, restructure, inventory, full review, organize, restructure, cleanup,
  reorganize, clean the knowledge base, organize the knowledge base, deep clean, consolidate, merge, split, subdivide, tier, archive, categorize.
---

# Knowledge Organize — Whole-Library Intelligent Restructuring Engine

## ⭐ Execution Model · Pre-Flight · Architecture (First Step of Any Job, Mandatory)

**Executor: Archival agent** — delegate via `task` (**delegation template + three-role execution model + combined-task boundaries**: must-read [execution-model.md](../knowledgebase/references/execution-model.md)). **Pre-Flight**: no work before it passes — one-probe double-check `kb_project_status` → branch handling → smoke test; full flow in [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md). **Mental model**: before operating, must-read [kb-architecture.md](../knowledgebase/references/kb-architecture.md) (5-layer model + consistency invariants + 91-tool map); MCP-first principle (no terminal/HTTP bypass) in [skill-trigger-contract.md](../knowledgebase/references/skill-trigger-contract.md) Rule 5.

> This skill depends heavily on Neo4j (L7 index + graph rebuild); `kb_project_start` must include `neo4j=true`.
> **Authoritative threshold source**: sub-KB split/merge thresholds are uniformly defined in [sub-kb-creation.md](../knowledgebase-ingest/references/sub-kb-creation.md). This skill and Ingest A8 share the same thresholds (≥6 documents to check, ≥8 to auto-split), avoiding inconsistency.

## ⭐ Related Skills
- Document ingest → `skill://knowledgebase-ingest`
- KB management → `skill://knowledgebase-manage`
- Validation & verification → `skill://knowledgebase-verify`
- Batch operations → `skill://knowledgebase-batch`
- Sub-KB creation protocol → [sub-kb-creation.md](../knowledgebase-ingest/references/sub-kb-creation.md) of `skill://knowledgebase-ingest`
- Experience linkage → `skill://knowledgebase-experience`
- Architecture mental model → [kb-architecture.md](../knowledgebase/references/kb-architecture.md) of `skill://knowledgebase`

## Sequential Workflow (O1→O8)
**Step 1 — O1 global survey**: kb_list + kb_tags_list + fs_get_tree → whole-library topology map.
**Step 2 — O2 deep audit**: kb_doc_read(1000 chars) per document → mark description/tag/domain quality + **kb_find_duplicates(kb_id) to detect duplicate document pairs** (exact SHA256 + near vector ≥0.90).
**Step 3 — O3 hierarchy analysis**: sub-KB split detection + cross-KB merge detection + hierarchy analysis.
**Step 4 — O4 fix execution**: L1 descriptions→L2 tags→L3 reclassification→L4 splits→L5 merges→L6 hierarchy→L7 indexes.
**Step 5 — O5 per-layer verification**: after each layer's fixes, immediately run O5+O5b three-level consistency.
**Step 6 — O6 experience linkage**: experience_check_stale + mark experiences needing review.
**Step 7 — O7 compliance strategy**: filter the fix scope per the user-specified strategy.
**Step 8 — O8 final report**: before/after comparison + fix statistics + compliance score.

## Core Capabilities

This skill performs the following seven classes of organizing operations, executed in complexity order:

| Layer | Operation | Description |
|------|------|------|
| **L1** | Description fixes | Content-driven rewriting of document/KB descriptions |
| **L2** | Tag hygiene | Blocklist removal → synonym merging → orphan removal |
| **L3** | Document reclassification | Misplaced documents moved to the correct KB |
| **L4** | KB → sub-KB splitting | Large KBs split into sub knowledge bases by sub-domain |
| **L5** | Cross-KB merging | KBs with overlapping domains merged into one parent KB + sub-KBs |
| **L6** | KB hierarchy restructuring | Create/rename/restructure the parent-KB-sub-KB hierarchy tree |
| **L7** | Index + graph rebuild | Whole-library vector indexing, knowledge graph rebuild |

---

## Mental Framework: Five Things to Settle Before Organizing ⭐

1. **What scope did the user specify?** — "organize everything" = whole library; "organize thermal engineering" = single KB; not said? Ask first.
2. **How many sub-domains does this KB have?** — ≥2 sub-domains and ≥6 documents → consider splitting.
3. **Any duplicate/overlapping KBs?** — Content overlap ≥60% → consider merging.
4. **Fix priorities?** — Description quality > tag standards > KB attribution (L3) > sub-KB splitting (L4) > merging (L5) > hierarchy (L6) > indexing (L7).
5. **Where must content be read?** — 1000 chars cannot be skipped. Changing classification without reading content = guessing; forbidden.

---

## Rules

1. **Every item's content must be read for 1000 chars** — `kb_doc_read(max_chars=1000)`; never substitute filenames/paths
2. **Verify fixes batch by batch** — execute L1→L7 in order; verify as soon as each layer completes; do not pile up verification to the end
3. **Split decisions cannot be skipped** — every KB at or above `SUB_KB_CHECK_THRESHOLD` (≥6 documents; see the authoritative source in [sub-kb-creation.md](../knowledgebase-ingest/references/sub-kb-creation.md)) must be checked for whether it needs sub-KB splitting
4. **Merge decisions cannot be skipped** — every pair of domain-overlapping KBs must be evaluated for mergeability
5. **File splitting is forbidden** — documents are complete units; no truncation/summarization/splitting
6. **⭐ MCP first** — all operations go through MCP tools; terminal/HTTP bypass is forbidden
7. **Confirm before executing** — any irreversible operation (delete/merge KB) must be executed only after user confirmation
8. **Single-document KBs must be consolidated** — a KB with only 1 document cannot exist independently; marked "pending consolidation" in O3
9. **Three-axis weight adaptation** — when the tag vocabulary is empty: entity_sim rises to 0.55 and domain_sim rises to 0.45 (tag data being absent makes it untrustworthy)
10. **O3 auto-generates the combo** — after O3a+O3b run, a combined merge+split plan must be generated; do not make the user assemble it manually

**Freedom Map** (freedom level per step):
| Step | Freedom | Notes |
|------|--------|------|
| L1 description fixes / L2 tag hygiene / L7 index rebuild | 🎯 **Execute** (medium freedom) | Batch execution per the rules; verify layer by layer |
| L3 document reclassification / L4 sub-KB split / L5 cross-KB merge / L6 hierarchy restructure | 🧠 **Judgment** (high freedom) | Requires domain judgment based on 1000 chars of content; the decision tree guides but is not mechanical |
| O5 per-layer verification / O5b three-way consistency | 🔒 **Mandatory** (low freedom) | Verify as soon as each layer completes; do not pile up; consistency checks cannot be skipped |
| L4/L5/L6 execution (irreversible operations) | 🔒 **Mandatory** (low freedom) | Splits/merges/restructures must show the plan and wait for user confirmation before executing |

---

## O1 — Global Survey

```
kb_list()                              # all KBs (UUID + description + doc count)
kb_tags_list()                         # global tag vocabulary
fs_get_tree(include_files=False, max_depth=0)  # KB hierarchy structure
```

**Output**: whole-library topology — parent KBs, sub-KBs, isolated KBs, empty KBs, test KBs.

---

## O2 — Deep Content Audit

> **Parallel speedup**: when KB count > 8 or total documents > 50, delegate sub-agents to audit KBs in parallel.

For every non-empty KB, read each document's content and mark its state:

```
for each doc in KB:
    content = kb_doc_read(max_chars=1000)
    
    # Mark
    mark:
      desc_quality:    [OK | MISSING | FILENAME | GENERIC | MISMATCH]
      tag_quality:     [OK | EMPTY | GENERIC | BLOCKLIST | COUNT_LOW]
      domain:          <sub-domain inferred from content>
      kb_alignment:    [MATCH | MISMATCH]
      suggested_tags:  <[2-5 content-derived tags]>    ← ⭐ auto-generated during audit
```

> **Tags are auto-generated in the O2 audit phase**, not deferred to L2. L2 only cleans, normalizes, and batch-writes back.

> ⏱ Estimate: ~1s per document; 100 documents ≈ 2 minutes.

**Note**: when KB count > 10, delegate content audits to sub-agents via `task(tasks=[{"agent":"archival","name":"KB-Audit","task":"audit KB docs...","effort":"med"}])`, processing 4 KBs per group in parallel.

---

## O3 — Hierarchy Topology Analysis ⭐ (New Core Capability)

### 3a. Sub-KB Split Detection

For every KB with document count ≥ `SUB_KB_CHECK_THRESHOLD` (**≥6 documents**; see the authoritative source table in [sub-kb-creation.md](../knowledgebase-ingest/references/sub-kb-creation.md)), analyze its content's sub-domain distribution.
**Must use** the [three-axis similarity protocol in sub-kb-creation.md](../knowledgebase-ingest/references/sub-kb-creation.md#multi-dimensional-similarity-scoring):

```
scan KB → read 1000 chars of each document → extract key entities → group into sub-domains (same entity_sim ≥ 0.4 groups together)
Result: {kb_id, kb_name, doc_count, sub_domains: {sub_domain: [doc_paths]}}
```

**Split condition**: ≥2 sub-domains (inter-group similarity ≤ 0.25), each with ≥2 documents.

### 3b. Cross-KB Merge Detection

For all KB pairs (especially similarly named ones), **must** compute the three-axis composite similarity:

```
Axis 1 (0.3) = tag_similarity:    |tags(a) ∩ tags(b)| / |tags(a) ∪ tags(b)|
Axis 2 (0.4) = entity_similarity: |entities(a) ∩ entities(b)| / |entities(a) ∪ entities(b)|
Axis 3 (0.3) = domain_similarity: three-level classification comparison (l1/l2/l3)

total = 0.3*tag + 0.4*entity + 0.3*domain
```

For the full decision matrix, see [sub-kb-creation.md § Decision Matrix](../knowledgebase-ingest/references/sub-kb-creation.md#decision-matrix).

### 3c. KB Hierarchy Analysis

```
Current state:
  flat: all KBs flat, no parent-child relations
  partial: some have parents, some are scattered
  structured: complete hierarchy already exists

Optimization goals:
  flat → create parent KBs and group sub-KBs
  partial → fill in missing parent KBs
  structured → verify the tiering is reasonable
```

**Output**: `topology_report` — listing each KB's split/merge/hierarchy recommendations.

> **Key**: this step's results must be shown to the user for confirmation; irreversible operations (merge/delete) require user approval.

---

## O4 — Fix Execution (In Layer Order; Verify With O5 After Each Layer)

Execute in L1→L7 order; verify immediately after each layer. Detailed execution pseudocode, dialogue templates, and parameters in [execution-details.md](references/execution-details.md).

| Layer | Operation | Risk | Key commands |
|------|------|------|---------|
| **L0** dedup cleanup | Delete exact/near duplicate documents | Needs verification | `kb_find_duplicates` → `kb_doc_delete` (keep the more complete version; merge tag/description differences) |
| **L1** description fixes | Content-based description rewriting (four elements) | Zero risk | `kb_doc_update_meta` / `kb_update` |
| **L2** tag hygiene | T1 blocklist removal + T2 normalization + T3 counts | Zero risk | `kb_doc_update_tags` (blocklist in [tag-quality-rules.md](../knowledgebase-ingest/references/tag-quality-rules.md)) |
| **L3** document reclassification | Move misplaced documents to the correct KB | Needs verification | `kb_doc_move` + `kb_index_document` |
| **L4** sub-KB split | KBs detected as splittable by O3a | **Needs user confirmation** | `kb_create(parent_id)` + `kb_doc_move` + `kb_batch_index(force=true)` |
| **L5** cross-KB merge | KB pairs detected as mergeable by O3b | **Needs user confirmation** | `kb_doc_move` → `kb_delete(source)` + `kb_graph_build(force=true)` |
| **L6** KB hierarchy restructure | Create/rename/delete parent KBs | **Needs user confirmation** | `kb_create` / `kb_update` / `kb_delete` |
| **L7** index + graph | Vector coverage + graph rebuild | Infrastructure | `kb_batch_index(force=true)` + `kb_graph_build(force=true)` |

**L4 splits/L5 merges must show the plan and wait for user confirmation before executing** (irreversible operations).

---

## O5 — Per-Layer Verification + O5b Three-Level Consistency

Verify immediately after each layer's fixes (verification method table in [execution-details.md](references/execution-details.md) §O5).

**O5b (mandatory)**: after L3/L4/L5/L6, must validate three-layer metadata (disk ↔ .tree-fs.json ↔ .knowledge-base.yml) + UUID sync + 20% content sampling. Fix rules in [execution-details.md](references/execution-details.md) §O5b.

---

## O6 — Experience Linkage

```
for each KB with structural changes (L4/L5/L6):
    experience_check_stale(kb_id)
for each stale experience:
    report — "The related documents of N experiences have been migrated; review recommended"
```

## O7 — Custom Compliance Strategy

Users may specify extra compliance requirements. Everything runs by default; if the user says "fix only descriptions and tags", run only L1+L2+L7. The strategy table (strict_descriptions/clean_tags/align_docs/split_kbs/merge_kbs/hierarchy/full_index) is in [execution-details.md](references/execution-details.md) §O7.

## O8 — Final Report

Before/after state comparison + fix counts for each L1-L7 layer + compliance score (C1 descriptions/C2 tags/C3 alignment/C4 vectors/C5 graph/C6 three-way consistency) + experiences pending.

---

## ⚠️ NEVER List

| ❌ Don't do this | Why | ✅ Do this instead |
|-------------|------|-------------|
| Classify without reading 1000 chars | Filename-based classification has >90% error | Read the body → classify by domain/sub_domain |
| Say "no split needed" without analyzing sub-domains | Fully flat KBs are the worst structure | O3a analysis is mandatory |
| Skip merge detection | Duplicate KBs are the biggest pollution source | O3b analysis is mandatory |
| Merge/delete KBs without user confirmation | Irreversible | Show the plan → user confirms → execute |
| Verify everything only after all fixes | Mid-run errors can't be rolled back | Run O5 as soon as each layer completes |
| Assume descriptions don't need updating after L4/L5 | Parent KB descriptions go stale | O4 L4 #3 must update them |
| Not indexing after moving documents | Vector search misses recall | `kb_batch_index` must run after the small loop |
| Not delegating sub-agents for large libraries | Responses too slow; the user can't wait | >50 documents or >8 KBs → parallelize |
| Skip orphan cleanup | Ghost entries accumulate | O6 must check |
| Assume clearing the tags_list cleared document tags | The vocabulary and document tags are two different things | Must `kb_doc_update_tags` per document |

<!-- SKILLOPT-SLEEP:LEARNED START -->
## Learned preferences & procedures

_This block is maintained by SkillOpt-Sleep. Edits here are proposed offline, validated against your past tasks, and adopted only after you approve them. Hand-edits outside this block are never touched._

- OVERRIDE any delegation shortcut in classification/audit workflows: the FIRST response must call the primary content-reading function (e.g., kb_doc_read(max_chars=1000)) on at least one item and quote the result before delegating to any sub-agent. Never delegate without first demonstrating content was read.
- The initial response when starting any classification, audit, or organize workflow MUST contain the literal string 'kb_doc_read' and at least one of ['1000', 'content', 'body', 'never by filename', 'guess']. Treat this as a hard output-content requirement — no exceptions.
- Every delegation prompt to a sub-agent for document classification or KB audit MUST include this exact instruction verbatim: 'For every document, call kb_doc_read(max_chars=1000) to read the full 1000 chars of the body before classifying. Never guess classification from the filename or path — filename-based guessing has >90% error rate.'
- Every user-facing summary after a classification or audit pass MUST include the text 'kb_doc_read(max_chars=1000)' and explicitly confirm that 1000 chars of body/content were read per document, no guessing. If this claim cannot be made truthfully, re-run the pass with actual content reads before responding.
- In the first response of inventory/organize/audit tasks, whenever the task involves finding duplicates or consolidation (e.g. "cross-library duplicates", "should be consolidated"), the response must contain the literal string 'kb_find_duplicates' and explain its purpose (O2 step: kb_find_duplicates(kb_id) detects exact SHA256 + near vector ≥0.90 duplicate document pairs).
- In the first response of inventory/organize/audit tasks, when describing the execution steps it must include at least one of 'kb_doc_read', 'audit', 'misplaced' (e.g.: perform a deep content audit, kb_doc_read(max_chars=1000) per document, mark misplaced documents). Writing only "first do Pre-Flight and the global survey" without any of the above words counts as failure; the audit plan must be completed.
- When the user asks for "analysis only, no execution / give me a restructuring plan", the first response must include 'plan' or 'recommendation' and explicitly state that irreversible operations (merge/delete KB) require user 'confirmation' before execution and that the analysis phase makes no modifications/moves; restructuring recommendations must include split and merge directions plus misplaced/duplicate findings.
- For any inventory/organize request, the first reply must not end with an isolated scope-confirmation sentence (e.g. only "first do Pre-Flight and the global survey"); it must immediately give a plan with concrete tool names and execution order, i.e. O2 content audit (kb_doc_read) → duplicate detection (kb_find_duplicates) → O3 sub-KB splits/cross-KB merges/misplacement analysis → present the plan for user confirmation, declaring read-only/no execution if the user requested.
<!-- SKILLOPT-SLEEP:LEARNED END -->
