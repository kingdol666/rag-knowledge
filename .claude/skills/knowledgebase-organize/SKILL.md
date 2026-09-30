---
name: knowledgebase-organize
description: "Full collection restructuring engine. O1→O8 workflow (plus O5b three-way consistency): hierarchical discovery (sub-KB split detection + cross-KB merge analysis), deep content audit (1000+ chars per doc), tiered fix execution, sub-KB auto-creation, cross-KB merge, parent restructuring, vector index + graph rebuild, three-way consistency, hygiene cleanup. No document splitting. Triggered by: 整理, 清洗, 重组, 盘点, 全面梳理, organize, restructure, cleanup, reorganize, 清洗知识库, 整理知识库, 大扫除, 归并, 合并, 拆分, 细分, 分层, 归档, 归类."
---
# Knowledge Organize — Whole-Library Restructuring Engine

## Execution model · Pre-Flight · Architecture (mandatory first step)
**Executor: Archival agent**, delegated via `task` — delegation template + three-role execution model in [execution-model.md](../knowledgebase/references/execution-model.md). **Pre-Flight**: no work before it passes — `kb_project_status` one-probe double-check → branch handling → smoke test, per [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md). **Mental model**: read [kb-architecture.md](../knowledgebase/references/kb-architecture.md) (5-layer model + consistency invariants) before operating; MCP-first (no terminal/HTTP bypass) per [skill-trigger-contract.md](../knowledgebase/references/skill-trigger-contract.md) Rule 5. This skill depends heavily on Neo4j (L7 index + graph rebuild), so `kb_project_start` must include `neo4j=true`. Sub-KB split/merge thresholds are authoritative in [sub-kb-creation.md](../knowledgebase-ingest/references/sub-kb-creation.md) — shared with Ingest A8 (≥6 documents to check, ≥8 to auto-split) to avoid inconsistency.

## Related skills
Ingest `skill://knowledgebase-ingest` · Manage `skill://knowledgebase-manage` · Verify `skill://knowledgebase-verify` · Batch `skill://knowledgebase-batch` · Experience linkage `skill://knowledgebase-experience`.

## Sequential workflow (O1→O8)
1. **O1 global survey** — kb_list + kb_tags_list + fs_get_tree → whole-library topology map.
2. **O2 deep audit** — kb_doc_read(1000 chars) per document → mark description/tag/domain quality; **kb_find_duplicates(kb_id)** detects duplicate document pairs (exact SHA256 + near vector ≥0.90).
3. **O3 hierarchy analysis** — sub-KB split detection + cross-KB merge detection + hierarchy analysis.
4. **O4 fix execution** — L1 descriptions → L2 tags → L3 reclassification → L4 splits → L5 merges → L6 hierarchy → L7 indexes.
5. **O5 per-layer verification** — after each layer's fixes, immediately run O5 + O5b three-level consistency.
6. **O6 experience linkage** — experience_check_stale + mark experiences needing review.
7. **O7 compliance strategy** — filter the fix scope per the user-specified strategy.
8. **O8 final report** — before/after comparison + fix statistics + compliance score.

## Mental framework — five things to settle before organizing
1. **What scope did the user specify?** "organize everything" = whole library; "organize thermal engineering" = one KB; not said → ask first.
2. **How many sub-domains does this KB have?** ≥2 sub-domains and ≥6 documents → consider splitting.
3. **Any duplicate/overlapping KBs?** content overlap ≥60% → consider merging.
4. **Fix priorities?** descriptions (L1) > tags (L2) > attribution (L3) > split (L4) > merge (L5) > hierarchy (L6) > index (L7).
5. **Where must content be read?** 1000 chars cannot be skipped — changing classification without reading content is guessing, forbidden.

## Rules
1. **Read 1000 chars of every document** — `kb_doc_read(max_chars=1000)`; never substitute filenames/paths (filename-based classification has >90% error).
2. **Verify fixes batch by batch** — execute L1→L7 in order; verify as soon as each layer completes (piled-up verification can't undo mid-run errors).
3. **Split decisions cannot be skipped** — every KB at or above `SUB_KB_CHECK_THRESHOLD` (≥6 documents; authoritative table in [sub-kb-creation.md](../knowledgebase-ingest/references/sub-kb-creation.md)) must be checked for splitting (fully flat KBs are the worst structure).
4. **Merge decisions cannot be skipped** — every domain-overlapping KB pair must be evaluated (duplicate KBs are the biggest pollution source).
5. **File splitting is forbidden** — documents are complete units; no truncation/summarization/splitting.
6. **MCP first** — all operations go through MCP tools; terminal/HTTP bypass is forbidden.
7. **Confirm before executing** — any irreversible operation (delete/merge KB) runs only after user confirmation.
8. **Single-document KBs must be consolidated** — a KB with only 1 document cannot exist independently; marked "pending consolidation" in O3.
9. **Three-axis weight adaptation** — when the tag vocabulary is empty, entity_sim rises to 0.55 and domain_sim to 0.45 (absent tag data is untrustworthy).
10. **O3 auto-generates the combo** — after O3a+O3b, generate the combined merge+split plan; never make the user assemble it manually.

## Freedom map
- **Execute (medium)** — L1 description fixes / L2 tag hygiene / L7 index rebuild: batch per the rules; verify layer by layer.
- **Judgment (high)** — L3 reclassification / L4 split / L5 merge / L6 hierarchy decisions: requires domain judgment from 1000 chars of content; the decision tree guides but is not mechanical.
- **Mandatory (low)** — O5 / O5b verification as soon as each layer completes, never piled up (consistency checks cannot be skipped); L4/L5/L6 execution shows the plan and waits for user confirmation before executing (irreversible).

## O1 — Global Survey
```text
kb_list()                                       # all KBs (UUID + description + doc count)
kb_tags_list()                                  # global tag vocabulary
fs_get_tree(include_files=False, max_depth=0)   # KB hierarchy structure
# → whole-library topology: parent KBs, sub-KBs, isolated KBs, empty KBs, test KBs
```

## O2 — Deep Content Audit (full-coverage O2-M manifest)
Before auditing, create one manifest line for every document (path → pending) and check lines off one by one; sub-agent results must be merged back into the same single manifest by the parent agent. At O2 end assert `audited_count == total_count` — any missing line = O2 incomplete, entering O3 forbidden (the legitimacy of organizing comes from every document actually being read; parallel division only changes who reads, never that every line gets a verdict). Part files (`xxx (part k of N).md`) group by stem into one logical unit: read part 1's 1000 chars to judge attribution for the whole, and L3 migration must move the whole group together (moving part 1 alone is an incident). >8 KBs or >50 documents → delegate parallel audits via `task(tasks=[{"agent":"archival","name":"KB-Audit","task":"audit KB docs...","effort":"med"}])`, ~4 KBs per group (≈1s per document; 100 documents ≈ 2 minutes). Tags are auto-generated during the O2 audit; L2 only cleans, normalizes, and batch-writes back. For every non-empty KB, read and mark each document:

```text
for each doc in KB:
    content = kb_doc_read(max_chars=1000)
    mark:
      desc_quality:   [OK | MISSING | FILENAME | GENERIC | MISMATCH]
      tag_quality:    [OK | EMPTY | GENERIC | BLOCKLIST | COUNT_LOW]
      domain:         <sub-domain inferred from content>
      kb_alignment:   [MATCH | MISMATCH]
      suggested_tags: <[2-5 content-derived tags]>   ← generated here, not deferred to L2
      best_target:    <for MISMATCH: argmax-KB from the L3-M scan>
```

## O3 — Hierarchy Topology Analysis
**O3a sub-KB split detection.** For every KB with document count ≥ `SUB_KB_CHECK_THRESHOLD` (≥6 documents), analyze sub-domain distribution using the [three-axis similarity protocol](../knowledgebase-ingest/references/sub-kb-creation.md#multi-dimensional-similarity-scoring):
scan KB → read 1000 chars of each document → extract key entities → group (same entity_sim ≥ 0.4 groups together) → `{kb_id, kb_name, doc_count, sub_domains: {sub_domain: [doc_paths]}}`
**Split condition**: ≥2 sub-domains (inter-group similarity ≤ 0.25), each with ≥2 documents.

**O3b cross-KB merge detection.** For all KB pairs (especially similarly named ones), compute the three-axis composite similarity:
Axis 1 (0.3) tag_similarity = |tags(a) ∩ tags(b)| / |tags(a) ∪ tags(b)|
Axis 2 (0.4) entity_similarity = |entities(a) ∩ entities(b)| / |entities(a) ∪ entities(b)|
Axis 3 (0.3) domain_similarity = three-level classification (l1/l2/l3) comparison · total = 0.3*tag + 0.4*entity + 0.3*domain
Full decision matrix: [sub-kb-creation.md § Decision Matrix](../knowledgebase-ingest/references/sub-kb-creation.md#decision-matrix).

**O3c hierarchy analysis.** flat → create parent KBs and group sub-KBs; partial → fill in missing parents; structured → verify the tiering is reasonable. Output `topology_report` — each KB's split/merge/hierarchy recommendations. Show the results to the user for confirmation; irreversible operations (merge/delete) require user approval.

## O4 — Fix Execution (in layer order; run O5 after each layer)
Detailed execution pseudocode, dialogue templates, and parameters: [execution-details.md](references/execution-details.md).

| Layer | Operation | Risk | Key commands |
|------|------|------|------|
| **L0** dedup cleanup | delete exact/near duplicate documents | needs verification | kb_find_duplicates → kb_doc_delete (keep the more complete version; merge tag/description differences) |
| **L1** description fixes | content-based rewriting (four elements) | zero | kb_doc_update_meta / kb_update |
| **L2** tag hygiene | T1 blocklist removal + T2 normalization + T3 counts | zero | kb_doc_update_tags (blocklist in [tag-quality-rules.md](../knowledgebase-ingest/references/tag-quality-rules.md)) |
| **L3** reclassification | move misplaced docs to the argmax-fit KB | needs verification | kb_doc_move + kb_index_document |
| **L4** sub-KB split | KBs detected as splittable by O3a | **user confirmation** | kb_create(parent_id) + kb_doc_move + kb_batch_index(force=true) |
| **L5** cross-KB merge | KB pairs detected as mergeable by O3b | **user confirmation** | kb_doc_move → kb_delete(source) + kb_graph_build(force=true) |
| **L6** hierarchy restructure | create/rename/delete parent KBs | **user confirmation** | kb_create / kb_update / kb_delete |
| **L7** index + graph | vector coverage + graph rebuild | infrastructure | kb_batch_index(force=true) + kb_graph_build(force=true) |

**L4/L5/L6 must show the plan and wait for user confirmation before executing** (irreversible operations).

### L3-M — Best-Target KB Scan + Whole-Group Migration
Never move a misplaced doc to "a KB that looks related" — for every MISMATCH document, scan every other KB's fit (sub_domain + methods + entities vs the KB's description), take the argmax, and record the runner-up for user review; part files migrate as one stem group. **Closeout sequence** — kb_doc_move's reindexing is fire-and-forget and batch_index(force=true) only re-indexes the listed documents without clearing source-KB orphan chunks (measured: after a move the source KB kept 3 orphan chunks and vector search kept hitting the migrated doc at 0.544): `kb_doc_move` → `kb_index_document` (new KB) → source KB `kb_reindex(force=true)` → new KB `kb_reindex(force=true)` (or batch_index) → `kb_graph_build(force=true)`.
**Post-migration probes** (the negative probe is the only reliable way to detect orphan chunks): `kb_search_vector(query=problem dimension, kb_id=new KB)` must recall the document, and the same query on the original KB must no longer return it. Upgrade descriptions to the D8 multi-dimensional standard ([description-guide.md](../knowledgebase-ingest/references/description-guide.md)) so retrieval-by-description still hits in the new KB after migration. After kb_doc_move, a stale `vector_index` (old collection/chunk prefix) and a missing graph_index are the expected intermediate state — O5b catches it and closeout clears it.
Parameter naming: `kb_list` returns `kbId`, while kb_get_documents/kb_doc_read/kb_doc_update_*/kb_batch_index/kb_graph_build require `kb_id`; `kb_doc_move(doc_path, target_kb_id)` has no source-KB parameter — print one entry to confirm key names before the first call.

### O5-C — Retrieval Regression Probes (mandatory after L3/L4/L5/L6/L7)
For every affected KB: generate probes from the description problem-dimensions of 2-3 of its documents; `kb_search_vector(query=probe, kb_id=<that KB>, top_k=3)` must return the expected document (results are chunk-level with no document-level dedup — judge hits by doc_path); plus the negative probe above (the migrated-out document's old query must no longer hit the original KB). Any probe miss → the index/graph rebuild is incomplete or a document was lost (most common: source-KB orphan chunks — close out with `kb_reindex(kb_id, force=true)`); stop further layers and fall back to the O5b consistency check. This is the executable definition of "retrieval does not degrade after organizing".

## O5 — Per-Layer Verification + O5b Three-Level Consistency
Verify immediately after each layer's fixes (verification method table: [execution-details.md](references/execution-details.md) §O5). **O5b (mandatory)**: after L3/L4/L5/L6, validate three-layer metadata (disk ↔ .tree-fs.json ↔ .knowledge-base.yml) + UUID sync + 20% content sampling; fix rules in §O5b.

## O6 — Experience Linkage
For each KB with structural changes (L4/L5/L6): `experience_check_stale(kb_id)`; report each stale experience ("the related documents of N experiences were migrated; review recommended").

## O7 — Custom Compliance Strategy
Everything runs by default; a user-specified strategy (strict_descriptions/clean_tags/align_docs/split_kbs/merge_kbs/hierarchy/full_index) filters the fix scope — e.g. "fix only descriptions and tags" → L1+L2+L7. Strategy table: [execution-details.md](references/execution-details.md) §O7.

## O8 — Final Report
Before/after comparison + audit coverage (O2-M: audited/total, must be 100%) + per-layer fix counts (L1-L7) + O5-C regression results (probes passed/total) + compliance score (C1 descriptions/C2 tags/C3 alignment/C4 vectors/C5 graph/C6 three-way consistency) + experiences pending review.

## NEVER
- Classify without reading 1000 chars — filename-based classification has >90% error; read the body and classify by domain/sub_domain.
- Say "no split needed" without O3a sub-domain analysis, or skip O3b merge detection — flat/duplicate KBs are the biggest pollution.
- Merge/delete KBs without user confirmation — irreversible; show the plan → user confirms → execute.
- Verify only after all fixes — mid-run errors can't be rolled back; run O5 as soon as each layer completes.
- Assume descriptions need no update after L4/L5 — parent-KB descriptions go stale; O4 L4 #3 must update them.
- Move documents without indexing — vector search silently misses; kb_batch_index must run after the small loop.
- Skip sub-agent delegation for large libraries — responses get too slow for the user to wait; >50 documents or >8 KBs → parallelize.
- Skip orphan cleanup — ghost entries accumulate; O6 must check.
- Assume clearing kb_tags_list cleared document tags — the vocabulary and document tags are two different things; kb_doc_update_tags per document.
- Audit by sampling and call it done — organizing is legitimate only because every document was actually read; check off the O2-M manifest until audited==total.
- Move a misplaced doc to "a KB that looks related" — a wrong attribution is stealthier than a wrong location; L3-M argmax + runner-up.
- Move only part 1 of a multi-part document — the same paper ends up split across KBs; migrate the whole stem group and run dual-KB probes.
- Trust that moves didn't break retrieval — stale indexes/graphs silently degrade retrieval; O5-C probes per KB, stop on any miss.

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
